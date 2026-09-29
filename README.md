# PharmaComplaint AI – AI-Powered Customer Complaint Management System

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

## v2 — Live Medical Transcription

Added in v2: a real-time medical consultation transcription feature that
captures live audio, runs Voice Activity Detection (VAD) to filter silence,
transcribes speech via Groq's Whisper API, and generates a structured clinical
summary using an LLM.

### How it works

1. **Microphone capture** — browser `getUserMedia` captures mono audio at 16kHz.
2. **Voice Activity Detection (VAD)** — WebRTC VAD detects speech segments in
   real-time so silence and background noise are never sent to the ASR model.
   Speech aggressiveness is set to level 1 (gentle) with a 1s silence timeout
   to avoid cutting off mid-sentence.
3. **Whisper ASR** — each detected speech segment is sent to Groq's
   `whisper-large-v3` model for transcription. Transcripts stream back to the
   UI in real-time as you speak.
4. **Clinical analysis** — on demand (button click), the full transcript is
   sent to the LLM which extracts structured medical information and generates
   a clinical summary.

### Clinical fields extracted

| Field | Content |
|-------|---------|
| Patient details | Name, age, sex, identifiers |
| Chief complaint | Primary reason for visit |
| History of present illness | Onset, duration, progression |
| Symptoms | Positives + negatives separately |
| Past medical history | Prior conditions, surgeries |
| Medication history | Current meds, dosages, adherence, allergies |
| Clinical observations | Vitals, exam findings |
| Assessment | Provisional diagnosis, differentials |
| Plan | Investigations, prescriptions, advice, follow-up |
| Clinical summary | 2-3 sentence summary for the medical record |

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `WS` | `/api/transcription/ws` | Live streaming transcription (binary audio → text) |
| `POST` | `/api/transcription/analyze` | Analyze completed transcript → clinical data |

### Demo flow

1. Navigate to **Live Transcription** from the sidebar.
2. Click **Start Mic** and speak naturally — VAD auto-chunks your speech.
3. Transcript appears in real-time with word/chunk counters.
4. Click **Process Transcript with AI** to generate the clinical summary.
5. Review the structured clinical summary on the right panel.
6. Click **Copy to Prescription** to copy the formatted summary to clipboard.

## v2.1 — Transcription Accuracy Improvements

Based on a 431-word live consultation evaluation (~8.5/10 accuracy), three
improvements were added:

1. **Medical term correction** — a post-processing dictionary
   (`medical_terms.py`) fixes common Whisper misrecognitions before the text
   reaches the UI or the clinical analysis (e.g. *extensional dyspnea →
   exertional dyspnea*, *spitting bomb puffer → pitting edema*, *H4-U4 →
   HFpEF*, *age 15 age 16 → age 58*). Falls back to an LLM correction pass
   only when garbled patterns remain.
2. **Age sanity check** — the clinical analysis prompt now flags implausible
   demographics (e.g. age 15 with heart failure/diabetes/hypertension) as
   *"age may be transcription error — verify with patient"*.
3. **Token limit fix** — clinical analysis `max_tokens` raised from 1024 →
   4096 so long transcripts produce complete, valid JSON summaries.

## v1 — AI Copilot Complaint Management

### AI Copilot — Tools

The copilot is a **LangGraph** agent with intent-based routing between three
tools, all backed by **Groq's `openai/gpt-oss-20b`** (fallback `openai/gpt-oss-120b`):

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
  Dashboard — list + status
  Copilot page — chat (right) drives a read-only auto-filled form (left)
  ComplaintDetail — workflow transitions + root cause/CAPA (investigation stage)
  Transcription — live mic → transcript + clinical summary (v2)
   │  REST (axios) + WebSocket
   ▼
backend (FastAPI)
   │  SQLAlchemy ORM
   ▼
Postgres  (complaints, complaint_history)
   │
   ├── LangGraph agent (backend/app/langgraph_agent)
   │    classify_intent → [extract_fields | apply_edit | compose_reply]
   │                     → completeness_check → risk_assessment → summarize → compose_reply
   │
   ├── Transcription (backend/app/transcription)
   │    WebRTC VAD → Groq Whisper ASR → LLM clinical analysis
   │
   ▼
Groq API
   ├── LLM: openai/gpt-oss-20b (fallback openai/gpt-oss-120b)
   └── ASR: whisper-large-v3
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
| LLM        | Groq `openai/gpt-oss-20b` (fallback `openai/gpt-oss-120b`) |
| ASR        | Groq `whisper-large-v3`                       |
| VAD        | WebRTC VAD (`webrtcvad`)                      |
| Database   | PostgreSQL (SQLAlchemy ORM)                   |
| Font       | Google Inter                                  |

## Setup

### Prerequisites

- **Docker Desktop** — https://www.docker.com/products/docker-desktop
- **Git**
- A **Groq API key** — free at https://console.groq.com (used for both the LLM and Whisper ASR)

### Step 1 — Clone the repository

```bash
git clone https://github.com/musab855/pharma-ai.git
cd pharma-ai
```

