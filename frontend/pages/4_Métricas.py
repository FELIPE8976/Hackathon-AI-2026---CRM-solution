"""
Métricas — Dashboard de estadísticas del pipeline CRM.

Muestra KPIs agregados y distribuciones de todos los mensajes procesados.
"""

import pandas as pd
import altair as alt
import streamlit as st

from utils import APPLE, api_get_metrics, render_sidebar

st.set_page_config(
    page_title="Métricas · CRM Multi-Agent",
    page_icon="📊",
    layout="wide",
)

render_sidebar()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='font-size:2rem;font-weight:700;letter-spacing:-0.03em;"
    f"margin-bottom:4px'>Métricas</h1>"
    f"<p style='color:{APPLE['secondary_label']};font-size:1rem;margin-top:0'>"
    f"Estadísticas en tiempo real del pipeline de mensajes CRM.</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Data fetch ─────────────────────────────────────────────────────────────────
data = api_get_metrics()

if data is None:
    st.error(
        "No se pudo obtener los datos del backend. "
        "Verifica que el servidor esté corriendo y revisa la **Backend URL** en el sidebar.",
        icon="❌",
    )
    st.stop()

total = data.get("total_messages", 0)

if total == 0:
    st.info(
        "Aún no hay mensajes procesados. "
        "Ve a la página **Mensajes** y envía algunos para ver las estadísticas aquí.",
        icon="ℹ️",
    )
    st.stop()


# ── KPI cards ──────────────────────────────────────────────────────────────────
st.markdown("##### Resumen general")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total mensajes", total)
k2.metric(
    "Tasa de escalación",
    f"{data['escalation_rate']}%",
    help="Porcentaje de mensajes escalados al supervisor.",
)
k3.metric(
    "Ruptura de SLA",
    f"{data['sla_breach_rate']}%",
    help="Porcentaje de mensajes que superaron el umbral de SLA.",
)
k4.metric(
    "Tasa de aprobación",
    f"{data['approval_rate']}%",
    help="De los mensajes escalados, cuántos fueron aprobados por el supervisor.",
)
k5.metric(
    "Pendientes",
    data["pending_approvals"],
    help="Mensajes actualmente en espera de decisión del supervisor.",
)

st.divider()


# ── Distribution charts ────────────────────────────────────────────────────────
st.markdown("##### Distribuciones")

col_sent, col_intent, col_action = st.columns(3)

# ── Sentiment donut ────────────────────────────────────────────────────────────
with col_sent:
    st.markdown(
        f"<p style='font-weight:600;font-size:0.9rem;margin-bottom:8px;"
        f"color:{APPLE['label']}'>Sentimiento</p>",
        unsafe_allow_html=True,
    )
    sent_rows = data.get("sentiment_distribution", [])
    if sent_rows:
        sent_df = pd.DataFrame(sent_rows)

        SENTIMENT_PALETTE = {
            "positive": APPLE["green"],
            "neutral":  APPLE["gray"],
            "negative": APPLE["red"],
        }
        SENTIMENT_ES = {
            "positive": "Positivo",
            "neutral":  "Neutral",
            "negative": "Negativo",
        }
        sent_df["label"] = sent_df["sentiment"].map(
            lambda s: SENTIMENT_ES.get(s, s.capitalize())
        )
        sent_df["color"] = sent_df["sentiment"].map(
            lambda s: SENTIMENT_PALETTE.get(s, APPLE["gray"])
        )

        chart = (
            alt.Chart(sent_df)
            .mark_arc(innerRadius=44, outerRadius=72)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color(
                    "label:N",
                    scale=alt.Scale(
                        domain=sent_df["label"].tolist(),
                        range=sent_df["color"].tolist(),
                    ),
                    legend=alt.Legend(title=None, orient="bottom", labelFontSize=12),
                ),
                tooltip=[
                    alt.Tooltip("label:N", title="Sentimiento"),
                    alt.Tooltip("count:Q", title="Mensajes"),
                    alt.Tooltip("percentage:Q", title="%", format=".1f"),
                ],
            )
            .properties(height=220, padding={"top": 20, "left": 5, "right": 5, "bottom": 5})
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Sin datos")

