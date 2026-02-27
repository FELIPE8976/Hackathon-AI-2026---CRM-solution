# Frontend — CRM Multi-Agent

## Descripción general

Interfaz web construida con **Streamlit** que permite simular mensajes de clientes CRM, observar el resultado del pipeline de agentes y gestionar los casos escalados que requieren aprobación humana.

---

## Stack

| Tecnología | Rol |
|---|---|
| Python | Lenguaje base |
| Streamlit | Framework de UI |
| requests | Cliente HTTP hacia el backend |
| python-dotenv | Carga de variables de entorno |

---

## Arrancar el frontend

```bash
cd frontend
streamlit run Home.py
```

La URL del backend se configura desde el sidebar de la app (por defecto `http://localhost:8000`).

---

## Variables de entorno (`.env` en la raíz del proyecto)

```env
BACKEND_URL=http://localhost:8000
SLA_THRESHOLD_HOURS=2.0
```

---

## Páginas

### Home (`Home.py`)

Página de bienvenida. Muestra:
- Descripción del pipeline de agentes (Analyst → Triage → Executor) con tarjetas por etapa.
- Links a las tres páginas funcionales.
- Indicador de estado de conexión con el backend (llama a `GET /health`).

---

### Mensajes (`pages/1_Mensajes.py`)

Permite simular un mensaje entrante al pipeline.

**Controles:**
- **Slider de antigüedad** (0–12 horas): ajusta el `timestamp` del mensaje para probar el SLA en tiempo real. Muestra un badge inmediato indicando si el mensaje breachearía el SLA configurado.
- **Formulario**: Client ID + texto del mensaje libre.
- **Ejemplos predefinidos**: 4 mensajes de muestra con distintas combinaciones de sentimiento e intención.

**Flujo al enviar:**
1. Construye el payload con el `timestamp` calculado desde el slider.
2. Llama `POST /api/v1/webhook/messages`.
3. Muestra el resultado con:
   - Alerta de estado (`processed` / `pending_approval`).
   - Tarjetas: Sentimiento, Intención, Acción propuesta, SLA.
   - Run ID del procesamiento.
   - Nota al supervisor (si aplica).
   - Respuesta generada al cliente (si el Executor la produjo).
   - Expansor con el JSON completo de la respuesta.

---

### Supervisor (`pages/2_Supervisor.py`)

Panel de gestión de casos escalados.

**Funcionamiento:**
1. Al cargar la página llama `GET /api/v1/supervisor/pending` y lista los casos activos.
2. Cada caso muestra:
   - Client ID con badges de sentimiento y SLA.
   - Mensaje original del cliente (destacado en blockquote).
   - Nota de briefing generada por el Triage (si existe).
   - Run ID y timestamp.
   - Panel expandido de decisión: campo de motivo opcional + botones **Aprobar** / **Rechazar**.
3. Al tomar una decisión llama `POST /api/v1/supervisor/decide` y recarga la vista.
4. Las decisiones de la sesión actual se muestran al pie con su resultado (execution_result si fue aprobado).

> Los casos ya decididos se filtran por `st.session_state["decisions"]` para no repetirlos hasta que la página se recargue completamente.

---

### Estado (`pages/3_Estado.py`)

Panel de diagnóstico de conexión con el backend.

**Secciones:**
- **Conexión**: muestra la URL activa, botón de verificación, resultado de `GET /health` con el JSON de respuesta o mensaje de error con instrucción de arranque.
- **API**: nombre y versión de la app (de `GET /`) + link directo al Swagger UI.
- **Endpoints**: tabla de referencia de todos los endpoints disponibles con método, ruta y descripción.

---

## Utilidades comunes (`utils.py`)

Módulo compartido que importan todas las páginas.

### Configuración
| Variable | Descripción |
|---|---|
| `DEFAULT_API_URL` | URL del backend leída de `BACKEND_URL` o `http://localhost:8000` |
| `SLA_THRESHOLD_HOURS` | Umbral SLA leído de `SLA_THRESHOLD_HOURS` o `2.0` |

### HTTP helpers
| Función | Descripción |
|---|---|
| `api_get(path)` | `GET` al backend con timeout 5s. Retorna `None` si falla. |
| `api_post(path, payload)` | `POST` JSON al backend con timeout 15s. Retorna `None` si falla. |
| `get_api_url()` | Retorna la URL activa desde `st.session_state`. |

### Sidebar
`render_sidebar()` — aplica los estilos CSS globales e inyecta el campo de **Backend URL** editable en el sidebar. El valor se almacena en `st.session_state["api_url"]`.

### Badges (HTML chips estilo Apple HIG)
| Función | Descripción |
|---|---|
| `sentiment_badge(sentiment)` | Chip de color por sentimiento (verde/gris/rojo) |
| `status_badge(status)` | Chip de color por estado del procesamiento |
| `sla_badge(breached)` | Chip "SLA OK" (verde) o "SLA vencido" (rojo) |
| `action_label(action)` | Texto legible del `proposed_action` |

### Helpers de SLA
| Función | Descripción |
|---|---|
| `timestamp_from_hours_ago(hours)` | Retorna `datetime` UTC hace N horas (para el slider) |
| `sla_preview(hours_ago)` | Badge HTML que indica si el mensaje breachearía el SLA en vivo |

### Info card
`info_card(label, value)` — tarjeta HTML estilo Apple HIG para mostrar pares clave/valor con formato consistente.

---

## Paleta de colores (Apple HIG System Colors)

| Token | Hex | Uso |
|---|---|---|
| `blue` | `#007AFF` | Método POST, links |
| `green` | `#34C759` | Éxito, SLA OK, positivo |
| `red` | `#FF3B30` | Error, SLA vencido, negativo |
| `orange` | `#FF9500` | Pendiente, Triage |
| `gray` | `#8E8E93` | Neutral, secundario |
| `bg` | `#F2F2F7` | Fondo de tarjetas y sidebar |
| `label` | `#1C1C1E` | Texto principal |
| `secondary_label` | `#6D6D72` | Texto secundario |

---

## Estructura de archivos

```
frontend/
├── Home.py              # Página de inicio y estado del backend
├── utils.py             # HTTP helpers, badges, estilos CSS, sidebar
└── pages/
    ├── 1_Mensajes.py    # Simulador de mensajes + visualización del pipeline
    ├── 2_Supervisor.py  # Panel de aprobación HITL
    └── 3_Estado.py      # Diagnóstico de conexión y referencia de endpoints
```
