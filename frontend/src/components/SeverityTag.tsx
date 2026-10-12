import React from "react";
import { Severity } from "../types";

export const SeverityTag: React.FC<{ severity: Severity }> = ({ severity }) => {
  const map: Record<Severity, { label: string; bg: string; text: string; border: string }> = {
    critical: { label: "CRITICAL", bg: "#450a0a", text: "#fecaca", border: "#7f1d1d" },
    high: { label: "HIGH", bg: "#7f1d1d", text: "#fee2e2", border: "#991b1b" },
    medium: { label: "MEDIUM", bg: "#fef3c7", text: "#92400e", border: "#fde68a" },
    low: { label: "LOW", bg: "#f1f5f9", text: "#475569", border: "#e2e8f0" },
  };
  const s = map[severity] || map.low;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 text-[10px] font-mono font-semibold rounded-sm tracking-wider border"
      style={{ backgroundColor: s.bg, color: s.text, borderColor: s.border }}
    >
      {s.label}
    </span>
  );
};
