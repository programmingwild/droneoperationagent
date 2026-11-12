# Drone Ops Agent

Production-grade, multi-agent RAG application for UAS/drone fleet maintenance and mission readiness.

> **Safety notice:** This is an engineering demo for decision support. It is **not** certified for real-world flight operations. Any `TAKEOFF`/arm recommendation is gated by a **human-in-the-loop (HITL) approval** step — never treat this system as an autonomous authorizer.

## What it does

- **RAG over real drone-domain docs** (FAA Part 107, EASA Open Category, DGCA Drone Rules, a hexacopter flight manual, a maintenance checklist, and a hexacopter UAV paper PDF). Answers are grounded in retrieved passages and **must include citations** (source + section/page). If retrieval confidence is below threshold, the agent refuses to guess and issues safe guidance.
- **Multi-agent graph (LangGraph)** with explicit routing/handoffs: `triage → {mission_planning | maintenance | regulation | anomaly} → safety_supervisor → (human_approval if required) → finalize`.
- **Real tool functions** (not mocked): physics-based battery/range estimator, flight-log CSV parser + anomaly scoring, airspace/NOTAM proxy (real METAR + clearly labelled simulated NOTAMs), SQLite/Postgres ticket writer, PDF report exporter.
- **Production basics**: FastAPI (`/chat` SSE, `/approve`, `/approvals/pending`, `/logs`, `/tickets/{id}`, `/report/{id}`, `/health`), Pydantic validation, structured JSON logging, env-gated LangSmith tracing, retrieval eval dataset (20 Q/A) + harness, pytest suite, Docker + docker-compose, GitHub Actions CI.
- **Streamlit UI**: chat with streaming agent trace, citations, ticket table, and a visible **pending human approval** banner.

## Architecture

```mermaid
flowchart LR
  U[Operator / Streamlit UI] -->|POST /chat SSE| API[FastAPI]
  API --> G[LangGraph]
  G --> T[Triage Router]
  T -->|mission_planning| M[Mission Planning Agent]
  T -->|maintenance / anomaly| MA[Maintenance & Log Agent]
  T -->|regulation| R[Regulation Compliance Agent]
  M --> S[Safety / HITL Supervisor]
  MA --> S
  R --> S
  S -->|requires approval| H[human_approval\ninterrupt_before + /approve]
  S -->|no authorization| F[Finalize]
  H --> F
  M -->|tools| BT[Battery-range estimator]
  MA -->|tools| FL[Flight-log parser + anomaly scoring]
  MA --> TK[Ticket writer + PDF export]
  R -->|RAG| VS[(Pinecone or local vector store)]
  R -->|tool| AX[Airspace/NOTAM proxy]
  VS --> DOCS[DGCA/EASA/FAA rules + manual + checklist + UAV paper]
  G --> CK[(SQLite checkpointer)]
  API --> DB[(SQLite/Postgres: tickets, approvals, run audit)]
```

**Typed state & handoffs:** `backend/app/agents/state.py` defines the shared `AgentState` (TypedDict). Triage sets `classification`; specialists populate `answer`, `citations`, `recommended_action`, `tool_results`; the safety supervisor sets `requires_approval`/`approval_id` and routes to HITL or finalize.

**HITL (required):** if the output implies takeoff/arm authorization (e.g., `recommended_action` in `TAKEOFF|ARM` or authorization keywords), the safety node persists a `PENDING` approval record and the graph is compiled with `interrupt_before=["human_approval"]`. The run pauses; an operator decides via `POST /approve` (or the Streamlit banner), which resumes the graph and records the decision. Approval persistence/resume failures fail **safe** (authorization blocked / rejected).

## Stack

- Python 3.12, FastAPI, Pydantic v2
- LangGraph (primary) + LangChain utilities; OpenAI (pluggable) with an **honest offline fallback** when no key is set
- Embeddings: OpenAI `text-embedding-3-small` or local `sentence-transformers/all-MiniLM-L6-v2`
- Vector store: **Pinecone** (serverless, cosine) or **local JSON+numpy** (`VECTOR_BACKEND=auto`)
- Storage: SQLite by default; Postgres via `DATABASE_URL` (used in docker-compose)
- Streamlit UI, Docker/Compose, GitHub Actions, AWS App Runner config (`apprunner.yaml`)

## Repository layout

```
backend/app/
  agents/        graph.py, nodes.py, state.py, llm.py, prompts.py
  rag/           chunking.py, embeddings.py, vectorstore.py, ingest.py, retrieve.py
  tools/         battery.py, flight_logs.py, notam.py, ticket.py, report.py
  evals/         eval_dataset.json (20 Q/A), run_eval.py
  main.py        FastAPI endpoints, SSE chat, HITL approve
frontend/        streamlit_app.py
data/docs/       regulations + manual + checklist + pdf/hexacopter_uav_design_paper.pdf
tests/           pytest suite (graph transitions, tools, RAG chunking, NOTAM, SSE slim)
evals/           results.json (latest run)
docs/            demo.gif, screenshot_approval_banner.jpeg
```

