import { useEffect, useState } from "react";
import { getShipments } from "./api/client.js";
import Home from "./components/Home.jsx";
import Shipments from "./components/Shipments.jsx";
import Investigation from "./components/Investigation.jsx";
import Actions from "./components/Actions.jsx";
import Briefings from "./components/Briefings.jsx";

const TABS = ["Home", "Shipments", "Investigation", "Actions", "Briefings"];

export default function App() {
  const [tab, setTab] = useState("Home");
  const [shipments, setShipments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [decisions, setDecisions] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    getShipments().then((d) => { setShipments(d); setSelectedId(d[0]?.id); }).catch((e) => setError(e.message));
  }, []);

  const selected = shipments.find((s) => s.id === selectedId);
  const setStatus = (id, st) => setShipments((l) => l.map((s) => (s.id === id ? { ...s, investigationStatus: st } : s)));
  const open = (id) => { setSelectedId(id); setTab("Shipments"); };

  return (
    <div className="app">
      <nav className="rail">
        <div className="brand">Control<br />Tower</div>
        {TABS.map((t) => <button key={t} className={t === tab ? "on" : ""} onClick={() => setTab(t)}>{t}</button>)}
      </nav>
      <main>
        {selected && tab !== "Home" && tab !== "Shipments" && (
          <label className="picker">Shipment
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {shipments.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.details.destination}</option>)}
            </select>
          </label>
        )}
        {error && <div className="empty err">{error}. Check that the backend is running or set VITE_USE_MOCK=true.</div>}
        {!error && !shipments.length && <div className="empty">Loading shipments…</div>}
        {shipments.length > 0 && (
          <>
            {tab === "Home" && <Home shipments={shipments} onOpen={open} />}
            {tab === "Shipments" && <Shipments shipments={shipments} selectedId={selectedId} onSelect={setSelectedId} />}
            {tab === "Investigation" && <Investigation shipment={selected} onStatus={setStatus} />}
            {tab === "Actions" && <Actions shipment={selected} decisions={decisions} onDecide={(id, d) => setDecisions((x) => ({ ...x, [id]: d }))} />}
            {tab === "Briefings" && <Briefings shipment={selected} />}
          </>
        )}
      </main>
    </div>
  );
}
