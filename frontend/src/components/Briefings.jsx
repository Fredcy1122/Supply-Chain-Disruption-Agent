import { useState } from "react";
import { Empty } from "./ui.jsx";

export default function Briefings({ shipment }) {
  const [copied, setCopied] = useState(false);
  const b = shipment?.briefing;
  if (!b) return <Empty>No briefing yet. Briefings appear for shipments with elevated risk.</Empty>;
  const text = `${b.summary}\n\nCause: ${b.cause}\nImpact: ${b.impact}\nActions: ${b.actions}`;
  const copy = async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return (
    <div className="panel brief">
      <header><h2>Disruption briefing</h2><button className="btn" onClick={copy}>{copied ? "Copied" : "Copy briefing"}</button></header>
      <p className="lead">{b.summary}</p>
      {[["What caused it", b.cause], ["Business impact", b.impact], ["What to do", b.actions]].map(([h, t]) => (
        <section key={h}><h3>{h}</h3><p>{t}</p></section>
      ))}
      <small>Generated {b.generatedAt}</small>
    </div>
  );
}
