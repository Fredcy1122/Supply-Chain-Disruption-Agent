// Talks to the FastAPI backend (proxied at /api) and converts its responses
// into the shipment shape the components use.
import { ApiError } from "./investigation.js";

const NA = "Not available";

// The backend has no list endpoint yet, so the demo loads a fixed list.
const DEMO_SHIPMENTS = (import.meta.env.VITE_DEMO_SHIPMENTS || "SHP-153444,SHP-153440")
  .split(",").map((ref) => ref.trim()).filter(Boolean);

// messages maps HTTP status codes to user-facing text, with a default.
async function request(method, path, messages) {
  let res;
  try {
    res = await fetch(path, { method });
  } catch {
    throw new ApiError(0, messages.default, "The backend could not be reached.");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, messages[res.status] || messages.default, body.detail);
  return body;
}

// Order date plus scheduled shipping days, e.g. "2017-06-18 (scheduled)".
function scheduledArrival(orderDate, days) {
  const start = Date.parse(`${String(orderDate).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(start)) return NA;
  return `${new Date(start + days * 86400000).toISOString().slice(0, 10)} (scheduled)`;
}

function toShipment(shipment, prediction) {
  return {
    id: shipment.shipment_reference,
    riskLevel: prediction.risk_level.toLowerCase(),
    delayProbability: prediction.delay_probability,
    requiresInvestigation: prediction.requires_investigation,
    investigationStatus: "none",
    details: {
      product: `${shipment.product_name} (${shipment.category})`,
      origin: NA,
      destination: `${shipment.destination_city}, ${shipment.destination_country}`,
      carrier: shipment.shipping_mode,
      eta: scheduledArrival(shipment.order_date, shipment.scheduled_shipping_days),
      status: NA,
      supplier: NA,
    },
    impact: null,
    evidence: [],
    briefing: null,
    recommendations: [],
    limitations: [],
  };
}

async function loadShipment(ref) {
  const messages = { 404: "Shipment not found", default: "Could not load shipment" };
  const path = encodeURIComponent(ref);
  const [shipment, prediction] = await Promise.all([
    request("GET", `/api/shipments/${path}`, messages),
    request("POST", `/api/predictions/evaluate/${path}`, messages),
  ]);
  return toShipment(shipment, prediction);
}

// Returns the shipments that loaded and a message for each one that did not.
export async function getShipments() {
  const results = await Promise.allSettled(DEMO_SHIPMENTS.map(loadShipment));
  const shipments = results.filter((r) => r.status === "fulfilled").map((r) => r.value);
  const failures = results.flatMap((r, i) =>
    r.status === "rejected" ? [`${DEMO_SHIPMENTS[i]}: ${r.reason.message}`] : []);
  if (!shipments.length) throw new Error(failures.join("; ") || "No demo shipments configured");
  return { shipments, failures };
}
