import { useState, useRef, useEffect } from "react";
import { streamInvestigation } from "../api/client.js";
import { StatusChip, Empty } from "./ui.jsx";

export default function Investigation({ shipment, onStatus }) {
  const [events, setEvents] = useState(null);
  const stop = useRef(null);
  useEffect(() => { setEvents(null); return () => stop.current?.(); }, [shipment?.id]);
  if (!shipment) return <Empty>Select a shipment first.</Empty>;

  const run = () => {
    setEvents([]); onStatus(shipment.id, "running");
    stop.current = streamInvestigation(
      shipment,
      (e) => setEvents((l) => [...l, e]),
      () => onStatus(shipment.id, "complete")
    );
  };
  const saved = shipment.evidence.flatMap((e) => [
    { type: "tool_call", name: e.tool, payload: e.input },
    { type: "tool_result", name: e.tool, payload: e.output },
  ]);
  const shown = events ?? saved;
  const fmt = (p) => (typeof p === "string" ? p : JSON.stringify(p));

  return (
    <div className="panel">
      <header>
        <h2>Investigating {shipment.id}</h2><StatusChip status={shipment.investigationStatus} />
        <button className="btn" onClick={run} disabled={shipment.investigationStatus === "running"}>
          {shipment.investigationStatus === "none" ? "Start investigation" : "Run again"}
        </button>
      </header>
      {shown.length === 0 && <Empty>No evidence yet. Start an investigation to see the agent's tool calls.</Empty>}
      <ol className="trace">
        {shown.map((e, i) => (
          <li key={i} className={e.type}>
            <small>{e.type === "tool_call" ? "Calling" : e.type === "tool_result" ? "Result from" : "Conclusion"}</small>
            <b>{e.name}{e.type === "tool_call" ? "()" : ""}</b>
            <code>{fmt(e.payload)}</code>
          </li>
        ))}
      </ol>
    </div>
  );
}