## Setup (local, offline-capable)

**Prereqs:** Python 3.12+. (Optional) [Docker Desktop](https://www.docker.com/products/docker-desktop/) for the one-command stack.

```bash
python -m venv .venv
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# Windows (cmd):        .venv\Scripts\activate.bat
# macOS/Linux:          source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env   # Windows (or: cp .env.example .env) — add keys only in .env

# Build the corpus + vector index (uses local embeddings if no OpenAI key)
python -m backend.app.rag.ingest --reset
```

**LLM provider.** Any one of: `OPENAI_API_KEY` (credited), or Groq's free tier (`GROQ_API_KEY` + `LLM_PROVIDER=groq`, OpenAI-compatible endpoint), or neither for labelled `[OFFLINE MODE]` extractive answers. Embeddings stay local (`EMBEDDING_PROVIDER=local`) so the checked-in 384-dim index remains valid — only the chat model changes.

## Run

**API (FastAPI):**
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
# docs: http://127.0.0.1:8000/docs   health: http://127.0.0.1:8000/health
```

**UI (Streamlit):**
```bash
streamlit run frontend/streamlit_app.py
# UI: http://localhost:8501  (DRONEOPS_API defaults to http://127.0.0.1:8000)
```

**One command (Docker Compose):**
```bash
copy .env.example .env   # set secrets in .env (never commit)
docker compose up --build
# UI http://localhost:8501  |  API http://localhost:8000  |  Postgres internal
```
**Docker setup (Windows):** install [Docker Desktop](https://www.docker.com/products/docker-desktop/), enable WSL2 backend if prompted, start Docker Desktop, then run the commands above from the repo root. Compose runs Postgres for the API; the image bakes the corpus + embeddings for an offline cold start. *Docker isn’t installed in this dev environment, so run/verify this on your Docker-enabled machine.*

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/chat` | Run the agent; **Server-Sent Events** stream (`run_started`, `node`, `approval_required`/`final`, `error`). Body: `{"query": "...", "log_file?": "...", "lat?": ..., "lon?": ...}` |
| `POST` | `/approve` | HITL decision; resumes an interrupted run. Body: `{"approval_id": "...", "approved": true/false, "decided_by": "..."}` |
| `GET` | `/approvals/pending` | Pending HITL approvals |
| `GET` | `/logs` | Tickets, approvals, recent runs, available flight-log CSVs |
| `GET` | `/tickets/{ticket_id}` | Ticket detail |
| `POST` | `/report/{ticket_id}` | Export ticket as `application/pdf` |
| `GET` | `/health` | Liveness + provider/backend status |

## Eval & tests

```bash
python -m pytest -q                 # tool + graph-transition tests (no live LLM required)
python -m backend.app.evals.run_eval  # 20 Q/A retrieval eval -> evals/results.json
```

Latest checked-in eval (`evals/results.json`, local embeddings, `top_k=4`, threshold `0.33`): **n=20, hit@1=0.90, hit@k=1.00, confident_rate=1.00, mean_top_score=0.5639**. The harness is retrieval-focused and offline-safe; add an LLM-as-judge only when `OPENAI_API_KEY` is configured (env-gated, consistent with LangSmith tracing).

## LangSmith tracing

Tracing is **env-gated** and off by default. Enable it in `.env`:
```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-rotated-key>   # never commit
LANGSMITH_PROJECT=droneops
# regional/custom endpoint if needed (e.g. EU or AWS-hosted):
LANGSMITH_ENDPOINT=https://aws.api.smith.langchain.com
```
`/health` reports `langsmith_tracing`. Restart the API after changes.

**Trace screenshot (required artifact):** `docs/langsmith_trace.png` is a **rendered snapshot of a real trace** fetched read-only from the LangSmith API (project `droneops`, trace `01a1cde7-…`, 7 spans, 0 errors). It shows the graph run tree (`LangGraph → triage → maintenance → safety_supervisor → finalize`) plus the root run inputs/outputs.

Regenerate / capture your own:
1. Set the vars above (use a **rotated** key; never paste keys in chat/commits) and restart the API.
2. Run a traced query (`POST /chat` or via Streamlit).
3. Either open [LangSmith](https://smith.langchain.com/) → project `droneops` → run/graph trace and screenshot it, or regenerate this snapshot:
   ```bash
   python scripts/fetch_langsmith_trace.py        # lists recent traces + trace ids
   python scripts/render_langsmith_trace.py <trace_id>
   ```
   (the renderer writes `docs/langsmith_trace.html`; screenshot it to `docs/langsmith_trace.png`).

![LangSmith trace — real run from project droneops](docs/langsmith_trace.png)

## Wiring a real NOTAM provider

Default is **simulated and labelled** (safe for demo). To use a real keyed provider (FAA official access is registered; many teams use a commercial NOTAM API):
1. Choose a provider and get its endpoint + API key.
2. In `.env`: `NOTAM_PROVIDER=http`, `NOTAM_API_URL=<provider endpoint>`, `NOTAM_API_KEY=<key>`. If the key is a query param, set `NOTAM_API_KEY_PARAM` (e.g. `access_key`) instead of the header.
3. Restart the API and call with coords (e.g., `{"query":"check airspace","lat":28.61,"lon":77.20}`) — confirm `notam_source` shows `http:<host>` and advisories are real.
4. If the provider fails, the tool **falls back to a clearly-labelled simulated advisory** (never silent). Verify NOTAMs/TFRs with an authoritative briefing before any real flight.

## Demo assets

- `docs/demo.gif` — UI/demo capture
- `docs/screenshot_approval_banner.jpeg` — HITL pending-approval banner

## Real vs simulated (honest)

| Component | Status | Notes |
|---|---|---|
| RAG corpus (DGCA/EASA/FAA, manual, checklist, UAV paper PDF) | **Real documents/content in-repo** | Ingested with metadata filters (`doc_type`, `section/page`, `regulation`). |
| Chunking, embeddings, vector search, citations | **Real** | Recursive chunking w/ overlap; Pinecone or local JSON+cosine. |
| Battery-range estimator | **Real** (physics model) | C-rate, voltage sag, wind margin, reserve; deterministic. |
| Flight-log parser + anomaly scoring | **Real** (deterministic) | CSV schema, imbalance/vibration/sag/temp rules, verdict, ticket creation. |
| METAR/TAF (aviationweather.gov) | **Real, no key**, with cache | Graceful offline mode. |
| NOTAM feed | **Pluggable: SIMULATED by default** (clearly labelled) or **real HTTP provider** when configured | METAR/TAF is real (aviationweather.gov). For real NOTAMs set `NOTAM_PROVIDER=http`, `NOTAM_API_URL`, `NOTAM_API_KEY` (and `NOTAM_API_KEY_HEADER`/`NOTAM_API_KEY_PARAM` as needed). Responses are best-effort mapped and `notam_source` is truthful; failures fall back to a labelled simulated advisory. **Never treat simulated NOTAMs as operational.** Verify via an authoritative briefing before flight. |
| LLM answers | **Real (OpenAI or Groq) or labelled offline fallback** | Without `OPENAI_API_KEY`/`GROQ_API_KEY`, responses are extractive and explicitly marked `[OFFLINE MODE]`. |
| Sample flight log / generated paper asset | **Sample/synthetic corpus assets** | For reproducible demo/eval; replace with your real fleet data. |

## Limitations

- Regulation answers are grounded in the bundled excerpts, not a live, complete legal database — verify with the authoritative aviation authority/portal (FAA LAANC/1800wxbrief, EASA, DGCA Digital Sky) before any real flight.
- NOTAM/TFR layer is simulated until a keyed provider is integrated.
- Triage falls back to keyword routing offline; mission-planning battery overrides are parsed heuristically from text.
- The safety model gates obvious authorization phrases/actions, but it is not a certified safety case. HITL is mandatory, not optional.
- Local vector store/embeddings are for dev/demo scale; use Pinecone + managed DB for production workloads.
- Never commit secrets — keep keys in `.env` (see `.env.example`).

## What I learned about agentic failure modes

Building a safety-relevant multi-agent system taught me most failures are *coordination and grounding* failures, not model cleverness failures. First, **ungrounded confidence** is the default risk: a fluent answer can be wrong, so I gate regulation responses on retrieval confidence, refuse with safe guidance rather than guessing, and require citations on every grounded claim. Second, **tool and state failures must fail safe**: if a tool or approval record errors, the graph returns `HOLD` instead of proceeding on partial truth. Third, **HITL is a control-flow guarantee, not a UI hint** — I enforce it with LangGraph `interrupt_before`, persisted approval state, and resume, so “takeoff authorized” cannot be emitted without a recorded human decision. Fourth, **routing errors compound**: a misrouted query reaches the wrong evidence and tools, so typed state and explicit handoffs matter. Finally, **observability is part of correctness** — structured logs, per-node traces, and env-gated LangSmith/evals make failure modes debuggable instead of mysterious.
