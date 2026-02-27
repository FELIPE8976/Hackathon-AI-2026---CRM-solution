import streamlit as st
from utils import render_sidebar, api_get, APPLE

st.set_page_config(
    page_title="CRM Multi-Agent",
    page_icon="🤖",
    layout="wide",
)

render_sidebar()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='font-size:2rem;font-weight:700;letter-spacing:-0.03em;"
    f"margin-bottom:4px'>CRM Multi-Agent</h1>"
    f"<p style='color:{APPLE['secondary_label']};font-size:1rem;margin-top:0'>"
    f"Automatización inteligente de CRM con supervisión humana.</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Pipeline ──────────────────────────────────────────────────────────────────
st.markdown("##### Pipeline de agentes")

steps = [
    ("Analyst",  APPLE["blue"],   "Detecta sentimiento e intención del mensaje mediante IA."),
    ("Triage",   APPLE["orange"], "Evalúa el SLA y decide la acción: responder, reembolsar o escalar."),
    ("Executor", APPLE["green"],  "Redacta una respuesta personalizada en el idioma del cliente."),
]

cols = st.columns(3)
for col, (title, color, description) in zip(cols, steps):
    with col:
        st.markdown(
            f'<div style="background:{color}14;border-left:3px solid {color};'
            f'border-radius:0 10px 10px 0;padding:14px 16px">'
            f'<p style="font-weight:600;color:{color};margin:0 0 6px 0;font-size:0.9rem">'
            f'{title}</p>'
            f'<p style="color:{APPLE["label"]};font-size:0.85rem;margin:0;line-height:1.5">'
            f'{description}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.divider()

# ── Quick links ───────────────────────────────────────────────────────────────
st.markdown("##### Páginas")

c1, c2, c3 = st.columns(3)
pages = [
    (c1, "Mensajes",    "Simula mensajes entrantes y observa el resultado del pipeline."),
    (c2, "Supervisor",  "Revisa y resuelve los casos escalados que requieren aprobación."),
    (c3, "Estado",      "Verifica la conexión con el backend y consulta los endpoints."),
]
for col, title, desc in pages:
    with col:
        st.markdown(
            f'<p style="font-weight:600;margin-bottom:4px">{title}</p>'
            f'<p style="color:{APPLE["secondary_label"]};font-size:0.85rem;'
            f'line-height:1.5;margin:0">{desc}</p>',
            unsafe_allow_html=True,
        )

st.divider()

# ── Backend status ────────────────────────────────────────────────────────────
response = api_get("/health")
if response and response.status_code == 200:
    st.success("Backend conectado", icon="✅")
else:
    st.error(
        "No se puede conectar al backend. "
        "Verifica que el servidor esté corriendo y revisa la **Backend URL** en el sidebar.",
        icon="❌",
    )
