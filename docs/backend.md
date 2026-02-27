# Backend — CRM Multi-Agent API

## Descripción general

API REST construida con **FastAPI** y orquestada con **LangGraph**. Recibe mensajes de clientes CRM, los clasifica y actúa automáticamente o escala al supervisor humano. Usa **Google Gemini 2.5 Flash Lite** como LLM y **PostgreSQL** (async SQLAlchemy) para persistencia.

---

## Stack

| Tecnología | Versión | Rol |
|---|---|---|
| Python | 3.12 | Lenguaje base |
| FastAPI | ≥ 0.111 | Framework HTTP |
| Uvicorn | ≥ 0.29 | Servidor ASGI |
| LangGraph | ≥ 0.2 | Orquestación del pipeline de agentes |
| langchain-google-genai | ≥ 2.0 | Cliente Gemini |
| SQLAlchemy (asyncio) | ≥ 2.0 | ORM async |
| asyncpg | ≥ 0.29 | Driver PostgreSQL async |
| Alembic | ≥ 1.13 | Migraciones de esquema |
| Pydantic v2 | ≥ 2.7 | Validación de schemas y configuración |
| python-jose | ≥ 3.3 | Generación y verificación de JWT |
| bcrypt | ≥ 4.0 | Hashing de contraseñas |
| python-multipart | ≥ 0.0.9 | Parseo de form-data en login |

---

## Configuración

### Variables de entorno (`.env`)

```env
# LLM
GEMINI_API_KEY=...

# Base de datos
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/crm

# CORS — orígenes permitidos, separados por coma
ALLOWED_ORIGINS=http://localhost:8501,https://crm.miempresa.com

# SLA (opcional, default 2.0 horas)
SLA_THRESHOLD_HOURS=2.0

# JWT — para el supervisor frontend
# Generar: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=...
JWT_EXPIRE_MINUTES=60

# Cuenta del supervisor (una sola, sin DB)
# Generar hash: python -c "import bcrypt; print(bcrypt.hashpw('tu-password'.encode(), bcrypt.gensalt()).decode())"
SUPERVISOR_USERNAME=supervisor
SUPERVISOR_PASSWORD_HASH=$2b$12$...

# Nivel de logging: DEBUG | INFO | WARNING | ERROR (default INFO)
LOG_LEVEL=INFO

# API Key para el bot CRM (Salesforce, WhatsApp, etc.)
# Generar: python -c "import secrets; print(secrets.token_urlsafe(32))"
WEBHOOK_API_KEY=...

# Usado solo por el frontend Streamlit
BACKEND_URL=http://localhost:8000
```

### Arrancar el servidor

```bash
# Primera vez
pip install -r requirements.txt
alembic upgrade head

# Desarrollo
uvicorn app.main:app --reload --port 8000
```

Swagger UI disponible en `http://localhost:8000/docs`.

> El `lifespan` de la app ejecuta `alembic upgrade head` automáticamente en cada arranque.

---

## Autenticación

### Mecanismos

| Endpoint | Mecanismo | Header |
|---|---|---|
| `POST /api/v1/auth/login` | Público | — |
| `POST /api/v1/webhook/messages` | API Key | `X-Api-Key: <valor>` |
| `GET /api/v1/supervisor/pending` | JWT Bearer | `Authorization: Bearer <token>` |
| `POST /api/v1/supervisor/decide` | JWT Bearer | `Authorization: Bearer <token>` |
| `GET /health`, `GET /` | Público | — |

### JWT (supervisor frontend)

El supervisor hace login con `POST /api/v1/auth/login` y recibe un token JWT con expiración configurable (`JWT_EXPIRE_MINUTES`). El frontend lo almacena en sesión y lo incluye en cada request como `Authorization: Bearer <token>`.

### API Key (bot CRM — máquina a máquina)

El bot incluye en cada request el header `X-Api-Key: <valor>`. La clave se configura una vez en el sistema externo:

- **Salesforce**: Named Credential → HTTP Header → `X-Api-Key`
- **WhatsApp via Twilio**: configurar header personalizado en la definición del webhook
- **WhatsApp via Meta directamente**: Meta no permite headers custom; en ese caso se valida el header `X-Hub-Signature-256` (HMAC-SHA256 firmado por Meta)

---

## Endpoints

### `POST /api/v1/auth/login`

Login del supervisor. Usa `application/x-www-form-urlencoded` (form-data), no JSON — es el estándar OAuth2.

**Request (form-data)**
```
username=supervisor
password=tu-password
```

**Response**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

---

### `POST /api/v1/webhook/messages`

Recibe un mensaje de cliente e inicia el pipeline completo. Requiere `X-Api-Key`.

**Headers**
```
X-Api-Key: <WEBHOOK_API_KEY>
```

