# backend/main.py
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from shapely.geometry import (
    shape,
    LineString,
    MultiLineString,
    mapping,
    Point,
    GeometryCollection,
)
from shapely.ops import split
import json
import csv
from io import StringIO

import networkx as nx  # <- para shortest path sobre la red

# --- TSP (3.3) ---
from tsp_algorithms import (
    geo_distance,                     # para pesar aristas
    brute_force_tsp_matrix,
    nearest_neighbor_tsp_matrix,
    simulated_annealing_tsp_matrix,
)

app = FastAPI(title="TSP-POC Backend", version="0.3.0")

# Ajusta si tu front corre en otro puerto/origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenamiento en memoria (POC)
EDGES: List[LineString] = []        # red vial cargada (lista de aristas)
POINTS_SNAPPED: List[dict] = []     # puntos integrados (snapped a la red)


@app.get("/health")
def health():
    return {"status": "ok"}


# =====================================================
# 3.1 Road Network Load: carga de la red vial
# =====================================================

@app.post("/upload/network")
async def upload_network(file: UploadFile):
    """
    Sube un GeoJSON (FeatureCollection de LineString).
    Se valida por contenido (JSON) y no por content-type del navegador.

    Requerimiento 3.1:
      - Cargar red vial desde archivo local
      - Representar la red internamente como aristas (LineString)
    """
    raw_bytes = await file.read()

    # Intentamos parsear JSON (independiente del content-type)
    try:
        gj = json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(400, "El archivo no es JSON válido (¿GeoJSON?).")

    if gj.get("type") != "FeatureCollection":
        raise HTTPException(400, "Se espera FeatureCollection.")

    feats = gj.get("features", [])
    if not feats:
        raise HTTPException(400, "FeatureCollection sin features.")

    edges: List[LineString] = []
    for f in feats:
        geom = f.get("geometry")
        if not geom:
            raise HTTPException(400, "Feature sin geometry.")
        g = shape(geom)
        if not isinstance(g, LineString) or g.is_empty or len(g.coords) < 2:
            raise HTTPException(400, "Cada feature debe ser LineString válida.")
        edges.append(g)

    global EDGES, POINTS_SNAPPED
    EDGES = edges
    POINTS_SNAPPED = []  # si suben nueva red, reseteamos puntos integrados

    return {"ok": True, "lines": len(EDGES)}


