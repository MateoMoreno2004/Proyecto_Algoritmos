import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON as RLGeoJSON, useMap } from "react-leaflet";
import L, { type LatLngBounds } from "leaflet";
import { saveAs } from "file-saver";
import type { FeatureCollection } from "geojson";

type FC = FeatureCollection;

function FitToData({ data }: { data: FC | null }) {
  const map = useMap();
  useEffect(() => {
    if (!data) return;
    const layer = L.geoJSON(data);
    const bounds = layer.getBounds() as LatLngBounds;
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [data, map]);
  return null;
}

export default function MapApp() {
  const [geojson, setGeojson] = useState<FC | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const uploadNetwork = async () => {
    if (!fileRef.current?.files?.length) return alert("Selecciona un archivo GeoJSON");
    const file = fileRef.current.files[0];
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("http://127.0.0.1:8000/upload/network", { method: "POST", body: fd });
    if (!res.ok) {
      const txt = await res.text();
      alert("Error al subir: " + txt);
      return;
    }
    const j = await res.json();
    alert(`Red cargada: ${j.lines} aristas`);
  };

  const fetchNetwork = async () => {
    const res = await fetch("http://127.0.0.1:8000/network.geojson");
    if (!res.ok) {
      const txt = await res.text();
      alert("No hay red cargada o error: " + txt);
      return;
    }
    const data = (await res.json()) as FC;
    setGeojson(data);
  };

  const downloadGeoJSON = async () => {
    const res = await fetch("http://127.0.0.1:8000/network.geojson");
    if (!res.ok) return alert("No hay red cargada");
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data)], { type: "application/geo+json" });
    saveAs(blob, "network.geojson");
  };

  const downloadWKT = async () => {
    const res = await fetch("http://127.0.0.1:8000/network.wkt");
    if (!res.ok) return alert("No hay red cargada");
    const text = await res.text();
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    saveAs(blob, "network.wkt");
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", height: "100vh" }}>
      <aside style={{ padding: 12, borderRight: "1px solid #ddd" }}>
        <h3>3.1 Carga de red vial</h3>
        <input ref={fileRef} type="file" accept=".geojson,application/geo+json,application/json" />
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          <button onClick={uploadNetwork}>Subir red (GeoJSON)</button>
          <button onClick={fetchNetwork}>Ver red</button>
          <button onClick={downloadGeoJSON}>Descargar GeoJSON</button>
          <button onClick={downloadWKT}>Descargar WKT</button>
        </div>
        <p style={{ fontSize: 12, color: "#666", marginTop: 12 }}>
          Sube un FeatureCollection de LineString. Luego “Ver red” para dibujarla.
        </p>
      </aside>
      <main>
        <MapContainer center={[4.65, -74.1]} zoom={12} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {geojson && <RLGeoJSON data={geojson as any} style={{ color: "#888", weight: 2 }} />}
          <FitToData data={geojson} />
        </MapContainer>
      </main>
    </div>
  );
}
