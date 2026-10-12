import React, { useState, useEffect } from "react";
import { 
  FileText, ShieldCheck, AlertOctagon, HelpCircle, Eye, 
  Check, X, Search, BookOpen, Clock, 
  ChevronRight, RefreshCw, Filter, ExternalLink, ShieldAlert
} from "lucide-react";
import { Finding, DocumentItem, Rule, Verdict, Severity } from "./types";
import { VerdictBadge } from "./components/VerdictBadge";
import { SeverityTag } from "./components/SeverityTag";
import { EvidenceQuote } from "./components/EvidenceQuote";
import { RuleChip } from "./components/RuleChip";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"workspace" | "rules" | "documents">("workspace");
  const [selectedVerdictFilter, setSelectedVerdictFilter] = useState<string>("all");
  const [selectedFindingId, setSelectedFindingId] = useState<string>("finding-1");
  const [backendHealth, setBackendHealth] = useState<any>(null);

  // Mock initial starter state representing an active NDA review
  const activeDocument: DocumentItem = {
    id: "doc-sample-nda-01",
    filename: "Mutual_Non_Disclosure_Agreement_Acme_Corp.pdf",
    file_type: "pdf",
    file_size_bytes: 482100,
    page_count: 5,
    is_ocr: false,
    status: "completed",
    uploaded_at: "2026-10-12T03:15:00Z",
    findings_summary: {
      compliant: 5,
      violation: 2,
      needs_review: 2,
      not_applicable: 1,
    }
  };

  const findings: Finding[] = [
    {
      id: "finding-1",
      document_id: "doc-sample-nda-01",
      rule_id: "rule-nda-02",
      rule_code: "NDA-02",
      rule_name: "Confidentiality Term & Duration Limit",
      rule_type: "numeric_threshold",
      verdict: "violation",
      severity: "high",
      evidence: {
        verbatim_quote: "The confidentiality obligations set forth herein shall survive termination of this Agreement and continue in perpetuity.",
        page_number: 2,
        char_start: 1420,
        char_end: 1545,
        verified: true,
      },
      reasoning: "The clause enforces indefinite/perpetual confidentiality obligations. Internal policy POL-SEC-04 dictates maximum confidentiality duration for standard commercial NDAs cannot exceed 3 years (36 months).",
      recommended_action: "Redline clause to specify a fixed term: '...shall expire three (3) years from the date of disclosure'.",
      confidence: 0.98,
      reviewer_status: "pending"
    },
    {
      id: "finding-2",
      document_id: "doc-sample-nda-01",
      rule_id: "rule-nda-04",
      rule_code: "NDA-04",
      rule_name: "Governing Law & Exclusive Jurisdiction",
      rule_type: "required_clause",
      verdict: "needs_review",
      severity: "medium",
      evidence: null,
      reasoning: "Multiple candidate sections mention arbitration under UNCITRAL rules, but no explicit state/country governing law clause (e.g., State of Delaware, England & Wales) was unambiguously detected.",
      recommended_action: "Confirm with legal counsel whether international UNCITRAL arbitration clause supersedes standard Delaware jurisdiction requirement.",
      confidence: 0.62,
      searches_run: [
        "hybrid_search('governing law and jurisdiction')",
        "text_search('laws of the state of')",
        "vector_search('dispute resolution applicable law forum')"
      ],
      reviewer_status: "pending"
    },
    {
      id: "finding-3",
      document_id: "doc-sample-nda-01",
      rule_id: "rule-nda-01",
      rule_code: "NDA-01",
      rule_name: "Standard Carve-outs / Exclusions Definition",
      rule_type: "required_clause",
      verdict: "compliant",
      severity: "low",
      evidence: {
        verbatim_quote: "Confidential Information shall not include information that: (a) is or becomes publicly known without breach; (b) was already in Recipient's possession prior to disclosure; (c) is independently developed by Recipient without reference to Discloser's information.",
        page_number: 1,
        char_start: 890,
        char_end: 1145,
        verified: true,
      },
      reasoning: "All mandatory carve-outs (public knowledge, prior possession, independent development) are clearly articulated in accordance with standard rule baseline.",
      recommended_action: "No redline required.",
      confidence: 0.95,
      reviewer_status: "confirmed"
    },
    {
      id: "finding-4",
      document_id: "doc-sample-nda-01",
      rule_id: "rule-nda-05",
      rule_code: "NDA-05",
      rule_name: "Prohibition of Non-Solicitation Encroachment",
      rule_type: "prohibited_term",
      verdict: "violation",
      severity: "critical",
      evidence: {
        verbatim_quote: "Recipient agrees that during the term of this Agreement and for eighteen (18) months thereafter, Recipient shall not directly or indirectly solicit, recruit, or hire any officer, employee, or independent contractor of Discloser.",
        page_number: 4,
        char_start: 3210,
        char_end: 3445,
        verified: true,
      },
      reasoning: "An unreciprocated 18-month non-solicitation covenant has been introduced into an NDA. Policy strictly prohibits embedding employee non-solicitation covenants inside preliminary confidentiality agreements.",
      recommended_action: "Strike entire section 8.2 (Non-Solicitation of Personnel) prior to execution.",
      confidence: 0.99,
      reviewer_status: "pending"
    }
  ];

  const rules: Rule[] = [
    {
      id: "rule-nda-01",
      code: "NDA-01",
      name: "Standard Carve-outs / Exclusions Definition",
      rule_set: "Standard Commercial NDA v2.1",
      version: "2.1.0",
      description: "Must contain standard exclusions: public domain, prior receipt, independent creation, and legally compelled disclosure.",
      rule_type: "required_clause",
      severity: "medium",
      applicable_document_types: ["NDA", "Confidentiality Agreement"],
      parameters: { required_elements: ["publicly known", "prior possession", "independently developed"] },
      is_active: true
    },
    {
      id: "rule-nda-02",
      code: "NDA-02",
      name: "Confidentiality Term & Duration Limit",
      rule_set: "Standard Commercial NDA v2.1",
      version: "2.1.0",
      description: "Confidentiality duration must not exceed maximum permissible threshold (36 months). Perpetual clauses are prohibited.",
      rule_type: "numeric_threshold",
      severity: "high",
      applicable_document_types: ["NDA"],
      parameters: { max_duration_months: 36, allow_perpetual: false },
      is_active: true
    },
    {
      id: "rule-nda-03",
      code: "NDA-03",
      name: "Return or Destruction of Confidential Materials",
      rule_set: "Standard Commercial NDA v2.1",
      version: "2.1.0",
      description: "Must allow certified destruction as an alternative to physical return, and permit archival backup retention under routine IT cycles.",
      rule_type: "required_clause",
      severity: "low",
      applicable_document_types: ["NDA"],
      parameters: { allow_destruction: true, allow_archival_backup: true },
      is_active: true
    },
    {
      id: "rule-nda-04",
      code: "NDA-04",
      name: "Governing Law & Exclusive Jurisdiction",
      rule_set: "Standard Commercial NDA v2.1",
      version: "2.1.0",
      description: "Must specify an approved governing jurisdiction and forum.",
      rule_type: "required_clause",
      severity: "medium",
      applicable_document_types: ["NDA", "Commercial Contract"],
      parameters: { approved_jurisdictions: ["Delaware", "New York", "England & Wales"] },
      is_active: true
    },
    {
      id: "rule-nda-05",
      code: "NDA-05",
      name: "Prohibition of Non-Solicitation Encroachment",
      rule_set: "Standard Commercial NDA v2.1",
      version: "2.1.0",
      description: "Non-solicitation of employees or contractors must not be sneaked into standard NDAs.",
      rule_type: "prohibited_term",
      severity: "critical",
      applicable_document_types: ["NDA"],
      parameters: { prohibited_terms: ["solicit", "hire any employee", "non-solicitation", "recruiting"] },
      is_active: true
    }
  ];

  useEffect(() => {
    fetch("/api/health")
      .then(res => res.json())
      .then(data => setBackendHealth(data))
      .catch(() => setBackendHealth({ status: "offline", service: "Compliance Agent API" }));
  }, []);

  const selectedFinding = findings.find(f => f.id === selectedFindingId) || findings[0];

  const filteredFindings = findings.filter(f => {
    if (selectedVerdictFilter === "all") return true;
    return f.verdict === selectedVerdictFilter;
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      {/* Disclaimer Top Bar */}
      <div className="bg-slate-900 text-slate-300 px-4 py-1.5 text-xs flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          <span className="font-medium text-slate-200">Legal Review Tooling:</span>
          <span>This system organizes and verifies clauses against policy controls. It does not provide legal advice.</span>
        </div>
        <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-400">
          <span>Backend: {backendHealth ? backendHealth.status : "Connecting..."}</span>
          <span>&bull;</span>
          <span>Model: gpt-4o-mini</span>
          <span>&bull;</span>
          <span>RuleSet: NDA-v2.1</span>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-sm bg-slate-900 text-white flex items-center justify-center font-bold font-mono text-sm">
              CA
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-900 leading-tight">Compliance Agent</h1>
              <p className="text-xs text-slate-500">Autonomous Contract & Policy Clause Verification</p>
            </div>
          </div>

          <nav className="flex items-center space-x-1 pl-6 border-l border-slate-200">
            <button
              onClick={() => setActiveTab("workspace")}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
                activeTab === "workspace" 
                  ? "bg-slate-900 text-white" 
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              Review Workspace
            </button>
            <button
              onClick={() => setActiveTab("rules")}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
                activeTab === "rules" 
                  ? "bg-slate-900 text-white" 
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              Rule Library ({rules.length})
            </button>
          </nav>
        </div>

        <div className="flex items-center space-x-3">
          <button className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-sm hover:bg-slate-50">
            <BookOpen className="w-3.5 h-3.5 text-slate-500" />
            <span>Export Report (PDF)</span>
          </button>
        </div>
      </header>

      {/* Document Summary Header (Drata/Vanta Style) */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <FileText className="w-5 h-5 text-slate-500" />
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-slate-900">{activeDocument.filename}</span>
              <span className="font-mono text-xs text-slate-400">({activeDocument.page_count} pages, {(activeDocument.file_size_bytes / 1024).toFixed(0)} KB)</span>
              <span className="text-[10px] bg-slate-100 text-slate-600 font-mono px-1.5 py-0.5 rounded-sm uppercase">OCR: {activeDocument.is_ocr ? "Used" : "No"}</span>
            </div>
            <div className="text-xs text-slate-500 flex items-center space-x-2 mt-0.5">
              <span>Ingested & Parsed</span>
              <span>&bull;</span>
              <span>Character offsets tracked</span>
              <span>&bull;</span>
              <span>Rule set: <strong className="text-slate-700 font-mono">Standard Commercial NDA v2.1</strong></span>
            </div>
          </div>
        </div>

        {/* Verdict Counters Bar */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center px-3 py-1 bg-red-50 border border-red-200 rounded-sm">
            <span className="text-xs font-medium text-red-900 mr-2">Violations:</span>
            <span className="text-xs font-bold text-red-900 font-mono">{activeDocument.findings_summary?.violation}</span>
          </div>
          <div className="flex items-center px-3 py-1 bg-amber-50 border border-amber-200 rounded-sm">
            <span className="text-xs font-medium text-amber-900 mr-2">Needs Review:</span>
            <span className="text-xs font-bold text-amber-900 font-mono">{activeDocument.findings_summary?.needs_review}</span>
          </div>
          <div className="flex items-center px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-sm">
            <span className="text-xs font-medium text-emerald-900 mr-2">Compliant:</span>
            <span className="text-xs font-bold text-emerald-900 font-mono">{activeDocument.findings_summary?.compliant}</span>
          </div>
        </div>
      </div>

      {/* Main Workspace: Three Panes */}
      {activeTab === "workspace" && (
        <div className="flex-1 grid grid-cols-12 min-h-0 divide-x divide-slate-200">
          {/* Pane 1: Findings List (Left, 3 cols) */}
          <div className="col-span-3 bg-white flex flex-col h-[calc(100vh-140px)]">
            <div className="p-3 border-b border-slate-200 bg-slate-50/50 flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600">Findings ({filteredFindings.length})</span>
                <span className="text-[11px] text-slate-400">Sorted by Severity</span>
              </div>
              <div className="flex items-center space-x-1">
                {(["all", "violation", "needs_review", "compliant"] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setSelectedVerdictFilter(f)}
                    className={`px-2 py-1 text-[11px] font-medium rounded-sm capitalize transition-colors ${
                      selectedVerdictFilter === f 
                        ? "bg-slate-900 text-white" 
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {f.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
              {filteredFindings.map(finding => {
                const isSelected = finding.id === selectedFindingId;
                return (
                  <div
                    key={finding.id}
                    onClick={() => setSelectedFindingId(finding.id)}
                    className={`p-3 cursor-pointer transition-colors ${
                      isSelected ? "bg-slate-100/90 border-l-4 border-slate-900" : "hover:bg-slate-50/80"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <RuleChip code={finding.rule_code} name={finding.rule_name} />
                      <SeverityTag severity={finding.severity} />
                    </div>
                    <div className="text-xs font-medium text-slate-900 line-clamp-1 mb-1">
                      {finding.rule_name}
                    </div>
                    <div className="flex items-center justify-between pt-1">
                      <VerdictBadge verdict={finding.verdict} size="sm" />
                      <span className="text-[11px] font-mono text-slate-400">
                        {finding.evidence ? `P.${finding.evidence.page_number}` : "Absence"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pane 2: Document Viewer (Center, 5 cols) */}
          <div className="col-span-5 bg-slate-100/60 flex flex-col h-[calc(100vh-140px)]">
            <div className="p-3 border-b border-slate-200 bg-white flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-medium text-slate-700">
                <FileText className="w-4 h-4 text-slate-400" />
                <span>Document Text Viewer</span>
                <span className="font-mono text-[11px] text-slate-400">Page 1-5</span>
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                Span Highlight: Offset [{selectedFinding.evidence?.char_start || 0}..{selectedFinding.evidence?.char_end || 0}]
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-white m-3 rounded-sm border border-slate-200 shadow-2xs">
              <div className="max-w-prose mx-auto document-prose text-xs text-slate-800 space-y-4">
                <div className="text-center pb-4 border-b border-slate-200">
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-sans">Mutual Non-Disclosure Agreement</h2>
                  <p className="text-[11px] text-slate-500 font-sans mt-0.5">Effective Date: October 1, 2026</p>
                </div>

                <p>
                  <strong>1. DEFINITIONS.</strong> "Confidential Information" refers to any proprietary information, technical data, trade secrets, or know-how disclosed by either party ("Discloser") to the other ("Recipient").
                </p>

                <p className={selectedFinding.id === "finding-3" ? "bg-emerald-50 border-l-2 border-emerald-600 pl-2 py-1" : ""}>
                  Confidential Information shall not include information that: (a) is or becomes publicly known without breach; (b) was already in Recipient's possession prior to disclosure; (c) is independently developed by Recipient without reference to Discloser's information.
                </p>

                <p>
                  <strong>2. NON-DISCLOSURE OBLIGATIONS.</strong> Recipient agrees to hold and maintain Discloser's Confidential Information in strictest confidence and exercise reasonable care to prevent unauthorized dissemination.
                </p>

                <p className={selectedFinding.id === "finding-1" ? "bg-red-50 border-l-2 border-red-600 pl-2 py-1" : ""}>
                  <strong>3. TERM AND TERMINATION.</strong> The confidentiality obligations set forth herein shall survive termination of this Agreement and continue in perpetuity.
                </p>

                <p>
                  <strong>4. RETURN OF MATERIALS.</strong> Upon written request, Recipient shall promptly return or certify destruction of all Confidential Information, provided that archival copies maintained pursuant to automated disaster recovery backups may be retained.
                </p>

                <p className={selectedFinding.id === "finding-4" ? "bg-red-50 border-l-2 border-red-600 pl-2 py-1" : ""}>
                  <strong>8. NON-SOLICITATION.</strong> Recipient agrees that during the term of this Agreement and for eighteen (18) months thereafter, Recipient shall not directly or indirectly solicit, recruit, or hire any officer, employee, or independent contractor of Discloser.
                </p>

                <p>
                  <strong>9. DISPUTE RESOLUTION.</strong> Any dispute arising under or in connection with this Agreement shall be referred to and finally resolved by arbitration administered under UNCITRAL rules.
                </p>
              </div>
            </div>
          </div>

          {/* Pane 3: Finding Detail & Reviewer Gate (Right, 4 cols) */}
          <div className="col-span-4 bg-white flex flex-col h-[calc(100vh-140px)] overflow-y-auto">
            <div className="p-4 border-b border-slate-200 bg-slate-50/50">
              <div className="flex items-center justify-between mb-2">
                <VerdictBadge verdict={selectedFinding.verdict} size="lg" />
                <SeverityTag severity={selectedFinding.severity} />
              </div>
              <h2 className="text-sm font-bold text-slate-900 leading-tight">
                {selectedFinding.rule_name}
              </h2>
              <div className="text-[11px] font-mono text-slate-500 mt-1">
                Rule ID: {selectedFinding.rule_code} &bull; Type: {selectedFinding.rule_type}
              </div>
            </div>

            <div className="p-4 space-y-4 flex-1">
              {/* Evidence Section */}
              <div>
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1.5">
                  Verbatim Source Evidence
                </label>
                <EvidenceQuote evidence={selectedFinding.evidence} />
              </div>

              {/* Reasoning Section */}
              <div>
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                  Agent Reasoning & Analysis
                </label>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-sm text-xs text-slate-800 leading-relaxed">
                  {selectedFinding.reasoning}
                </div>
              </div>

              {/* Recommended Action */}
              <div>
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                  Recommended Redline / Action
                </label>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-sm text-xs font-mono text-slate-900">
                  {selectedFinding.recommended_action}
                </div>
              </div>

              {/* Searches Run Trace (For Absence / Needs Review) */}
              {selectedFinding.searches_run && (
                <div>
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                    Searches Run Trace (Absence Verification)
                  </label>
                  <div className="p-2.5 bg-slate-900 text-slate-200 font-mono text-[11px] rounded-sm space-y-1">
                    {selectedFinding.searches_run.map((search, i) => (
                      <div key={i} className="flex items-center space-x-1.5">
                        <Search className="w-3 h-3 text-slate-400" />
                        <span>{search}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Reviewer Action Gate */}
              <div className="pt-3 border-t border-slate-200">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
                  Reviewer Gate (Human-in-the-Loop)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button className="flex items-center justify-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-emerald-800 bg-emerald-50 border border-emerald-300 rounded-sm hover:bg-emerald-100">
                    <Check className="w-3.5 h-3.5" />
                    <span>Confirm</span>
                  </button>
                  <button className="flex items-center justify-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-amber-800 bg-amber-50 border border-amber-300 rounded-sm hover:bg-amber-100">
                    <span>Override</span>
                  </button>
                  <button className="flex items-center justify-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 border border-slate-300 rounded-sm hover:bg-slate-200">
                    <span>Not Applicable</span>
                  </button>
                </div>
                <div className="mt-2 text-[11px] text-slate-400 italic">
                  All reviewer actions record an immutable audit log with user timestamp.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rule Library Tab */}
      {activeTab === "rules" && (
        <div className="p-6 max-w-6xl mx-auto w-full">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Compliance Rule Library</h2>
              <p className="text-xs text-slate-500">Versioned rules with deterministic pre-checks and LLM evaluation criteria</p>
            </div>
            <button className="px-3 py-1.5 bg-slate-900 text-white text-xs font-medium rounded-sm hover:bg-slate-800">
              + New Rule Definition
            </button>
          </div>

          <div className="bg-white border border-slate-200 rounded-sm shadow-2xs overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-mono">
                  <th className="p-3">CODE</th>
                  <th className="p-3">RULE NAME</th>
                  <th className="p-3">TYPE</th>
                  <th className="p-3">SEVERITY</th>
                  <th className="p-3">VERSION</th>
                  <th className="p-3">PARAMETERS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {rules.map(rule => (
                  <tr key={rule.id} className="hover:bg-slate-50/70">
                    <td className="p-3 font-mono font-bold text-slate-900">{rule.code}</td>
                    <td className="p-3">
                      <div className="font-semibold text-slate-900">{rule.name}</div>
                      <div className="text-slate-500 text-[11px] mt-0.5">{rule.description}</div>
                    </td>
                    <td className="p-3 font-mono text-[11px]">{rule.rule_type}</td>
                    <td className="p-3">
                      <SeverityTag severity={rule.severity} />
                    </td>
                    <td className="p-3 font-mono text-slate-500">{rule.version}</td>
                    <td className="p-3 font-mono text-[11px] text-slate-600">
                      {JSON.stringify(rule.parameters)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
