import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils import render_sidebar, api_get, api_post, sentiment_badge, sla_badge, status_badge, APPLE

st.set_page_config(page_title="Supervisor — CRM", page_icon="👤", layout="wide")
render_sidebar()

st.markdown(
    "<h2 style='font-weight:700;letter-spacing:-0.02em;margin-bottom:4px'>Supervisor</h2>"
    f"<p style='color:{APPLE['secondary_label']};margin-top:0'>"
    f"Casos escalados que requieren aprobación humana.</p>",
    unsafe_allow_html=True,
)
st.divider()

if "decisions" not in st.session_state:
    st.session_state["decisions"] = {}

# ── Fetch ─────────────────────────────────────────────────────────────────────
col_header, col_btn = st.columns([5, 1])
with col_header:
    st.markdown("##### Pendientes")
with col_btn:
    if st.button("Actualizar", use_container_width=True):
        st.rerun()

response = api_get("/api/v1/supervisor/pending")

if response is None:
    st.error("No se pudo conectar al backend. Verifica la URL en el sidebar.")
    st.stop()
if response.status_code != 200:
    st.error(f"Error {response.status_code}: {response.text}")
    st.stop()

pending: list = response.json()
active = [p for p in pending if p["run_id"] not in st.session_state["decisions"]]

if not active:
    st.markdown(
        f"<p style='color:{APPLE['secondary_label']};font-size:0.9rem'>No hay casos pendientes.</p>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<p style='font-size:0.82rem;color:{APPLE['secondary_label']};margin-bottom:4px'>"
        f"{len(active)} caso(s) esperando decisión</p>",
        unsafe_allow_html=True,
    )

# ── Pending items ─────────────────────────────────────────────────────────────
for item in active:
    run_id = item["run_id"]

    with st.container(border=True):
        # Header chips
        chips = (
            sentiment_badge(item["sentiment"])
            + "&nbsp;&nbsp;"
            + sla_badge(item["sla_breached"])
        )
        st.markdown(
            f"<div style='margin-bottom:10px'>"
            f"<span style='font-weight:600'>{item['client_id']}</span>"
            f"&nbsp;&nbsp;{chips}</div>",
            unsafe_allow_html=True,
        )

        # Message
        st.markdown(
            f"<blockquote style='border-left:3px solid {APPLE['blue']};"
            f"margin:0 0 12px 0;padding:8px 14px;background:{APPLE['blue']}0D;"
            f"border-radius:0 8px 8px 0;color:{APPLE['label']};font-size:0.9rem'>"
            f"{item['message']}</blockquote>",
            unsafe_allow_html=True,
        )

        # Supervisor note
        if item.get("supervisor_note"):
            st.warning(item["supervisor_note"])

        st.markdown(
            f"<p style='font-size:0.75rem;color:{APPLE['secondary_label']};margin-bottom:12px'>"
            f"Run ID: <code>{run_id}</code> · {item.get('timestamp', '')}</p>",
            unsafe_allow_html=True,
        )

        # Decision
        with st.expander("Tomar decisión", expanded=True):
            reason = st.text_input(
                "Motivo (opcional)",
                key=f"reason_{run_id}",
                placeholder="Ej: Cliente VIP, proceder con cautela...",
            )

            btn1, btn2, _ = st.columns([2, 2, 4])
            approve = btn1.button("Aprobar", key=f"approve_{run_id}", use_container_width=True, type="primary")
            reject  = btn2.button("Rechazar", key=f"reject_{run_id}", use_container_width=True)

            if approve or reject:
                payload = {
                    "run_id": run_id,
                    "approved": approve,
                    "reason": reason.strip() or None,
                }
                with st.spinner("Enviando decisión..."):
                    dec = api_post("/api/v1/supervisor/decide", payload)

                if dec is None:
                    st.error("No se pudo conectar al backend.")
                elif dec.status_code != 200:
                    st.error(f"Error {dec.status_code}: {dec.text}")
                else:
                    st.session_state["decisions"][run_id] = {"approved": approve, "result": dec.json()}
                    st.rerun()

# ── Decisions made this session ───────────────────────────────────────────────
if st.session_state["decisions"]:
    st.divider()
    st.markdown("##### Decisiones de esta sesión")

    for run_id, decision in st.session_state["decisions"].items():
        result = decision["result"]
        status = result.get("status", "")

        with st.container(border=True):
            st.markdown(
                f"{status_badge(status)}&nbsp;&nbsp;"
                f"<span style='font-size:0.82rem;color:{APPLE['secondary_label']}'>"
                f"<code>{run_id}</code></span>",
                unsafe_allow_html=True,
            )
            if result.get("execution_result"):
                st.success(result["execution_result"])
            if result.get("message"):
                st.markdown(
                    f"<p style='font-size:0.8rem;color:{APPLE['secondary_label']};margin:4px 0 0'>"
                    f"{result['message']}</p>",
                    unsafe_allow_html=True,
                )
            with st.expander("Ver JSON"):
                st.json(result)
