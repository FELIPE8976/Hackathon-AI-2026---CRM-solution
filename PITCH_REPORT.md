# CRM Multi-Agent AI System — Reporte de Estado
### Hackathon AI 2026 · 26 de Febrero de 2026

---

## Índice

1. [Estado General del Proyecto](#1-estado-general-del-proyecto)
2. [Arquitectura Implementada](#2-arquitectura-implementada)
3. [Stack Técnico](#3-stack-técnico)
4. [Agentes y sus Responsabilidades](#4-agentes-y-sus-responsabilidades)
5. [Endpoints Disponibles](#5-endpoints-disponibles)
6. [Por Qué NO es un Chatbot Común](#6-por-qué-no-es-un-chatbot-común)
7. [Escenarios de Demo](#7-escenarios-de-demo-para-el-pitch-en-vivo)
8. [Historial de Desarrollo](#8-historial-de-desarrollo)
9. [Repositorio](#9-repositorio)

---

## 1. Estado General del Proyecto

| Dimensión | Estado | Detalle |
|---|---|---|
| API REST funcional | ✅ Operativo | 4 endpoints activos, Swagger UI disponible |
| Pipeline multi-agente (LangGraph) | ✅ Operativo | 3 agentes orquestados en grafo de estado |
| LLM conectado | ✅ Operativo | Google Gemini 2.5 Flash Lite |
| Human-in-the-Loop (HITL) | ✅ Operativo | Pausa automática + aprobación/rechazo del supervisor |
| Evaluación de SLA | ✅ Operativo | Detección automática por timestamp |
| Análisis de sentimiento | ✅ Operativo | Clasificación con structured output — sin alucinaciones |
| Respuestas bilingües (EN/ES) | ✅ Operativo | Detección automática del idioma del cliente |
| Colección Postman (15 escenarios) | ✅ Listo | Importable directamente, con test scripts |
| Script de pruebas automatizadas | ✅ Listo | `python run_tests.py` — 7 escenarios E2E |
| Repositorio GitHub | ✅ Público | 6 commits documentados |

---

## 2. Arquitectura Implementada

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE / CRM EXTERNO                    │
└───────────────────────┬─────────────────────────────────────┘
                        │ POST /api/v1/webhook/messages
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (ASGI)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               LangGraph StateGraph                   │   │
│  │                                                      │   │
│  │  ┌────────────┐        ┌────────────┐                │   │
│  │  │  ANALYST   │───────▶│   TRIAGE   │                │   │
│  │  │            │        │            │                │   │
│  │  │ - Gemini   │        │ - SLA check│                │   │
│  │  │ - Sentiment│        │ - Routing  │                │   │
│  │  │ - Intent   │        │ - Sup. note│                │   │
│  │  └────────────┘        └──────┬─────┘                │   │
│  │                               │                      │   │
│  │               ┌───────────────┴────────────────┐     │   │
│  │               │ ¿Escalate?                      │     │   │
│  │              YES                               NO    │   │
│  │               │                                │     │   │
│  │               ▼                                ▼     │   │
│  │           ┌───────┐                     ┌──────────┐ │   │
│  │           │  END  │                     │ EXECUTOR │ │   │
│  │           │(pause)│                     │          │ │   │
│  │           └───┬───┘                     │ - Gemini │ │   │
│  │               │                         │ - Respues│ │   │
│  │               │                         │   ta     │ │   │
│  └───────────────┼─────────────────────────┴──────────┘ │   │
└──────────────────┼──────────────────────────────────────────┘
                   │
     GET  /api/v1/supervisor/pending
     POST /api/v1/supervisor/decide
                   │
                   ▼
      ┌────────────────────────┐
      │    SUPERVISOR HUMANO   │
      │                        │
      │  Ve: mensaje, sentiment│
      │  sla_breached,         │
      │  supervisor_note (IA)  │
      │                        │
      │  Decide: Aprobar ✅    │
      │          Rechazar ❌   │
      └────────────────────────┘
```

---

## 3. Stack Técnico

| Capa | Tecnología | Versión |
|---|---|---|
| Framework API | FastAPI | 0.133.1 |
| Servidor ASGI | Uvicorn | — |
| Orquestación de agentes | LangGraph | 1.0.9 |
| LLM Provider | Google Gemini 2.5 Flash Lite | — |
| Integración LLM | langchain-google-genai | 4.2.1 |
| Core LangChain | langchain-core | 1.2.16 |
| Validación de datos | Pydantic v2 | 2.12.5 |
| Configuración | pydantic-settings | — |
| Lenguaje | Python | 3.12 |
| Base de datos | In-memory (dict) → SQLite ready | — |

---

## 4. Agentes y sus Responsabilidades

### 4.1 Agente Analista (`app/agents/analyst.py`)

**Rol:** Clasificador de contexto — primer nodo del pipeline.

**Qué hace:**
- Recibe el mensaje crudo del cliente
- Determina el **sentimiento**: `positive` / `neutral` / `negative`
- Determina la **intención**: `refund_request` / `support_request` / `general_inquiry`

**Decisión de diseño clave:**
Usa `with_structured_output()` — el LLM devuelve directamente un objeto Pydantic validado.
Imposible que retorne un valor fuera del schema. Cero alucinaciones en la clasificación.

```
temperature = 0  →  Clasificación determinista y reproducible
```

---

### 4.2 Agente de Triage — Agente Crítico (`app/agents/triage.py`)

**Rol:** Árbitro de routing — decide qué pasa con el caso.

**Qué hace:**
- Calcula si el SLA fue violado (lógica determinista, sin LLM)
- Aplica matriz de decisión para elegir la acción
- Cuando escala: genera un **briefing en lenguaje natural** para el supervisor humano

**Matriz de decisión:**

| Condición | Acción |
|---|---|
| `sentiment == "negative"` OR `sla_breached == true` | `escalate_to_human` |
| `intent == "refund_request"` | `process_refund` |
| Cualquier otro caso | `send_standard_response` |

**Decisión de diseño clave:**
El LLM solo se invoca para generar el `supervisor_note` — donde la síntesis en lenguaje natural tiene valor real.
La lógica de routing es código puro: predecible, auditable, sin costo de tokens.

```
temperature = 0.1  →  Phrasing natural pero consistente
```

---

### 4.3 Agente Ejecutor (`app/agents/executor.py`)

**Rol:** Redactor — genera la respuesta final para el cliente.

**Qué hace:**
- Recibe el mensaje original + la acción confirmada
- Genera una respuesta **personalizada** al contexto del cliente
- Detecta automáticamente el idioma (EN/ES) y responde en el mismo idioma
- Aplica restricciones profesionales estrictas: sin jerga interna, sin promesas de fechas, sin frases genéricas de apertura

**Decisión de diseño clave:**
No hay templates fijos. Cada respuesta es generada contextualmente para el mensaje específico del cliente.

```
temperature = 0.3  →  Variación natural en el phrasing, mantiene profesionalismo
```

---

## 5. Endpoints Disponibles

### `POST /api/v1/webhook/messages`
Recibe el mensaje del cliente y ejecuta el pipeline completo.

**Request:**
```json
{
  "client_id": "CRM-001",
  "message": "My order arrived damaged. I want a refund immediately.",
  "timestamp": "2026-02-26T10:00:00Z"
}
```

**Response (auto-procesado):**
```json
{
  "run_id": "uuid",
  "status": "processed",
  "sentiment": "negative",
  "sla_breached": false,
  "proposed_action": "escalate_to_human",
  "supervisor_note": "This case requires escalation due to strongly negative client sentiment...",
  "execution_result": null,
  "message": "Message requires human approval."
}
```

---

### `GET /api/v1/supervisor/pending`
Lista todos los casos esperando decisión humana, incluyendo el briefing generado por IA.

---

### `POST /api/v1/supervisor/decide`
El supervisor aprueba o rechaza. Si aprueba, el Executor genera la respuesta al cliente.

**Request:**
```json
{
  "run_id": "uuid-del-caso",
  "approved": true,
  "reason": "High-priority client. Proceed with priority resolution."
}
```

---

### `GET /health` · `GET /docs`
Health check y Swagger UI interactivo.

---

## 6. Por Qué NO Es un Chatbot Común

> Este es el diferenciador central del sistema frente a soluciones convencionales.

### 6.1 Agentes Especializados vs. LLM Único

| Chatbot convencional | Este sistema |
|---|---|
| Un solo LLM recibe el mensaje y responde | Tres agentes especializados con responsabilidades distintas |
| Toda la lógica vive en el prompt | Cada agente tiene una responsabilidad acotada, verificable y auditable |
| El modelo decide la acción y la redacta todo a la vez | Clasificar ≠ decidir ≠ redactar — tres pasos separados con controles distintos |
| No hay forma de saber qué parte "salió mal" | Cada campo del estado es trazable: `sentiment`, `intent`, `sla_breached`, `proposed_action` |

---

### 6.2 Supervisión Humana Estructurada — Human-in-the-Loop

Un chatbot no sabe cuándo detenerse. Este sistema **sabe exactamente cuándo pausar**:

- Detecta automáticamente cuándo una situación supera el umbral de riesgo
- **Para el pipeline** antes de actuar sobre clientes en situación crítica
- Genera un **briefing contextual** para el supervisor (no solo "hay un problema" — explica por qué y qué hacer)
- **Espera aprobación explícita** antes de ejecutar cualquier acción sobre el cliente

```
No es un bot que siempre responde.
Es un sistema que sabe cuándo NO responder.
```

---

### 6.3 SLA como Ciudadano de Primera Clase

Los chatbots no tienen concepto de tiempo. Este sistema:

- Evalúa el **timestamp** de cada mensaje entrante en el momento de procesarlo
- Calcula automáticamente si el tiempo de respuesta superó el umbral configurable (default: 2 horas)
- Escala inmediatamente al supervisor si el SLA está en riesgo — **incluso si el mensaje es neutral**
- El umbral es configurable por variable de entorno sin tocar código: `SLA_THRESHOLD_HOURS=2.0`

---

### 6.4 Structured Output — Sin Alucinaciones en la Clasificación

Un chatbot puede clasificar un sentimiento como "muy negativo" o "bastante neutro" — valores que no existen en el sistema.

Este sistema usa `with_structured_output()`:
- El LLM **nunca puede** devolver un valor fuera del schema
- El output es validado por Pydantic antes de entrar al estado del grafo
- Si el LLM falla, hay fallback seguro — el pipeline nunca se rompe

---

### 6.5 Respuestas Personalizadas, No Templates

| Chatbot | Este sistema |
|---|---|
| `"Thank you for contacting us. We will get back to you."` | Respuesta generada con el contexto real del mensaje del cliente |
| Mismo idioma siempre (o traducción torpe) | Detecta automáticamente EN o ES y responde en el idioma del cliente |
| Genérico, aplica a cualquier cliente | Hace referencia a la situación específica mencionada en el mensaje |

---

### 6.6 Decisiones Auditables por Diseño

Cada respuesta de la API expone el razonamiento completo:

```json
{
  "sentiment": "negative",
  "sla_breached": true,
  "proposed_action": "escalate_to_human",
  "supervisor_note": "This case requires escalation due to a 5-hour SLA breach combined with strongly negative client sentiment. Recommend direct phone contact and assign to a senior account manager for priority resolution."
}
```

Un chatbot no puede decirte *por qué* tomó una decisión.
Este sistema documenta el razonamiento en cada llamada.

---

## 7. Escenarios de Demo (para el Pitch en Vivo)

### Escenario A — Happy Path · ~30 segundos
**Objetivo:** Mostrar el flujo automático completo con respuesta personalizada.

```http
POST /api/v1/webhook/messages
{
  "client_id": "CRM-001",
  "message": "Hi, I need to know the status of my order #78432.",
  "timestamp": "2026-02-26T10:00:00Z"
}
```
**Resultado esperado:** `status: "processed"` · `execution_result`: respuesta personalizada del LLM en inglés.

---

### Escenario B — Escalación con HITL · ~60 segundos
**Objetivo:** Mostrar el flujo completo de supervisión humana.

**Paso 1 — Mensaje crítico:**
```http
POST /api/v1/webhook/messages
{
  "client_id": "CRM-002",
  "message": "This is outrageous! My order arrived damaged for the third time. I will cancel my contract.",
  "timestamp": "2026-02-26T10:00:00Z"
}
```
**Resultado:** `status: "pending_approval"` · `supervisor_note` generado por IA

**Paso 2 — Supervisor revisa:**
```http
GET /api/v1/supervisor/pending
```
**Resultado:** Lista el caso con briefing contextual

**Paso 3 — Supervisor aprueba:**
```http
POST /api/v1/supervisor/decide
{
  "run_id": "{{run_id}}",
  "approved": true,
  "reason": "Verified high-priority client. Proceed immediately."
}
```
**Resultado:** `status: "approved_and_executed"` · `execution_result`: respuesta empática redactada por el LLM

---

### Escenario C — SLA Breach Automático · ~20 segundos
**Objetivo:** Mostrar monitoreo proactivo de SLA.

```http
POST /api/v1/webhook/messages
{
  "client_id": "CRM-003",
  "message": "I am still waiting for a response to my ticket from yesterday.",
  "timestamp": "2026-02-26T05:00:00Z"    ← 5 horas atrás
}
```
**Resultado esperado:** `sla_breached: true` · `status: "pending_approval"` — aunque el mensaje sea neutral.

---

### Escenario D — Demo en Español · ~20 segundos
**Objetivo:** Mostrar detección automática de idioma.

```http
POST /api/v1/webhook/messages
{
  "client_id": "CRM-004",
  "message": "Buenas tardes, quisiera solicitar la devolución de mi último pedido.",
  "timestamp": "2026-02-26T10:00:00Z"
}
```
**Resultado esperado:** `execution_result` redactado completamente en español.

---

## 8. Historial de Desarrollo

| Commit | Descripción |
|---|---|
| `fae5a61` | `feat: initial MVP` — estructura base del proyecto |
| `16cf469` | `feat: real LLM calls` — integración con IA real |
| `abcbbaf` | `feat: migrate to Google Gemini` — cambio de proveedor LLM |
| `13e7822` | `test: automated test runner` — script E2E con 7 escenarios |
| `c0f2bbb` | `test: Postman collection` — 15 escenarios importables |
| `870b3c9` | `fix: gemini-2.5-flash-lite` — modelo productivo con cuota disponible |

---

## 9. Repositorio

**GitHub:** [https://github.com/FELIPE8976/Hackathon-AI-2026---CRM-solution](https://github.com/FELIPE8976/Hackathon-AI-2026---CRM-solution)

**Cómo ejecutar:**
```bash
# 1. Activar entorno virtual
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac / Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Levantar servidor
uvicorn app.main:app --reload --port 8000

# 4. Swagger UI
# http://localhost:8000/docs

# 5. Suite de pruebas
python run_tests.py
```

---

*Sistema construido sobre **FastAPI** · **LangGraph** · **Google Gemini 2.5 Flash Lite** · **Pydantic v2***

*Hackathon AI 2026 — Felipe · Claude Sonnet 4.6*
