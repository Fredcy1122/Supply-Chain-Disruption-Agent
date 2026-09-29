import { shipments as mock } from "../data/mock.js";
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

export async function getShipments() {
  if (USE_MOCK) { await wait(400); return structuredClone(mock); }
  const res = await fetch("/api/shipments");
  if (!res.ok) throw new Error(`Could not load shipments (${res.status})`);
  return res.json();
}

// Streams agent events: { type: "tool_call" | "tool_result" | "message", name, payload }
export function streamInvestigation(shipment, onEvent, onDone) {
  if (USE_MOCK) {
    const evs = shipment.evidence.flatMap((e) => [
      { type: "tool_call", name: e.tool, payload: e.input },
      { type: "tool_result", name: e.tool, payload: e.output },
    ]);
    evs.push({ type: "message", name: "agent", payload: shipment.cause });
    let i = 0;
    const t = setInterval(() => {
      if (i < evs.length) onEvent(evs[i++]);
      else { clearInterval(t); onDone(); }
    }, 900);
    return () => clearInterval(t);
  }
  const es = new EventSource(`/api/shipments/${shipment.id}/investigate/stream`);
  es.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.type === "done") { es.close(); onDone(); } else onEvent(ev);
  };
  es.onerror = () => { es.close(); onDone(); };
  return () => es.close();
}
