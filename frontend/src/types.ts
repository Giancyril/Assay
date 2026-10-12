export type Verdict = "compliant" | "violation" | "needs_review" | "not_applicable";

export type Severity = "low" | "medium" | "high" | "critical";

export type RuleType = "required_clause" | "prohibited_term" | "numeric_threshold" | "conditional";

export interface EvidenceQuote {
  verbatim_quote: string;
  page_number: number;
  char_start: number;
  char_end: number;
  verified: boolean;
}

export interface Finding {
  id: string;
  document_id: string;
  rule_id: string;
  rule_code: string;
  rule_name: string;
  rule_type: RuleType;
  verdict: Verdict;
  severity: Severity;
  evidence: EvidenceQuote | null;
  reasoning: string;
  recommended_action: string;
  confidence: number;
  searches_run?: string[];
  reviewer_status?: "pending" | "confirmed" | "overridden" | "not_applicable";
  reviewer_override_reason?: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: "pdf" | "docx";
  file_size_bytes: number;
  page_count: number;
  is_ocr: boolean;
  status: "uploaded" | "parsing" | "parsed" | "checking" | "completed" | "error";
  uploaded_at: string;
  findings_summary?: {
    compliant: number;
    violation: number;
    needs_review: number;
    not_applicable: number;
  };
}

export interface Rule {
  id: string;
  code: string;
  name: string;
  rule_set: string;
  version: string;
  description: string;
  rule_type: RuleType;
  severity: Severity;
  applicable_document_types: string[];
  parameters: Record<string, any>;
  is_active: boolean;
}
