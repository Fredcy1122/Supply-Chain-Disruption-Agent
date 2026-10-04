import { RiskBadge, Meter, pct, money } from "./ui.jsx";

export default function Home({ shipments, onOpen }) {
  const atRisk = shipments.filter((s) => s.requiresInvestigation);
  // Impact is not provided by the backend yet; show "Not available" until it is.
  const withImpact = shipments.filter((s) => s.impact?.cost != null);
  const cost = withImpact.length ? withImpact.reduce((a, s) => a + s.impact.cost, 0) : null;
  const avg = shipments.reduce((a, s) => a + s.delayProbability, 0) / (shipments.length || 1);
  const stats = [
    ["Active shipments", shipments.length],
    ["Need investigation", atRisk.length],
    ["Average delay probability", pct(avg)],
    ["Value at risk", money(cost)],
  ];
  return (
    <>
      <section className="hero">
        <h1>{atRisk.length} shipments need attention today</h1>
        <p>Delays are predicted before they turn into stockouts. Open a shipment to see why, and what to do.</p>
      </section>
      <div className="stats">
        {stats.map(([l, v]) => <div className="stat" key={l}><b>{v}</b><span>{l}</span></div>)}
      </div>
      <h2>Highest risk right now</h2>
      <div className="stack">
        {[...shipments].sort((a, b) => b.delayProbability - a.delayProbability).slice(0, 4).map((s) => (
          <button key={s.id} className="row" onClick={() => onOpen(s.id)}>
            <strong>{s.id}</strong>
            <span>To {s.details.destination}</span>
            <Meter value={s.delayProbability} level={s.riskLevel} />
            <em>{pct(s.delayProbability)}</em>
            <RiskBadge level={s.riskLevel} />
          </button>
        ))}
      </div>
    </>
  );
}
