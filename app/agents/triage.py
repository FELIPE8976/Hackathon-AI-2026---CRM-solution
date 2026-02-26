"""
Triage Agent — Critical Agent (Mock)

Responsibility:
  1. Evaluate SLA compliance by comparing the message timestamp to *now*.
  2. Decide the routing action based on sentiment + SLA status.

Replace with an LLM-based reasoning chain when ready.
"""

from datetime import datetime, timezone
from app.agents.state import AgentState
from app.core.config import settings


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_triage(state: AgentState) -> dict:
    """
    Mock Triage Agent node.

    Decision matrix
    ---------------
    | Sentiment  | SLA OK | SLA Breached | Action                |
    |------------|--------|--------------|-----------------------|
    | negative   |   *    |      *       | escalate_to_human     |
    | any        |  no    |      yes     | escalate_to_human     |
    | any        |  refund|      no      | process_refund        |
    | positive / neutral | no  |  no    | send_standard_response|
    """

    # ------------------------------------------------------------------ #
    # 1. SLA check                                                         #
    # ------------------------------------------------------------------ #
    sla_breached = False
    try:
        msg_time = datetime.fromisoformat(state["timestamp"])
        # Make timezone-aware if naive
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=timezone.utc)
        elapsed_hours = (datetime.now(timezone.utc) - msg_time).total_seconds() / 3600
        sla_breached = elapsed_hours > settings.SLA_THRESHOLD_HOURS
    except (ValueError, KeyError):
        # Malformed timestamp → do not breach SLA by default
        sla_breached = False

    # ------------------------------------------------------------------ #
    # 2. Routing decision                                                  #
    # ------------------------------------------------------------------ #
    sentiment = state.get("sentiment", "neutral")
    intent = state.get("intent", "general_inquiry")

    if sla_breached or sentiment == "negative":
        proposed_action = "escalate_to_human"
    elif intent == "refund_request":
        proposed_action = "process_refund"
    else:
        proposed_action = "send_standard_response"

    print(
        f"[TRIAGE]  client={state['client_id']} → sla_breached={sla_breached}, "
        f"proposed_action={proposed_action}"
    )

    return {"sla_breached": sla_breached, "proposed_action": proposed_action}
