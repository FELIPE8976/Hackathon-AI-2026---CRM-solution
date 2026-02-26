"""
Triage Agent — Critical Routing Agent

Responsibilities:
  1. Evaluate SLA compliance via deterministic datetime comparison (no LLM needed).
  2. Apply a rule-based routing matrix to decide the next action.
  3. When escalation is required, generate a concise, factual briefing note
     for the human supervisor using the LLM.

Design rationale:
  - SLA and routing logic stay deterministic: they depend on timestamps and
    enum values, not natural language reasoning. Using an LLM here would add
    latency and introduce variability with no benefit.
  - The LLM is used ONLY to produce the human-readable supervisor_note,
    where natural language synthesis genuinely adds value.
"""

from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.state import AgentState
from app.core.config import settings


# ---------------------------------------------------------------------------
# Supervisor note prompt — fired only on escalations
# ---------------------------------------------------------------------------

_SUPERVISOR_NOTE_PROMPT = """\
You are a CRM triage specialist drafting a briefing note for a human supervisor.

You will receive structured data about a client case. Write a note that:
- Is exactly 2 sentences long.
- Sentence 1: state the reason this case requires human intervention \
(reference sentiment, SLA breach, or both — only what is true).
- Sentence 2: recommend a specific, actionable next step the supervisor \
should take.

CONSTRAINTS:
- Professional enterprise tone. No informal language.
- Do not invent information beyond what is provided.
- Do not mention agent names, internal system names, or technical terms.
- Do not use filler phrases like "I hope this helps" or "Please note that".\
"""


# ---------------------------------------------------------------------------
# LLM singleton — low temperature for consistent, professional phrasing
# ---------------------------------------------------------------------------

_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.1,        # slight variation for natural phrasing, not creativity
    google_api_key=settings.GEMINI_API_KEY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_sla(timestamp_iso: str) -> bool:
    """Returns True if the message is older than the configured SLA threshold."""
    try:
        msg_time = datetime.fromisoformat(timestamp_iso)
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=timezone.utc)
        elapsed_hours = (datetime.now(timezone.utc) - msg_time).total_seconds() / 3600
        return elapsed_hours > settings.SLA_THRESHOLD_HOURS
    except (ValueError, KeyError):
        return False  # malformed timestamp: do not penalise with a false SLA breach


def _generate_supervisor_note(state: AgentState, sla_breached: bool) -> str | None:
    """
    Calls the LLM to produce a 2-sentence escalation briefing for the supervisor.
    Returns None on failure so the pipeline is never blocked.
    """
    reasons = []
    if state.get("sentiment") == "negative":
        reasons.append("negative client sentiment")
    if sla_breached:
        reasons.append(f"SLA breach (threshold: {settings.SLA_THRESHOLD_HOURS}h)")

    user_context = (
        f"Client ID: {state['client_id']}\n"
        f"Client message: \"{state['messages'][-1]['content']}\"\n"
        f"Detected sentiment: {state.get('sentiment', 'unknown')}\n"
        f"Detected intent: {state.get('intent', 'unknown')}\n"
        f"Escalation reasons: {', '.join(reasons) if reasons else 'policy rule'}\n"
        f"SLA breached: {sla_breached}"
    )

    try:
        response = _llm.invoke([
            {"role": "system", "content": _SUPERVISOR_NOTE_PROMPT},
            {"role": "user",   "content": user_context},
        ])
        return response.content.strip()
    except Exception as exc:
        print(f"[TRIAGE] Supervisor note generation failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_triage(state: AgentState) -> dict:
    """
    Triage Agent node for LangGraph.

    Applies the routing matrix and, when escalating, generates a supervisor note.
    Returns a partial state update.

    Routing matrix
    --------------
    | Condition                              | proposed_action           |
    |----------------------------------------|---------------------------|
    | sentiment == "negative" OR sla_breached| escalate_to_human         |
    | intent == "refund_request"             | process_refund            |
    | all other cases                        | send_standard_response    |
    """
    sla_breached    = _check_sla(state["timestamp"])
    sentiment       = state.get("sentiment", "neutral")
    intent          = state.get("intent", "general_inquiry")
    supervisor_note = None

    # ------------------------------------------------------------------ #
    # Routing decision — deterministic rule-based matrix                  #
    # ------------------------------------------------------------------ #
    if sla_breached or sentiment == "negative":
        proposed_action = "escalate_to_human"
        supervisor_note = _generate_supervisor_note(state, sla_breached)

    elif intent == "refund_request":
        proposed_action = "process_refund"

    else:
        proposed_action = "send_standard_response"

    print(
        f"[TRIAGE]  client={state['client_id']} → "
        f"sla_breached={sla_breached}, proposed_action={proposed_action}"
    )

    return {
        "sla_breached":    sla_breached,
        "proposed_action": proposed_action,
        "supervisor_note": supervisor_note,
    }
