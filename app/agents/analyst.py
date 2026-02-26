"""
Analyst Agent (Mock)

Responsibility: Extract *sentiment* and *intent* from the latest client message.

This is a keyword-based mock. Replace the body of `run_analyst` with an LLM
call (e.g. langchain_openai.ChatOpenAI) once the API key is available.
"""

from app.agents.state import AgentState

# ---------------------------------------------------------------------------
# Keyword dictionaries (bilingual EN / ES for CRM context)
# ---------------------------------------------------------------------------

_NEGATIVE_KEYWORDS = {
    # English
    "urgent", "angry", "terrible", "worst", "horrible", "unacceptable",
    "furious", "awful", "disgusting", "broken", "damaged", "fraud", "scam",
    # Spanish
    "urgente", "enojado", "terrible", "pésimo", "horrible", "inaceptable",
    "furioso", "estafado", "fraude", "dañado", "roto", "molesto",
}

_POSITIVE_KEYWORDS = {
    # English
    "great", "happy", "thanks", "thank", "excellent", "wonderful",
    "perfect", "love", "amazing", "satisfied", "pleased",
    # Spanish
    "genial", "feliz", "gracias", "excelente", "maravilloso",
    "perfecto", "encanta", "increíble", "satisfecho",
}

_REFUND_KEYWORDS = {
    "refund", "reimbursement", "money back", "charge back",
    "devolución", "reembolso", "devolver dinero",
}

_SUPPORT_KEYWORDS = {
    "support", "help", "issue", "problem", "error", "not working", "fix",
    "soporte", "ayuda", "problema", "error", "no funciona", "arreglar",
}


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_analyst(state: AgentState) -> dict:
    """
    Mock Analyst Agent node.

    Reads the last message in `state["messages"]`, infers sentiment and
    intent, and returns a partial state update.

    Returns a *dict* (not a full AgentState) — LangGraph merges it into
    the existing state automatically.
    """
    message: str = state["messages"][-1]["content"].lower()
    words = set(message.split())

    # --- Sentiment ---
    if words & _NEGATIVE_KEYWORDS:
        sentiment = "negative"
    elif words & _POSITIVE_KEYWORDS:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # --- Intent (check multi-word phrases too) ---
    if any(kw in message for kw in _REFUND_KEYWORDS):
        intent = "refund_request"
    elif any(kw in message for kw in _SUPPORT_KEYWORDS):
        intent = "support_request"
    else:
        intent = "general_inquiry"

    print(f"[ANALYST] client={state['client_id']} → sentiment={sentiment}, intent={intent}")

    return {"sentiment": sentiment, "intent": intent}
