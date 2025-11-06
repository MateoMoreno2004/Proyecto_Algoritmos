TSP-POC · FastAPI + React + Leaflet

POC para cargar una red vial (GeoJSON), visualizarla en mapa y exportarla (GeoJSON/WKT).
Backend en FastAPI · Frontend en React + Vite + Leaflet.

Índice

Requisitos

Estructura del proyecto

Backend (FastAPI)

Instalación

Ejecutar

Endpoints

Probar con curl

Frontend (React + Leaflet)

Instalación

Ejecutar

Datos de ejemplo

Troubleshooting

gitignore recomendado

Comandos rápidos (TL;DR)

Requisitos

WSL (Ubuntu) en Windows (recomendado) o Linux/Mac.

Python 3.10+ (ideal 3.12).

Node.js 20+ (en WSL; se sugiere nvm).

💡 Si usas WSL, abre el proyecto con code . desde Ubuntu (abajo-izquierda debe decir WSL: Ubuntu).

##Estructura del proyecto
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

##Backend (FastAPI)
###Instalación
cd ~/proyectos/tsp-poc
python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install fastapi uvicorn[standard] shapely python-multipart geojson pydantic[dotenv] pytest

###Ejecutar
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

Docs (Swagger): http://127.0.0.1:8000/docs
OpenAPI: http://127.0.0.1:8000/openapi.json

###Endpoints

POST /upload/network → subir FeatureCollection de LineString (multipart).
GET /network.geojson → devuelve red cargada (GeoJSON).
GET /network.wkt → devuelve red cargada (WKT, MultiLineString).

##Probar con curl
###crear carpeta de samples si no existe
mkdir -p ~/proyectos/tsp-poc/samples

###(opcional) pegar aquí tu red_ejemplo.geojson
curl -s -X POST http://127.0.0.1:8000/upload/network \
  -F "file=@/home/$USER/proyectos/tsp-poc/samples/red_ejemplo.geojson"

curl -s http://127.0.0.1:8000/network.geojson | head
curl -s http://127.0.0.1:8000/network.wkt

#Frontend (React + Leaflet)
##Instalación
cd ~/proyectos/tsp-poc/frontend

##React 19 + react-leaflet 5
npm i -E react@19.2.0 react-dom@19.2.0
npm i -E react-leaflet@5 leaflet@1.9.4 file-saver
npm i -D @types/leaflet @types/geojson @types/file-saver

Asegúrarse de importar el CSS de Leaflet al inicio de src/main.tsx:
import "leaflet/dist/leaflet.css";

##Ejecutar
npm run dev

Abre: http://127.0.0.1:5173
El backend debe estar corriendo en http://127.0.0.1:8000
 (CORS ya permite localhost:5173 y 127.0.0.1:5173).
