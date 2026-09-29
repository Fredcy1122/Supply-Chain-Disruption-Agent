export const pct = (p) => `${Math.round(p * 100)}%`;
export const money = (n) => `$${n.toLocaleString()}`;

export const RiskBadge = ({ level }) => <span className={`badge ${level}`}>{level}</span>;

export const StatusChip = ({ status }) => (
  <span className={`chip ${status}`}>{status === "none" ? "Not started" : status === "running" ? "Investigating" : status === "complete" ? "Complete" : "Failed"}</span>
);

export const Meter = ({ value, level }) => (
  <div className="meter" title={pct(value)}><i className={level} style={{ width: pct(value) }} /></div>
);

export const Empty = ({ children }) => <div className="empty">{children}</div>;
