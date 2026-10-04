// Consumes the backend's investigation stream (Server-Sent Events) and turns
// each event into the shipment fields the components use.
const NA = "Not available";

export class ApiError extends Error {
  // code is the backend's failure code, when it reported one.
  constructor(status, message, detail, code) {
    super(message);
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

const FAILED = "Investigation failed";
// User-facing text for the backend's failure codes and HTTP statuses.
const MESSAGES = {
  investigation_not_required: "Low risk — no investigation needed",
  shipment_not_found: "Shipment not found",
  404: "Shipment not found",
};
const messageFor = (code, status) => MESSAGES[code] || MESSAGES[status] || FAILED;

const malformed = () => new ApiError(0, FAILED, "The server sent a response that could not be understood.");
const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

// Yields { event, data } for each complete event in an SSE response body.
// An event cut off by the end of the stream is dropped, not yielded.
async function* readEvents(body) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) return;
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n");
      let end;
      while ((end = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, end);
        buffer = buffer.slice(end + 2);
        let event = "message";
        const data = [];
        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        // Blocks without data are comments or keep-alives.
        if (data.length) yield { event, data: data.join("\n") };
      }
    }
  } finally {
    // Stops the download when the caller finishes early.
    reader.cancel().catch(() => {});
  }
}

// A failed tool call keeps its status, and its error replaces the output.
const toEvidence = (t) => ({
  tool: t.tool ?? t.name,
  input: t.input,
  output: t.status === "error" ? t.error : t.output,
  status: t.status,
});

// The backend lists this limitation while its recommended actions are fixed
// placeholders rather than retrieved from the operational knowledge base.
const PLACEHOLDER_ACTIONS = /RAG retrieval is not yet integrated/i;
export const RECOMMENDATIONS_PENDING =
  "Approved operational recommendations will appear when the knowledge base is connected.";

const capitalize = (v) => { const t = String(v).replace(/_/g, " ").toLowerCase(); return t.charAt(0).toUpperCase() + t.slice(1); };
const percent = (p) => `${(p * 100).toFixed(1)}%`;

// The shipment fields for a finished briefing (the done event's payload).
function toResult(b) {
  if (!isObject(b) || typeof b.shipment_id !== "string" || typeof b.risk_level !== "string"
    || typeof b.delay_probability !== "number" || typeof b.summary !== "string"
    || !isObject(b.evidence) || !Array.isArray(b.tool_trace)
    || !Array.isArray(b.recommended_actions) || !Array.isArray(b.limitations)) throw malformed();
  const cause = [b.evidence.historical_delay_summary, b.evidence.weather_summary]
    .filter(Boolean).join(" ");
  // Placeholder actions, and the summary that cites them as policy, are not
  // shown as if the knowledge base had produced them.
  const pending = b.limitations.some((l) => PLACEHOLDER_ACTIONS.test(l));
  const actions = pending ? [] : b.recommended_actions;
  const summary = pending
    ? `Shipment ${b.shipment_id} has a ${b.risk_level.toLowerCase()} risk of delay (${percent(b.delay_probability)} probability).`
    : b.summary;
  return {
    riskLevel: b.risk_level.toLowerCase(),
    delayProbability: b.delay_probability,
    evidence: b.tool_trace.map(toEvidence),
    conclusion: summary,
    briefing: {
      summary,
      cause: cause || NA,
      impact: "Not yet available",
      actions: pending ? RECOMMENDATIONS_PENDING : actions.join(" "),
      generatedAt: new Date().toLocaleString(),
    },
    recommendations: actions.map((action, i) => ({
      id: `${b.shipment_id}-${i}`,
      title: action,
      detail: "",
      cost: null,
      time: null,
      risk: null,
    })),
    recommendationsPending: pending,
    limitations: pending
      ? [...b.limitations.filter((l) => !PLACEHOLDER_ACTIONS.test(l)), RECOMMENDATIONS_PENDING]
      : b.limitations,
  };
}

// The low-risk explanation, worded from the risk result the stream delivered
// before the rejection. Null when that result is missing.
function lowRiskDetail(evidence) {
  const risk = evidence.find((e) => e.tool === "get_delay_risk" && e.status === "success")?.output;
  if (typeof risk?.shipment_id !== "string" || typeof risk.delay_probability !== "number") return null;
  return `Shipment ${risk.shipment_id} has a low risk of delay (${percent(risk.delay_probability)}) and does not require further investigation.`;
}

