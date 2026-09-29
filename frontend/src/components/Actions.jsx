import { Empty } from "./ui.jsx";

export default function Actions({ shipment, decisions, onDecide }) {
  if (!shipment?.recommendations.length) return <Empty>No action needed. This shipment is on track.</Empty>;
  return (
    <div className="panel">
      <header><h2>Recommended actions for {shipment.id}</h2></header>
      <div className="cards">
        {shipment.recommendations.map((r) => {
          const d = decisions[r.id];
          return (
            <article key={r.id} className={`card ${d || ""}`}>
              <h3>{r.title}</h3><p>{r.detail}</p>
              <dl className="trade"><div><dt>Cost</dt><dd>{r.cost}</dd></div><div><dt>Time</dt><dd>{r.time}</dd></div><div><dt>Risk</dt><dd>{r.risk}</dd></div></dl>
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
