# Control Tower (React frontend)

Start the FastAPI backend on port 8000, then:

    npm install && npm run dev

Vite proxies `/api` to `http://localhost:8000`.

## Configuration

`VITE_DEMO_SHIPMENTS` (see `.env.example`) lists the shipment references to load,
for example `SHP-153444,SHP-153440`. Without it, those two are used.

## API flow

1. For each demo shipment:
   - `GET /api/shipments/{ref}` returns the shipment facts.
   - `POST /api/predictions/evaluate/{ref}` returns the delay probability, risk level and whether investigation is required.
2. "Start investigation" opens `GET /api/agent/investigate/{ref}/stream` (Server-Sent Events, read with `fetch`) and updates the list of steps as events arrive. Each tool is shown as a user-facing step ("Assessing delay risk", "Checking shipment details", "Reviewing historical delay patterns", "Checking destination weather") with a one-line finding; tool names and raw results are never shown.
   - `tool_start`: the step is shown as in progress.
   - `tool_complete` / `tool_error`: the step shows its finding, or that the information could not be retrieved.
   - `message`: "Preparing briefing".
   - `done`: "Investigation complete" with the briefing, the same body as `POST /api/agent/investigate/{ref}`. Its `limitations` are shown under the steps, its `recommended_actions` under Actions, and the summary under Briefings.
   - `error`: the investigation failed; `status`, `code` and `detail` say why.
   While the backend reports that its recommendations are placeholders (the "RAG retrieval is not yet integrated" limitation), they are not shown: Actions and the briefing say that approved operational recommendations will appear when the knowledge base is connected, and the briefing summary is built from the risk level and probability.
3. An investigation is "Complete" only when a valid `done` event was received. Otherwise:
   - `investigation_not_required`: "Low risk — no investigation needed"
   - `shipment_not_found` or HTTP 404: "Shipment not found"
   - anything else, including a lost connection, a malformed event or a stream that ends early: "Investigation failed"

`npm test` checks the stream handling with Node's built-in test runner.

Origin, status, supplier and business impact are not provided by the backend yet and show as "Not available". Approve and Dismiss decisions are kept in the browser only.
