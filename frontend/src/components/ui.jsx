export const NA = "Not available";
const isNumber = (v) => typeof v === "number" && Number.isFinite(v);
export const pct = (p) => (isNumber(p) ? `${Math.round(p * 100)}%` : NA);
export const money = (n) => (isNumber(n) ? `$${n.toLocaleString()}` : NA);

export const RiskBadge = ({ level }) => <span className={`badge ${level}`}>{level}</span>;

export const StatusChip = ({ status }) => (
  <span className={`chip ${status}`}>{status === "none" ? "Not started" : status === "running" ? "Investigating" : status === "complete" ? "Complete" : status === "not_required" ? "Not required" : "Failed"}</span>
);

export const Meter = ({ value, level }) => (
  <div className="meter" title={pct(value)}><i className={level} style={{ width: isNumber(value) ? pct(value) : 0 }} /></div>
);

export const Empty = ({ children }) => <div className="empty">{children}</div>;