### Step 2 — Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env` and set your Groq API key:

```
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_FALLBACK_MODEL=openai/gpt-oss-120b
```

### Step 3 — Start Docker Desktop

Open Docker Desktop and wait until the status light turns **green** (30–60 seconds). Verify with:

```bash
docker ps
```

### Step 4 — Run the project

```bash
docker compose up --build
```

- **First build takes 5–10 minutes** (downloading images + dependencies). Subsequent runs are instant (cached).
- Use `docker compose up` (no `--build`) on later runs.

### Step 5 — Verify it's working

Open these three URLs:

| URL | Expected result |
|-----|-----------------|
| `http://localhost:8000/api/health` | `{"status":"ok"}` |
| `http://localhost:3000` | Dashboard with complaints table |
| `http://localhost:3000/transcription` | Live transcription page |

### Ports

| Service  | Port  |
|----------|-------|
| Frontend | 3000  |
| Backend  | 8000  |
| Postgres | 5432  |

If port 5432 or 8000 is already in use (another app or project), edit
`docker-compose.yml` and change the **left side** of the port mapping
(e.g. `5433:5432` → `8001:8000`), then `docker compose up -d --force-recreate`.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `port is already allocated` | Another container is using the port. Find it: `docker ps`. Stop it or change the port in `docker-compose.yml`. |
| Microphone blocked in browser | Click the mic icon in the address bar → **Allow**, then refresh the page. Must access via `localhost`, not an IP. |
| `All Groq models failed` | Verify your API key in `backend/.env` and that the model names match (`openai/gpt-oss-20b` / `openai/gpt-oss-120b`). |
| `Analysis unavailable` | Long transcripts need `max_tokens=4096` in `backend/app/langgraph_agent/groq_client.py`. |
| Frontend shows old code after edit | Hard refresh: **Ctrl+Shift+R** (or open Incognito). Docker volume mounts sync source files to the dev server. |
| Containers start but backend crashes | Check logs: `docker compose logs backend --tail=50` |

### Run without Docker (alternative)

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
# Start PostgreSQL locally (or use a cloud DB) and set DATABASE_URL in .env
uvicorn app.main:app --reload
```

**Frontend** (separate terminal)
```bash
cd frontend
npm install
npm start
```

## Demo Flow

### v1 — AI Copilot

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
5. Try **Upload Document** with a `.pdf` or `.txt` complaint file to
   see the **Document Extraction tool** populate the same form directly
   from a document.
6. From the complaint's detail page (via the Dashboard), move it through
   **New → Under Review → Investigation → CAPA → Closed**, and add Root
   Cause / CAPA notes (these investigation fields are edited manually, since
   they come later in the workflow, after the AI-driven intake stage).

### v2 — Live Transcription

1. Navigate to **Live Transcription** from the sidebar.
2. Click **Start Mic** — Chrome will prompt for microphone permission. Click Allow.
3. Speak naturally — VAD auto-detects speech and filters silence.
4. Watch the transcript appear in real-time with word/chunk counters.
5. Click **Process Transcript with AI** to generate the clinical summary.
6. Review the structured clinical summary (patient details, chief complaint,
   symptoms, assessment, plan, etc.) on the right panel.
7. Click **Copy to Prescription** to copy the formatted summary to clipboard.
8. Click **Save Recording** to download the transcript as a `.txt` file.

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
      transcription.py            WebSocket + REST for live transcription (v2)
    langgraph_agent/
      state.py                    CopilotState (shared agent state)
      nodes.py                    classify_intent / extract_fields / apply_edit /
                                   completeness_check / risk_assessment / summarize /
                                   compose_reply
      graph.py                    Conditional routing between the 3 tools
      groq_client.py              Groq API wrapper with fallback model
    transcription/
      vad.py                      WebRTC VAD wrapper for streaming speech detection
      whisper_service.py          Groq Whisper API client (no local model)
      medical_terms.py            Dictionary + LLM correction of Whisper errors (v2.1)
      clinical_analysis.py        LLM-based clinical data extraction
frontend/
  src/
    store/
      copilotSlice.js             Chat messages + live draft complaint
      complaintsSlice.js          Dashboard list + status/investigation edits
      transcriptionSlice.js       Live transcription state (v2)
    api/client.js                 Axios API client
    pages/
      Dashboard.jsx               List + severity/status
      Copilot.jsx                 Chat-driven intake/edit (Log/Edit/Upload)
      ComplaintDetail.jsx         Workflow transitions + investigation notes
      Transcription.jsx           Live medical transcription (v2)
    components/
      AudioRecorder.jsx           Mic capture, VAD, WebSocket streaming (v2)
      ClinicalSummary.jsx         Structured clinical summary display (v2)
      StatusBadge.jsx             Severity/status badges
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
- v2 adds **Live Medical Transcription** with WebRTC VAD, Groq Whisper ASR,
  and LLM-based clinical analysis. All AI processing runs on Groq's cloud
  servers — no local GPU/RAM required.
