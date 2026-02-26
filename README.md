# CRM Multi-Agent API — Hackathon MVP

API REST para un sistema multi-agente de automatización de CRM con supervisión humana (Human-in-the-Loop).

---

## Configuración del Entorno

### 1. Crear el entorno virtual
```bash
python -m venv venv
```

### 2. Activar el entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Mac / Linux:**
```bash
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Levantar el servidor
```bash
uvicorn app.main:app --reload --port 8000
```

La documentación interactiva (Swagger UI) estará disponible en: http://localhost:8000/docs

---

## Flujo del Sistema

```
Webhook POST /api/v1/webhook/messages
        │
        ▼
   [Analyst]  → extrae sentimiento e intención (mock)
        │
        ▼
   [Triage]   → evalúa SLA y enruta
        │
   ┌────┴────┐
   │         │
   ▼         ▼
[Executor] [END → Supervisor]
(auto)     (requiere aprobación humana)
```

**Escalación a supervisor:** sentimiento negativo O SLA > 2 horas.

---

## Endpoints Principales

| Método | Ruta                          | Descripción                        |
|--------|-------------------------------|------------------------------------|
| POST   | `/api/v1/webhook/messages`    | Recibe mensaje entrante del CRM    |
| GET    | `/api/v1/supervisor/pending`  | Lista acciones pendientes de aprobación |
| POST   | `/api/v1/supervisor/decide`   | Aprueba o rechaza una acción       |
| GET    | `/health`                     | Health check                       |
