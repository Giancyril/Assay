# Compliance Agent

A production-grade, AI-augmented autonomous compliance agent that analyzes policies, contracts, and agreements, extracts key clauses, evaluates them against versioned compliance rules, detects violations, and provides deterministic evidence verification for every finding.

> **Legal Disclaimer**: This software is an automated contract analysis and issue organization tool for human compliance reviewers. It does not provide legal advice or substitute for licensed legal counsel.

---

## Core Loop

$$\text{Documents} \longrightarrow \text{Rules} \longrightarrow \text{Evidence} \longrightarrow \text{Report}$$

1. **Ingest Documents**: Extract text while preserving exact page numbers and character offsets.
2. **Index & Retrieve Clauses**: Structure-aware chunking on headings/sections with hybrid retrieval (vector + full-text search).
3. **Check Rules**: LangGraph state graph evaluating each rule with structured verdicts.
4. **Verify Evidence**: Deterministic quote verification against the source document (unverified quotes are rejected).
5. **Generate Report**: Summaries by verdict, verbatim quotes, audit trail, and PDF/Markdown export.

---

## 4 Core Invariants

1. **No finding without verified evidence**: Every finding must include a verbatim quote from the document plus its page number and character offsets. A deterministic code check validates that the quote actually exists in the source text. If it does not, the finding is rejected.
2. **Three outcomes, never two**: Every rule check ends as `Compliant`, `Violation`, or `Needs human review`. Absence of a clause records the searches executed so a reviewer can inspect the trace.
3. **Rules are data, not prompts**: Rules live in a versioned table with specific types (`required_clause`, `prohibited_term`, `numeric_threshold`, `conditional`). Pre-checks use deterministic regexes where possible.
4. **Document text is untrusted input**: Document content is labeled and isolated before reaching models to defend against prompt-injection and override instructions.

---

## System Architecture

```mermaid
graph TD
    subgraph Client ["Frontend (React 18 + TypeScript + Vite)"]
        UI["Review Workspace (Three-Pane UI)"]
        Summary["Document Summary Header (Drata/Vanta Style)"]
        Viewer["Document Text / PDF Viewer (Highlighting)"]
        Findings["Findings List (Grouped by Verdict & Severity)"]
        ReviewGate["Reviewer Gate (Confirm / Override / N/A)"]
    end

    subgraph Server ["Backend (FastAPI + LangGraph)"]
        API["FastAPI Endpoints (/api/health, /api/documents, /api/rules)"]
        Ingestion["Ingestion Engine (PyMuPDF / docx / OCR Fallback)"]
        OffsetTracker["Page & Character Offset Tracker"]
        Indexer["Hybrid Clause Indexer (Vector + pgvector & Full-Text)"]
        Agent["LangGraph Compliance Agent (Retrieve -> Judge -> Verify)"]
        Verifier["Deterministic Evidence Verifier"]
        Reporter["Report Generator (Markdown / PDF)"]
    end

    subgraph Storage ["Data & Storage Layer"]
        PG[(PostgreSQL + pgvector)]
        AuditLog[(Append-Only Audit Log)]
        Disk[(Isolated Document Storage)]
    end

    UI --> API
    API --> Ingestion
    Ingestion --> OffsetTracker
    OffsetTracker --> Indexer
    Indexer --> PG
    API --> Agent
    Agent --> Verifier
    Verifier --> AuditLog
    Agent --> Reporter
```

---

## Project Structure

```
Compliance Agent/
├── backend/
│   ├── app/               # FastAPI application, config, database sessions, health checks
│   ├── ingestion/         # Document parsers (PDF, DOCX, OCR fallback) with offset tracking
│   ├── indexing/          # Structure-aware chunking, embeddings, pgvector + full-text search
│   ├── rules/             # Rule schema, versioning, starter NDA library, deterministic regexes
│   ├── agent/             # LangGraph state graph: retrieve -> judge -> verify -> review interrupt
│   ├── evidence/          # Verbatim quote verification and offset resolution
│   └── reporting/         # Compliance report generators (Markdown / PDF)
├── frontend/              # React + Vite + TypeScript (Three-pane review workspace, rule library)
├── eval/                  # Evaluation datasets (CUAD-compatible, adversarial prompt injection)
├── infra/                 # Docker Compose with PostgreSQL + pgvector
├── scripts/               # Commit helpers (commit-stage.sh, commit-stage.ps1)
└── tests/                 # Unit and integration test suites
```

---

## Starter Rule Library (Commercial NDAs)

| Code | Rule Name | Type | Severity | Description |
| :--- | :--- | :--- | :--- | :--- |
| **NDA-01** | Standard Carve-outs & Exclusions | `required_clause` | HIGH | Public domain, prior possession, independent development |
| **NDA-02** | Confidentiality Term Limit | `numeric_threshold` | HIGH | Maximum duration $\le 36$ months; perpetual duration prohibited |
| **NDA-03** | Return or Destruction of Materials | `required_clause` | LOW | Certified destruction and archival IT backup carve-outs |
| **NDA-04** | Approved Governing Law & Forum | `required_clause` | MEDIUM | Delaware, New York, or England & Wales |
| **NDA-05** | Prohibition of Non-Solicitation | `prohibited_term` | CRITICAL | Non-solicitation covenants prohibited inside standard NDAs |
| **NDA-06** | Permitted Compelled Disclosures | `required_clause` | HIGH | Subpoenas/court orders permitted with prompt written notice |
| **NDA-07** | Standard of Care | `required_clause` | MEDIUM | Reasonable care; highest possible care / absolute guarantee prohibited |
| **NDA-08** | Injunctive Relief & Remedies | `required_clause` | LOW | Right to equitable remedies without posting bond |
| **NDA-09** | As-Is Information Disclaimer | `required_clause` | LOW | No implied warranties of accuracy or completeness |
| **NDA-10** | Prohibition of Non-Circumvent | `prohibited_term` | HIGH | Deal exclusivity and lock-up terms prohibited in preliminary NDAs |

---

## Quickstart & Local Setup

### 1. Database (Docker Compose)
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2. Backend
```bash
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```
Health Check: `http://localhost:8000/api/health`

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
UI Workspace: `http://localhost:5173`

### 4. Run Tests
```bash
pytest tests/ -v
```

---

## License

MIT
