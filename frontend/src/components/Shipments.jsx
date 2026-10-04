import { RiskBadge, StatusChip, Meter, pct, money, NA } from "./ui.jsx";

export default function Shipments({ shipments, selectedId, onSelect }) {
  const s = shipments.find((x) => x.id === selectedId) || shipments[0];
  if (!s) return null;
  const d = s.details;
  const facts = [
    ["Product", d.product], ["Origin", d.origin], ["Destination", d.destination], ["Shipping mode", d.carrier],
    ["ETA", d.eta], ["Status", d.status], ["Supplier", d.supplier],
  ].map(([k, v]) => [k, v ?? NA]);
  const impact = s.impact || {};
  return (
    <div className="split">
      <div className="stack">
        {shipments.map((x) => (
          <button key={x.id} className={`row compact ${x.id === s.id ? "on" : ""}`} onClick={() => onSelect(x.id)}>
            <strong>{x.id}</strong><span>{x.details.destination}</span>
            <StatusChip status={x.investigationStatus} /><RiskBadge level={x.riskLevel} />
          </button>
        ))}
      </div>
      <div className="panel">
        <header><h2>{s.id}</h2><RiskBadge level={s.riskLevel} /></header>
        <div className="prob"><span>Delay probability</span><Meter value={s.delayProbability} level={s.riskLevel} /><b>{pct(s.delayProbability)}</b></div>
        <dl className="facts">{facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
        <h3>Business impact</h3>
        <div className="stats small">
          <div className="stat"><b>{impact.affectedOrders ?? NA}</b><span>Orders affected</span></div>
          <div className="stat"><b>{impact.stockoutDays != null ? `${impact.stockoutDays}d` : NA}</b><span>Stock remaining</span></div>
          <div className="stat"><b>{money(impact.cost)}</b><span>Value at risk</span></div>
        </div>
      </div>
    </div>
  );
}