**Request body**
```json
{
  "client_id": "CRM-001",
  "message": "I want a refund, this is unacceptable!",
  "timestamp": "2026-02-26T08:00:00Z"
}
```

**Response** — `ProcessingResponse`
```json
{
  "run_id": "uuid",
  "status": "processed | pending_approval",
  "sentiment": "positive | neutral | negative",
  "sla_breached": false,
  "proposed_action": "send_standard_response | process_refund | escalate_to_human",
  "supervisor_note": null,
  "execution_result": "Texto de respuesta al cliente...",
  "message": "Descripción del resultado"
}
```

---

### `GET /api/v1/supervisor/pending`

Devuelve todos los casos escalados pendientes de decisión, leídos desde PostgreSQL. Requiere JWT.

**Headers**
```
Authorization: Bearer <jwt_token>
```

**Response** — `List[PendingApprovalItem]`
```json
[
  {
    "run_id": "uuid",
    "client_id": "CRM-001",
    "message": "Mensaje original del cliente",
    "sentiment": "negative",
    "sla_breached": true,
    "proposed_action": "escalate_to_human",
    "supervisor_note": "Nota generada por Triage...",
    "timestamp": "2026-02-26T08:00:00Z"
  }
]
```

---

### `POST /api/v1/supervisor/decide`

El supervisor aprueba o rechaza un caso escalado. Requiere JWT.

**Headers**
```
Authorization: Bearer <jwt_token>
```

**Request body**
```json
{
  "run_id": "uuid",
  "approved": true,
  "reason": "Cliente VIP, proceder"
}
```

**Response** — `ProcessingResponse` con status `approved_and_executed` o `rejected`.

---

### `GET /health`

```json
{ "status": "healthy" }
```

### `GET /`

```json
{ "app": "CRM Multi-Agent API", "version": "0.1.0", "docs": "/docs" }
```

---

## Pipeline de agentes (LangGraph)

```
POST /webhook/messages
    └─► [Analyst]  → classifica sentiment + intent (Gemini, temp=0, structured output)
    └─► [Triage]   → evalúa SLA + aplica routing matrix (determinístico)
    └─► conditional edge:
        ├─ proposed_action == "escalate_to_human"
        │       → guarda estado en PostgreSQL → retorna "pending_approval"
        └─ otherwise
                └─► [Executor] → genera respuesta personalizada (Gemini, temp=0.3)
```

### Agente Analyst (`app/agents/analyst.py`)

- Llama a Gemini con `with_structured_output()` — salida garantizada por schema Pydantic.
- Detecta **sentiment**: `positive | neutral | negative`
- Detecta **intent**: `refund_request | support_request | general_inquiry`
- En caso de error LLM, hace fallback a `neutral / general_inquiry`.

### Agente Triage (`app/agents/triage.py`)

Routing **determinístico** basado en:

| Condición | `proposed_action` |
|---|---|
| `sentiment == "negative"` **O** `sla_breached == True` | `escalate_to_human` |
| `intent == "refund_request"` | `process_refund` |
| cualquier otro caso | `send_standard_response` |

Cuando escala, llama al LLM (temp=0.1) para generar `supervisor_note` (2 frases de briefing).

SLA se evalúa comparando el `timestamp` del mensaje contra `now()` usando `SLA_THRESHOLD_HOURS`.

### Agente Executor (`app/agents/executor.py`)

- Detecta el idioma del mensaje y responde en el mismo (EN/ES).
- Genera una respuesta de 2-4 frases, empática y sin jerga interna.
- Temperatura 0.3 para variación natural en el lenguaje.
- Fallback estático si el LLM falla.

---

## Persistencia (PostgreSQL)

### Tabla `pending_approvals`

| Columna | Tipo | Descripción |
|---|---|---|
| `run_id` | VARCHAR PK | UUID del run |
| `client_id` | VARCHAR | ID del cliente CRM |
| `message` | TEXT | Mensaje original |
| `timestamp` | VARCHAR | ISO 8601 del mensaje |
| `sentiment` | VARCHAR | Clasificación del Analyst |
| `intent` | VARCHAR | Intención detectada |
| `sla_breached` | BOOLEAN | Si se superó el umbral de SLA |
| `proposed_action` | VARCHAR | Decisión del Triage |
| `supervisor_note` | TEXT (nullable) | Nota de briefing para el supervisor |
| `messages_json` | JSONB | Lista completa de mensajes para el Executor |
| `created_at` | TIMESTAMPTZ | Fecha de inserción |

### Store (`app/core/store.py`)

| Función | Operación SQL |
|---|---|
| `save_pending(run_id, state, db)` | `INSERT` |
| `get_pending(run_id, db)` | `SELECT WHERE run_id = ?` |
| `delete_pending(run_id, db)` | `DELETE WHERE run_id = ?` |
| `list_pending(db)` | `SELECT * ORDER BY created_at` |

