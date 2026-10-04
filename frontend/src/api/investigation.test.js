// Run with `npm test` (Node's built-in test runner; no backend needed).
import test from "node:test";
import assert from "node:assert/strict";
import { ApiError, RECOMMENDATIONS_PENDING, failureDetail, investigate, toSteps } from "./investigation.js";

const sse = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

const BRIEFING = {
  shipment_id: "SHP-1",
  risk_level: "MEDIUM",
  delay_probability: 0.55,
  evidence: { shipment_summary: "s", historical_delay_summary: "History.", weather_summary: "Weather." },
  rag_policy_citations: ["SOP-04"],
  summary: "Conclusion text",
  recommended_actions: ["Reroute", "Check buffer"],
  tool_trace: [
    { tool: "get_delay_risk", input: { shipment_id: "SHP-1" }, output: { risk_level: "MEDIUM" }, status: "success", error: null },
    { tool: "get_destination_weather", input: { shipment_id: "SHP-1" }, output: null, status: "error", error: "timeout" },
  ],
  limitations: ["Weather evidence was not collected: timeout"],
};

const SUCCESS = [
  sse("tool_start", { name: "get_delay_risk", input: { shipment_id: "SHP-1" } }),
  sse("tool_complete", { name: "get_delay_risk", input: { shipment_id: "SHP-1" }, output: { risk_level: "MEDIUM" }, status: "success", error: null }),
  sse("tool_start", { name: "get_destination_weather", input: { shipment_id: "SHP-1" } }),
  sse("tool_error", { name: "get_destination_weather", input: { shipment_id: "SHP-1" }, output: null, status: "error", error: "timeout" }),
  sse("message", { role: "agent", content: "Conclusion text" }),
  sse("done", BRIEFING),
];

// A fetch that answers with the given chunks as a streamed response body.
function fakeFetch(chunks, { status = 200, contentType = "text/event-stream", failAfter } = {}) {
  const calls = [];
  const fetchFn = async (url, options) => {
    calls.push({ url, options });
    const encoder = new TextEncoder();
    let i = 0;
    const body = new ReadableStream({
      pull(controller) {
        if (failAfter !== undefined && i === failAfter) return controller.error(new TypeError("network error"));
        if (i < chunks.length) controller.enqueue(encoder.encode(chunks[i++]));
        else controller.close();
      },
    });
    return new Response(body, { status, headers: { "content-type": contentType } });
  };
  fetchFn.calls = calls;
  return fetchFn;
}

// Runs investigate and returns every update plus the outcome.
async function run(chunks, options) {
  const updates = [];
  const fetchFn = typeof chunks === "function" ? chunks : fakeFetch(chunks, options);
  try {
    const result = await investigate("SHP-1", (patch) => updates.push(patch), { fetch: fetchFn });
    return { updates, result, fetchFn };
  } catch (error) {
    return { updates, error, fetchFn };
  }
}

const failed = (outcome, detail) => {
  assert.ok(outcome.error instanceof ApiError, "expected an ApiError");
  assert.equal(outcome.result, undefined);
  assert.equal(outcome.error.message, "Investigation failed");
  if (detail) assert.match(outcome.error.detail, detail);
  // No update may look like a finished briefing.
  assert.ok(outcome.updates.every((u) => !u.briefing));
};

test("requests the stream endpoint for the shipment", async () => {
  const { fetchFn } = await run(SUCCESS);
  assert.equal(fetchFn.calls[0].url, "/api/agent/investigate/SHP-1/stream");
});

test("updates progressively as events arrive", async () => {
  const { updates, result } = await run(SUCCESS);

  assert.deepEqual(updates[0].evidence, [{ tool: "get_delay_risk", input: { shipment_id: "SHP-1" }, status: "running" }]);
  assert.deepEqual(updates[1].evidence, [
    { tool: "get_delay_risk", input: { shipment_id: "SHP-1" }, output: { risk_level: "MEDIUM" }, status: "success" },
  ]);
  assert.equal(updates[2].evidence[1].status, "running");
  assert.deepEqual(updates[3].evidence[1], {
    tool: "get_destination_weather", input: { shipment_id: "SHP-1" }, output: "timeout", status: "error",
  });
  assert.deepEqual(updates[4], { conclusion: "Conclusion text" });
  assert.equal(updates.length, 6);
  assert.equal(updates[5], result);
});