@app.get("/network.geojson")
async def get_network_geojson():
    """
    Devuelve la red cargada como FeatureCollection de LineString.

    Requerimiento especial: exportar la red en formato GIS estándar (GeoJSON).
    """
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    features = [
        {"type": "Feature", "geometry": mapping(ls), "properties": {}}
        for ls in EDGES
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/network.wkt")
async def get_network_wkt():
    """
    Devuelve la red cargada como MULTILINESTRING WKT.

    Requerimiento especial: exportar la red en WKT.
    """
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    mls = MultiLineString([list(ls.coords) for ls in EDGES])
    return mls.wkt


# =====================================================
# 3.2 Pointset Load: integración de puntos en la red
# =====================================================

@app.post("/upload/points")
async def upload_points(file: UploadFile):
    """
    Sube un CSV con columnas: id, lat, lon (nombres flexibles).
      - id: identificador del punto
      - lat: latitud
      - lon: longitud

    Para cada punto:
      - Se calcula la distancia mínima (perpendicular) a cada arista (LineString).
      - Se toma la arista más cercana.
      - Se proyecta el punto sobre esa arista.
      - Se parte la arista original en segmentos nuevos que incluyen el punto.
        *Si el punto cae en un extremo de la arista y no se parte, igualmente
         se registra el punto sin modificar la red*.
    """
    global EDGES, POINTS_SNAPPED

    if not EDGES:
        raise HTTPException(400, "Primero debe cargarse una red (/upload/network).")

    try:
        raw_bytes = await file.read()
        try:
            text = raw_bytes.decode("utf-8")
        except Exception:
            raise HTTPException(400, "No se pudo decodificar el archivo como UTF-8.")

        # Parseamos CSV
        f = StringIO(text)
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise HTTPException(400, "El CSV no tiene encabezados.")

        # Intentamos mapear nombres de columnas flexibles:
        # id / ID / Id, lat / latitude, lon / lng / longitude
        field_id = None
        field_lat = None
        field_lon = None

        cols_lower = [c.lower() for c in reader.fieldnames]
        for original, lower in zip(reader.fieldnames, cols_lower):
            if lower in ("id", "point_id"):
                field_id = original
            elif lower in ("lat", "latitude"):
                field_lat = original
            elif lower in ("lon", "lng", "longitude"):
                field_lon = original

        if not (field_id and field_lat and field_lon):
            raise HTTPException(
                400,
                "El CSV debe tener columnas para id, lat, lon (por ejemplo: id,lat,lon).",
            )

        points_added = 0

        for row in reader:
            pid = row[field_id]
            try:
                lat = float(row[field_lat])
                lon = float(row[field_lon])
            except Exception:
                raise HTTPException(
                    400,
                    (
                        f"Lat/Lon inválidos para el punto con id={row.get(field_id)} "
                        f"(lat={row.get(field_lat)}, lon={row.get(field_lon)})."
                    ),
                )

            # En coordenadas geoespaciales usuales, GeoJSON usa [lon, lat]
            p = Point(lon, lat)

            # Buscar la arista más cercana (distancia mínima punto-línea)
            best_idx = None
            best_dist = None
            best_proj_point = None

            for idx, edge in enumerate(EDGES):
                d = edge.distance(p)
                if best_dist is None or d < best_dist:
                    best_dist = d
                    # proyectamos el punto sobre la línea
                    proj_point = edge.interpolate(edge.project(p))
                    best_idx = idx
                    best_proj_point = proj_point

            if best_idx is None or best_proj_point is None:
                # No debería ocurrir si EDGES no está vacío, pero por seguridad:
                continue

            edge_to_split = EDGES[best_idx]

            # Preparamos la info del punto integrado (da igual si luego se parte o no)
            snapped_info = {
                "id": pid,
                "original": {"type": "Point", "coordinates": [lon, lat]},
                "snapped": mapping(best_proj_point),
                "edge_index": best_idx,
                "distance_to_edge": best_dist,
            }

            # Intentamos partir la arista elegida usando el punto proyectado
            parts_raw = split(edge_to_split, best_proj_point)

            # Shapely 2: GeometryCollection/MultiLineString no son iterables directos
            if isinstance(parts_raw, (GeometryCollection, MultiLineString)):
                geoms_iter = parts_raw.geoms
            else:
                geoms_iter = [parts_raw]

            # Filtramos solo LineString válidas
            parts: List[LineString] = []
            for geom in geoms_iter:
                if isinstance(geom, LineString) and len(geom.coords) >= 2:
                    parts.append(geom)

            if len(parts) < 2:
                # No se partió la arista (por ejemplo, el punto coincide con un extremo).
                # En este caso: NO modificamos EDGES, pero SÍ registramos el punto.
                POINTS_SNAPPED.append(snapped_info)
                points_added += 1
                continue

            # Caso normal: actualizamos la lista de aristas
            new_edges = list(EDGES)
            # Removemos la arista original
            del new_edges[best_idx]
            # Insertamos las nuevas aristas en la misma posición
            for geom in reversed(parts):
                new_edges.insert(best_idx, geom)

            EDGES = new_edges

            # Guardamos el punto integrado para que el front lo pueda dibujar
            POINTS_SNAPPED.append(snapped_info)
            points_added += 1

        if points_added == 0:
            raise HTTPException(400, "No se integró ningún punto (¿CSV vacío?).")

        return {
            "ok": True,
            "points_integrated": points_added,
            "total_points": len(POINTS_SNAPPED),
            "edges_after_split": len(EDGES),
        }

    except HTTPException:
        # Re-lanzamos errores que ya controlamos
        raise
    except Exception as e:
        # Cualquier error inesperado se reporta como 500 con detalle
        raise HTTPException(500, f"Error inesperado procesando puntos: {e}")


@app.get("/points.geojson")
async def get_points_geojson():
    """
    Devuelve los puntos integrados a la red como GeoJSON (usamos la posición 'snapped').
    El frontend puede pintarlos con otro estilo (forma/color) para cumplir el requerimiento.

    Requerimiento 3.2: mostrar nodos integrados con estilo diferente.
    """
    if not POINTS_SNAPPED:
        raise HTTPException(404, "No hay puntos integrados.")

    features = []
    for p in POINTS_SNAPPED:
        feat = {
            "type": "Feature",
            "geometry": p["snapped"],
            "properties": {
                "id": p["id"],
                "distance_to_edge": p["distance_to_edge"],
            },
        }
        features.append(feat)

    return {"type": "FeatureCollection", "features": features}


# =====================================================
# Helpers para TSP sobre la red
# =====================================================

def get_snapped_points_coordinates():
    """
    Devuelve la lista de coordenadas (lon, lat) de los puntos integrados.
    """
    if not POINTS_SNAPPED:
        raise HTTPException(status_code=400, detail="No hay puntos integrados.")
    coords = []
    for p in POINTS_SNAPPED:
        lon, lat = p["snapped"]["coordinates"]
        coords.append((lon, lat))
    if len(coords) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 puntos integrados para evaluar TSP.",
        )
    return coords