### Migraciones (Alembic)

```bash
# Aplicar migraciones
alembic upgrade head

# Crear nueva migración tras cambios en db_models.py
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Revertir una migración
alembic downgrade -1
```

La migración `0001` crea la tabla `pending_approvals`.

---

## Estructura de archivos

```
app/
├── main.py                      # FastAPI app + lifespan (Alembic en startup)
├── core/
│   ├── config.py                # Settings (pydantic-settings, lee .env)
│   ├── database.py              # Engine async, AsyncSession, get_db()
│   ├── security.py              # JWT helpers + API Key dependency
│   └── store.py                 # Funciones CRUD async sobre pending_approvals
├── agents/
│   ├── state.py                 # AgentState TypedDict (contrato compartido)
│   ├── orchestrator.py          # StateGraph de LangGraph (singleton crm_graph)
│   ├── analyst.py               # Nodo Analyst
│   ├── triage.py                # Nodo Triage
│   └── executor.py              # Nodo Executor
├── api/endpoints/
│   ├── auth.py                  # POST /auth/login
│   ├── webhooks.py              # POST /webhook/messages
│   └── supervisor.py            # GET/POST /supervisor/*
└── models/
    ├── schemas.py               # Pydantic models de request/response
    └── db_models.py             # ORM model PendingApproval (SQLAlchemy)

alembic/
├── env.py                       # Configuración async de Alembic
├── script.py.mako               # Template de migrations
└── versions/
    └── 0001_create_pending_approvals_table.py
alembic.ini
```

---

## Logging

### Configuración

El logging se configura en `main.py` al arrancar la app con `logging.basicConfig`. El nivel se controla con `LOG_LEVEL` en el `.env`.

```
INFO     → flujo normal (recomendado en producción)
DEBUG    → todo, incluyendo detalles internos (desarrollo)
WARNING  → solo advertencias y errores
ERROR    → solo errores
```

Loggers de terceros ruidosos (`httpx`, `httpcore`, `sqlalchemy.engine`) están silenciados a `WARNING` independientemente del `LOG_LEVEL`.

### Formato

```
2026-02-26 15:42:01 | INFO     | app.agents.analyst  | client=CRM-005 sentiment=negative intent=support_request
2026-02-26 15:42:02 | INFO     | app.agents.triage   | client=CRM-005 sla_breached=False proposed_action=escalate_to_human
2026-02-26 15:42:03 | INFO     | app.agents.executor | client=CRM-005 action=escalate_to_human response_drafted=true
2026-02-26 15:42:03 | INFO     | app.main            | POST /api/v1/webhook/messages → 200  (2341.7 ms)
```

Cada módulo tiene su propio logger (`logging.getLogger(__name__)`), lo que permite identificar exactamente qué componente generó cada línea.

### Middleware de requests

Cada request HTTP loguea: método, path, status code y duración en ms.

### Ver logs

```bash
# En terminal directamente
uvicorn app.main:app --reload --port 8000

# Guardar a archivo
uvicorn app.main:app --port 8000 >> logs/app.log 2>&1

# Ver en consola Y guardar
uvicorn app.main:app --port 8000 2>&1 | tee logs/app.log
```

En producción con Docker o plataformas cloud (Railway, Render, AWS), los logs de stdout se recogen automáticamente.

---

## Manejo de errores

### Errores de validación (422)

FastAPI maneja automáticamente los errores de validación Pydantic. Devuelven HTTP `422` con detalle de qué campo falló.

### Errores de negocio (404)

Los endpoints lanzan `HTTPException(status_code=404)` cuando un `run_id` no existe.

### Errores de autenticación (401)

Los endpoints protegidos devuelven `401` con `WWW-Authenticate: Bearer` cuando el JWT o API Key es inválido o está ausente.

### Errores inesperados (500)

Un exception handler global en `main.py` captura cualquier excepción no manejada:
- Loguea el stacktrace completo con `logger.exception()` en la terminal del servidor
- Con `DEBUG=True`: devuelve el mensaje de error real en `detail` (útil en desarrollo)
- Con `DEBUG=False`: devuelve un mensaje genérico, sin exponer internos al cliente

```json
{ "detail": "An unexpected error occurred. Please try again later." }
```

---

## Flujo HITL (Human-in-the-Loop)

1. El Triage decide `escalate_to_human`.
2. El webhook guarda el estado en PostgreSQL y retorna `status: pending_approval` con el `run_id`.
3. El supervisor consulta `GET /supervisor/pending` y ve el caso con la nota de briefing.
4. El supervisor llama `POST /supervisor/decide` con `approved: true/false`.
5. Si `approved: true`: se llama `run_executor(state)` directamente y se retorna `approved_and_executed`.
6. La fila se elimina de PostgreSQL en ambos casos.
