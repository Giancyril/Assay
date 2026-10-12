import React from "react";
import { Verdict } from "../types";

interface VerdictBadgeProps {
  verdict: Verdict;
  size?: "sm" | "md" | "lg";
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({ verdict, size = "md" }) => {
  const styles = {
    compliant: {
      bg: "var(--verdict-compliant-bg)",
      text: "var(--verdict-compliant-text)",
      border: "var(--verdict-compliant-border)",
      label: "Compliant",
    },
    violation: {
      bg: "var(--verdict-violation-bg)",
      text: "var(--verdict-violation-text)",
      border: "var(--verdict-violation-border)",
      label: "Violation",
    },
    needs_review: {
      bg: "var(--verdict-review-bg)",
      text: "var(--verdict-review-text)",
      border: "var(--verdict-review-border)",
      label: "Needs Review",
    },
    not_applicable: {
      bg: "var(--verdict-na-bg)",
      text: "var(--verdict-na-text)",
      border: "var(--verdict-na-border)",
      label: "Not Applicable",
    },
  }[verdict];

  const sizeStyle = size === "sm" ? "px-2 py-0.5 text-xs" : size === "lg" ? "px-3 py-1.5 text-sm font-semibold" : "px-2.5 py-1 text-xs font-medium";

  return (
    <span
      className={`inline-flex items-center rounded-sm border ${sizeStyle}`}
      style={{
        backgroundColor: styles.bg,
        color: styles.text,
        borderColor: styles.border,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5" style={{ backgroundColor: styles.text }}></span>
      {styles.label}
    </span>
  );
};
