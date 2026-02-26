"""
In-memory store for pending human-approval requests.

NOTE: This is an MVP/demo store. In production, replace with Redis or a
persistent database so that state survives server restarts and scales
across multiple workers.
"""
from typing import Dict, Any

# key: run_id (str)  →  value: AgentState dict
pending_approvals: Dict[str, Dict[str, Any]] = {}
