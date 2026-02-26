"""
LangGraph Orchestrator

Defines and compiles the CRM automation state machine:

    ┌─────────┐     ┌────────┐     ┌──────────────────────┐
    │ analyst │────▶│ triage │────▶│ executor  (auto OK)  │──▶ END
    └─────────┘     └────────┘  │  └──────────────────────┘
                                │
                                └▶ END  (escalate_to_human → supervisor pause)

The graph is compiled once at import time and reused across requests.
"""

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.analyst import run_analyst
from app.agents.triage import run_triage
from app.agents.executor import run_executor


# ---------------------------------------------------------------------------
# Routing / conditional edge logic
# ---------------------------------------------------------------------------

def _route_after_triage(state: AgentState) -> str:
    """
    Returns the name of the next node (or a key that maps to END).

    'needs_human'  → the graph pauses here; the supervisor endpoint resumes it.
    'auto_execute' → proceed to the executor node automatically.
    """
    if state.get("proposed_action") == "escalate_to_human":
        return "needs_human"
    return "auto_execute"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Build and compile the LangGraph state machine."""

    workflow = StateGraph(AgentState)

    # -- Nodes ---------------------------------------------------------------
    workflow.add_node("analyst", run_analyst)
    workflow.add_node("triage", run_triage)
    workflow.add_node("executor", run_executor)

    # -- Entry point ---------------------------------------------------------
    workflow.set_entry_point("analyst")

    # -- Edges ---------------------------------------------------------------
    workflow.add_edge("analyst", "triage")

    workflow.add_conditional_edges(
        "triage",
        _route_after_triage,
        {
            "needs_human": END,    # pause — waits for supervisor decision
            "auto_execute": "executor",
        },
    )

    workflow.add_edge("executor", END)

    return workflow.compile()


# Singleton — compiled once, shared across all FastAPI requests.
crm_graph = build_graph()
