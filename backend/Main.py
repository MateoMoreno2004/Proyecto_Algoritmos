# backend/Main.py
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from shapely.geometry import shape, LineString, MultiLineString, mapping
import json

app = FastAPI(title="TSP-POC Backend", version="0.1.0")

# Ajusta si tu front corre en otro puerto/origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EDGES: List[LineString] = []  # almacenamos la red cargada

@app.get("/health")
def health():
    return {"status": "ok"}

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

    global EDGES
    EDGES = edges
    return {"ok": True, "lines": len(EDGES)}

@app.get("/network.geojson")
async def get_network_geojson():
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    features = [{"type": "Feature", "geometry": mapping(ls), "properties": {}} for ls in EDGES]
    return {"type": "FeatureCollection", "features": features}

@app.get("/network.wkt")
async def get_network_wkt():
    if not EDGES:
        raise HTTPException(404, "No hay red cargada.")
    mls = MultiLineString([list(ls.coords) for ls in EDGES])
    return mls.wkt
