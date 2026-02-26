"""
Executor Agent

Responsibility: Draft and deliver a professional, personalised client response.

The LLM is given the original client message, the confirmed action, and strict
stylistic constraints so that every response is:
  - Written in the client's own language (EN or ES detected automatically).
  - Empathetic but concise (2–4 sentences).
  - Free of internal jargon, agent identifiers, or process details.
  - Actionable — every response closes with a clear next step.
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.state import AgentState
from app.core.config import settings


# ---------------------------------------------------------------------------
# Action context injected into the prompt — tells the LLM WHAT to communicate
# ---------------------------------------------------------------------------

_ACTION_CONTEXT: dict[str, str] = {
    "send_standard_response": (
        "Acknowledge receipt of the client's message, confirm the team is reviewing "
        "the case, and assure the client they will receive a follow-up."
    ),
    "process_refund": (
        "Confirm that the refund request has been accepted and is being processed. "
        "Specify that the client will receive a confirmation by email and that funds "
        "are returned within 3 to 5 business days."
    ),
}

_FALLBACK_ACTION_CONTEXT = _ACTION_CONTEXT["send_standard_response"]


# ---------------------------------------------------------------------------
# System prompt — strict style and content constraints
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a professional CRM response specialist for an enterprise company.

Your task: write one client-facing response message.

STYLE RULES (mandatory):
1. Detect the language of the client's message and respond in that exact language \
(English or Spanish). Do not mix languages.
2. Tone: professional, empathetic, and solution-focused. Never robotic or distant.
3. Length: 2 to 4 sentences. No more.
4. Do NOT open with generic filler such as "We value your business", \
"Thank you for contacting us", or "I hope this message finds you well".
5. Do NOT disclose internal processes, system names, agent IDs, or SLA metrics.
6. Do NOT make promises about specific resolution dates or times.
7. Address the specific concern raised in the client's message directly.
8. Close with one concrete next step or a clear confirmation of the action taken.

CONTENT INSTRUCTION:
{action_context}\
"""


# ---------------------------------------------------------------------------
# LLM singleton — slightly higher temperature for natural, varied phrasing
# ---------------------------------------------------------------------------

_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3,        # natural variation in phrasing while staying professional
    google_api_key=settings.GEMINI_API_KEY,
)


# ---------------------------------------------------------------------------
# Fallback responses (used only if the LLM call fails)
# ---------------------------------------------------------------------------

_FALLBACK_RESPONSES: dict[str, str] = {
    "send_standard_response": (
        "We have received your message and a member of our team will follow up "
        "with you shortly. Thank you for your patience."
    ),
    "process_refund": (
        "Your refund request has been received and is being processed. "
        "You will receive an email confirmation within 3–5 business days."
    ),
}


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_executor(state: AgentState) -> dict:
    """
    Executor Agent node for LangGraph.

    Generates a personalised client response using the LLM and returns a
    partial state update containing the execution_result.
    Falls back to a static professional message if the LLM call fails.
    """
    action         = state.get("proposed_action", "send_standard_response")
    action_context = _ACTION_CONTEXT.get(action, _FALLBACK_ACTION_CONTEXT)
    client_message = state["messages"][-1]["content"]

    system_prompt = _SYSTEM_PROMPT.format(action_context=action_context)

    try:
        response = _llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Client message: {client_message}"},
        ])
        execution_result = response.content.strip()

    except Exception as exc:
        print(f"[EXECUTOR] LLM error — using static fallback. Error: {exc}")
        execution_result = _FALLBACK_RESPONSES.get(action, _FALLBACK_RESPONSES["send_standard_response"])

    print(f"[EXECUTOR] client={state['client_id']} → response drafted for action={action}")
    return {"execution_result": execution_result}
