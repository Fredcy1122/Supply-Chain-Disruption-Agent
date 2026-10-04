import { RECOMMENDATIONS_PENDING } from "../api/investigation.js";
import { Empty } from "./ui.jsx";

export default function Actions({ shipment, decisions, onDecide }) {
  if (!shipment?.recommendations?.length) {
    return <Empty>{shipment?.recommendationsPending ? RECOMMENDATIONS_PENDING : "No recommendations yet. Run an investigation for this shipment first."}</Empty>;
  }
  const shown = (v) => v ?? "Not assessed";
  return (
    <div className="panel">
      <header><h2>Recommended actions for {shipment.id}</h2></header>
      <div className="cards">
        {shipment.recommendations.map((r) => {
          const d = decisions[r.id];
          return (
            <article key={r.id} className={`card ${d || ""}`}>
              <h3>{r.title}</h3><p>{r.detail}</p>
              <dl className="trade"><div><dt>Cost</dt><dd>{shown(r.cost)}</dd></div><div><dt>Time</dt><dd>{shown(r.time)}</dd></div><div><dt>Risk</dt><dd>{shown(r.risk)}</dd></div></dl>
              {d ? <p className="done">{d === "approved" ? "Approved" : "Dismissed"}</p> : (
                <div className="btns">
                  <button className="btn" onClick={() => onDecide(r.id, "approved")}>Approve</button>
                  <button className="btn ghost" onClick={() => onDecide(r.id, "dismissed")}>Dismiss</button>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