// Runs the backend investigation. onUpdate receives the shipment fields to
// merge as each event arrives. Resolves only when a valid done event was
// received; every other outcome throws ApiError with a user-facing message.
// An aborted signal rejects with the fetch AbortError instead.
export async function investigate(id, onUpdate, { signal, fetch: fetchFn = fetch } = {}) {
  let res;
  try {
    res = await fetchFn(`/api/agent/investigate/${encodeURIComponent(id)}/stream`, {
      headers: { Accept: "text/event-stream" },
      signal,
    });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new ApiError(0, FAILED, "The backend could not be reached.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : undefined;
    throw new ApiError(res.status, messageFor(null, res.status), detail);
  }
  if (!res.body || !(res.headers.get("content-type") || "").includes("text/event-stream")) throw malformed();

  // Tool calls so far, in order. The last entry is the one in progress.
  let evidence = [];
  const finishTool = (data) => {
    const call = toEvidence(data);
    const last = evidence.length - 1;
    evidence = evidence[last]?.tool === call.tool && evidence[last].status === "running"
      ? [...evidence.slice(0, last), call] : [...evidence, call];
    onUpdate({ evidence });
  };

  try {
    for await (const { event, data: raw } of readEvents(res.body)) {
      let data;
      try { data = JSON.parse(raw); } catch { throw malformed(); }
      if (!isObject(data)) throw malformed();

      if (event === "tool_start") {
        if (typeof data.name !== "string") throw malformed();
        evidence = [...evidence, { tool: data.name, input: data.input, status: "running" }];
        onUpdate({ evidence });
      } else if (event === "tool_complete" || event === "tool_error") {
        if (typeof data.name !== "string") throw malformed();
        finishTool({ ...data, status: event === "tool_error" ? "error" : "success" });
      } else if (event === "message") {
        if (typeof data.content !== "string") throw malformed();
        onUpdate({ conclusion: data.content });
      } else if (event === "done") {
        const result = toResult(data);
        onUpdate(result);
        return result;
      } else if (event === "error") {
        const detail = typeof data.detail === "string" ? data.detail : undefined;
        throw new ApiError(
          typeof data.status === "number" ? data.status : 0,
          messageFor(data.code, data.status),
          (data.code === "investigation_not_required" && lowRiskDetail(evidence)) || detail,
          data.code,
        );
      }
      // Other event names are ignored so the backend can add new ones.
    }
  } catch (e) {
    if (e instanceof ApiError || signal?.aborted) throw e;
    throw new ApiError(0, FAILED, "The connection to the backend was lost.");
  }
  throw new ApiError(0, FAILED, "The connection closed before the investigation finished.");
}

// The explanation shown under a failure. The backend's detail is only shown
// for outcomes it words for the user; other failures may carry internal error
// text, so they get a neutral explanation. Status 0 details are written here.
export function failureDetail(e) {
  if (e.status === 0 || e.code === "investigation_not_required" || e.code === "shipment_not_found") return e.detail;
  if (e.status === 404) return undefined;
  return "Something went wrong while investigating this shipment. Please try again.";
}

const HIGHEST_FACTOR = { product: "Product", market: "Market", shipping_mode: "Shipping mode" };

// How each investigation step is presented: a label, and a one-line finding
// built from the step's result. Tool names and raw results are never shown.
const STEPS = {
  get_delay_risk: {
    label: "Assessing delay risk",
    finding: (o) => `${capitalize(o.risk_level)} risk · ${percent(o.delay_probability)} probability`,
  },
  get_shipment: {
    label: "Checking shipment details",
    finding: (o) => `${o.destination_city}, ${o.destination_country} · ${o.shipping_mode}`,
  },
  get_historical_delay_context: {
    label: "Reviewing historical delay patterns",
    finding: (o) => `${HIGHEST_FACTOR[o.highest_delay_rate_factor]} has the highest historical delay rate`
      + ` (${percent(o.historical_delay_rates[o.highest_delay_rate_factor])})`,
  },
  get_destination_weather: {
    label: "Checking destination weather",
    finding: (o) => `${capitalize(o.worst_weather_description)} · ${capitalize(o.severity)} severity`,
  },
};
const OTHER_STEP = { label: "Gathering additional evidence", finding: () => null };

// A finding is only shown when the result has the expected fields.
function findingFor(step, output) {
  try {
    const text = step.finding(output);
    return typeof text === "string" && !/undefined|null|NaN/.test(text) ? text : null;
  } catch {
    return null;
  }
}

// Steps for the investigation view: { label, finding, status }, where status
// is "running", "done", "failed" or, for the closing step, "complete".
export function toSteps(shipment) {
  const running = shipment.investigationStatus === "running";
  const steps = (shipment.evidence || []).map((e) => {
    const step = Object.hasOwn(STEPS, e.tool) ? STEPS[e.tool] : OTHER_STEP;
    if (e.status === "success") return { label: step.label, finding: findingFor(step, e.output), status: "done" };
    if (e.status === "running" && running) return { label: step.label, finding: null, status: "running" };
    // Failed, or still in progress when the investigation stopped.
    return { label: step.label, finding: "This information could not be retrieved.", status: "failed" };
  });
  if (shipment.briefing) {
    steps.push({ label: "Investigation complete", finding: shipment.briefing.summary, status: "complete" });
  } else if (shipment.conclusion && running) {
    steps.push({ label: "Preparing briefing", finding: null, status: "running" });
  }
  return steps;
}
