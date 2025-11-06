TSP-POC — Backend (FastAPI) + Frontend (React + Leaflet)

Aplicación prueba de concepto para cargar una red vial (GeoJSON), visualizarla en un mapa web y descargar la red en GeoJSON/WKT.
Backend en FastAPI (Python) y frontend en React + Vite + Leaflet.

🧱 Estructura del proyecto
tsp-poc/
├─ backend/
│  └─ main.py
├─ frontend/
│  ├─ src/
│  │  ├─ main.tsx
│  │  └─ MapApp.tsx
│  └─ package.json
├─ samples/
│  └─ red_ejemplo.geojson
├─ .gitignore
└─ README.md

✅ Requisitos

WSL (Ubuntu) en Windows (recomendado) o Linux/Mac.

Python 3.10+ (ideal 3.12).

Node.js 20+ (en WSL, usa nvm).

Instalar Node en WSL con nvm (opcional pero recomendado)
# en Ubuntu (WSL)
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts
node -v && npm -v

🚀 Backend — FastAPI
1) Crear/activar entorno virtual e instalar dependencias
cd ~/proyectos/tsp-poc
python -m venv .venv
source .venv/bin/activate

# dependencias mínimas
python -m pip install --upgrade pip
pip install fastapi uvicorn[standard] shapely python-multipart geojson pydantic[dotenv] pytest


(opcional) guarda dependencias:

pip freeze > requirements.txt

2) Ejecutar el backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000


Docs (Swagger): http://127.0.0.1:8000/docs

OpenAPI JSON: http://127.0.0.1:8000/openapi.json

3) Endpoints clave

POST /upload/network — subir GeoJSON FeatureCollection de LineString (multipart/form-data).

GET /network.geojson — devuelve la red cargada en GeoJSON.

GET /network.wkt — devuelve la red cargada en WKT (MultiLineString).

4) Probar por terminal (curl)
# (crea un sample si no tienes)
mkdir -p ~/proyectos/tsp-poc/samples
cat > ~/proyectos/tsp-poc/samples/red_ejemplo.geojson <<'JSON'
{
  "type": "FeatureCollection",
  "features": [
    { "type": "Feature", "properties": { "edge_id": 1 },
      "geometry": { "type": "LineString", "coordinates": [[-74.1000,4.6500],[-74.0950,4.6510],[-74.0900,4.6540]] } },
    { "type": "Feature", "properties": { "edge_id": 2 },
      "geometry": { "type": "LineString", "coordinates": [[-74.0950,4.6480],[-74.0900,4.6510],[-74.0850,4.6520]] } }
  ]
}
JSON

# subir red
curl -s -X POST http://127.0.0.1:8000/upload/network \
  -F "file=@/home/$USER/proyectos/tsp-poc/samples/red_ejemplo.geojson"

# ver/descargar
curl -s http://127.0.0.1:8000/network.geojson | head
curl -s http://127.0.0.1:8000/network.wkt


Nota: El backend valida por contenido, no por Content-Type. Soporta UTF-8 y archivos con BOM.

🗺️ Frontend — React + Vite + Leaflet

Proyecto creado con Vite (React + TS), React 19, react-leaflet 5 y Leaflet 1.9.

1) Instalar dependencias (en frontend/)
cd ~/proyectos/tsp-poc/frontend

# asegúrate de estar en la carpeta frontend
rm -rf node_modules package-lock.json 2>/dev/null || true

npm i -E react@19.2.0 react-dom@19.2.0
npm i -E react-leaflet@5 leaflet@1.9.4 file-saver
npm i -D @types/leaflet @types/geojson @types/file-saver

2) Ajustes de código (importante)

src/main.tsx — importa el CSS de Leaflet en la primera línea:

import "leaflet/dist/leaflet.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);


Creacion de src/MapApp.tsx — componente principal

src/App.tsx

import MapApp from "./MapApp";
export default function App() { return <MapApp />; }

3) Ejecutar el frontend
npm run dev


Abre: http://127.0.0.1:5173

El backend debe estar corriendo en http://127.0.0.1:8000
 (CORS ya permite localhost:5173 y 127.0.0.1:5173).

🧪 Flujo de uso

Sube un archivo .geojson (FeatureCollection de LineString) desde el panel lateral.

Pulsa “Ver red” → se dibuja la red y auto-encuadra el mapa.

Usa “Descargar GeoJSON” o “Descargar WKT” para exportar.

Puedes usar samples/red_ejemplo.geojson del bloque de curl de arriba.

🧯 Troubleshooting

VS Code no toma WSL: abre el proyecto con code . desde Ubuntu. Abajo a la izquierda debe decir WSL: Ubuntu.

El front no carga el mapa: confirma que importaste leaflet.css en src/main.tsx.

CORS: si usas otro puerto/origen en front, añádelo en el CORSMiddleware del backend.

“localhost” falla: usa http://127.0.0.1 o arranca Uvicorn con IPv6 --host ::.

Tipos TS de Leaflet: instala @types/leaflet @types/geojson @types/file-saver y usa import * as L from "leaflet";.

📦 .gitignore recomendado
# Python
.venv/
__pycache__/
*.pyc

# Frontend
frontend/node_modules/
frontend/dist/

# SO/Editor
.DS_Store
.vscode/

💡 Comandos rápidos (TL;DR)
# Backend
cd ~/proyectos/tsp-poc
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn[standard] shapely python-multipart geojson pydantic[dotenv] pytest
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd ~/proyectos/tsp-poc/frontend
npm i
npm run dev