# ── Intent bar ─────────────────────────────────────────────────────────────────
with col_intent:
    st.markdown(
        f"<p style='font-weight:600;font-size:0.9rem;margin-bottom:8px;"
        f"color:{APPLE['label']}'>Intención</p>",
        unsafe_allow_html=True,
    )
    intent_rows = data.get("intent_distribution", [])
    if intent_rows:
        INTENT_ES = {
            "refund_request":   "Solicitud de reembolso",
            "support_request":  "Soporte",
            "general_inquiry":  "Consulta general",
        }
        intent_df = pd.DataFrame(intent_rows)
        intent_df["label"] = intent_df["intent"].map(
            lambda i: INTENT_ES.get(i, i.replace("_", " ").capitalize())
        )

        chart = (
            alt.Chart(intent_df)
            .mark_bar(cornerRadiusEnd=6)
            .encode(
                x=alt.X("count:Q", title="Mensajes", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("label:N", sort="-x", title="", axis=alt.Axis(labelLimit=160)),
                color=alt.value(APPLE["blue"]),
                tooltip=[
                    alt.Tooltip("label:N", title="Intención"),
                    alt.Tooltip("count:Q", title="Mensajes"),
                    alt.Tooltip("percentage:Q", title="%", format=".1f"),
                ],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Sin datos")

# ── Action bar ─────────────────────────────────────────────────────────────────
with col_action:
    st.markdown(
        f"<p style='font-weight:600;font-size:0.9rem;margin-bottom:8px;"
        f"color:{APPLE['label']}'>Acción propuesta</p>",
        unsafe_allow_html=True,
    )
    action_rows = data.get("action_distribution", [])
    if action_rows:
        ACTION_ES = {
            "send_standard_response": "Respuesta estándar",
            "process_refund":         "Procesar reembolso",
            "escalate_to_human":      "Escalar a supervisor",
        }
        ACTION_COLOR = {
            "send_standard_response": APPLE["green"],
            "process_refund":         APPLE["blue"],
            "escalate_to_human":      APPLE["orange"],
        }
        action_df = pd.DataFrame(action_rows)
        action_df["label"] = action_df["action"].map(
            lambda a: ACTION_ES.get(a, a.replace("_", " ").capitalize())
        )
        action_df["color"] = action_df["action"].map(
            lambda a: ACTION_COLOR.get(a, APPLE["gray"])
        )

        chart = (
            alt.Chart(action_df)
            .mark_bar(cornerRadiusEnd=6)
            .encode(
                x=alt.X("count:Q", title="Mensajes", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("label:N", sort="-x", title="", axis=alt.Axis(labelLimit=160)),
                color=alt.Color(
                    "label:N",
                    scale=alt.Scale(
                        domain=action_df["label"].tolist(),
                        range=action_df["color"].tolist(),
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("label:N", title="Acción"),
                    alt.Tooltip("count:Q", title="Mensajes"),
                    alt.Tooltip("percentage:Q", title="%", format=".1f"),
                ],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Sin datos")

st.divider()


# ── Top clients table ──────────────────────────────────────────────────────────
st.markdown("##### Top clientes por volumen")

client_rows = data.get("top_clients", [])
if client_rows:
    clients_df = pd.DataFrame(client_rows).rename(
        columns={
            "client_id":          "Cliente",
            "total":              "Mensajes",
            "negative_count":     "Sentimiento negativo",
            "sla_breached_count": "SLA vencido",
        }
    )

    # Compute risk score (simple: negative + sla_breached normalised 0–100)
    clients_df["Riesgo"] = (
        (clients_df["Sentimiento negativo"] + clients_df["SLA vencido"])
        / clients_df["Mensajes"]
        * 100
    ).round(1).astype(str) + "%"

    st.dataframe(
        clients_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cliente":               st.column_config.TextColumn(width="small"),
            "Mensajes":              st.column_config.NumberColumn(width="small"),
            "Sentimiento negativo":  st.column_config.NumberColumn(width="medium"),
            "SLA vencido":           st.column_config.NumberColumn(width="medium"),
            "Riesgo":                st.column_config.TextColumn(
                width="small",
                help="(negativos + SLA vencido) / total × 100",
            ),
        },
    )
else:
    st.caption("Sin datos de clientes.")

st.divider()

# ── Footer refresh ─────────────────────────────────────────────────────────────
if st.button("Actualizar métricas", type="secondary"):
    st.rerun()
