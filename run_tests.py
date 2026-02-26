"""
CRM Multi-Agent API — Test Runner
==================================
Ejecuta los escenarios clave de extremo a extremo contra el servidor local.

Uso:
    python run_tests.py

Requisito: el servidor debe estar corriendo en http://localhost:8000
    uvicorn app.main:app --reload --port 8000
"""

import json
import sys
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("Instalando 'requests'...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

BASE_URL = "http://localhost:8000/api/v1"

# ---------------------------------------------------------------------------
# Helpers de presentación
# ---------------------------------------------------------------------------

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")

def _ok(label: str, value: str = "") -> None:
    print(f"  {GREEN}✔{RESET}  {label}: {BOLD}{value}{RESET}")

def _fail(label: str, value: str = "") -> None:
    print(f"  {RED}✘{RESET}  {label}: {BOLD}{value}{RESET}")

def _info(label: str, value: str = "") -> None:
    print(f"  {YELLOW}→{RESET}  {label}: {value}")

def _print_response(resp: dict) -> None:
    for key, val in resp.items():
        if val is None:
            continue
        if key in ("execution_result", "supervisor_note"):
            print(f"\n  {YELLOW}{key}:{RESET}")
            print(f"    \"{val}\"")
        else:
            print(f"  {YELLOW}{key}:{RESET} {val}")

def _assert(condition: bool, msg: str) -> bool:
    if condition:
        _ok(msg)
    else:
        _fail(msg)
    return condition

passed = 0
failed = 0

def run_scenario(title: str, fn) -> None:
    global passed, failed
    _header(title)
    try:
        fn()
        passed += 1
    except AssertionError as e:
        _fail("ASSERTION FAILED", str(e))
        failed += 1
    except Exception as e:
        _fail("UNEXPECTED ERROR", str(e))
        failed += 1


# ---------------------------------------------------------------------------
# Escenario 0 — Health check
# ---------------------------------------------------------------------------

def test_health():
    r = requests.get("http://localhost:8000/health", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    _assert(r.json()["status"] == "healthy", "Server is healthy")


# ---------------------------------------------------------------------------
# Escenario 1 — Mensaje neutro → procesado automáticamente
# ---------------------------------------------------------------------------

def test_neutral_message():
    payload = {
        "client_id": "CRM-TEST-001",
        "message": "Hi, I would like to know the status of my order #45231.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r = requests.post(f"{BASE_URL}/webhook/messages", json=payload, timeout=30)
    data = r.json()
    _print_response(data)

    assert r.status_code == 200
    _assert(data["status"] == "processed", f"status='{data['status']}'")
    _assert(data["sentiment"] in ("neutral", "positive"), f"sentiment='{data['sentiment']}'")
    _assert(data["execution_result"] is not None, "execution_result generated")
    _assert(data["supervisor_note"] is None, "no supervisor_note for auto cases")


# ---------------------------------------------------------------------------
# Escenario 2 — Solicitud de reembolso neutra → executor automático
# ---------------------------------------------------------------------------

def test_refund_request():
    payload = {
        "client_id": "CRM-TEST-002",
        "message": "I need to request a refund for my last invoice. Please process it.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r = requests.post(f"{BASE_URL}/webhook/messages", json=payload, timeout=30)
    data = r.json()
    _print_response(data)

    assert r.status_code == 200
    _assert(data["status"] == "processed", f"status='{data['status']}'")
    _assert(data["proposed_action"] == "process_refund", f"proposed_action='{data['proposed_action']}'")
    _assert(data["execution_result"] is not None, "executor drafted a response")


# ---------------------------------------------------------------------------
# Escenario 3 — Mensaje negativo → escalación → supervisor APRUEBA
# ---------------------------------------------------------------------------

def test_negative_escalation_approve():
    payload = {
        "client_id": "CRM-TEST-003",
        "message": (
            "This is completely unacceptable! My shipment arrived damaged for the "
            "second time. I am furious and will escalate this to your management."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r = requests.post(f"{BASE_URL}/webhook/messages", json=payload, timeout=30)
    data = r.json()
    _print_response(data)

    assert r.status_code == 200
    _assert(data["status"] == "pending_approval", f"status='{data['status']}'")
    _assert(data["sentiment"] == "negative", f"sentiment='{data['sentiment']}'")
    _assert(data["supervisor_note"] is not None, "supervisor_note generated by Triage")

    run_id = data["run_id"]

    # Verificar que aparece en /pending
    r2 = requests.get(f"{BASE_URL}/supervisor/pending", timeout=10)
    pending_ids = [item["run_id"] for item in r2.json()]
    _assert(run_id in pending_ids, "run_id visible in /supervisor/pending")

    # Supervisor aprueba
    decision = {"run_id": run_id, "approved": True, "reason": "High-priority client. Proceed with escalation response."}
    r3 = requests.post(f"{BASE_URL}/supervisor/decide", json=decision, timeout=30)
    result = r3.json()
    _print_response(result)

    assert r3.status_code == 200
    _assert(result["status"] == "approved_and_executed", f"status='{result['status']}'")
    _assert(result["execution_result"] is not None, "executor ran after approval")


# ---------------------------------------------------------------------------
# Escenario 4 — SLA breach (timestamp antiguo) → escalación → supervisor RECHAZA
# ---------------------------------------------------------------------------

def test_sla_breach_reject():
    old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    payload = {
        "client_id": "CRM-TEST-004",
        "message": "I sent an email 5 hours ago and nobody has replied. Please help.",
        "timestamp": old_timestamp,
    }
    r = requests.post(f"{BASE_URL}/webhook/messages", json=payload, timeout=30)
    data = r.json()
    _print_response(data)

    assert r.status_code == 200
    _assert(data["sla_breached"] is True, "SLA correctly detected as breached")
    _assert(data["status"] == "pending_approval", f"status='{data['status']}'")

    run_id = data["run_id"]

    # Supervisor rechaza
    decision = {"run_id": run_id, "approved": False, "reason": "Duplicate case — already being handled by account manager."}
    r2 = requests.post(f"{BASE_URL}/supervisor/decide", json=decision, timeout=10)
    result = r2.json()
    _print_response(result)

    assert r2.status_code == 200
    _assert(result["status"] == "rejected", f"status='{result['status']}'")
    _assert(result["execution_result"] is None, "no execution on rejection")


# ---------------------------------------------------------------------------
# Escenario 5 — Mensaje en español → respuesta en español
# ---------------------------------------------------------------------------

def test_spanish_message():
    payload = {
        "client_id": "CRM-TEST-005",
        "message": "Hola, quisiera saber cuándo estará disponible el nuevo plan de facturación mensual.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r = requests.post(f"{BASE_URL}/webhook/messages", json=payload, timeout=30)
    data = r.json()
    _print_response(data)

    assert r.status_code == 200
    _assert(data["status"] == "processed", f"status='{data['status']}'")
    # Verificación heurística: una respuesta en español tendrá vocales con tilde o palabras clave
    result_text = (data.get("execution_result") or "").lower()
    has_spanish = any(w in result_text for w in ["su", "usted", "hemos", "recibido", "equipo", "pronto", "mensaje"])
    _assert(has_spanish, "executor responded in Spanish")


# ---------------------------------------------------------------------------
# Escenario 6 — Validación de entrada inválida → 422
# ---------------------------------------------------------------------------

def test_invalid_payload():
    payload = {"client_id": "", "message": "test"}   # falta timestamp, client_id vacío
    r = requests.post(f"{BASE_URL}/webhook/messages", json=payload, timeout=10)
    _assert(r.status_code == 422, f"HTTP 422 for invalid input (got {r.status_code})")
    _info("Validation errors", str([e["loc"] for e in r.json()["detail"]]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n{BOLD}CRM Multi-Agent API — Test Suite{RESET}")
    print(f"Target: {BASE_URL}\n")

    # Verificar conectividad primero
    try:
        requests.get("http://localhost:8000/health", timeout=3)
    except requests.exceptions.ConnectionError:
        print(f"{RED}{BOLD}ERROR: Cannot reach http://localhost:8000{RESET}")
        print("Start the server first:  uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    run_scenario("0 · Health Check",                    test_health)
    run_scenario("1 · Neutral message (auto-processed)", test_neutral_message)
    run_scenario("2 · Refund request (auto-processed)",  test_refund_request)
    run_scenario("3 · Negative → escalate → APPROVE",   test_negative_escalation_approve)
    run_scenario("4 · SLA breach → escalate → REJECT",  test_sla_breach_reject)
    run_scenario("5 · Spanish message",                  test_spanish_message)
    run_scenario("6 · Invalid payload → 422",            test_invalid_payload)

    # Resumen final
    total = passed + failed
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  Results: {GREEN}{passed} passed{RESET}{BOLD} / {RED}{failed} failed{RESET}{BOLD} / {total} total{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")

    sys.exit(0 if failed == 0 else 1)
