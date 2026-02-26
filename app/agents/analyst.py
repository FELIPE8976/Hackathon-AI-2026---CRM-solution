"""
Analyst Agent

Responsibility: Classify the incoming client message into a precise
*sentiment* and *intent* using a constrained LLM call with structured output.

Uses OpenAI function-calling under the hood via `with_structured_output`,
which eliminates free-text parsing and prevents hallucination of invalid values.
"""

from pydantic import BaseModel
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.state import AgentState
from app.core.config import settings


# ---------------------------------------------------------------------------
# Output contract — the LLM is forced to return exactly this shape
# ---------------------------------------------------------------------------

class _AnalystOutput(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    intent: Literal["refund_request", "support_request", "general_inquiry"]


# ---------------------------------------------------------------------------
# System prompt — strict, closed-domain, no room for fabrication
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a CRM message classifier for an enterprise B2B support system.

TASK: Classify the client message into exactly the categories below. \
No other values are accepted.

SENTIMENT CATEGORIES:
- "negative": dissatisfaction, frustration, anger, urgency caused by a \
problem, complaint, or implicit/explicit threat to escalate or cancel.
- "positive": satisfaction, gratitude, compliment, or explicit approval.
- "neutral": factual question, status request, or informational inquiry \
with no emotional charge.

INTENT CATEGORIES:
- "refund_request": explicit or implicit request for money back, order \
cancellation with refund, billing dispute, or chargeback.
- "support_request": report of a technical or operational problem, \
service malfunction, or a request for help resolving an issue.
- "general_inquiry": question about information, pricing, availability, \
status, or any topic not covered by the categories above.

CLASSIFICATION RULES:
1. Base your classification only on what is explicitly written or \
unambiguously implied in the message.
2. Do not assume context or history beyond the message provided.
3. When sentiment is borderline, default to "negative" — it is safer \
to escalate unnecessarily than to miss a dissatisfied client.
4. Respond exclusively with the required structured output.\
"""


# ---------------------------------------------------------------------------
# LLM singleton — instantiated once at module load, reused across requests
# ---------------------------------------------------------------------------

_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,          # deterministic: classification must be reproducible
    google_api_key=settings.GEMINI_API_KEY,
)
_structured_llm = _llm.with_structured_output(_AnalystOutput)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_analyst(state: AgentState) -> dict:
    """
    Analyst Agent node for LangGraph.

    Calls the LLM with a strict classification prompt and returns a partial
    state update. Falls back to safe defaults if the LLM call fails.
    """
    message: str = state["messages"][-1]["content"]

    try:
        result: _AnalystOutput = _structured_llm.invoke([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": message},
        ])
        sentiment = result.sentiment
        intent    = result.intent

    except Exception as exc:
        # Fallback: safe defaults that avoid silent failures blocking the pipeline
        print(f"[ANALYST] LLM error — falling back to defaults. Error: {exc}")
        sentiment = "neutral"
        intent    = "general_inquiry"

    print(f"[ANALYST] client={state['client_id']} → sentiment={sentiment}, intent={intent}")
    return {"sentiment": sentiment, "intent": intent}