test("done populates the briefing, recommendations and limitations", async () => {
  const { result } = await run(SUCCESS);

  assert.equal(result.riskLevel, "medium");
  assert.equal(result.delayProbability, 0.55);
  assert.equal(result.briefing.summary, "Conclusion text");
  assert.equal(result.briefing.cause, "History. Weather.");
  assert.deepEqual(result.recommendations.map((r) => r.title), ["Reroute", "Check buffer"]);
  assert.deepEqual(result.limitations, BRIEFING.limitations);
  assert.deepEqual(result.evidence.map((e) => e.status), ["success", "error"]);
});

test("handles events split across chunks and CRLF line endings", async () => {
  const text = SUCCESS.join("").replace(/\n/g, "\r\n");
  const chunks = [];
  for (let i = 0; i < text.length; i += 7) chunks.push(text.slice(i, i + 7));

  const { result, updates } = await run(chunks);
  assert.equal(result.briefing.summary, "Conclusion text");
  assert.equal(updates.length, 6);
});

test("ignores comments and unknown event names", async () => {
  const { result } = await run([": keep-alive\n\n", sse("heartbeat", { n: 1 }), ...SUCCESS]);
  assert.equal(result.briefing.summary, "Conclusion text");
});

// Tool results as the backend sends them.
const OUTPUTS = {
  get_delay_risk: { shipment_id: "SHP-1", delay_probability: 0.4033, risk_level: "MEDIUM", requires_investigation: true },
  get_shipment: { shipment_reference: "SHP-1", destination_city: "Indaial", destination_country: "Brasil", shipping_mode: "Standard Class", order_id: 61334 },
  get_historical_delay_context: {
    product_name: "Rip Deck", market: "LATAM", shipping_mode: "Standard Class",
    historical_delay_rates: { product: 0.57, market: 0.55, shipping_mode: 0.38 }, highest_delay_rate_factor: "product",
  },
  get_destination_weather: { destination: "Indaial, Brazil", worst_weather_description: "light drizzle", severity: "low", daily: [] },
};
const TOOLS = Object.keys(OUTPUTS);
const evidenceFor = (tools) => tools.map((tool) => ({ tool, input: { shipment_id: "SHP-1" }, output: OUTPUTS[tool], status: "success" }));

