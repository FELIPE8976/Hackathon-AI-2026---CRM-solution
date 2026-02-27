import streamlit as st
import requests
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
SLA_THRESHOLD_HOURS = float(os.environ.get("SLA_THRESHOLD_HOURS", "2.0"))
WEBHOOK_API_KEY = os.environ.get("WEBHOOK_API_KEY", "")

# ---------------------------------------------------------------------------
# Apple HIG — System Colors
# ---------------------------------------------------------------------------

APPLE = {
    "blue":   "#007AFF",
    "green":  "#34C759",
    "red":    "#FF3B30",
    "orange": "#FF9500",
    "gray":   "#8E8E93",
    "bg":     "#F2F2F7",
    "label":  "#1C1C1E",
    "secondary_label": "#6D6D72",
}

SENTIMENT_COLOR = {
    "positive": APPLE["green"],
    "neutral":  APPLE["gray"],
    "negative": APPLE["red"],
}

STATUS_COLOR = {
    "processed":             APPLE["green"],
    "pending_approval":      APPLE["orange"],
    "approved_and_executed": APPLE["green"],
    "rejected":              APPLE["red"],
}

STATUS_LABEL = {
    "processed":             "Procesado",
    "pending_approval":      "Pendiente de aprobación",
    "approved_and_executed": "Aprobado y ejecutado",
    "rejected":              "Rechazado",
}

