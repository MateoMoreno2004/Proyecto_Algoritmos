# Proyecto_Algoritmos · TSP-POC (FastAPI + React + Leaflet)

Proyecto final de la clase **Análisis de algoritmos**.  
Permite cargar una **red vial (GeoJSON)**, visualizarla en un mapa web y exportarla (GeoJSON/WKT).  
Backend en **FastAPI** · Frontend en **React + Vite + Leaflet**.

---

## Índice

1. [Requisitos](#requisitos)
2. [Instalación en Windows con WSL (solo primera vez)](#instalación-en-windows-con-wsl-solo-primera-vez)
   - [2.1. Instalar WSL y Ubuntu](#21-instalar-wsl-y-ubuntu)
   - [2.2. Instalar VS Code + extensión WSL](#22-instalar-vs-code--extensión-wsl)
   - [2.3. Instalar Git dentro de Ubuntu](#23-instalar-git-dentro-de-ubuntu)
3. [Clonar este repositorio en WSL](#clonar-este-repositorio-en-wsl)
4. [Abrir el proyecto con VS Code desde WSL](#abrir-el-proyecto-con-vs-code-desde-wsl)
5. [Backend (FastAPI)](#backend-fastapi)
   - [5.1. Crear entorno virtual](#51-crear-entorno-virtual)
   - [5.2. Instalar dependencias](#52-instalar-dependencias)
   - [5.3. Ejecutar el backend](#53-ejecutar-el-backend)
   - [5.4. Probar la-api](#54-probar-la-api)
6. [Frontend (React + Vite + Leaflet)](#frontend-react--vite--leaflet)
   - [6.1. Instalar Nodejs con nvm](#61-instalar-nodejs-con-nvm)
   - [6.2. Instalar dependencias del-frontend](#62-instalar-dependencias-del-frontend)
   - [6.3. Ejecutar el frontend](#63-ejecutar-el-frontend)
7. [Estructura del proyecto](#estructura-del-proyecto)
8. [Flujo típico de desarrollo](#flujo-típico-de-desarrollo)

---

## Requisitos

- **Sistema operativo:** Windows 10/11.
- **WSL 2** con **Ubuntu**.
- **Visual Studio Code** instalado en Windows.
- Extensión de VS Code: **WSL** (de Microsoft).
- **Git** instalado dentro de Ubuntu.
- **Python 3.10+** (ideal 3.12) dentro de Ubuntu.
- **Node.js 20+** dentro de Ubuntu (se recomienda instalarlo con `nvm`).

---

## Instalación en Windows con WSL (solo primera vez)

### 2.1. Instalar WSL y Ubuntu

1. Abre **PowerShell** como administrador.
2. Ejecuta:

   ```powershell
   wsl --install -d Ubuntu
3. Reinicia el equipo si Windows lo pide.
4. Abre la app Ubuntu (desde el menú Inicio), espera a que termine la instalación y crea:
  -un usuario de Linux
  -una contraseña (solo para Ubuntu).
   
---

## A partir de ahora, siempre que veas comandos con $ se ejecutan dentro de Ubuntu (WSL).

## 2.2. Instalar VS Code + extensión WSL
### Instala Visual Studio Code en Windows (si no lo tienes).

1. Abre VS Code → pestaña Extensions (icono de cuadritos).
2. Busca e instala la extensión: “WSL” (de Microsoft).
3. Desde la app Ubuntu, ejecuta:

    ```powershell
    code .
  - VS Code se abrirá conectado a WSL.

## 2.3. Instalar Git dentro de Ubuntu
1. En la terminal de Ubuntu:

    ```powershell
    sudo apt update
    sudo apt install -y git
  - Clonar este repositorio en WSL
Elige una carpeta para tus proyectos, por ejemplo ~/proyectos:

    ```powershell
    mkdir -p ~/proyectos
    cd ~/proyectos

2. Clona el proyecto:

    ```powershell
    git clone https://github.com/MateoMoreno2004/Proyecto_Algoritmos.git
    cd Proyecto_Algoritmos
    
3. Abrir el proyecto con VS Code desde WSL
Desde la carpeta del proyecto:
     ```powershell
    cd ~/proyectos/Proyecto_Algoritmos
    code .
VS Code se abrirá con el proyecto cargado dentro de WSL.

# Backend (FastAPI)
El backend corre sobre FastAPI usando Uvicorn.

## 5.1. Crear entorno virtual
Dentro de la carpeta del proyecto (en WSL):

  source .venv/bin/activate
Verás algo como (.venv) al inicio de la línea de la terminal.

Siempre que vayas a trabajar con el backend, activar antes el entorno:

    source .venv/bin/activate
    
## 5.2. Instalar dependencias
Con el entorno virtual activado:

    python -m pip install --upgrade pip
    pip install fastapi "uvicorn[standard]" shapely python-multipart geojson "pydantic[dotenv]" pytest

## 5.3. Ejecutar el backend
Desde la carpeta backend/:

    cd ~/proyectos/Proyecto_Algoritmos/backend
    uvicorn Main:app --reload --host 0.0.0.0 --port 8000
    
Deja esa terminal abierta: el servidor se queda corriendo ahí.

## 5.4. Probar la API
Desde el navegador en Windows:

  - Documentación interactiva (Swagger):
  - http://127.0.0.1:8000/docs

  - Esquema OpenAPI:
  - http://127.0.0.1:8000/openapi.json

---

#Frontend (React + Vite + Leaflet)
El frontend se ejecuta en otra terminal de Ubuntu (el backend debe seguir corriendo).

## 6.1. Instalar Nodejs con nvm
Si no tienes nvm:

    sudo apt update
    sudo apt install -y curl
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
    source ~/.nvm/nvm.sh
    
Instalar Node 20 y usarlo:

    nvm install 20
    nvm use 20
    
Cada vez que abras una nueva terminal, si es necesario, ejecuta:

    source ~/.nvm/nvm.sh
    nvm use 20
    
### 6.2. Instalar dependencias del-frontend
Ir a la carpeta frontend/:

    cd ~/proyectos/Proyecto_Algoritmos/frontend
    
Instalar dependencias (si el proyecto ya trae package.json configurado):

    npm install
    
Asegúrate de importar el CSS de Leaflet al inicio de src/main.tsx:

    import "leaflet/dist/leaflet.css";
    
## 6.3. Ejecutar el frontend
En la carpeta frontend/:

    npm run dev
    
La terminal mostrará algo como:


    Local:   http://127.0.0.1:5173/
    
Abre en el navegador:

Frontend: http://127.0.0.1:5173

Backend (ya debe estar corriendo): http://127.0.0.1:8000

Estructura del proyecto
Vista simplificada:

text
Copiar código
Proyecto_Algoritmos/

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

Flujo típico de desarrollo
Abrir Ubuntu y activar entorno:

    cd ~/proyectos/Proyecto_Algoritmos
    source .venv/bin/activate
    
Terminal 1 → backend:

    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    
Terminal 2 → frontend:

    cd ~/proyectos/Proyecto_Algoritmos/frontend
    nvm use 20
    npm run dev
    
Abrir http://127.0.0.1:5173 en el navegador y trabajar.

---

# Probar App

Simplemente descargar los dos .geojson y subirlos en la página
