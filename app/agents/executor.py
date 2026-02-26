"""
Executor Agent (Mock)

Responsibility: Simulate sending an automated response to the client.

In production this node would call:
  - An email/SMS gateway
  - A CRM write API (create ticket, update status)
  - A payment/refund processor
"""

from app.agents.state import AgentState

# ---------------------------------------------------------------------------
# Response templates keyed by proposed_action
# ---------------------------------------------------------------------------

_RESPONSE_TEMPLATES: dict[str, str] = {
    "send_standard_response": (
        "Dear valued client, we have received your message and our team will "
        "get back to you within 24 hours. Thank you for your patience."
    ),
    "process_refund": (
        "Dear client, we have initiated a refund for your account. "
        "You will receive a confirmation email within 3–5 business days."
    ),
}

_DEFAULT_TEMPLATE = _RESPONSE_TEMPLATES["send_standard_response"]


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_executor(state: AgentState) -> dict:
    """
    Mock Executor Agent node.

    Picks the right response template based on `proposed_action`, logs the
    simulated send, and returns an execution_result string.
    """
    action = state.get("proposed_action", "send_standard_response")
    response_body = _RESPONSE_TEMPLATES.get(action, _DEFAULT_TEMPLATE)

    result = (
        f"[MOCK SEND] To: client={state['client_id']} | "
        f"Action: {action} | Message: \"{response_body}\""
    )
    print(f"[EXECUTOR] {result}")

    return {"execution_result": result}
