import { useRef, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON as RLGeoJSON,
  useMap,
} from "react-leaflet";
import L, { LatLngBoundsExpression } from "leaflet";
import { saveAs } from "file-saver";
import type { FeatureCollection, Feature } from "geojson";

type FC = FeatureCollection;
const API_BASE = "http://127.0.0.1:8000";

type TspResult = {
  route: number[];
  distance: number;
  time: number;
  geojson: Feature;
};

type TspResponse = {
  bruteforce: TspResult;
  nearest_neighbor: TspResult;
  simulated_annealing: TspResult;
};

function FitToData({ data }: { data: FC | null }) {
  const map = useMap();
  if (!data) return null;

  const bounds = L.geoJSON(data as any).getBounds();
  if (bounds.isValid()) {
    map.fitBounds(bounds as unknown as LatLngBoundsExpression, {
      padding: [20, 20],
    });
  }
  return null;
}

export default function MapApp() {
  const [network, setNetwork] = useState<FC | null>(null);
  const [points, setPoints] = useState<FC | null>(null);
  const [tsp, setTsp] = useState<TspResponse | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [tspError, setTspError] = useState<string | null>(null);
  const [networkVersion, setNetworkVersion] = useState(0);

  const networkFileRef = useRef<HTMLInputElement | null>(null);
  const pointsFileRef = useRef<HTMLInputElement | null>(null);

  // --------- helpers de fetch con cache-buster ---------
  const fetchNetwork = async () => {
    try {
      const res = await fetch(`${API_BASE}/network.geojson?ts=${Date.now()}`);
      if (!res.ok) {
        const txt = await res.text();
        alert("No hay red cargada o error: " + txt);
        return;
      }
      const data = (await res.json()) as FC;
      setNetwork(data);
      setNetworkVersion((v) => v + 1);
    } catch (err: any) {
      alert("Error al obtener red: " + err?.message);
    }
  };

  const fetchPoints = async () => {
    try {
      const res = await fetch(`${API_BASE}/points.geojson?ts=${Date.now()}`);
      if (!res.ok) {
        const txt = await res.text();
        alert("No hay puntos integrados o error: " + txt);
        return;
      }
      const data = (await res.json()) as FC;
      setPoints(data);
    } catch (err: any) {
      alert("Error al obtener puntos: " + err?.message);
    }
  };

  // ---------- 3.1 Subir red ----------
  const uploadNetwork = async () => {
    if (!networkFileRef.current?.files?.length) {
      alert("Selecciona un archivo GeoJSON de red vial");
      return;
    }
    const file = networkFileRef.current.files[0];
    const fd = new FormData();
    fd.append("file", file);

    try {
      // limpiamos estado del front
      setNetwork(null);
      setPoints(null);
      setTsp(null);
      setTspError(null);
      setStatusMsg(null);
      setNetworkVersion((v) => v + 1);

      const res = await fetch(`${API_BASE}/upload/network`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const txt = await res.text();
        alert("Error al subir red: " + txt);
        return;
      }
      const j = await res.json();
      setStatusMsg(`Red cargada: ${j.lines} aristas`);

      await fetchNetwork();
    } catch (err: any) {
      alert("Error al subir red: " + err?.message);
    }
  };

  const downloadNetworkGeoJSON = async () => {
    try {
      const res = await fetch(`${API_BASE}/network.geojson?ts=${Date.now()}`);
      if (!res.ok) {
        alert("No hay red cargada");
        return;
      }
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data)], {
        type: "application/geo+json",
      });
      saveAs(blob, "network.geojson");
    } catch (err: any) {
      alert("Error al descargar GeoJSON: " + err?.message);
    }
  };

  const downloadNetworkWKT = async () => {
    try {
      const res = await fetch(`${API_BASE}/network.wkt?ts=${Date.now()}`);
      if (!res.ok) {
        alert("No hay red cargada");
        return;
      }
      const text = await res.text();
      const blob = new Blob([text], {
        type: "text/plain;charset=utf-8",
      });
      saveAs(blob, "network.wkt");
    } catch (err: any) {
      alert("Error al descargar WKT: " + err?.message);
    }
  };

  // ---------- 3.2 Subir CSV de puntos ----------
  const uploadPoints = async () => {
    if (!pointsFileRef.current?.files?.length) {
      alert("Selecciona un archivo CSV con columnas id,lat,lon");
      return;
    }
    const file = pointsFileRef.current.files[0];
    const fd = new FormData();
    fd.append("file", file);

    try {
      setPoints(null);
      setTsp(null);
      setTspError(null);
      setStatusMsg(null);

      const res = await fetch(`${API_BASE}/upload/points`, {
        method: "POST",
        body: fd,
      });
      const txt = await res.text();
      if (!res.ok) {
        alert("Error al integrar puntos: " + txt);
        return;
      }
      const j = JSON.parse(txt);
      setStatusMsg(
        `Puntos integrados: ${j.points_integrated}. Total puntos: ${j.total_points}`
      );

      await fetchPoints();
    } catch (err: any) {
      alert("Error al subir puntos: " + err?.message);
    }
  };

  // ---------- 3.3 Evaluar TSP ----------
  const evaluateTsp = async () => {
    try {
      setTsp(null);
      setTspError(null);
      const res = await fetch(`${API_BASE}/tsp/evaluate?ts=${Date.now()}`);
      const txt = await res.text();
      if (!res.ok) {
        setTspError(txt);
        alert("Error al evaluar TSP: " + txt);
        return;
      }
      const data = JSON.parse(txt) as TspResponse;
      setTsp(data);
    } catch (err: any) {
      alert("Error al evaluar TSP: " + err?.message);
    }
  };

  const downloadTspRoutes = () => {
    if (!tsp) return;
    const fc: FC = {
      type: "FeatureCollection",
      features: [
        tsp.bruteforce.geojson,
        tsp.nearest_neighbor.geojson,
        tsp.simulated_annealing.geojson,
      ],
    };
    const blob = new Blob([JSON.stringify(fc)], {
      type: "application/geo+json",
    });
    saveAs(blob, "tsp_routes.geojson");
  };

  // ---------- render ----------
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "320px 1fr",
        height: "100vh",
      }}
    >
      <aside
        style={{
          padding: 12,
          borderRight: "1px solid #ddd",
          background: "#f5f5f5",
          color: "#222",
          fontSize: 14,
        }}
      >
        {/* 3.1 */}
        <h3 style={{ marginTop: 0 }}>3.1 Carga de red vial</h3>
        <input
          ref={networkFileRef}
          type="file"
          accept=".geojson,application/geo+json,application/json"
        />
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          <button onClick={uploadNetwork}>Subir red (GeoJSON)</button>
          <button onClick={fetchNetwork}>Ver red</button>
          <button onClick={downloadNetworkGeoJSON}>Descargar red (GeoJSON)</button>
          <button onClick={downloadNetworkWKT}>Descargar red (WKT)</button>
        </div>

        <hr style={{ margin: "16px 0" }} />

        {/* 3.2 */}
        <h3>3.2 Carga de pointset</h3>
        <input ref={pointsFileRef} type="file" accept=".csv,text/csv" />
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          <button onClick={uploadPoints}>Subir e integrar puntos (CSV)</button>
          <button onClick={fetchPoints}>Ver puntos integrados</button>
        </div>
        <p style={{ fontSize: 11, opacity: 0.75, marginTop: 8 }}>
          CSV con columnas <code>id,lat,lon</code> (también acepta nombres similares
          como <code>latitude</code>, <code>longitude</code>, <code>point_id</code>).
        </p>

        <hr style={{ margin: "16px 0" }} />

        {/* 3.3 */}
        <h3>3.3 Evaluación de algoritmos TSP</h3>
        <p style={{ fontSize: 11, opacity: 0.75 }}>
          Requiere tener puntos integrados en la red (3.2).
        </p>
        <div style={{ display: "grid", gap: 8 }}>
          <button onClick={evaluateTsp}>Evaluar algoritmos TSP</button>
          <button onClick={downloadTspRoutes} disabled={!tsp}>
            Descargar rutas TSP (GeoJSON)
          </button>
        </div>

        {statusMsg && (
          <p style={{ marginTop: 12, fontSize: 12, color: "#0a7b34" }}>
            {statusMsg}
          </p>
        )}
        {tspError && (
          <p style={{ marginTop: 12, fontSize: 12, color: "#c0392b" }}>
            {tspError}
          </p>
        )}

        {/* Tabla de resultados TSP */}
        {tsp && (
          <div style={{ marginTop: 16, fontSize: 12 }}>
            <h4>Resultados TSP</h4>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 12,
              }}
            >
              <thead>
                <tr>
                  <th
                    style={{
                      borderBottom: "1px solid #ccc",
                      textAlign: "left",
                      padding: "4px 6px",
                    }}
                  >
                    Algoritmo
                  </th>
                  <th
                    style={{
                      borderBottom: "1px solid #ccc",
                      textAlign: "right",
                      padding: "4px 6px",
                    }}
                  >
                    Distancia (m)
                  </th>
                  <th
                    style={{
                      borderBottom: "1px solid #ccc",
                      textAlign: "right",
                      padding: "4px 6px",
                    }}
                  >
                    Tiempo (s)
                  </th>
                </tr>
              </thead>
              <tbody>
              {tsp.bruteforce && (
                <tr>
                  <td style={{ padding: "4px 6px" }}>Fuerza bruta</td>
                  <td style={{ padding: "4px 6px", textAlign: "right" }}>
                    {tsp.bruteforce.distance.toFixed(1)}
                  </td>
                  <td style={{ padding: "4px 6px", textAlign: "right" }}>
                    {(tsp.bruteforce.time * 1000).toFixed(2)} ms
                  </td>
                </tr>
              )}

              <tr>
                <td style={{ padding: "4px 6px" }}>Vecino más cercano</td>
                <td style={{ padding: "4px 6px", textAlign: "right" }}>
                  {tsp.nearest_neighbor.distance.toFixed(1)}
                </td>
                <td style={{ padding: "4px 6px", textAlign: "right" }}>
                  {(tsp.nearest_neighbor.time * 1000).toFixed(2)} ms
                </td>
              </tr>

              <tr>
                <td style={{ padding: "4px 6px" }}>Simulated annealing</td>
                <td style={{ padding: "4px 6px", textAlign: "right" }}>
                  {tsp.simulated_annealing.distance.toFixed(1)}
                </td>
                <td style={{ padding: "4px 6px", textAlign: "right" }}>
                  {(tsp.simulated_annealing.time * 1000).toFixed(2)} ms
                </td>
              </tr>
            </tbody>

            </table>
          </div>
        )}
      </aside>

      <main>
        <MapContainer
          center={[4.655, -74.095]}
          zoom={15}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Red vial: gris oscuro, clave por versión para limpiar al cambiar */}
          {network && (
            <RLGeoJSON
              key={`network-${networkVersion}`}
              data={network as any}
              style={{ color: "#555555", weight: 3 }}
            />
          )}

          {/* Puntos integrados */}
          {points && (
            <RLGeoJSON
              data={points as any}
              pointToLayer={(_feature, latlng) =>
                L.circleMarker(latlng, {
                  radius: 5,
                  color: "#d62c1a",
                  weight: 2,
                  fillColor: "#e74c3c",
                  fillOpacity: 1,
                })
              }
            />
          )}

          {/* Rutas TSP: dejamos el verde para las rutas */}
          {tsp && (
            <>
              {/* óptimo (fuerza bruta) en verde fuerte */}
              <RLGeoJSON
                data={tsp.bruteforce.geojson as any}
                style={{ color: "#00c853", weight: 4 }}
              />
              {/* vecino más cercano en verde más claro / fino */}
              <RLGeoJSON
                data={tsp.nearest_neighbor.geojson as any}
                style={{ color: "#76ff03", weight: 3, dashArray: "6 4" }}
              />
              {/* simulated annealing en verde azulado, línea discontinua */}
              <RLGeoJSON
                data={tsp.simulated_annealing.geojson as any}
                style={{ color: "#1de9b6", weight: 3, dashArray: "2 6" }}
              />
            </>
          )}

          <FitToData data={network} />
        </MapContainer>
      </main>
    </div>
  );
}
