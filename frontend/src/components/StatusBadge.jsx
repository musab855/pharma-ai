import React from "react";

export function SeverityBadge({ severity }) {
  const cls = (severity || "Unclassified").toLowerCase();
  return <span className={`badge ${cls}`}>{severity || "Unclassified"}</span>;
}

export function StatusBadge({ status }) {
  return <span className="badge status">{status}</span>;
}
