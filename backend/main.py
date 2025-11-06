# backend/main.py
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from shapely.geometry import shape, LineString, MultiLineString, mapping
import json

app = FastAPI(title="TSP-POC Backend", version="0.1.1")

# Si tu front corre en otro origen/puerto, añádelo aquí
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memoria simple para 3.1
EDGES: List[LineString] = []  # aristas cargadas

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload/network")
async def upload_network(file: UploadFile):
    """
    Sube un GeoJSON (FeatureCollection de LineString).
    NOTA: No confiamos en content-type del navegador; validamos por CONTENIDO.
    """
    # 1) Leer bytes del archivo subido (multipart/form-data)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(400, "Archivo vacío.")

    # 2) Decodificar como UTF-8 (acepta BOM si viene del Bloc de notas)
    try:
        txt = raw_bytes.decode("utf-8-sig")
    except Exception:
        raise HTTPException(400, "No se pudo decodificar como UTF-8.")

    # 3) Parsear JSON (independiente de la extensión o content-type)
    try:
        gj = json.loads(txt)
    except Exception:
        raise HTTPException(400, "El archivo no es JSON válido (¿GeoJSON?).")

    # 4) Validar estructura GeoJSON mínima esperada para 3.1
    if gj.get("type") != "FeatureCollection":
        raise HTTPException(400, "Se espera FeatureCollection.")
    feats = gj.get("features", [])
    if not feats:
        raise HTTPException(400, "FeatureCollection sin features.")

    # 5) Convertir cada feature a LineString válida
    edges: List[LineString] = []
    for idx, f in enumerate(feats):
        geom = f.get("geometry")
        if not geom:
            raise HTTPException(400, f"Feature {idx} sin geometry.")
        try:
            g = shape(geom)
        except Exception:
            raise HTTPException(400, f"Geometry inválida en feature {idx}.")
        if not isinstance(g, LineString) or g.is_empty or len(g.coords) < 2:
            raise HTTPException(400, f"Feature {idx}: se requiere LineString válida.")
        edges.append(g)

    # 6) Guardar en memoria
    global EDGES
    EDGES = edges
    return {"ok": True, "lines": len(EDGES)}

@app.get("/network.geojson")
async def get_network_geojson():
    """
    Devuelve la red cargada como GeoJSON FeatureCollection.
    """
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    features = [{"type": "Feature", "geometry": mapping(ls), "properties": {}} for ls in EDGES]
    return {"type": "FeatureCollection", "features": features}

@app.get("/network.wkt")
async def get_network_wkt():
    """
    Devuelve la red cargada como WKT (MultiLineString).
    """
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    mls = MultiLineString([list(ls.coords) for ls in EDGES])
    return mls.wkt
