# backend/Main.py
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

app = FastAPI(title="TSP-POC Backend", version="0.2.0")

# Ajusta si tu front corre en otro puerto/origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EDGES: List[LineString] = []        # almacenamos la red cargada
POINTS_SNAPPED: List[dict] = []     # almacenamos los puntos integrados a la red


@app.get("/health")
def health():
    return {"status": "ok"}


# ----------- 3.1 Network Load: carga de la red ----------- #

@app.post("/upload/network")
async def upload_network(file: UploadFile):
    """
    Sube un GeoJSON (FeatureCollection de LineString).
    Validamos por contenido (JSON) y no por content-type del navegador.
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
    """
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    mls = MultiLineString([list(ls.coords) for ls in EDGES])
    return mls.wkt


# ----------- 3.2 Pointset Load: integración de puntos en la red ----------- #

@app.post("/upload/points")
async def upload_points(file: UploadFile):
    """
    Sube un CSV con columnas: id, lat, lon
    - id: identificador del punto
    - lat: latitud
    - lon: longitud

    Para cada punto:
      - Se calcula la distancia perpendicular a cada arista (LineString).
      - Se toma la arista más cercana.
      - Se proyecta el punto sobre esa arista.
      - Se parte la arista original en segmentos nuevos que incluyen el punto.
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

        # Intentamos mapear nombres de columnas flexibles
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
                    f"Lat/Lon inválidos para el punto con id={row.get(field_id)} "
                    f"(lat={row.get(field_lat)}, lon={row.get(field_lon)}).",
                )

            # En coordenadas geoespaciales usuales, GeoJSON usa [lon, lat]
            p = Point(lon, lat)

            # Buscar la arista más cercana
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

            # Partimos la arista elegida en dos usando el punto proyectado
            edge_to_split = EDGES[best_idx]
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

            # Si no quedaron al menos 2 segmentos, no actualizamos esa arista
            if len(parts) < 2:
                continue

            # Actualizamos la lista de aristas:
            new_edges = list(EDGES)
            # Removemos la arista original
            del new_edges[best_idx]
            # Insertamos las nuevas aristas en la misma posición
            for geom in reversed(parts):
                new_edges.insert(best_idx, geom)

            EDGES = new_edges

            # Guardamos el punto integrado (proyectado) para que el front lo pueda dibujar
            POINTS_SNAPPED.append(
                {
                    "id": pid,
                    "original": {"type": "Point", "coordinates": [lon, lat]},
                    "snapped": mapping(best_proj_point),
                    "edge_index": best_idx,
                    "distance_to_edge": best_dist,
                }
            )
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
