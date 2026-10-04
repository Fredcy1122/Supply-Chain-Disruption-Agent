import { failureDetail, investigate, toSteps } from "../api/investigation.js";
import { StatusChip, Empty } from "./ui.jsx";

// The running investigation for each shipment. Kept outside the component so
// a stream keeps updating its shipment while another tab is shown.
const active = new Map();

export default function Investigation({ shipment, onUpdate }) {
  if (!shipment) return <Empty>Select a shipment first.</Empty>;

  // Progress, the result and any error are stored on the shipment, so they
  // survive tab changes.
  const run = async () => {
    const id = shipment.id;
    // A new run for a shipment replaces the one in progress.
    active.get(id)?.abort();
    const controller = new AbortController();
    active.set(id, controller);
    // Updates from a run that has been replaced are dropped.
    const update = (patch) => { if (active.get(id) === controller) onUpdate(id, patch); };
    update({
      investigationStatus: "running", investigationError: null, conclusion: null,
      evidence: [], briefing: null, recommendations: [], recommendationsPending: false, limitations: [],
    });
    try {
      await investigate(id, update, { signal: controller.signal });
      // Only reached when a valid done event was received.
      update({ investigationStatus: "complete" });
    } catch (e) {
      update({
        investigationStatus: e.code === "investigation_not_required" ? "not_required" : "failed",
        investigationError: { message: e.message, detail: failureDetail(e) },
      });
    } finally {
      if (active.get(id) === controller) active.delete(id);
    }
  };
  const shown = toSteps(shipment);
  const status = shipment.investigationStatus;
  const failure = shipment.investigationError;
  const limitations = shipment.limitations || [];
  const STEP_STATUS = { running: "In progress", done: "Done", failed: "Unavailable", complete: "Briefing" };

  return (
    <div className="panel">
      <header>
        <h2>Investigating {shipment.id}</h2><StatusChip status={status} />
        <button className="btn" onClick={run} disabled={status === "running"}>
          {status === "none" ? "Start investigation" : "Run again"}
        </button>
      </header>
      {status === "running" && <Empty>Investigating… gathering evidence for this shipment.</Empty>}
      {failure && status !== "running" && (
        <div className={`empty ${status === "failed" ? "err" : ""}`}>
          <b>{failure.message}</b>{failure.detail && <p>{failure.detail}</p>}
        </div>
      )}
      {!failure && status !== "running" && shown.length === 0 && (
        <Empty>No evidence yet. Start an investigation to see what the agent finds.</Empty>
      )}
      <ol className="trace">
        {shown.map((e, i) => (
          <li key={i} className={e.status}>
            <small>{STEP_STATUS[e.status]}</small>
            <b>{e.label}</b>
            {e.finding && <span>{e.finding}</span>}
          </li>
        ))}
      </ol>
      {limitations.length > 0 && (
        <section>
          <h3>Limitations</h3>
          <ul>{limitations.map((l) => <li key={l}>{l}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