def build_network_graph() -> nx.Graph:
    """
    Construye un grafo no dirigido a partir de EDGES.
    Cada vértice es una coordenada (lon, lat).
    Cada arista conecta dos coordenadas consecutivas de un LineString,
    con peso igual a la distancia geográfica (Haversine).
    """
    if not EDGES:
        raise HTTPException(status_code=400, detail="No hay red cargada.")

    G = nx.Graph()

    for ls in EDGES:
        coords = list(ls.coords)
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]

            u = (lon1, lat1)
            v = (lon2, lat2)

            d = geo_distance(Point(lon1, lat1), Point(lon2, lat2))

            if G.has_edge(u, v):
                # Por si el GeoJSON tiene segmentos duplicados, guardamos el mínimo
                if d < G[u][v]["weight"]:
                    G[u][v]["weight"] = d
            else:
                G.add_edge(u, v, weight=d)

    return G


def compute_distance_and_paths():
    """
    Construye:
      - dist_matrix[i][j]: distancia más corta en la red entre puntos i y j.
      - path_matrix[i][j]: lista de coordenadas (lon, lat) que siguen la red.

    Usa Dijkstra sobre el grafo de la red.
    """
    G = build_network_graph()
    points_coords = get_snapped_points_coordinates()
    n = len(points_coords)

    # Verificar que todos los puntos existan como nodos del grafo
    for idx, coord in enumerate(points_coords):
        if coord not in G.nodes:
            raise HTTPException(
                status_code=500,
                detail=f"El punto integrado {idx} ({coord}) no se encuentra como nodo de la red.",
            )

    # Inicializamos matrices
    dist_matrix: List[List[float]] = [[0.0] * n for _ in range(n)]
    path_matrix: List[List[List[tuple]]] = [[[] for _ in range(n)] for _ in range(n)]

    for i in range(n):
        source = points_coords[i]
        # Single-source Dijkstra desde cada punto
        lengths, paths = nx.single_source_dijkstra(G, source, weight="weight")

        for j in range(n):
            target = points_coords[j]
            if i == j:
                dist_matrix[i][j] = 0.0
                path_matrix[i][j] = [source]
            else:
                if target not in lengths or target not in paths:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No hay camino en la red entre los puntos {i} y {j}.",
                    )
                dist_matrix[i][j] = float(lengths[target])
                path_matrix[i][j] = paths[target]

    return dist_matrix, path_matrix


def route_nodes_to_geojson_feature(route: List[int], path_matrix: List[List[List[tuple]]]):
    """
    Convierte una ruta de índices en un Feature GeoJSON tipo LineString
    concatenando los caminos más cortos entre cada par consecutivo
    sobre la red (sin repetir nodos intermedios).
    """
    if not route:
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": []},
            "properties": {},
        }

    coords: List[tuple] = []

    for k in range(len(route) - 1):
        i = route[k]
        j = route[k + 1]
        segment = path_matrix[i][j]  # lista de (lon, lat)

        if not segment:
            continue

        if k == 0:
            coords.extend(segment)
        else:
            # evitamos repetir el primer nodo del segmento (ya está como último en coords)
            coords.extend(segment[1:])

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {},
    }


# =====================================================
# 3.3 Algorithms Evaluation (TSP) sobre la red
# =====================================================

@app.get("/tsp/evaluate")
def evaluate_tsp():
    """
    Caso de uso 3.3:
      - Construye un grafo de la red vial (EDGES).
      - Calcula la distancia más corta en la red entre cada par de puntos integrados.
      - Ejecuta los tres algoritmos TSP (fuerza bruta, vecino más cercano,
        simulated annealing) usando esa matriz de distancias.
      - Devuelve rutas y métricas.
      - Las geometrías de las rutas siguen la red vial (no líneas rectas).

    Esto cumple la exigencia de trabajar sobre "shortest path over a network".
    """
    # 1) Matrices de distancias y caminos sobre la red
    dist_matrix, path_matrix = compute_distance_and_paths()

    # 2) Ejecutar algoritmos TSP sobre la matriz
    bf_route, bf_dist, bf_time = brute_force_tsp_matrix(dist_matrix)
    nn_route, nn_dist, nn_time = nearest_neighbor_tsp_matrix(dist_matrix)
    sa_route, sa_dist, sa_time = simulated_annealing_tsp_matrix(dist_matrix)

    # 3) Convertir rutas a GeoJSON siguiendo la red
    bf_geo = route_nodes_to_geojson_feature(bf_route, path_matrix)
    nn_geo = route_nodes_to_geojson_feature(nn_route, path_matrix)
    sa_geo = route_nodes_to_geojson_feature(sa_route, path_matrix)

    return {
        "bruteforce": {
            "route": bf_route,
            "distance": bf_dist,
            "time": bf_time,
            "geojson": bf_geo,
        },
        "nearest_neighbor": {
            "route": nn_route,
            "distance": nn_dist,
            "time": nn_time,
            "geojson": nn_geo,
        },
        "simulated_annealing": {
            "route": sa_route,
            "distance": sa_dist,
            "time": sa_time,
            "geojson": sa_geo,
        },
    }
