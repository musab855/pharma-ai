# AIVOA – AI-Powered Customer Complaint Management System

Round 1 Full Stack Developer Assessment submission, built for the pharmaceutical
manufacturing (API/FDF) industry.

## Background: Customer Complaints in a Pharma QMS

In a pharmaceutical Quality Management System (aligned to 21 CFR 211.198 and
ICH Q10), the **Customer Complaint** module is the entry point for any
product-quality signal reported from the field — a pharmacy, distributor,
patient, or sales rep. A complaint must be logged with full traceable context
(who, what product/batch, when, what happened), triaged for completeness and
severity, investigated (root cause, CAPA), and closed out.

This project digitizes that lifecycle as **New → Under Review → Investigation
→ CAPA → Closed** (or **Rejected**), and — per the reference demo — the
intake/edit step is driven entirely through an **AI Copilot chat interface**,
not a manual form. The user describes or pastes a complaint (or uploads a
document) in the copilot chat; the AI extracts structured fields, fills the
form, and runs an initial risk assessment.

## AI Copilot — Tools

The copilot is a **LangGraph** agent with intent-based routing between three
tools, all backed by **Groq's `gemma2-9b-it`** (fallback `llama-3.3-70b-versatile`):

1. **Log Complaint tool** — triggered when there's no existing complaint yet.
   Extracts structured fields (customer, product, batch, mfg/expiry dates,
   description, type) from the user's free-text message, creates the
   complaint record, checks completeness against mandatory QMS intake
   fields, and runs risk assessment.
2. **Edit Complaint tool** — triggered on a message against an already-logged
   complaint (e.g. "change the batch number to X"). The LLM diffs the
   instruction against the current field values, returns only the fields
   that should change, and the risk assessment is re-run on the merged data.
3. **Document Extraction tool** — same extraction pipeline as Log Complaint,
   but sourced from an uploaded file instead of typed/pasted text. Native support
   for `.pdf` (using `pypdf`) and `.txt` files, with null-byte sanitization for
   database safety. Production-grade OCR (for scanned images) is out of scope per
   the brief.

A message that isn't a data change (a plain question) is routed to a general
**chat** reply instead of triggering either tool.

### Risk Assessment (populates the copilot panel)

After Log or Edit, a dedicated `risk_assessment` node asks the LLM for:
- **Severity** (Critical / Major / Minor)
- **Suggested next action** (what Quality should do next)
- **Initial risk assessment** (short justification: patient-safety impact,
  batch-wide vs isolated, GMP implications)

### Completeness Checker (bonus feature)

Deterministic, rule-based scoring against the mandatory intake fields
(customer, product, batch, mfg date, expiry date, description, type) — kept
rule-based rather than LLM-driven so the score is consistent and auditable,
regardless of how the LLM phrases things.

### Structured Defect Summary (bonus feature)

A concise, LLM-written synthesis of the complaint for the official QMS
record, shown on both the copilot form and the complaint detail page.

## Architecture

```
frontend (React + Redux Toolkit)
  Copilot page — chat (right) drives a read-only auto-filled form (left)
  Dashboard — list + status
  ComplaintDetail — workflow transitions + root cause/CAPA (investigation stage)
   │  REST (axios)
   ▼
backend (FastAPI)
   │  SQLAlchemy ORM
   ▼
Postgres  (complaints, complaint_history)
   │
   ▼
LangGraph agent (backend/app/langgraph_agent)
   classify_intent → [extract_fields | apply_edit | compose_reply]
                    → completeness_check → risk_assessment → summarize → compose_reply
   │
   ▼
Groq API (gemma2-9b-it, fallback llama-3.3-70b-versatile)
```

### LangGraph graph (`backend/app/langgraph_agent/graph.py`)

`classify_intent` conditionally routes to one of three paths:

- **log_new** → `extract_fields` (Log Complaint tool) → `completeness_check`
  → `risk_assessment` → `summarize` → `compose_reply`
- **edit_existing** → `apply_edit` (Edit Complaint tool) → `risk_assessment`
  → `summarize` → `compose_reply`
- **general_chat** → `compose_reply` directly (plain LLM answer, no tool)

State is a `TypedDict` (`CopilotState`) threaded through all nodes.

### Why intent-routing instead of one fixed pipeline

