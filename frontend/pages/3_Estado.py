import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils import render_sidebar, api_get, get_api_url, APPLE

st.set_page_config(page_title="Estado — CRM", page_icon="💚", layout="wide")
render_sidebar()

st.markdown(
    "<h2 style='font-weight:700;letter-spacing:-0.02em;margin-bottom:4px'>Estado</h2>"
    f"<p style='color:{APPLE['secondary_label']};margin-top:0'>"
    f"Conexión con el backend y referencia de endpoints.</p>",
    unsafe_allow_html=True,
)
st.divider()

col_status, col_info = st.columns(2)

# ── Health ────────────────────────────────────────────────────────────────────
with col_status:
    st.markdown("##### Conexión")
    st.markdown(
        f"<p style='font-size:0.82rem;color:{APPLE['secondary_label']};margin-bottom:12px'>"
        f"<code>{get_api_url()}</code></p>",
        unsafe_allow_html=True,
    )

    if st.button("Verificar", use_container_width=True):
        st.rerun()

    health = api_get("/health")
    if health is None:
        st.error("Sin conexión — el backend no responde.")
        st.markdown(
            "```bash\nuvicorn app.main:app --reload --port 8000\n```\n"
            "Luego ajusta la **Backend URL** en el sidebar si es necesario."
        )
    elif health.status_code == 200:
        st.success("Backend activo")
        st.json(health.json())
    else:
        st.warning(f"HTTP {health.status_code}")
        st.text(health.text)

# ── API info ──────────────────────────────────────────────────────────────────
with col_info:
    st.markdown("##### API")
    info = api_get("/")
    if info and info.status_code == 200:
        d = info.json()
        st.markdown(
            f"<p style='margin:0'><span style='color:{APPLE['secondary_label']};font-size:0.8rem'>"
            f"Nombre</span><br><strong>{d.get('app', '-')}</strong></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='margin:8px 0'><span style='color:{APPLE['secondary_label']};font-size:0.8rem'>"
            f"Versión</span><br><code>{d.get('version', '-')}</code></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"[Abrir Swagger UI]({get_api_url()}/docs)",
        )
    else:
        st.markdown(
            f"<p style='color:{APPLE['secondary_label']};font-size:0.9rem'>"
            f"No disponible mientras el backend esté desconectado.</p>",
            unsafe_allow_html=True,
        )

st.divider()

# ── Endpoints reference ───────────────────────────────────────────────────────
st.markdown("##### Endpoints")

endpoints = [
    ("POST", "/api/v1/webhook/messages",   "Recibe un mensaje e inicia el pipeline"),
    ("GET",  "/api/v1/supervisor/pending", "Lista los casos pendientes de aprobación"),
    ("POST", "/api/v1/supervisor/decide",  "Aprueba o rechaza un caso escalado"),
    ("GET",  "/health",                    "Health check"),
    ("GET",  "/",                          "Info general de la API"),
]

METHOD_COLOR = {"GET": APPLE["green"], "POST": APPLE["blue"]}

for method, path, description in endpoints:
    color = METHOD_COLOR.get(method, APPLE["gray"])
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;'
        f'border-bottom:1px solid rgba(0,0,0,0.05)">'
        f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:6px;'
        f'font-size:0.72rem;font-weight:600;letter-spacing:0.03em;min-width:40px;'
        f'text-align:center">{method}</span>'
        f'<code style="font-size:0.82rem;flex:1">{path}</code>'
        f'<span style="color:{APPLE["secondary_label"]};font-size:0.82rem">{description}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