ACTION_LABEL = {
    "send_standard_response": "Respuesta estándar",
    "process_refund":         "Procesar reembolso",
    "escalate_to_human":      "Escalar a supervisor",
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def apply_styles():
    st.markdown(
        """
        <style>
        /* ── Typography ─────────────────────────────────────────────────── */
        html, body, [class*="css"], .stMarkdown, .stText {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                         "Helvetica Neue", Arial, sans-serif;
        }
        h1, h2, h3 {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                         "Helvetica Neue", Arial, sans-serif;
            font-weight: 600;
            letter-spacing: -0.02em;
        }

        /* ── Layout ─────────────────────────────────────────────────────── */
        .main .block-container {
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            max-width: 900px;
        }

        /* ── Sidebar ─────────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background-color: #F2F2F7;
            border-right: 1px solid rgba(0,0,0,0.08);
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(0,0,0,0.08);
        }

        /* ── Bordered containers ─────────────────────────────────────────── */
        [data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 14px !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            padding: 4px 0;
        }

        /* ── Metric cards ────────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background-color: #F2F2F7;
            border-radius: 12px;
            padding: 14px 18px;
        }
        [data-testid="metric-container"] label {
            font-size: 0.72rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #8E8E93 !important;
        }

        /* ── Buttons ─────────────────────────────────────────────────────── */
        [data-testid="baseButton-primary"],
        [data-testid="baseButton-secondary"],
        [data-testid="baseButton-secondaryFormSubmit"] {
            border-radius: 10px !important;
            font-weight: 500 !important;
            letter-spacing: -0.01em;
        }

        /* ── Inputs ──────────────────────────────────────────────────────── */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] > div {
            border-radius: 10px !important;
            border: 1px solid rgba(0,0,0,0.12) !important;
            background-color: #FFFFFF;
        }

        /* ── Alert boxes ─────────────────────────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 12px !important;
            border: none !important;
        }

        /* ── Expander ────────────────────────────────────────────────────── */
        [data-testid="stExpander"] summary {
            border-radius: 10px !important;
            font-weight: 500;
        }

        /* ── Divider ─────────────────────────────────────────────────────── */
        hr {
            border-color: rgba(0,0,0,0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    apply_styles()
    with st.sidebar:
        st.markdown(
            "<p style='font-size:1.15rem;font-weight:600;margin-bottom:0;"
            "letter-spacing:-0.02em'>CRM Multi-Agent</p>"
            "<p style='font-size:0.8rem;color:#8E8E93;margin-top:2px'>Hackathon AI 2026</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        if "api_url" not in st.session_state:
            st.session_state["api_url"] = DEFAULT_API_URL

        new_url = st.text_input(
            "Backend URL",
            value=st.session_state["api_url"],
            help="URL base del servidor FastAPI",
            label_visibility="visible",
        )
        st.session_state["api_url"] = (new_url or DEFAULT_API_URL).rstrip("/")
        st.divider()


def get_api_url() -> str:
    return st.session_state.get("api_url", DEFAULT_API_URL)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def api_get(path: str):
    try:
        return requests.get(get_api_url() + path, timeout=15)
    except requests.exceptions.RequestException:
        return None


def api_post(path: str, payload: dict):
    try:
        headers = {"X-Api-Key": WEBHOOK_API_KEY} if WEBHOOK_API_KEY else {}
        return requests.post(get_api_url() + path, json=payload, headers=headers, timeout=90)
    except requests.exceptions.RequestException:
        return None


def api_get_auth(path: str, token: str):
    """GET with JWT Bearer token — use for protected supervisor endpoints."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(get_api_url() + path, headers=headers, timeout=15)
    except requests.exceptions.RequestException:
        return None


def api_post_auth(path: str, payload: dict, token: str):
    """POST with JWT Bearer token — use for protected supervisor endpoints."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        return requests.post(get_api_url() + path, json=payload, headers=headers, timeout=15)
    except requests.exceptions.RequestException:
        return None


def login(username: str, password: str):
    """Call POST /api/v1/auth/login (form-data) and return the token string or None."""
    try:
        response = requests.post(
            get_api_url() + "/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=20,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except requests.exceptions.RequestException:
        return None


def api_get_metrics() -> dict | None:
    """Call GET /api/v1/metrics/summary and return the parsed JSON or None."""
    response = api_get("/api/v1/metrics/summary")
    if response and response.status_code == 200:
        return response.json()
    return None


# ---------------------------------------------------------------------------
# Badge helpers — Apple HIG HTML chips
# ---------------------------------------------------------------------------

def _chip(label: str, color: str) -> str:
    """Renders an Apple-style filled pill badge."""
    return (
        f'<span style="display:inline-block;background:{color};color:#fff;'
        f'padding:3px 11px;border-radius:20px;font-size:0.8rem;font-weight:500;'
        f'letter-spacing:0.01em;line-height:1.5">{label}</span>'
    )


def sentiment_badge(sentiment: str) -> str:
    color = SENTIMENT_COLOR.get(sentiment, APPLE["gray"])
    return _chip(sentiment.capitalize(), color)


def status_badge(status: str) -> str:
    color = STATUS_COLOR.get(status, APPLE["gray"])
    label = STATUS_LABEL.get(status, status.replace("_", " ").capitalize())
    return _chip(label, color)


def action_label(action: str) -> str:
    return ACTION_LABEL.get(action, action.replace("_", " ").capitalize())


def sla_badge(breached: bool) -> str:
    if breached:
        return _chip("SLA vencido", APPLE["red"])
    return _chip("SLA OK", APPLE["green"])


# ---------------------------------------------------------------------------
# Info card (replaces st.metric for richer display)
# ---------------------------------------------------------------------------

def info_card(label: str, value: str) -> str:
    """Returns an Apple HIG-style info card as HTML."""
    return (
        f'<div style="background:#F2F2F7;border-radius:12px;padding:14px 18px">'
        f'<p style="font-size:0.72rem;font-weight:500;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:#8E8E93;margin:0 0 6px 0">{label}</p>'
        f'<p style="font-size:0.95rem;font-weight:500;color:#1C1C1E;margin:0">{value}</p>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# SLA timestamp helper
# ---------------------------------------------------------------------------

def timestamp_from_hours_ago(hours: float) -> datetime:
    """Returns a UTC datetime that is `hours` ago from now."""
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def sla_preview(hours_ago: float) -> str:
    """Returns an HTML badge indicating if the given age would breach SLA."""
    if hours_ago > SLA_THRESHOLD_HOURS:
        return _chip(f"SLA vencido — {hours_ago:.1f}h > {SLA_THRESHOLD_HOURS:.0f}h", APPLE["red"])
    remaining = SLA_THRESHOLD_HOURS - hours_ago
    return _chip(f"Dentro del SLA — quedan {remaining:.1f}h", APPLE["green"])