The copilot needs to behave differently for "log this complaint" vs.
"change the batch number" vs. "what does CAPA mean" — a single linear
pipeline can't do that. Routing on intent first, then reusing the shared
`risk_assessment`/`summarize` nodes on whichever path was taken, keeps the
three tools from duplicating logic while still behaving like distinct tools
from the user's point of view.

## Tech Stack

| Layer      | Choice                                      |
|------------|----------------------------------------------|
| Frontend   | React 18 + Redux Toolkit + React Router       |
| Backend    | Python FastAPI                                |
| AI Agent   | LangGraph                                     |
| LLM        | Groq `gemma2-9b-it` (fallback `llama-3.3-70b-versatile`) |
| Database   | PostgreSQL (SQLAlchemy ORM)                   |
| Font       | Google Inter                                  |

## Setup

### 1. Environment variables

```bash
cp backend/.env.example backend/.env
# then edit backend/.env and set GROQ_API_KEY=<your key from console.groq.com>
```

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend docs (Swagger): http://localhost:8000/docs
- Postgres: localhost:5432 (user/pass/db: `aivoa`/`aivoa`/`aivoa_complaints`)

### 3. Run manually (without Docker)

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# make sure Postgres is running locally and DATABASE_URL in .env points to it
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm start
```

## Demo Flow

1. Go to **Log Complaint (AI Copilot)**. Click **Try Sample Complaint** (or
   type/paste your own, e.g. *"Apollo Pharmacy reported discolored capsules
   in Amoxicillin capsules 500mg. Batch number AMX240602, manufacturing date
   March 2026, expiry date Feb 2028. Please log this complaint."*).
2. The **Log Complaint tool** fires: the left-hand form fills in
   automatically, and the copilot replies with completeness %, severity,
   and a suggested next action.
3. In the same chat, type an edit instruction, e.g. *"change the batch
   number to AMX240999"* — the **Edit Complaint tool** fires, updates the
   form, and re-runs the risk assessment.
4. Try `sample_data/sample_complaint_2_incomplete.txt` (paste its contents)
   to see the completeness checker flag missing fields.
5. Try **📎 Upload Document** with a `.pdf` or `.txt` complaint file to
   see the **Document Extraction tool** populate the same form directly 
   from a document.
6. From the complaint's detail page (via the Dashboard), move it through
   **New → Under Review → Investigation → CAPA → Closed**, and add Root
   Cause / CAPA notes (these investigation fields are edited manually, since
   they come later in the workflow, after the AI-driven intake stage).

## Repository Structure

```
backend/
  app/
    main.py                       FastAPI app entrypoint
    models.py                     SQLAlchemy models (Complaint, ComplaintHistory)
    schemas.py                    Pydantic schemas incl. Copilot request/response
    crud.py                       DB ops: copilot create/edit, status transitions
    routers/
      complaints.py               List/get/status/manual investigation fields
      copilot.py                  POST /api/copilot/message, /api/copilot/upload
    langgraph_agent/
      state.py                    CopilotState (shared agent state)
      nodes.py                    classify_intent / extract_fields / apply_edit /
                                   completeness_check / risk_assessment / summarize /
                                   compose_reply
      graph.py                    Conditional routing between the 3 tools
      groq_client.py               Groq API wrapper with fallback model
frontend/
  src/
    store/
      copilotSlice.js             Chat messages + live draft complaint
      complaintsSlice.js          Dashboard list + status/investigation edits
    api/client.js                 Axios API client
    pages/
      Dashboard.jsx                List + severity/status
      Copilot.jsx                  Chat-driven intake/edit (Log/Edit/Upload)
      ComplaintDetail.jsx           Workflow transitions + investigation notes
    components/StatusBadge.jsx
sample_data/                      Sample complaint text files (1 complete, 1 incomplete)
docker-compose.yml
```

## Notes on Scope

- Per the brief, uploaded/pasted text simulates parsed email/PDF/OCR content
  rather than building production-grade OCR.
- Bonus scope for this submission: **Completeness Checker + Structured
  Summary**, plus **Risk Assessment** (severity, suggested action,
  justification) since it's core to the demoed copilot flow. Duplicate
  detection, root-cause recommendation, and CAPA recommendation are natural
  next additions on the same `CopilotState`/graph.

