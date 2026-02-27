# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CRM Multi-Agent REST API using LangGraph for pipeline orchestration and Google Gemini as the LLM. The system routes incoming CRM messages through three specialized agents (Analyst → Triage → Executor) with optional Human-in-the-Loop (HITL) escalation when sentiment is negative or SLA is breached.

## Commands

### Setup
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

Create a `.env` file with:
```
GEMINI_API_KEY=your_key_here
SLA_THRESHOLD_HOURS=2.0
```

### Run the server
```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### Run tests
```bash
# Server must be running first, then in a separate terminal:
python run_tests.py
```

## Architecture

The application is a FastAPI server backed by a LangGraph `StateGraph`. All state flows through `AgentState` (defined in `app/agents/state.py`), a TypedDict with fields like `sentiment`, `intent`, `proposed_action`, `sla_breached`, `supervisor_note`, `execution_result`.

### Agent Pipeline

```
POST /api/v1/webhook/messages
    └─► analyst node      → classifies sentiment + intent via Gemini (temp=0, structured output)
    └─► triage node       → deterministic SLA check + routing; LLM only for supervisor_note
    └─► conditional edge:
        ├─ proposed_action == "escalate_to_human"
        │   → stores state in pending_approvals dict (app/core/store.py), returns "pending_approval"
        └─ otherwise
            └─► executor node  → generates personalized response via Gemini (temp=0.3, bilingual)
```

### HITL Flow
1. Escalated messages are stored in the in-memory `pending_approvals: dict` keyed by `run_id` (UUID).
2. Supervisor retrieves them via `GET /api/v1/supervisor/pending`.
3. Supervisor posts a decision to `POST /api/v1/supervisor/decide` with `approved: bool`.
4. If approved, `run_executor(state)` is called directly (bypassing the LangGraph graph).

### Key Files

| File | Role |
|------|------|
| `app/main.py` | FastAPI app assembly, router registration |
| `app/agents/state.py` | `AgentState` TypedDict — the shared state contract |
| `app/agents/orchestrator.py` | LangGraph `StateGraph` assembly; exports `crm_graph` singleton |
| `app/agents/analyst.py` | Gemini call with `with_structured_output()` for sentiment/intent |
| `app/agents/triage.py` | Deterministic SLA logic + routing matrix + optional LLM note |
| `app/agents/executor.py` | Response generation; auto language detection (EN/ES) |
| `app/core/config.py` | `Settings` (pydantic-settings); `GEMINI_API_KEY`, `SLA_THRESHOLD_HOURS` |
| `app/core/store.py` | In-memory `pending_approvals` dict (no persistence between restarts) |
| `app/models/schemas.py` | Pydantic v2 models for API request/response shapes |
| `app/api/endpoints/webhooks.py` | `POST /webhook/messages` handler |
| `app/api/endpoints/supervisor.py` | `GET/POST /supervisor/*` handlers |

### Triage Routing Matrix

| Condition | `proposed_action` |
|-----------|-------------------|
| `sentiment == "negative"` OR `sla_breached == True` | `escalate_to_human` |
| `intent == "refund_request"` | `process_refund` |
| otherwise | `send_standard_response` |

## Tech Stack

- **Python 3.12**, FastAPI 0.111+, Uvicorn
- **LangGraph 0.2** — StateGraph pipeline orchestration
- **langchain-google-genai** — Gemini 2.5 Flash Lite (`gemini-2.5-flash-lite`)
- **Pydantic v2** — schemas and settings

## Limitations to Be Aware Of

- `pending_approvals` is an in-memory dict — all pending approvals are lost on server restart.
- There is no database persistence; the system is designed as an MVP/hackathon demo.
- The `run_executor()` function is called directly (not through the LangGraph graph) when a supervisor approves an escalation.