// Everything a step shows to the user.
const visible = (steps) => steps.map((s) => `${s.label} ${s.finding ?? ""}`).join("\n");
const assertNoInternals = (steps) => {
  assert.doesNotMatch(visible(steps), /get_|shipment_id|[{}\[\]"]|\(\)|undefined|null|NaN/);
};

test("toSteps shows each step with a friendly label and finding", () => {
  const steps = toSteps({ investigationStatus: "running", evidence: evidenceFor(TOOLS) });

  assert.deepEqual(steps, [
    { label: "Assessing delay risk", finding: "Medium risk · 40.3% probability", status: "done" },
    { label: "Checking shipment details", finding: "Indaial, Brasil · Standard Class", status: "done" },
    { label: "Reviewing historical delay patterns", finding: "Product has the highest historical delay rate (57.0%)", status: "done" },
    { label: "Checking destination weather", finding: "Light drizzle · Low severity", status: "done" },
  ]);
  assertNoInternals(steps);
});

test("toSteps shows a step in progress without a finding", () => {
  const evidence = [...evidenceFor(TOOLS.slice(0, 1)), { tool: "get_shipment", input: {}, status: "running" }];
  const steps = toSteps({ investigationStatus: "running", evidence });

  assert.deepEqual(steps[1], { label: "Checking shipment details", finding: null, status: "running" });
  assertNoInternals(steps);
});

test("toSteps hides the error text of a failed step", () => {
  const evidence = [{ tool: "get_destination_weather", input: {}, output: "HTTPSConnectionPool(host='x'): {\"reason\": 1}", status: "error" }];
  const [step] = toSteps({ investigationStatus: "running", evidence });

  assert.deepEqual(step, { label: "Checking destination weather", finding: "This information could not be retrieved.", status: "failed" });
});

test("toSteps does not leave a step in progress after the investigation stopped", () => {
  const evidence = [{ tool: "get_shipment", input: {}, status: "running" }];
  assert.equal(toSteps({ investigationStatus: "failed", evidence })[0].status, "failed");
});

test("toSteps never shows an unknown tool's name or an unexpected result", () => {
  const steps = toSteps({
    investigationStatus: "running",
    evidence: [
      { tool: "get_supplier_status", input: {}, output: { a: 1 }, status: "success" },
      { tool: "get_delay_risk", input: {}, output: { unexpected: true }, status: "success" },
      { tool: "constructor", input: {}, output: {}, status: "success" },
    ],
  });

  assert.deepEqual(steps.map((s) => s.label), ["Gathering additional evidence", "Assessing delay risk", "Gathering additional evidence"]);
  assert.deepEqual(steps.map((s) => s.finding), [null, null, null]);
});

test("toSteps closes with the briefing only once the investigation is done", () => {
  const evidence = evidenceFor(TOOLS);
  const preparing = toSteps({ investigationStatus: "running", evidence, conclusion: "raw backend summary" });
  assert.deepEqual(preparing.at(-1), { label: "Preparing briefing", finding: null, status: "running" });
  assert.doesNotMatch(visible(preparing), /raw backend summary/);

  const done = toSteps({ investigationStatus: "complete", evidence, conclusion: "x", briefing: { summary: "Final summary." } });
  assert.deepEqual(done.at(-1), { label: "Investigation complete", finding: "Final summary.", status: "complete" });
  assert.equal(done.length, 5);
});

test("placeholder recommendations are not presented as knowledge-base output", async () => {
  const placeholder = "Policy citations and recommended actions come from the briefing service placeholder: RAG retrieval is not yet integrated.";
  const briefing = {
    ...BRIEFING,
    summary: "Shipment SHP-1 faces a MEDIUM risk (55.0%). RAG policy suggests immediate intervention.",
    recommended_actions: ["Trigger SOP-04: Reroute via secondary transit hub immediately."],
    limitations: ["Weather scope.", placeholder],
  };
  const { result } = await run([sse("done", briefing)]);

  assert.deepEqual(result.recommendations, []);
  assert.equal(result.recommendationsPending, true);
  assert.equal(result.briefing.actions, RECOMMENDATIONS_PENDING);
  assert.equal(result.briefing.summary, "Shipment SHP-1 has a medium risk of delay (55.0% probability).");
  assert.deepEqual(result.limitations, ["Weather scope.", RECOMMENDATIONS_PENDING]);
  assert.doesNotMatch(JSON.stringify([result.briefing, result.limitations, result.conclusion]), /RAG|SOP-04/);
});

test("real recommendations are shown once the placeholder limitation is gone", async () => {
  const { result } = await run(SUCCESS);

  assert.equal(result.recommendationsPending, false);
  assert.equal(result.briefing.actions, "Reroute Check buffer");
  assert.equal(result.briefing.summary, "Conclusion text");
});

test("failureDetail keeps user-worded details and hides internal ones", () => {
  assert.equal(failureDetail(new ApiError(400, "m", "Shipment SHP-1 is LOW risk", "investigation_not_required")), "Shipment SHP-1 is LOW risk");
  assert.equal(failureDetail(new ApiError(404, "m", "Shipment 'SHP-9' was not found.", "shipment_not_found")), "Shipment 'SHP-9' was not found.");
  assert.equal(failureDetail(new ApiError(0, "m", "The backend could not be reached.")), "The backend could not be reached.");
  assert.doesNotMatch(failureDetail(new ApiError(500, "m", "Agent investigation failed: KeyError('x')", "investigation_failed")), /KeyError|Agent/);
  assert.doesNotMatch(failureDetail(new ApiError(502, "m", "<html>")), /html/);
});

const LOW_RISK_ERROR = sse("error", {
  status: 400, code: "investigation_not_required",
  detail: "Shipment SHP-153440 is LOW risk (0.3985) and does not require AI investigation.",
});

test("low-risk error event is reported as not required, in user-facing wording", async () => {
  const outcome = await run([
    sse("tool_start", { name: "get_delay_risk", input: { shipment_id: "SHP-153440" } }),
    sse("tool_complete", {
      name: "get_delay_risk", input: { shipment_id: "SHP-153440" }, status: "success", error: null,
      output: { shipment_id: "SHP-153440", delay_probability: 0.3985, risk_level: "LOW", requires_investigation: false },
    }),
    LOW_RISK_ERROR,
  ]);
  assert.equal(outcome.error.code, "investigation_not_required");
  assert.equal(outcome.error.status, 400);
  assert.equal(outcome.error.message, "Low risk — no investigation needed");
  assert.equal(outcome.error.detail, "Shipment SHP-153440 has a low risk of delay (39.9%) and does not require further investigation.");
  // The reworded detail is what the Investigation view shows.
  assert.equal(failureDetail(outcome.error), outcome.error.detail);
  assert.equal(outcome.result, undefined);
});

test("low-risk detail falls back to the backend's text without a risk result", async () => {
  const outcome = await run([LOW_RISK_ERROR]);
  assert.equal(outcome.error.code, "investigation_not_required");
  assert.equal(outcome.error.detail, "Shipment SHP-153440 is LOW risk (0.3985) and does not require AI investigation.");
});

test("unknown shipment error event reads 'Shipment not found'", async () => {
  const outcome = await run([sse("error", { status: 404, code: "shipment_not_found", detail: "not found" })]);
  assert.equal(outcome.error.message, "Shipment not found");
  assert.equal(outcome.error.status, 404);
});

test("fatal error event fails and ignores anything after it", async () => {
  const outcome = await run([
    sse("error", { status: 500, code: "investigation_failed", detail: "Agent investigation failed: boom" }),
    sse("done", BRIEFING),
  ]);
  failed(outcome, /boom/);
  assert.equal(outcome.error.status, 500);
});

for (const [status, message] of [[400, "Investigation failed"], [404, "Shipment not found"], [500, "Investigation failed"]]) {
  test(`HTTP ${status} is a failure, never a completion`, async () => {
    const outcome = await run([JSON.stringify({ detail: "server said no" })], { status, contentType: "application/json" });
    assert.ok(outcome.error instanceof ApiError);
    assert.equal(outcome.error.status, status);
    assert.equal(outcome.error.message, message);
    assert.equal(outcome.error.detail, "server said no");
    assert.equal(outcome.updates.length, 0);
  });
}

test("HTTP error with a non-JSON body still fails cleanly", async () => {
  const outcome = await run(["<html>Bad Gateway</html>"], { status: 502, contentType: "text/html" });
  failed(outcome);
  assert.equal(outcome.error.status, 502);
});

test("connection failure is reported", async () => {
  const outcome = await run(async () => { throw new TypeError("fetch failed"); });
  failed(outcome, /could not be reached/);
});

test("a 200 response that is not an event stream fails", async () => {
  failed(await run([JSON.stringify(BRIEFING)], { contentType: "application/json" }), /could not be understood/);
});

test("stream that ends before done fails", async () => {
  failed(await run(SUCCESS.slice(0, 4)), /closed before the investigation finished/);
});

test("done event cut off mid-way fails", async () => {
  const done = SUCCESS[5];
  failed(await run([...SUCCESS.slice(0, 5), done.slice(0, done.length - 20)]), /closed before/);
});

test("connection dropped mid-stream fails", async () => {
  failed(await run(SUCCESS, { failAfter: 2 }), /connection to the backend was lost/);
});

test("malformed JSON in an event fails", async () => {
  failed(await run([SUCCESS[0], "event: tool_complete\ndata: {not json\n\n", SUCCESS[5]]), /could not be understood/);
});

test("event with the wrong shape fails", async () => {
  failed(await run([sse("tool_start", { tool: "missing name" })]), /could not be understood/);
  failed(await run(["event: tool_start\ndata: [1,2]\n\n"]), /could not be understood/);
});

test("done event missing required fields fails", async () => {
  const { tool_trace, ...incomplete } = BRIEFING;
  failed(await run([...SUCCESS.slice(0, 5), sse("done", incomplete)]), /could not be understood/);
});

test("abort rejects with the abort error and sends no further updates", async () => {
  const controller = new AbortController();
  const updates = [];
  const fetchFn = async (url, { signal }) => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(c) {
        c.enqueue(encoder.encode(SUCCESS[0]));
        signal.addEventListener("abort", () => c.error(signal.reason));
      },
    });
    return new Response(body, { headers: { "content-type": "text/event-stream" } });
  };
  const pending = investigate("SHP-1", (patch) => { updates.push(patch); controller.abort(); }, { signal: controller.signal, fetch: fetchFn });

  await assert.rejects(pending, (e) => !(e instanceof ApiError) && e.name === "AbortError");
  assert.equal(updates.length, 1);
});
