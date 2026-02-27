import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils import (
    render_sidebar,
    api_post,
    sentiment_badge,
    status_badge,
    sla_badge,
    action_label,
    info_card,
    sla_preview,
    timestamp_from_hours_ago,
    APPLE,
    SLA_THRESHOLD_HOURS,
)

st.set_page_config(page_title="Mensajes — CRM", page_icon="📨", layout="wide")
render_sidebar()

st.markdown(
    "<h2 style='font-weight:700;letter-spacing:-0.02em;margin-bottom:4px'>Mensajes</h2>"
    f"<p style='color:{APPLE['secondary_label']};margin-top:0'>"
    f"Simula un mensaje entrante y observa el pipeline en acción.</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── SLA Configurator (outside form → actualiza en vivo) ───────────────────────
st.markdown("##### Antigüedad del mensaje")

col_slider, col_indicator = st.columns([3, 2])

with col_slider:
    hours_ago = st.slider(
        "Hace cuántas horas se envió el mensaje",
        min_value=0.0,
        max_value=12.0,
        value=0.0,
        step=0.5,
        format="%.1f h",
        help=f"El umbral de SLA está configurado en {SLA_THRESHOLD_HOURS:.0f} horas",
    )

with col_indicator:
    st.markdown("<div style='padding-top:28px'>", unsafe_allow_html=True)
    st.markdown(sla_preview(hours_ago), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ── Message Form ──────────────────────────────────────────────────────────────
st.markdown("##### Mensaje")

col_form, col_examples = st.columns([3, 2])

with col_form:
    with st.form("message_form"):
        client_id = st.text_input("Client ID", value="CRM-001")
        message = st.text_area(
            "Mensaje del cliente",
            height=140,
            placeholder="Ej: My order arrived damaged and I want a refund immediately!",
        )
        submitted = st.form_submit_button(
            "Enviar al pipeline", use_container_width=True, type="primary"
        )

with col_examples:
    st.markdown(
        f"<p style='font-size:0.8rem;font-weight:500;color:{APPLE['secondary_label']};"
        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px'>"
        f"Ejemplos</p>",
        unsafe_allow_html=True,
    )
    examples = [
        ("Negativo + reembolso",  "I demand a refund! This is unacceptable!"),
        ("Consulta neutral",      "Could you help me track my order?"),
        ("Negativo en español",   "Necesito un reembolso, estoy muy enojado."),
        ("Positivo",              "Great service, thanks for the quick response!"),
    ]
    for label, text in examples:
        st.markdown(
            f"<p style='font-size:0.75rem;color:{APPLE['secondary_label']};margin:8px 0 2px'>"
            f"{label}</p>",
            unsafe_allow_html=True,
        )
        st.code(text, language=None)

# ── Process ───────────────────────────────────────────────────────────────────
if submitted:
    if not client_id.strip():
        st.error("El Client ID no puede estar vacío.")
        st.stop()
    if not message.strip():
        st.error("El mensaje no puede estar vacío.")
        st.stop()

    ts = timestamp_from_hours_ago(hours_ago)

    payload = {
        "client_id": client_id.strip(),
        "message":   message.strip(),
        "timestamp": ts.isoformat(),
    }

    with st.spinner("Procesando con los agentes..."):
        response = api_post("/api/v1/webhook/messages", payload)

    st.divider()

    if response is None:
        st.error(
            "El pipeline tardó demasiado o el backend no responde. "
            "Los modelos de IA en free tier pueden demorar hasta 60 s. "
            "Verifica que el backend esté corriendo y reintenta."
        )
        st.stop()

    if response.status_code != 200:
        st.error(f"Error {response.status_code}: {response.text}")
        st.stop()

    data = response.json()
    status = data.get("status", "")

    st.markdown(
        "<h3 style='font-weight:600;letter-spacing:-0.02em;margin-bottom:12px'>Resultado</h3>",
        unsafe_allow_html=True,
    )

    if status == "processed":
        st.success("El mensaje fue procesado y respondido automáticamente.")
    elif status == "pending_approval":
        st.warning("El caso fue escalado al supervisor para su aprobación.")
    else:
        st.info(data.get("message", status))

    # ── Info cards ──
    cards_html = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0">'
        + info_card("Sentimiento", sentiment_badge(data.get("sentiment", "-")))
        + info_card("Intención", data.get("intent", "-").replace("_", " ").capitalize())
        + info_card("Acción", action_label(data.get("proposed_action", "-")))
        + info_card("SLA", sla_badge(data.get("sla_breached", False)))
        + "</div>"
    )
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Details ──
    st.markdown(
        f"<p style='font-size:0.82rem;color:{APPLE['secondary_label']};margin-bottom:12px'>"
        f"Run ID: <code>{data.get('run_id', '-')}</code></p>",
        unsafe_allow_html=True,
    )

    if data.get("supervisor_note"):
        st.markdown("**Nota para el supervisor**")
        st.warning(data["supervisor_note"])

    if data.get("execution_result"):
        st.markdown("**Respuesta al cliente**")
        st.success(data["execution_result"])
    elif status == "pending_approval":
        st.markdown(
            f"<p style='color:{APPLE['secondary_label']};font-size:0.9rem'>"
            f"Pendiente — en espera de aprobación del supervisor.</p>",
            unsafe_allow_html=True,
        )

    with st.expander("Ver respuesta JSON completa"):
        st.json(data)
