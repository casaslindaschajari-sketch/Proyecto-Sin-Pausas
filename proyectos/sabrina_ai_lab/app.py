#!/usr/bin/env python3
"""
Sabrina AI Lab - MVP web funcional con backend real.

Servidor web sin dependencias externas:
- Frontend responsive embebido.
- Backend HTTP/JSON con persistencia SQLite o PostgreSQL remoto.
- Calculadora comercial para casos de IA.
- Captura de oportunidades/leads con exportación y campañas de email.
- Asistente estratégico local con integración opcional Azure OpenAI / LiteLLM compatible.
- Sistema de inventario con asistente conversacional para smartstacks.
- Sistema de facturación completo con integración bancaria.
- CASO 1: SIMULACIÓN DE SMARTSTACKS DE CERCANÍA
- CASO 2: SIMULACIÓN DE AUTOMATIZACIÓN CON EMPATÍA (LiteLLM Middleware)
- SIMULACIÓN DE PROYECTOS LLAVE EN MANO

Ejecutar:
    python3 proyectos/sabrina_ai_lab/app.py
Abrir:
    http://127.0.0.1:8000
#!/usr/bin/env python3
"""

#!/usr/bin/env python3
"""
Sabrina AI Lab - MVP web funcional
Ejecutar: python3 app.py
Abrir: http://127.0.0.1:8000
"""

#!/usr/bin/env python3
"""
Sabrina AI Lab - MVP web funcional con backend real.

Servidor web sin dependencias externas:
- Frontend responsive embebido.
- Backend HTTP/JSON con persistencia SQLite o PostgreSQL remoto.
- Calculadora comercial para casos de IA.
- Captura de oportunidades/leads con exportación y campañas de email.
- Asistente estratégico local con integración opcional Azure OpenAI / LiteLLM compatible.
- Sistema de inventario con asistente conversacional para smartstacks.
- Sistema de facturación completo con integración bancaria.
- CASO 1: SIMULACIÓN DE SMARTSTACKS DE CERCANÍA
- CASO 2: SIMULACIÓN DE AUTOMATIZACIÓN CON EMPATÍA (LiteLLM Middleware)
- SIMULACIÓN DE PROYECTOS LLAVE EN MANO

Ejecutar:
    python3 proyectos/sabrina_ai_lab/app.py
Abrir:
    http://127.0.0.1:8000
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import sqlite3
import smtplib
import textwrap
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "sabrina_lab.sqlite3"
HOST = os.environ.get("SABRINA_HOST", "0.0.0.0")
PORT = int(os.environ.get("SABRINA_PORT", "8000"))

# Email config (opcional)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "sabrina@example.com")
SENDER_NAME = os.environ.get("SENDER_NAME", "Sabrina AI Lab")

# Remote DB config (opcional)
USE_REMOTE_DB = os.environ.get("USE_REMOTE_DB", "false").lower() == "true"
REMOTE_DB_URL = os.environ.get("REMOTE_DB_URL", "")


USE_CASES = [
    {
        "id": "smartstacks",
        "title": "Asistente Experto para Negocios y Pymes",
        "tag": "Inventario + ventas",
        "problem": "Vendedores pierden tiempo buscando códigos, stock y fichas técnicas.",
        "solution": "Base local de productos + asistente conversacional para WhatsApp, tablet o mostrador.",
        "model": "Suscripción mensual SaaS para comercios.",
        "price": 290,
        "setup": 850,
        "impact": ["Menos filas", "Respuestas rápidas", "Menos estrés del personal"],
    },
    {
        "id": "middleware",
        "title": "Automatización Empática Multicanal",
        "tag": "LiteLLM + canales",
        "problem": "Emprendedores y equipos responden preguntas repetidas durante horas.",
        "solution": "Proxy unificado que balancea modelos GPT y responde con tono empático en varios canales.",
        "model": "Membresía fija o fee por volumen de interacciones resueltas.",
        "price": 390,
        "setup": 1200,
        "impact": ["Ahorro de tiempo", "Tono consistente", "Control de costos por tokens"],
    },
    {
        "id": "llave-en-mano",
        "title": "Digitalización IA Llave en Mano",
        "tag": "Consultoría",
        "problem": "Empresas tradicionales quieren IA pero temen complejidad, costos y pérdida de datos.",
        "solution": "Módulos Docker para atención, correos, agenda o conocimiento interno funcionando con datos reales.",
        "model": "Proyecto de implementación con setup alto y soporte posterior.",
        "price": 650,
        "setup": 3500,
        "impact": ["Prueba viva", "Datos propios", "Sistema transferible"],
    },
]

ROADMAP = [
    {
        "weeks": "1-2",
        "title": "Aprendizaje y entorno",
        "items": ["Terminal y SSH", "LiteLLM", "Pruebas de 3 modelos GPT", "Estimación de costos por respuesta"],
    },
    {
        "weeks": "3-4",
        "title": "MVP con sentido humano",
        "items": ["Caso de uso real", "Backend estable", "Persistencia SQLite", "tmux para disponibilidad"],
    },
    {
        "weeks": "5-6",
        "title": "Pruebas y propuesta comercial",
        "items": ["Interfaz web", "HTTPS con Nginx/Certbot", "Usuarios piloto", "Propuesta para Sin Pausas"],
    },
]


# ============================================
# CONFIGURACIÓN BANCARIA
# ============================================
BANK_ACCOUNTS = [
    {
        "id": "banco_1",
        "name": "Banco Nacional - Cuenta Corriente",
        "bank": "Banco Nacional",
        "account_type": "Cuenta Corriente",
        "account_number": "1234567890",
        "rut": "12.345.678-9",
        "email": "pagos@tunegocio.cl",
        "phone": "+569 1234 5678",
        "active": True
    },
    {
        "id": "banco_2",
        "name": "Banco Internacional - Cuenta Ahorro",
        "bank": "Banco Internacional",
        "account_type": "Cuenta Ahorro",
        "account_number": "0987654321",
        "rut": "98.765.432-1",
        "email": "ahorro@tunegocio.cl",
        "phone": "+569 8765 4321",
        "active": True
    }
]

PAYMENT_METHODS = [
    {"id": "transferencia", "name": "Transferencia Bancaria", "active": True},
    {"id": "tarjeta", "name": "Tarjeta de Crédito/Débito", "active": True},
    {"id": "paypal", "name": "PayPal", "active": False},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                business TEXT NOT NULL,
                email TEXT NOT NULL,
                use_case TEXT NOT NULL,
                pain TEXT NOT NULL,
                budget TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'nuevo'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                use_case TEXT NOT NULL,
                interactions INTEGER NOT NULL,
                human_minutes_saved INTEGER NOT NULL,
                hourly_cost REAL NOT NULL,
                estimated_ai_cost REAL NOT NULL,
                monthly_value REAL NOT NULL,
                suggested_price REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                channel TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                recipient_emails TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                sent_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                recipient_email TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                price REAL,
                description TEXT,
                category TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                channel TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS channel_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                channel TEXT NOT NULL,
                customer_message TEXT NOT NULL,
                reply TEXT NOT NULL,
                source TEXT NOT NULL,
                tokens_estimated INTEGER NOT NULL DEFAULT 0,
                cost_estimated REAL NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                sender TEXT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                client_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'confirmada'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT,
                customer_rut TEXT,
                products TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                payment_method TEXT NOT NULL,
                bank_account TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                payment_proof TEXT,
                verified_by TEXT,
                verified_at TEXT,
                notes TEXT,
                notification_sent INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                bank TEXT NOT NULL,
                account_type TEXT NOT NULL,
                account_number TEXT NOT NULL,
                rut TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                active INTEGER DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                invoice_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TEXT,
                sent_to TEXT,
                status TEXT DEFAULT 'pending'
            )
            """
        )

        if not conn.execute("SELECT COUNT(*) FROM bank_accounts").fetchone()[0]:
            for account in BANK_ACCOUNTS:
                conn.execute(
                    """
                    INSERT INTO bank_accounts (created_at, name, bank, account_type, account_number, rut, email, phone, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (now_iso(), account["name"], account["bank"], account["account_type"],
                     account["account_number"], account["rut"], account.get("email"),
                     account.get("phone"), 1 if account.get("active", True) else 0)
                )

        if not conn.execute("SELECT COUNT(*) FROM payment_methods").fetchone()[0]:
            for method in PAYMENT_METHODS:
                conn.execute(
                    """
                    INSERT INTO payment_methods (created_at, name, active)
                    VALUES (?, ?, ?)
                    """,
                    (now_iso(), method["name"], 1 if method.get("active", True) else 0)
                )


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler: BaseHTTPRequestHandler, html: str, status: int = 200) -> None:
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def file_response(handler: BaseHTTPRequestHandler, content: bytes, filename: str, content_type: str = "text/csv") -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Disposition", f"attachment; filename={filename}")
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def get_dashboard_state() -> dict[str, Any]:
    total, used, free = shutil.disk_usage("/")
    with db_connect() as conn:
        leads = rows_to_dicts(
            conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 20").fetchall()
        )
        estimates = rows_to_dicts(
            conn.execute("SELECT * FROM estimates ORDER BY id DESC LIMIT 10").fetchall()
        )
        events = rows_to_dicts(
            conn.execute("SELECT * FROM assistant_events ORDER BY id DESC LIMIT 10").fetchall()
        )
        lead_count = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]
        estimate_count = conn.execute("SELECT COUNT(*) AS c FROM estimates").fetchone()["c"]
        campaign_count = conn.execute("SELECT COUNT(*) AS c FROM email_campaigns WHERE status='sent'").fetchone()["c"]
        invoice_count = conn.execute("SELECT COUNT(*) AS c FROM invoices").fetchone()["c"]
        pending_invoices = conn.execute("SELECT COUNT(*) AS c FROM invoices WHERE status='pending'").fetchone()["c"]

    azure_ready = all(
        [
            os.environ.get("AZURE_OPENAI_API_KEY"),
            os.environ.get("AZURE_OPENAI_ENDPOINT"),
            os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        ]
    )
    litellm_ready = bool(os.environ.get("LITELLM_BASE_URL"))
    email_ready = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

    return {
        "generated_at": now_iso(),
        "server": {
            "vm_name": "Sabrina",
            "public_ip": "20.115.208.7",
            "os": "Ubuntu 24.04 LTS",
            "hardware": "Standard FX2mds v2 · 2 vCPU · 42 GiB RAM",
            "storage_warning": "Monitorear periódicamente con df -h",
            "disk": {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "used_percent": round((used / total) * 100, 1),
            },
        },
        "integrations": {
            "azure_openai_ready": azure_ready,
            "litellm_ready": litellm_ready,
            "email_ready": email_ready,
            "mode": "Azure/OpenAI real" if azure_ready or litellm_ready else "Simulador local sin credenciales",
        },
        "use_cases": USE_CASES,
        "roadmap": ROADMAP,
        "metrics": {
            "leads": lead_count,
            "estimates": estimate_count,
            "campaigns_sent": campaign_count,
            "invoices": invoice_count,
            "pending_invoices": pending_invoices,
        },
        "leads": leads,
        "estimates": estimates,
        "assistant_events": events,
    }


def get_smartstacks_state() -> dict[str, Any]:
    with db_connect() as conn:
        products = rows_to_dicts(
            conn.execute("SELECT * FROM inventory_products ORDER BY created_at DESC").fetchall()
        )
        conversations = rows_to_dicts(
            conn.execute("SELECT * FROM inventory_conversations ORDER BY id DESC LIMIT 20").fetchall()
        )
        total_stock = conn.execute("SELECT SUM(quantity) AS total FROM inventory_products").fetchone()["total"] or 0
        product_count = conn.execute("SELECT COUNT(*) AS c FROM inventory_products").fetchone()["c"]

    return {
        "products": products,
        "conversations": conversations,
        "metrics": {
            "total_products": product_count,
            "total_stock": total_stock,
        },
    }


def validate_required(payload: dict[str, Any], fields: list[str]) -> list[str]:
    missing = []
    for field in fields:
        value = payload.get(field)
        if value is None or str(value).strip() == "":
            missing.append(field)
    return missing


def create_lead(payload: dict[str, Any]) -> dict[str, Any]:
    missing = validate_required(payload, ["name", "business", "email", "use_case", "pain", "budget"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    with db_connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads (created_at, name, business, email, use_case, pain, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_iso(),
                str(payload["name"]).strip(),
                str(payload["business"]).strip(),
                str(payload["email"]).strip(),
                str(payload["use_case"]).strip(),
                str(payload["pain"]).strip(),
                str(payload["budget"]).strip(),
            ),
        )
        lead_id = cur.lastrowid

    return {
        "ok": True,
        "lead_id": lead_id,
        "message": "Oportunidad registrada. Ya queda guardada en SQLite para seguimiento comercial.",
    }


def estimate_cost(payload: dict[str, Any]) -> dict[str, Any]:
    use_case_id = str(payload.get("use_case", "smartstacks"))
    interactions = max(1, int(payload.get("interactions", 1500)))
    minutes_saved = max(1, int(payload.get("minutes_saved", 4)))
    hourly_cost = max(0.0, float(payload.get("hourly_cost", 9.5)))

    use_case = next((case for case in USE_CASES if case["id"] == use_case_id), USE_CASES[0])

    avg_tokens = 900
    cost_per_1k_tokens = 0.004
    estimated_ai_cost = interactions * (avg_tokens / 1000) * cost_per_1k_tokens

    saved_hours = interactions * minutes_saved / 60
    monthly_value = saved_hours * hourly_cost
    suggested_price = max(use_case["price"], monthly_value * 0.28 + estimated_ai_cost * 2)

    result = {
        "ok": True,
        "use_case": use_case["title"],
        "interactions": interactions,
        "human_hours_saved": round(saved_hours, 1),
        "estimated_ai_cost": round(estimated_ai_cost, 2),
        "monthly_value": round(monthly_value, 2),
        "suggested_price": round(suggested_price, 2),
        "setup": use_case["setup"],
        "margin_hint": round(suggested_price - estimated_ai_cost, 2),
    }

    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO estimates (
                created_at, use_case, interactions, human_minutes_saved, hourly_cost,
                estimated_ai_cost, monthly_value, suggested_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_iso(),
                use_case_id,
                interactions,
                minutes_saved,
                hourly_cost,
                result["estimated_ai_cost"],
                result["monthly_value"],
                result["suggested_price"],
            ),
        )

    return result


def local_strategy_answer(question: str, channel: str) -> str:
    q = question.lower()
    if "ferreter" in q or "inventario" in q or "stock" in q or "producto" in q:
        focus = USE_CASES[0]
    elif "mensaje" in q or "instagram" in q or "whatsapp" in q or "redes" in q:
        focus = USE_CASES[1]
    elif "empresa" in q or "docker" in q or "agenda" in q or "correo" in q:
        focus = USE_CASES[2]
    else:
        focus = USE_CASES[1]

    return textwrap.dedent(
        f"""
        Para este caso en canal {channel}, conviene partir con: {focus['title']}.

        Problema humano detectado:
        {focus['problem']}

        MVP recomendado para las 6 semanas:
        1. Cargar una base pequeña de datos reales del negocio.
        2. Crear un flujo de conversación simple con tono empático.
        3. Medir tres métricas: minutos ahorrados, respuestas correctas y oportunidades comerciales.
        4. Preparar una propuesta para Sin Pausas con precio mensual sugerido desde USD {focus['price']} y setup desde USD {focus['setup']}.

        Próximo paso práctico:
        Conseguir 20 preguntas reales de usuarios/clientes y probarlas en la interfaz para validar si la solución reduce carga operativa.
        """
    ).strip()


def get_inventory_products() -> list[dict[str, Any]]:
    with db_connect() as conn:
        return rows_to_dicts(
            conn.execute("SELECT id, code, name, quantity, price, description, category FROM inventory_products ORDER BY name").fetchall()
        )


def format_inventory_context(products: list[dict[str, Any]]) -> str:
    if not products:
        return "El inventario está vacío."

    lines = ["INVENTARIO ACTUAL:\n"]
    for p in products:
        lines.append(f"- Código {p['code']}: {p['name']} (Stock: {p['quantity']} unidades, Precio: ${p['price'] or 'N/A'})")
        if p.get('description'):
            lines.append(f"  Descripción: {p['description']}")

    return "\n".join(lines)


def get_inventory_context() -> str:
    return format_inventory_context(get_inventory_products())


_INVENTORY_STOPWORDS = {
    "tienes", "tiene", "tienen", "hay", "tenemos", "tengo", "disponible", "disponibles",
    "stock", "cuanto", "cuanta", "cuantos", "cuantas", "cuesta", "cuestan", "precio", "precios",
    "costo", "costos", "valor", "de", "del", "el", "la", "los", "las", "un", "una", "unos", "unas",
    "que", "cual", "cuales", "es", "son", "por", "favor", "porfavor", "como", "quiero", "necesito",
    "busco", "sobre", "info", "informacion", "dame", "dime", "puedes", "podrias", "codigo", "code",
    "referencia", "en", "con", "para", "y", "o", "me", "nos", "si", "no", "hola", "buenas",
}


def _normalize_text(text: str) -> str:
    replacements = str.maketrans("áéíóúñü", "aeiounu")
    cleaned = text.lower().translate(replacements)
    for ch in "¿?¡!.,;:()[]{}\"'":
        cleaned = cleaned.replace(ch, " ")
    return cleaned
def _extract_search_terms(question: str) -> list[str]:
    words = _normalize_text(question).split()
    return [w for w in words if w and w not in _INVENTORY_STOPWORDS]


def _word_variants(word: str) -> set[str]:
    variants = {word}
    for suffix in ("es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            variants.add(word[: -len(suffix)])
    return variants


def _term_matches(term: str, haystack_words: set[str]) -> bool:
    term_variants = _word_variants(term)
    for word in haystack_words:
        if term_variants & _word_variants(word):
            return True
    return False


def _search_inventory_products(products: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    if not terms:
        return []
    matches = []
    for p in products:
        haystack_words = set(_normalize_text(f"{p['code']} {p['name']} {p.get('description') or ''}").split())
        if all(_term_matches(term, haystack_words) for term in terms):
            matches.append(p)
    return matches


def local_inventory_answer(question: str, products: list[dict[str, Any]], channel: str) -> str:
    if not products:
        return "Nuestro inventario está vacío por ahora. Agrega productos desde el panel de SmartStacks para poder responder consultas."

    terms = _extract_search_terms(question)

    if not terms:
        return f"Claro, este es nuestro catálogo actual:\n\n{format_inventory_context(products)}\n\n¿Buscas algo en particular?"

    matches = _search_inventory_products(products, terms)

    if not matches:
        catalog_names = ", ".join(p["name"] for p in products[:5])
        if len(products) > 5:
            catalog_names += f" y {len(products) - 5} productos más"
        return (
            f"No tenemos '{' '.join(terms)}' en nuestro inventario actual. "
            f"Estos son los productos que sí tenemos disponibles: {catalog_names}."
        )

    lines = [f"Sí, tenemos {len(matches)} producto(s) que coinciden con '{' '.join(terms)}':\n"]
    for p in matches:
        stock_line = f"Stock: {p['quantity']} unidades" if p["quantity"] > 0 else "Sin stock por el momento"
        price_line = f"Precio: ${p['price']}" if p.get("price") else "Precio: no definido"
        lines.append(f"- {p['name']} (Código {p['code']}) — {stock_line}, {price_line}")
        if p.get("description"):
            lines.append(f"  {p['description']}")

    return "\n".join(lines)


def smartstacks_assistant_reply(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    channel = str(payload.get("channel", "web")).strip() or "web"

    if not question:
        return {"ok": False, "error": "Escribe una pregunta sobre el inventario."}

    products = get_inventory_products()
    answer, source = call_external_model_with_inventory(question, channel, products)

    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO inventory_conversations (created_at, channel, question, answer, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now_iso(), channel, question, answer, source),
        )

    return {"ok": True, "answer": answer, "source": source}


def call_external_model_with_inventory(question: str, channel: str, products: list[dict[str, Any]]) -> tuple[str, str]:
    inventory_context = format_inventory_context(products)
    litellm_base = os.environ.get("LITELLM_BASE_URL", "").rstrip("/")
    litellm_key = os.environ.get("LITELLM_API_KEY", "sk-local")
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    system_prompt = f"""Eres un asistente experto de atención al cliente para un negocio.
Responde preguntas sobre productos, disponibilidad y detalles técnicos basándote ÚNICAMENTE en el inventario proporcionado.
Sé conciso, amable y profesional. Si algo no está en el inventario, indícalo claramente.

{inventory_context}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Canal: {channel}\nConsulta: {question}"},
    ]

    if litellm_base:
        url = f"{litellm_base}/chat/completions"
        payload = {"model": os.environ.get("LITELLM_MODEL", "gpt-4o-mini"), "messages": messages}
        headers = {"Authorization": f"Bearer {litellm_key}", "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "litellm"

    if azure_key and azure_endpoint and azure_deployment:
        url = (
            f"{azure_endpoint}/openai/deployments/{azure_deployment}/chat/completions"
            f"?api-version={azure_version}"
        )
        payload = {"messages": messages, "temperature": 0.4, "max_tokens": 650}
        headers = {"api-key": azure_key, "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "azure_openai"

    return local_inventory_answer(question, products, channel), "local"


def call_external_model(question: str, channel: str) -> tuple[str, str]:
    litellm_base = os.environ.get("LITELLM_BASE_URL", "").rstrip("/")
    litellm_key = os.environ.get("LITELLM_API_KEY", "sk-local")
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asesor estratégico empático para Sabrina AI Lab. "
                "Transformas infraestructura de IA en propuestas humanas, simples y monetizables."
            ),
        },
        {"role": "user", "content": f"Canal: {channel}\nConsulta: {question}"},
    ]

    if litellm_base:
        url = f"{litellm_base}/chat/completions"
        payload = {"model": os.environ.get("LITELLM_MODEL", "gpt-4o-mini"), "messages": messages}
        headers = {"Authorization": f"Bearer {litellm_key}", "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "litellm"

    if azure_key and azure_endpoint and azure_deployment:
        url = (
            f"{azure_endpoint}/openai/deployments/{azure_deployment}/chat/completions"
            f"?api-version={azure_version}"
        )
        payload = {"messages": messages, "temperature": 0.4, "max_tokens": 650}
        headers = {"api-key": azure_key, "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "azure_openai"

    return local_strategy_answer(question, channel), "local"


def post_chat_completion(url: str, headers: dict[str, str], payload: dict[str, Any]) -> str:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            return parsed["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
        return (
            "No pude completar la llamada externa al modelo. "
            f"Modo seguro activado.\n\n{local_strategy_answer(payload['messages'][-1]['content'], 'web')}\n\n"
            f"Detalle técnico: {exc}"
        )


def assistant_reply(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    channel = str(payload.get("channel", "web")).strip() or "web"
    if not question:
        return {"ok": False, "error": "Escribe una pregunta o situación de negocio."}

    answer, source = call_external_model(question, channel)
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO assistant_events (created_at, channel, question, answer, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now_iso(), channel, question, answer, source),
        )

    return {"ok": True, "answer": answer, "source": source}


# ============================================
# SERVICIO 2 · AUTOMATIZACIÓN EMPÁTICA MULTICANAL
# ============================================

CHANNEL_COST_PER_1K_TOKENS = float(os.environ.get("CHANNEL_COST_PER_1K_TOKENS", "0.002"))
CHANNEL_TONE_HINTS = {
    "whatsapp": "cercano, breve y directo, como un mensaje de chat",
    "instagram": "casual, amigable y con emojis moderados",
    "email": "formal, bien estructurado y completo",
    "web": "claro, profesional y directo",
}


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


_SPANISH_NUMBER_WORDS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "quince": 15, "veinte": 20, "veinticinco": 25, "treinta": 30,
    "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80,
    "noventa": 90, "cien": 100, "cientos": 100, "doscientos": 200, "trescientos": 300,
    "quinientos": 500, "mil": 1000,
}


def _extract_mentioned_quantity(normalized_text: str) -> str | None:
    candidates = [int(n) for n in re.findall(r"\b(\d{1,6})\b", normalized_text)]
    for word, value in _SPANISH_NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", normalized_text):
            candidates.append(value)
    return str(max(candidates)) if candidates else None


_CHANNEL_INTENTS = [
    (
        "urgente",
        ("reclamo", "queja", "problema", "no funciona", "esta mal", "urgente", "emergencia", "no llego", "no llega", "roto", "cancelar mi pedido"),
        "Lamento mucho el inconveniente, entiendo la molestia.",
        "Vamos a resolverlo lo antes posible; un miembro de nuestro equipo dará seguimiento a tu caso hoy mismo.",
    ),
    (
        "logistica",
        ("envio", "envios", "despacho", "despachos", "logistica", "reparto", "repartos", "pedido", "pedidos", "tracking", "seguimiento de pedido", "distribucion", "delivery"),
        None,
        None,
    ),
    (
        "agendar",
        ("agendar", "cita", "reunion", "llamada", "disponibilidad", "horario", "agenda"),
        "Con gusto coordinamos un espacio para conversarlo con calma.",
        "Cuéntame qué día y horario te acomoda y te confirmamos la cita; también puedes escribirnos por este mismo canal.",
    ),
    (
        "precio",
        ("precio", "costo", "cuanto cuesta", "cuanto sale", "comprar", "cotizacion", "presupuesto", "planes", "mensualidad"),
        "Con gusto te ayudo con esa información.",
        "Te puedo enviar una cotización detallada por este mismo canal; solo cuéntame el volumen aproximado que manejas para ajustarla a tu caso.",
    ),
    (
        "agradecimiento",
        ("gracias", "excelente", "genial", "muy bien", "buen servicio", "perfecto"),
        "¡Gracias a ti por tu mensaje, nos alegra mucho leerte!",
        "Cualquier otra cosa que necesites, aquí estamos.",
    ),
    (
        "saludo",
        ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "que tal"),
        "¡Hola! Un gusto saludarte.",
        "Cuéntame en qué te podemos ayudar hoy.",
    ),
]


def local_channel_answer(message: str, channel: str) -> str:
    normalized = _normalize_text(message)
    tone = CHANNEL_TONE_HINTS.get(channel.lower(), "cercano y profesional")

    for intent, keywords, opening, closing in _CHANNEL_INTENTS:
        if not any(kw in normalized for kw in keywords):
            continue

        if intent == "logistica":
            qty = _extract_mentioned_quantity(normalized)
            volume_line = f" con un volumen como el tuyo (~{qty} al día)" if qty else ""
            opening = f"Sí, esto se puede automatizar{volume_line}."
            closing = (
                "Con nuestra Automatización Empática Multicanal centralizamos WhatsApp, redes y correo en un solo panel, "
                "generamos actualizaciones automáticas de estado de envío para tus clientes y solo escalamos a una persona "
                "cuando el caso realmente lo requiere. El siguiente paso natural sería agendar una llamada de 15 minutos "
                "para revisar tus canales actuales y armar una propuesta con precio ajustado a tu volumen."
            )

        return f"{opening} (tono {tone})\n\n{closing}"

    trimmed = message.strip()
    excerpt = trimmed if len(trimmed) <= 140 else trimmed[:137].rstrip() + "..."
    return (
        f"Gracias por escribirnos. (tono {tone})\n\n"
        f'Anoté lo que nos compartes: "{excerpt}". Para darte una respuesta precisa, '
        "¿me confirmas si esto es una consulta comercial, un tema de soporte, o quieres agendar una llamada? "
        "Con esa info te conecto con la persona indicada de inmediato."
    )


def call_external_model_channel(message: str, channel: str) -> tuple[str, str]:
    litellm_base = os.environ.get("LITELLM_BASE_URL", "").rstrip("/")
    litellm_key = os.environ.get("LITELLM_API_KEY", "sk-local")
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    tone = CHANNEL_TONE_HINTS.get(channel.lower(), "cercano y profesional")
    system_prompt = (
        "Eres un agente de atención al cliente empático que centraliza respuestas para varios canales. "
        f"Responde en español, con un tono {tone}. Sé breve, humano y resolutivo. "
        "No inventes datos concretos de precios o stock si no los tienes; ofrece dar seguimiento."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Canal: {channel}\nMensaje del cliente: {message}"},
    ]

    if litellm_base:
        url = f"{litellm_base}/chat/completions"
        payload = {"model": os.environ.get("LITELLM_MODEL", "gpt-4o-mini"), "messages": messages}
        headers = {"Authorization": f"Bearer {litellm_key}", "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "litellm"

    if azure_key and azure_endpoint and azure_deployment:
        url = (
            f"{azure_endpoint}/openai/deployments/{azure_deployment}/chat/completions"
            f"?api-version={azure_version}"
        )
        payload = {"messages": messages, "temperature": 0.5, "max_tokens": 400}
        headers = {"api-key": azure_key, "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "azure_openai"

    return local_channel_answer(message, channel), "local"


def channel_reply(payload: dict[str, Any]) -> dict[str, Any]:
    channel = str(payload.get("channel", "web")).strip() or "web"
    message = str(payload.get("message", "")).strip()
    if not message:
        return {"ok": False, "error": "Escribe el mensaje del cliente."}

    answer, source = call_external_model_channel(message, channel)
    tokens_estimated = estimate_tokens(message) + estimate_tokens(answer)
    cost_estimated = round((tokens_estimated / 1000) * CHANNEL_COST_PER_1K_TOKENS, 5)

    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO channel_messages (created_at, channel, customer_message, reply, source, tokens_estimated, cost_estimated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now_iso(), channel, message, answer, source, tokens_estimated, cost_estimated),
        )

    return {
        "ok": True,
        "answer": answer,
        "source": source,
        "tokens_estimated": tokens_estimated,
        "cost_estimated": cost_estimated,
    }


def get_middleware_state() -> dict[str, Any]:
    with db_connect() as conn:
        messages = rows_to_dicts(
            conn.execute("SELECT * FROM channel_messages ORDER BY id DESC LIMIT 20").fetchall()
        )
        totals = conn.execute(
            "SELECT COUNT(*) AS c, COALESCE(SUM(cost_estimated), 0) AS cost FROM channel_messages"
        ).fetchone()
        by_channel = rows_to_dicts(
            conn.execute(
                """
                SELECT channel, COUNT(*) AS total, COALESCE(SUM(cost_estimated), 0) AS cost
                FROM channel_messages GROUP BY channel ORDER BY total DESC
                """
            ).fetchall()
        )

    return {
        "messages": messages,
        "total_messages": totals["c"],
        "total_cost": round(totals["cost"], 5),
        "by_channel": by_channel,
    }


# ============================================
# SERVICIO 3 · DIGITALIZACIÓN IA LLAVE EN MANO
# ============================================

_EMAIL_CATEGORY_RULES = [
    ("urgente", ("urgente", "inmediato", "reclamo", "queja", "no funciona", "roto", "emergencia", "ayuda urgente")),
    ("ventas", ("cotizacion", "precio", "comprar", "presupuesto", "interesado", "contratar", "producto", "servicio")),
    ("administrativo", ("factura", "pago", "recibo", "boleta", "rut", "contrato", "documento")),
    ("spam", ("promocion", "descuento exclusivo", "gana dinero", "premio", "haz click", "gratis", "suscribete")),
]

_EMAIL_SUGGESTED_ACTIONS = {
    "urgente": "Responder en menos de 1 hora. Escalar a soporte humano si es un reclamo grave.",
    "ventas": "Enviar cotización o agendar una llamada comercial en las próximas 24 horas.",
    "administrativo": "Derivar al área de facturación/contabilidad para su gestión.",
    "spam": "Archivar o mover a spam. No requiere respuesta.",
    "general": "Responder con información estándar o agendar un seguimiento.",
}

_EMAIL_PRIORITY_BY_CATEGORY = {
    "urgente": "alta",
    "ventas": "media",
    "administrativo": "media",
    "spam": "baja",
    "general": "baja",
}


def classify_email_local(subject: str, body: str) -> tuple[str, str, str]:
    text = _normalize_text(f"{subject} {body}")
    category = "general"
    for cat, keywords in _EMAIL_CATEGORY_RULES:
        if any(_normalize_text(kw) in text for kw in keywords):
            category = cat
            break

    priority = _EMAIL_PRIORITY_BY_CATEGORY.get(category, "baja")
    action = _EMAIL_SUGGESTED_ACTIONS.get(category, _EMAIL_SUGGESTED_ACTIONS["general"])
    return category, priority, action


def call_external_email_action(category: str, subject: str, body: str) -> tuple[str, str]:
    litellm_base = os.environ.get("LITELLM_BASE_URL", "").rstrip("/")
    litellm_key = os.environ.get("LITELLM_API_KEY", "sk-local")
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    default_action = _EMAIL_SUGGESTED_ACTIONS.get(category, _EMAIL_SUGGESTED_ACTIONS["general"])
    if not litellm_base and not (azure_key and azure_endpoint and azure_deployment):
        return default_action, "local"

    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente que filtra correos entrantes de una empresa. "
                f"Este correo ya fue clasificado como categoría '{category}'. "
                "En máximo 2 frases, en español, sugiere la acción concreta a seguir."
            ),
        },
        {"role": "user", "content": f"Asunto: {subject}\nCuerpo: {body}"},
    ]

    if litellm_base:
        url = f"{litellm_base}/chat/completions"
        payload = {"model": os.environ.get("LITELLM_MODEL", "gpt-4o-mini"), "messages": messages}
        headers = {"Authorization": f"Bearer {litellm_key}", "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "litellm"

    url = (
        f"{azure_endpoint}/openai/deployments/{azure_deployment}/chat/completions"
        f"?api-version={azure_version}"
    )
    payload = {"messages": messages, "temperature": 0.3, "max_tokens": 150}
    headers = {"api-key": azure_key, "Content-Type": "application/json"}
    return post_chat_completion(url, headers, payload), "azure_openai"


def classify_email(payload: dict[str, Any]) -> dict[str, Any]:
    subject = str(payload.get("subject", "")).strip()
    body = str(payload.get("body", "")).strip()
    sender = str(payload.get("sender", "")).strip()

    if not subject and not body:
        return {"ok": False, "error": "Escribe al menos el asunto o el cuerpo del correo."}

    category, priority, local_action = classify_email_local(subject, body)
    action, source = call_external_email_action(category, subject, body)
    if not action:
        action = local_action

    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO email_classifications (created_at, sender, subject, body, category, priority, suggested_action, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now_iso(), sender, subject, body, category, priority, action, source),
        )

    return {
        "ok": True,
        "category": category,
        "priority": priority,
        "suggested_action": action,
        "source": source,
    }


def create_appointment(payload: dict[str, Any]) -> dict[str, Any]:
    client_name = str(payload.get("client_name", "")).strip()
    contact = str(payload.get("contact", "")).strip()
    appointment_date = str(payload.get("appointment_date", "")).strip()
    appointment_time = str(payload.get("appointment_time", "")).strip()
    notes = str(payload.get("notes", "")).strip()

    if not client_name or not contact or not appointment_date or not appointment_time:
        return {"ok": False, "error": "Completa nombre, contacto, fecha y hora."}

    try:
        datetime.strptime(appointment_date, "%Y-%m-%d")
        datetime.strptime(appointment_time, "%H:%M")
    except ValueError:
        return {"ok": False, "error": "Fecha u hora inválida. Usa formato AAAA-MM-DD y HH:MM."}

    with db_connect() as conn:
        conflict = conn.execute(
            """
            SELECT id FROM appointments
            WHERE appointment_date = ? AND appointment_time = ? AND status != 'cancelada'
            """,
            (appointment_date, appointment_time),
        ).fetchone()
        if conflict:
            return {"ok": False, "error": "Ya existe una cita agendada en esa fecha y hora."}

        cursor = conn.execute(
            """
            INSERT INTO appointments (created_at, client_name, contact, appointment_date, appointment_time, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmada')
            """,
            (now_iso(), client_name, contact, appointment_date, appointment_time, notes),
        )
        appointment_id = cursor.lastrowid

    return {
        "ok": True,
        "appointment_id": appointment_id,
        "message": f"Cita confirmada para {client_name} el {appointment_date} a las {appointment_time}.",
    }


def cancel_appointment(payload: dict[str, Any]) -> dict[str, Any]:
    appointment_id = payload.get("appointment_id")
    if not appointment_id:
        return {"ok": False, "error": "Falta appointment_id."}

    with db_connect() as conn:
        conn.execute("UPDATE appointments SET status = 'cancelada' WHERE id = ?", (int(appointment_id),))

    return {"ok": True, "message": "Cita cancelada."}


def get_consulting_state() -> dict[str, Any]:
    with db_connect() as conn:
        emails = rows_to_dicts(
            conn.execute("SELECT * FROM email_classifications ORDER BY id DESC LIMIT 20").fetchall()
        )
        appointments = rows_to_dicts(
            conn.execute(
                "SELECT * FROM appointments ORDER BY appointment_date, appointment_time LIMIT 50"
            ).fetchall()
        )
        email_count = conn.execute("SELECT COUNT(*) AS c FROM email_classifications").fetchone()["c"]
        upcoming_count = conn.execute(
            "SELECT COUNT(*) AS c FROM appointments WHERE status = 'confirmada'"
        ).fetchone()["c"]

    return {
        "emails": emails,
        "appointments": appointments,
        "email_count": email_count,
        "upcoming_count": upcoming_count,
    }

# ============================================
# CASO 1: SMARTSTACKS DE CERCANÍA - ASISTENTE EXPERTO
# ============================================

SMARTSTACKS_DEMO = {
    "id": "smartstacks",
    "name": "🏪 SmartStacks de Cercanía",
    "description": "Asistente conversacional para negocios locales que responde preguntas de inventario al instante.",
    "icon": "🏪",
    "steps": [
        {
            "title": "1. Cargar el Inventario Local",
            "desc": "Subimos los datos de tu negocio: productos, códigos, precios y descripciones.",
            "details": [
                "✅ 42 GiB de RAM para almacenar todo el inventario localmente",
                "✅ Sistema de búsqueda rápida por código y nombre",
                "✅ Base de datos con productos, stock y precios",
                "✅ Historial de consultas para mejorar el asistente"
            ],
            "action": "Cargar Inventario"
        },
        {
            "title": "2. Conectar el Asistente",
            "desc": "Vinculamos el asistente IA a los canales de comunicación de tu negocio.",
            "details": [
                "✅ WhatsApp Business API conectada",
                "✅ Tablet en tienda con interfaz amigable",
                "✅ Web para consultas remotas",
                "✅ Sistema de respuestas en lenguaje natural"
            ],
            "action": "Conectar Asistente"
        },
        {
            "title": "3. Entrenar con Preguntas Reales",
            "desc": "El asistente aprende a entender las preguntas típicas de tus clientes y vendedores.",
            "details": [
                "✅ Análisis de preguntas frecuentes",
                "✅ Entrenamiento con lenguaje coloquial",
                "✅ Reconocimiento de productos por nombre común",
                "✅ Respuestas en menos de 1 segundo"
            ],
            "action": "Entrenar Asistente"
        },
        {
            "title": "4. ¡Asistente en Vivo!",
            "desc": "El sistema ya está funcionando. Aquí puedes ver cómo responde a preguntas reales:",
            "action": "Ver Asistente en Acción"
        }
    ],
    "example_products": [
        {"code": "PER-001", "name": "Perno de Anclaje 3/8\"", "price": 2500, "stock": 45, "description": "Perno de anclaje galvanizado, ideal para fijaciones en hormigón."},
        {"code": "TUB-002", "name": "Tubería PVC 1/2\"", "price": 3800, "stock": 120, "description": "Tubería PVC para instalaciones eléctricas y sanitarias."},
        {"code": "MART-003", "name": "Martillo de Peña", "price": 15900, "stock": 12, "description": "Martillo de peña profesional, mango de fibra de vidrio."},
        {"code": "CIN-004", "name": "Cinta Métrica 5m", "price": 4500, "stock": 28, "description": "Cinta métrica de 5 metros con sistema de freno."},
        {"code": "LLAVE-005", "name": "Llave Francesa 12\"", "price": 8900, "stock": 15, "description": "Llave francesa ajustable, acero cromado."},
        {"code": "DIS-006", "name": "Disco de Corte 4\"", "price": 3200, "stock": 80, "description": "Disco de corte para metal, diámetro 4 pulgadas."},
        {"code": "PINT-007", "name": "Pintura Esmalte Rojo", "price": 12500, "stock": 6, "description": "Pintura esmalte sintético color rojo, 1 litro."},
        {"code": "CLAV-008", "name": "Clavos 2\" Caja x 100", "price": 4800, "stock": 35, "description": "Clavos de 2 pulgadas, caja con 100 unidades."},
        {"code": "SIER-009", "name": "Sierra Manual", "price": 18900, "stock": 8, "description": "Sierra manual para madera, hoja de 24 dientes."},
        {"code": "TAL-010", "name": "Taladro Percutor", "price": 45900, "stock": 4, "description": "Taladro percutor 600W, 13mm, incluye maletín."}
    ],
    "example_questions": [
        {"question": "¿Tienes pernos de anclaje 3/8?", "answer": "Sí, tenemos el Perno de Anclaje 3/8 (Código: PER-001). Disponemos de 45 unidades a $2.500 cada uno. ¿Necesitas que te reserve algunos? 🔩"},
        {"question": "¿Cuánto cuesta la tubería PVC?", "answer": "Tenemos Tubería PVC 1/2\" (Código: TUB-002) a $3.800 cada una. Tenemos 120 unidades en stock. ¿Cuántas necesitas? 🏗️"},
        {"question": "Necesito un martillo bueno", "answer": "Tenemos el Martillo de Peña profesional (Código: MART-003) a $15.900. Es de mango de fibra de vidrio y tenemos 12 unidades disponibles. ¿Te lo llevas? 🔨"},
        {"question": "¿Tienes pintura roja?", "answer": "Sí, tenemos Pintura Esmalte Rojo (Código: PINT-007) a $12.500 el litro. Actualmente tenemos 6 unidades disponibles. ¿Cuántos litros necesitas? 🎨"}
    ],
    "stats": {
        "total_products": 10,
        "total_stock": 353,
        "avg_response_time": 0.8,
        "questions_answered": 0,
        "hours_saved": 0,
        "customer_satisfaction": 0
    }
}


def get_smartstacks_demo_state() -> dict[str, Any]:
    """Obtiene el estado de la demostración del caso 1."""
    return {
        "ok": True,
        "demo": SMARTSTACKS_DEMO,
        "current_step": 0,
        "is_complete": False,
        "stats": {
            "questions_answered": 0,
            "hours_saved": 0,
            "customer_satisfaction": 0
        }
    }


def run_smartstacks_demo_step(payload: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta un paso de la demostración de SmartStacks."""
    step_index = payload.get("step_index", 0)
    user_data = payload.get("user_data", {})
    
    demo = SMARTSTACKS_DEMO
    steps = demo["steps"]
    
    if step_index >= len(steps):
        return {"ok": False, "error": "Paso fuera de rango"}
    
    step = steps[step_index]
    result = {
        "ok": True,
        "step_index": step_index,
        "step": step,
        "completed": False,
        "message": f"✅ Paso '{step['title']}' completado",
        "data": {}
    }
    
    if step_index == 3:  # Último paso - mostrar asistente en acción
        result["data"]["dashboard"] = {
            "stats": demo["stats"],
            "products": demo["example_products"],
            "recent_questions": [
                {"question": "¿Tienes pernos de anclaje 3/8?", "answer": "Sí, tenemos 45 unidades a $2.500 cada uno.", "time": "hace 1 min"},
                {"question": "¿Cuánto cuesta la tubería PVC?", "answer": "Tubería PVC 1/2\" a $3.800. Tenemos 120 unidades.", "time": "hace 3 min"},
                {"question": "Necesito un martillo bueno", "answer": "Martillo de Peña a $15.900. Tenemos 12 unidades.", "time": "hace 5 min"}
            ],
            "impact": {
                "questions_answered": demo["stats"]["questions_answered"],
                "hours_saved": demo["stats"]["hours_saved"],
                "customer_satisfaction": demo["stats"]["customer_satisfaction"]
            }
        }
        result["completed"] = True
        result["message"] = "🎉 ¡Asistente en vivo! Los vendedores ahora responden en segundos."
    
    return result


def simulate_smartstacks_question(payload: dict[str, Any]) -> dict[str, Any]:
    """Simula una pregunta al asistente de inventario."""
    import random
    
    question = payload.get("question", "").strip()
    
    if not question:
        return {"ok": False, "error": "Escribe una pregunta sobre el inventario."}
    
    products = SMARTSTACKS_DEMO["example_products"]
    question_lower = question.lower()
    
    matches = []
    for product in products:
        if product["name"].lower() in question_lower or product["code"].lower() in question_lower:
            matches.append(product)
        elif any(word in question_lower for word in product["name"].lower().split()[:2]):
            matches.append(product)
    
    if not matches:
        categories = {
            "perno": "PER-001",
            "tuberia": "TUB-002",
            "martillo": "MART-003",
            "cinta": "CIN-004",
            "llave": "LLAVE-005",
            "disco": "DIS-006",
            "pintura": "PINT-007",
            "clavo": "CLAV-008",
            "sierra": "SIER-009",
            "taladro": "TAL-010"
        }
        
        for key, code in categories.items():
            if key in question_lower:
                product = next((p for p in products if p["code"] == code), None)
                if product:
                    matches.append(product)
    
    if not matches:
        responses = [
            "No encontré ese producto en nuestro inventario. ¿Podrías darme más detalles? 🤔",
            "Hmm, no reconozco ese producto. ¿Qué estás buscando exactamente? 🛠️",
            "Lo siento, no tengo información sobre ese producto. ¿Puedes describirlo mejor? 📋"
        ]
        return {
            "ok": True,
            "answer": random.choice(responses),
            "matches": [],
            "response_time": round(random.uniform(0.3, 1.2), 1),
            "tokens": estimate_tokens(question) + estimate_tokens(responses[0])
        }
    
    if len(matches) == 1:
        p = matches[0]
        stock_emoji = "✅" if p["stock"] > 10 else "⚠️" if p["stock"] > 0 else "❌"
        stock_text = f"{stock_emoji} Stock: {p['stock']} unidades" if p["stock"] > 0 else "❌ Sin stock disponible"
        
        answer = f"Sí, tenemos {p['name']} (Código: {p['code']}). {stock_text}. Precio: ${p['price']}."
        
        if p["description"]:
            answer += f"\n\n📋 {p['description']}"
        
        if p["stock"] > 10:
            answer += f"\n\n💡 ¿Te gustaría que te reserve algunos? Tenemos buena disponibilidad."
        elif p["stock"] > 0:
            answer += f"\n\n⚠️ Solo quedan {p['stock']} unidades. ¡Te recomiendo reservar pronto!"
        else:
            answer += f"\n\n🔄 Este producto está agotado. Podemos pedirlo en 24 horas."
        
        answer += " 😊"
        
        response_time = round(random.uniform(0.2, 1.2), 1)
        tokens = estimate_tokens(question) + estimate_tokens(answer)
        
        return {
            "ok": True,
            "answer": answer,
            "matches": [dict(p) for p in matches],
            "response_time": response_time,
            "tokens": tokens,
            "source": "inventory_match"
        }
    
    else:
        answer = f"Encontré {len(matches)} productos que coinciden con tu búsqueda:\n\n"
        for p in matches:
            stock_emoji = "✅" if p["stock"] > 10 else "⚠️" if p["stock"] > 0 else "❌"
            answer += f"📌 {p['name']} (Código: {p['code']}) - ${p['price']} - {stock_emoji} Stock: {p['stock']}\n"
        
        answer += "\n¿Cuál te interesa? Dime el código o el nombre y te doy más detalles. 🛒"
        
        response_time = round(random.uniform(0.3, 1.5), 1)
        tokens = estimate_tokens(question) + estimate_tokens(answer)
        
        return {
            "ok": True,
            "answer": answer,
            "matches": [dict(p) for p in matches],
            "response_time": response_time,
            "tokens": tokens,
            "source": "multi_match"
        }


def add_custom_inventory_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Agrega un producto personalizado al inventario de demostración."""
    missing = validate_required(payload, ["code", "name", "stock", "price"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}
    
    try:
        product = {
            "code": str(payload["code"]).strip(),
            "name": str(payload["name"]).strip(),
            "stock": int(payload["stock"]),
            "price": float(payload["price"]),
            "description": str(payload.get("description", "")).strip() or "Sin descripción"
        }
        
        if any(p["code"] == product["code"] for p in SMARTSTACKS_DEMO["example_products"]):
            return {"ok": False, "error": f"El código {product['code']} ya existe"}
        
        SMARTSTACKS_DEMO["example_products"].append(product)
        SMARTSTACKS_DEMO["stats"]["total_products"] += 1
        SMARTSTACKS_DEMO["stats"]["total_stock"] += product["stock"]
        
        return {
            "ok": True,
            "message": f"Producto {product['name']} agregado correctamente",
            "product": product
        }
    except ValueError as e:
        return {"ok": False, "error": f"Error en los datos: {str(e)}"}


# ============================================
# CASO 2: SIMULACIÓN DE AUTOMATIZACIÓN CON EMPATÍA (LiteLLM Middleware)
# ============================================

MIDDLEWARE_DEMO = {
    "id": "middleware",
    "name": "🤖 Automatización de Respuestas con Empatía",
    "description": "Proxy unificado que centraliza respuestas para múltiples canales con tono empático personalizado.",
    "icon": "🤖",
    "steps": [
        {
            "title": "1. Configurar el Proxy LiteLLM",
            "desc": "Instalamos y configuramos LiteLLM como proxy unificado para administrar múltiples modelos GPT.",
            "details": [
                "✅ LiteLLM instalado en la VM con 42 GiB de RAM",
                "✅ 3 modelos GPT configurados (GPT-4, GPT-3.5, GPT-4o-mini)",
                "✅ Balanceo de carga automático configurado",
                "✅ Control de costos por token activado"
            ],
            "action": "Configurar Proxy"
        },
        {
            "title": "2. Conectar Canales",
            "desc": "Conectamos tus canales de comunicación al proxy unificado.",
            "details": [
                "✅ WhatsApp Business API conectada",
                "✅ Instagram Messenger integrado",
                "✅ Email (IMAP/SMTP) configurado",
                "✅ Web Chat conectado"
            ],
            "action": "Conectar Canales"
        },
        {
            "title": "3. Definir Tono y Personalidad",
            "desc": "Configuramos el tono de voz para cada canal según tu marca.",
            "channels": [
                {"name": "WhatsApp", "tone": "Cercano y breve", "emoji": "💬", "example": "¡Hola! ¿En qué te ayudo hoy? 😊"},
                {"name": "Instagram", "tone": "Casual y con emojis", "emoji": "📸", "example": "Hey! Gracias por tu mensaje 🌟 ¿Cómo puedo ayudarte?"},
                {"name": "Email", "tone": "Formal y estructurado", "emoji": "📧", "example": "Estimado/a, agradecemos su consulta..."},
                {"name": "Web", "tone": "Profesional y directo", "emoji": "🌐", "example": "Bienvenido. ¿En qué podemos ayudarle hoy?"}
            ],
            "action": "Configurar Tono"
        },
        {
            "title": "4. ¡Sistema en Vivo!",
            "desc": "El sistema ya está respondiendo con empatía en todos tus canales. Aquí puedes ver ejemplos:",
            "action": "Ver Dashboard"
        }
    ],
    "example_messages": [
        {"channel": "whatsapp", "message": "Hola, ¿tienen envío a domicilio?", "response": "¡Hola! Sí, realizamos envíos a todo el país. ¿Me indicas tu código postal para darte el costo exacto? 😊"},
        {"channel": "instagram", "message": "Me encantó el producto, ¿hay descuento por primera compra?", "response": "¡Gracias! Me alegra que te haya gustado 🌟 Para primera compra tenemos un 10% de descuento. ¿Te interesa? 🛍️"},
        {"channel": "email", "message": "Quisiera una cotización para 50 unidades.", "response": "Estimado/a, gracias por su consulta. Con gusto le enviamos una cotización detallada en las próximas 2 horas. Quedamos atentos."},
        {"channel": "web", "message": "¿Cómo funciona el sistema de garantía?", "response": "Nuestro sistema de garantía cubre 12 meses. Puedes revisar los detalles en nuestra página de políticas o contactarnos para más información."}
    ],
    "stats": {
        "total_messages": 1250,
        "avg_response_time": 2.3,
        "tokens_used": 450000,
        "total_cost": 1.35,
        "hours_saved": 48,
        "response_rate": 98.5
    },
    "channel_stats": [
        {"channel": "WhatsApp", "messages": 450, "avg_time": 1.8, "cost": 0.48},
        {"channel": "Instagram", "messages": 380, "avg_time": 2.1, "cost": 0.41},
        {"channel": "Email", "messages": 220, "avg_time": 3.2, "cost": 0.28},
        {"channel": "Web", "messages": 200, "avg_time": 2.5, "cost": 0.18}
    ]
}


def get_middleware_demo_state() -> dict[str, Any]:
    """Obtiene el estado de la demostración del caso 2."""
    return {
        "ok": True,
        "demo": MIDDLEWARE_DEMO,
        "current_step": 0,
        "is_complete": False
    }


def run_middleware_demo_step(payload: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta un paso de la demostración del middleware."""
    step_index = payload.get("step_index", 0)
    user_data = payload.get("user_data", {})
    
    demo = MIDDLEWARE_DEMO
    steps = demo["steps"]
    
    if step_index >= len(steps):
        return {"ok": False, "error": "Paso fuera de rango"}
    
    step = steps[step_index]
    result = {
        "ok": True,
        "step_index": step_index,
        "step": step,
        "completed": False,
        "message": f"✅ Paso '{step['title']}' completado",
        "data": {}
    }
    
    if step_index == 3:
        result["data"]["dashboard"] = {
            "stats": demo["stats"],
            "recent_messages": [
                {
                    "channel": "WhatsApp",
                    "message": "Hola, ¿tienen stock de martillos?",
                    "response": "¡Sí! Tenemos martillos en stock. ¿Cuántos necesitas? Tenemos diferentes tamaños. 🔨",
                    "time": "hace 2 min",
                    "tokens": 45,
                    "cost": 0.00018
                },
                {
                    "channel": "Instagram",
                    "message": "Me encantó la promoción!",
                    "response": "¡Qué bien! Me alegra que te guste 🌟 La promo termina este viernes, ¿quieres que te reserve algo? 💫",
                    "time": "hace 15 min",
                    "tokens": 38,
                    "cost": 0.00015
                },
                {
                    "channel": "Email",
                    "message": "Solicito información sobre precios mayoristas",
                    "response": "Estimado/a, con gusto le enviamos nuestra lista de precios mayoristas. ¿Podría indicarnos qué productos le interesan?",
                    "time": "hace 1 hora",
                    "tokens": 62,
                    "cost": 0.00025
                }
            ],
            "channel_stats": demo["channel_stats"]
        }
        result["completed"] = True
        result["message"] = "🎉 ¡Sistema completo! Puedes ver el dashboard en vivo."
    
    elif step_index == 2:
        if user_data.get("custom_tone"):
            result["data"]["custom_tone"] = user_data["custom_tone"]
            result["message"] = "✅ Tono personalizado aplicado para todos los canales."
        else:
            result["data"]["channels"] = step["channels"]
    
    return result


def simulate_middleware_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Simula el envío de un mensaje y genera una respuesta."""
    import random
    
    channel = payload.get("channel", "web")
    message = payload.get("message", "").strip()
    custom_tone = payload.get("tone", "")
    
    if not message:
        return {"ok": False, "error": "Escribe un mensaje para simular"}
    
    example_messages = MIDDLEWARE_DEMO["example_messages"]
    matched_example = None
    
    for example in example_messages:
        if example["channel"].lower() == channel.lower():
            example_words = set(example["message"].lower().split())
            message_words = set(message.lower().split())
            if len(example_words.intersection(message_words)) >= 2:
                matched_example = example
                break
    
    if not matched_example:
        responses = {
            "whatsapp": [
                "¡Gracias por tu mensaje! 😊 ¿En qué más puedo ayudarte?",
                "Entendido, te ayudo con eso 💪 Déjame revisar la información.",
                "¡Claro! Déjame revisarlo 📋 y te respondo en un momento."
            ],
            "instagram": [
                "¡Hola! Gracias por escribir 🌟 Cuéntame más sobre lo que necesitas.",
                "Qué interesante, cuéntame más detalles 💫 para poder ayudarte mejor.",
                "¡Me encanta! Vamos a ver eso 🎯 y te doy una respuesta."
            ],
            "email": [
                "Estimado/a, gracias por su consulta. Le responderemos a la brevedad.",
                "Agradecemos su mensaje, le responderemos pronto con la información solicitada.",
                "Hemos recibido su solicitud, le contactaremos en las próximas horas."
            ],
            "web": [
                "Gracias por tu consulta. ¿En qué más puedo ayudarte?",
                "Entendido, te ayudaremos con eso. ¿Algo más que necesites?",
                "Procesando tu solicitud. Te responderemos en breve."
            ]
        }
        
        response = random.choice(responses.get(channel.lower(), ["Gracias por tu mensaje."]))
        
        if custom_tone:
            response = f"({custom_tone}) {response}"
        
        tokens = estimate_tokens(message) + estimate_tokens(response)
        cost = round((tokens / 1000) * 0.002, 5)
        
        return {
            "ok": True,
            "response": response,
            "channel": channel,
            "tokens": tokens,
            "cost": cost,
            "response_time": round(random.uniform(0.8, 2.5), 1),
            "source": "simulated"
        }
    
    tokens = estimate_tokens(message) + estimate_tokens(matched_example["response"])
    cost = round((tokens / 1000) * 0.002, 5)
    
    return {
        "ok": True,
        "response": matched_example["response"],
        "channel": channel,
        "tokens": tokens,
        "cost": cost,
        "response_time": round(random.uniform(0.8, 2.5), 1),
        "source": "example"
    }


# ============================================
# NUEVO MÓDULO: SIMULACIÓN DE PROYECTO "LLAVE EN MANO"
# ============================================

AUTOMATION_DEMOS = {
    "correo": {
        "name": "📬 Automatización de Correos",
        "description": "Filtra, clasifica y prioriza correos entrantes automáticamente, sugiriendo acciones a tomar.",
        "icon": "📧",
        "steps": [
            {"title": "1. Conectar Bandeja de Entrada", "desc": "Simulamos la conexión a tu correo. (En la vida real, usaríamos la API de Gmail/Outlook)", "action": "Conectar Correo Demo"},
            {"title": "2. Definir Reglas de Clasificación", "desc": "Creamos reglas para identificar correos urgentes, de ventas, administrativos o spam.", "action": "Definir Reglas"},
            {"title": "3. Entrenar el Filtro IA", "desc": "El asistente IA aprende a clasificar correos basándose en el contenido y el asunto.", "action": "Entrenar IA"},
            {"title": "4. ¡Automatización Activa!", "desc": "Los correos ahora se clasifican automáticamente y se te notifica de los más importantes.", "action": "Ver Panel de Control"},
        ],
        "example_data": [
            {"sender": "cliente1@gmail.com", "subject": "Urgente: Problema con el pedido #1234", "body": "No he recibido mi pedido y ya pasó la fecha de entrega. Necesito una solución inmediata."},
            {"sender": "proveedor@suministros.cl", "subject": "Cotización de productos", "body": "Buenos días, adjunto la cotización para los productos que nos solicitó la semana pasada. Quedo atento."},
            {"sender": "info@empresa.com", "subject": "Factura del mes de julio", "body": "Adjunto la factura correspondiente al mes de julio. Por favor, revisarla y confirmar su recepción."},
            {"sender": "promociones@spam.com", "subject": "¡Gane un premio!", "body": "¡Haga click aquí y gane un premio increíble! Último día para participar."},
        ]
    },
    "agenda": {
        "name": "📅 Gestión de Agenda Inteligente",
        "description": "Un asistente que agenda, confirma y administra tus citas automáticamente.",
        "icon": "🗓️",
        "steps": [
            {"title": "1. Configurar Disponibilidad", "desc": "Definimos tus horarios de trabajo y días disponibles.", "action": "Configurar Horarios"},
            {"title": "2. Integrar con Calendario", "desc": "Sincronizamos el asistente con tu calendario (Google, Outlook, etc.)", "action": "Sincronizar Calendario"},
            {"title": "3. Definir Tipos de Cita", "desc": "Creamos diferentes tipos de cita: ventas, soporte, consultoría, etc.", "action": "Crear Tipos de Cita"},
            {"title": "4. ¡Sistema de Agendamiento en Vivo!", "desc": "El asistente agenda citas, envía recordatorios y cancela automáticamente.", "action": "Probar Agendamiento"},
        ],
        "example_data": [
            {"client": "María Pérez", "contact": "maria@gmail.com", "date": "2026-08-15", "time": "10:00", "notes": "Reunión de ventas"},
            {"client": "Juan Gómez", "contact": "juan@empresa.cl", "date": "2026-08-16", "time": "15:30", "notes": "Soporte técnico"},
            {"client": "Ana Rodríguez", "contact": "ana@negocio.com", "date": "2026-08-17", "time": "11:00", "notes": "Consultoría de IA"},
        ]
    },
    "whatsapp": {
        "name": "💬 Automatización Empática (WhatsApp)",
        "description": "Un asistente que responde consultas de WhatsApp con un tono empático y personalizado.",
        "icon": "🤖",
        "steps": [
            {"title": "1. Conectar con WhatsApp", "desc": "Configuramos la API de WhatsApp Business para recibir y enviar mensajes.", "action": "Conectar WhatsApp"},
            {"title": "2. Definir Flujos de Conversación", "desc": "Creamos flujos para preguntas frecuentes: precios, stock, envíos, etc.", "action": "Crear Flujos"},
            {"title": "3. Entrenar con Preguntas Reales", "desc": "El asistente aprende a responder con ejemplos reales de tus clientes.", "action": "Entrenar Asistente"},
            {"title": "4. ¡Botón de 'Responder con IA'!", "desc": "Cuando llega un mensaje, el asistente sugiere una respuesta que puedes revisar y enviar.", "action": "Probar Respuesta IA"},
        ],
        "example_data": [
            {"message": "Hola, ¿tienen stock de martillos? Necesito 10 para mañana."},
            {"message": "Buenas, ¿cuánto cuesta el envío a la región de Valparaíso?"},
            {"message": "Quiero agendar una hora para ver el showroom, ¿están disponibles mañana?"},
            {"message": "¡Gracias! Su atención es excelente."},
        ]
    },
    "facturacion": {
        "name": "🧾 Facturación y Pagos Automatizada",
        "description": "Sistema de facturación que genera documentos, envía correos y verifica pagos automáticamente.",
        "icon": "💳",
        "steps": [
            {"title": "1. Configurar Productos y Precios", "desc": "Cargamos tu catálogo de productos con precios y stock.", "action": "Cargar Productos"},
            {"title": "2. Definir Datos Bancarios", "desc": "Configuramos las cuentas bancarias para los pagos.", "action": "Configurar Cuentas"},
            {"title": "3. Crear Plantillas de Factura", "desc": "Diseñamos la plantilla de factura que se enviará a los clientes.", "action": "Diseñar Plantilla"},
            {"title": "4. ¡Sistema de Facturación en Vivo!", "desc": "Crea una factura, el cliente recibe un correo y puede pagar.", "action": "Crear Factura Demo"},
        ],
        "example_data": [
            {"client": "Cliente Demo 1", "products": [{"name": "Producto A", "price": 15000, "qty": 2}, {"name": "Producto B", "price": 5000, "qty": 1}]},
            {"client": "Cliente Demo 2", "products": [{"name": "Producto C", "price": 25000, "qty": 1}, {"name": "Producto D", "price": 10000, "qty": 3}]},
        ]
    }
}


def get_demo_state() -> dict[str, Any]:
    """Obtiene el estado de las demostraciones de proyectos."""
    return {
        "ok": True,
        "demos": AUTOMATION_DEMOS,
        "current_step": 0,
        "demo_data": {},
    }


def run_demo_step(payload: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta un paso de la demostración de un proyecto."""
    demo_id = payload.get("demo_id")
    step_index = payload.get("step_index", 0)
    user_data = payload.get("user_data", {})

    if demo_id not in AUTOMATION_DEMOS:
        return {"ok": False, "error": "Proyecto no encontrado"}

    demo = AUTOMATION_DEMOS[demo_id]
    steps = demo["steps"]
    
    if step_index >= len(steps):
        return {"ok": False, "error": "Paso fuera de rango"}

    step = steps[step_index]
    
    result = {
        "ok": True,
        "step_index": step_index,
        "step": step,
        "completed": False,
        "message": f"Paso '{step['title']}' completado. ¡Excelente progreso!",
        "next_action": "Continuar",
        "data": {}
    }

    if demo_id == "correo":
        if step_index == 3:
            result["data"]["classified_emails"] = [
                {"subject": "Urgente: Problema con el pedido #1234", "category": "urgente", "priority": "alta", "action": "Responder en 1 hora"},
                {"subject": "Cotización de productos", "category": "ventas", "priority": "media", "action": "Enviar cotización"},
                {"subject": "Factura del mes de julio", "category": "administrativo", "priority": "media", "action": "Derivar a contabilidad"},
                {"subject": "¡Gane un premio!", "category": "spam", "priority": "baja", "action": "Archivar"},
            ]
            result["message"] = "✅ ¡Filtro de correos activo! Ahora todos los correos se clasifican automáticamente."
            result["completed"] = True

    elif demo_id == "agenda":
        if step_index == 3:
            result["data"]["appointments"] = [
                {"client": "María Pérez", "date": "2026-08-15", "time": "10:00", "status": "confirmada"},
                {"client": "Juan Gómez", "date": "2026-08-16", "time": "15:30", "status": "confirmada"},
                {"client": "Carlos López", "date": "2026-08-17", "time": "09:00", "status": "pendiente"},
            ]
            result["message"] = "✅ ¡Agenda sincronizada! Las citas se gestionan automáticamente."
            result["completed"] = True

    elif demo_id == "whatsapp":
        if step_index == 3:
            messages = user_data.get("messages", demo["example_data"])
            result["data"]["responses"] = [
                {"message": msg["message"], "response": f"✅ Respuesta empática generada para: '{msg['message'][:30]}...'"}
                for msg in messages
            ]
            result["message"] = "✅ ¡Asistente de WhatsApp activo! Puedes ver las respuestas sugeridas."
            result["completed"] = True

    elif demo_id == "facturacion":
        if step_index == 3:
            client = user_data.get("client", "Cliente Demo")
            products = user_data.get("products", demo["example_data"][0]["products"])
            subtotal = sum(p["price"] * p["qty"] for p in products)
            tax = subtotal * 0.19
            total = subtotal + tax
            
            result["data"]["invoice"] = {
                "number": "INV-2026-0001",
                "client": client,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "status": "enviada"
            }
            result["message"] = f"✅ ¡Factura {result['data']['invoice']['number']} creada y enviada a {client}!"
            result["completed"] = True

    return result


def get_demo_data(demo_id: str) -> dict[str, Any]:
    """Obtiene datos de ejemplo para un demo específico."""
    if demo_id in AUTOMATION_DEMOS:
        return {"ok": True, "data": AUTOMATION_DEMOS[demo_id]["example_data"]}
    return {"ok": False, "error": "Demo no encontrado"}


# ============================================
# FUNCIONES DE INVENTARIO
# ============================================

def add_inventory_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Agrega un producto al inventario."""
    missing = validate_required(payload, ["code", "name", "quantity"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    try:
        code = str(payload["code"]).strip()
        name = str(payload["name"]).strip()
        quantity = int(payload["quantity"])
        price = float(payload.get("price", 0)) if payload.get("price") else None
        description = str(payload.get("description", "")).strip() or None
        category = str(payload.get("category", "")).strip() or None

        with db_connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO inventory_products (created_at, code, name, quantity, price, description, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (now_iso(), code, name, quantity, price, description, category),
            )
            product_id = cur.lastrowid

        return {
            "ok": True,
            "product_id": product_id,
            "message": f"Producto '{name}' (Código: {code}) agregado al inventario con {quantity} unidades.",
        }
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"El código '{code}' ya existe en el inventario."}
    except ValueError as e:
        return {"ok": False, "error": f"Error en los datos: {str(e)}"}


def update_inventory_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Actualiza un producto del inventario."""
    missing = validate_required(payload, ["product_id"])
    if missing:
        return {"ok": False, "error": "Falta el ID del producto."}

    try:
        product_id = int(payload["product_id"])

        updates = []
        values = []

        if "quantity" in payload:
            updates.append("quantity = ?")
            values.append(int(payload["quantity"]))

        if "price" in payload:
            updates.append("price = ?")
            values.append(float(payload["price"]) if payload["price"] else None)

        if "description" in payload:
            updates.append("description = ?")
            values.append(str(payload["description"]).strip() or None)

        if "name" in payload:
            updates.append("name = ?")
            values.append(str(payload["name"]).strip())

        if not updates:
            return {"ok": False, "error": "No hay campos para actualizar."}

        values.append(product_id)

        with db_connect() as conn:
            conn.execute(f"UPDATE inventory_products SET {', '.join(updates)} WHERE id = ?", values)

        return {"ok": True, "message": "Producto actualizado correctamente."}
    except ValueError as e:
        return {"ok": False, "error": f"Error en los datos: {str(e)}"}


def delete_inventory_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Elimina un producto del inventario."""
    product_id = payload.get("product_id")
    if not product_id:
        return {"ok": False, "error": "Falta el ID del producto."}

    try:
        product_id = int(product_id)
        with db_connect() as conn:
            conn.execute("DELETE FROM inventory_products WHERE id = ?", (product_id,))

        return {"ok": True, "message": "Producto eliminado correctamente."}
    except ValueError:
        return {"ok": False, "error": "ID inválido."}


def export_leads_csv() -> bytes:
    """Exporta todos los leads a CSV."""
    with db_connect() as conn:
        leads = conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()

    output = io.StringIO()
    if leads:
        writer = csv.writer(output)
        writer.writerow(["ID", "Fecha", "Nombre", "Negocio", "Email", "Caso", "Dolor", "Presupuesto", "Estado"])
        for lead in leads:
            writer.writerow(
                [
                    lead["id"],
                    lead["created_at"],
                    lead["name"],
                    lead["business"],
                    lead["email"],
                    lead["use_case"],
                    lead["pain"],
                    lead["budget"],
                    lead["status"],
                ]
            )

    return output.getvalue().encode("utf-8")


def export_leads_json() -> bytes:
    """Exporta todos los leads a JSON."""
    with db_connect() as conn:
        leads = rows_to_dicts(conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall())

    return json.dumps(leads, ensure_ascii=False, indent=2).encode("utf-8")


def export_inventory_csv() -> bytes:
    """Exporta inventario a CSV."""
    with db_connect() as conn:
        products = conn.execute("SELECT * FROM inventory_products ORDER BY created_at DESC").fetchall()

    output = io.StringIO()
    if products:
        writer = csv.writer(output)
        writer.writerow(["ID", "Código", "Nombre", "Cantidad", "Precio", "Categoría", "Descripción", "Fecha"])
        for p in products:
            writer.writerow(
                [
                    p["id"],
                    p["code"],
                    p["name"],
                    p["quantity"],
                    p["price"] or "",
                    p["category"] or "",
                    p["description"] or "",
                    p["created_at"],
                ]
            )

    return output.getvalue().encode("utf-8")


def send_email(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    """Envía un correo individual."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False, "Email no configurado. Configura SMTP_HOST, SMTP_USER, SMTP_PASSWORD."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = recipient

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

        return True, "Correo enviado"
    except Exception as e:
        return False, str(e)


def create_email_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    """Crea una campaña de email (draft)."""
    missing = validate_required(payload, ["subject", "body", "recipient_emails"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    recipient_list = payload.get("recipient_emails", [])
    if not isinstance(recipient_list, list) or not recipient_list:
        return {"ok": False, "error": "recipient_emails debe ser una lista de emails"}

    recipient_str = json.dumps(recipient_list)

    with db_connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO email_campaigns (created_at, subject, body, recipient_emails, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now_iso(), payload["subject"], payload["body"], recipient_str, "draft"),
        )
        campaign_id = cur.lastrowid

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "status": "draft",
        "message": f"Campaña creada con {len(recipient_list)} destinatarios. Estado: draft",
    }


def send_email_campaign(campaign_id: int) -> dict[str, Any]:
    """Envía una campaña de email."""
    with db_connect() as conn:
        campaign = conn.execute("SELECT * FROM email_campaigns WHERE id = ?", (campaign_id,)).fetchone()

        if not campaign:
            return {"ok": False, "error": "Campaña no encontrada"}

        if campaign["status"] == "sent":
            return {"ok": False, "error": "Esta campaña ya fue enviada"}

        recipient_emails = json.loads(campaign["recipient_emails"])
        sent_count = 0
        failed_count = 0
        errors = []

        for email in recipient_emails:
            lead = conn.execute("SELECT name FROM leads WHERE email = ? ORDER BY id DESC LIMIT 1", (email,)).fetchone()
            recipient_name = lead["name"] if lead else email
            personalized_body = campaign["body"].replace("{name}", recipient_name).replace("{email}", email)

            success, msg = send_email(email, campaign["subject"], personalized_body)
            if success:
                sent_count += 1
            else:
                failed_count += 1
                errors.append(f"{email}: {msg}")

            conn.execute(
                """
                INSERT INTO email_logs (campaign_id, recipient_email, sent_at, status, error_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (campaign_id, email, now_iso(), "sent" if success else "failed", msg if not success else None),
            )

        conn.execute(
            "UPDATE email_campaigns SET status = 'sent', sent_at = ? WHERE id = ?", (now_iso(), campaign_id)
        )

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "sent": sent_count,
        "failed": failed_count,
        "message": f"Campaña enviada: {sent_count} exitosos, {failed_count} fallidos",
        "errors": errors if errors else None,
    }


def send_single_email(payload: dict[str, Any]) -> dict[str, Any]:
    """Envía un correo único a un lead."""
    missing = validate_required(payload, ["lead_id", "subject", "body"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    lead_id = int(payload["lead_id"])

    with db_connect() as conn:
        lead = conn.execute("SELECT email, name FROM leads WHERE id = ?", (lead_id,)).fetchone()

        if not lead:
            return {"ok": False, "error": "Lead no encontrado"}

        body = payload["body"].replace("{name}", lead["name"]).replace("{email}", lead["email"])

        success, msg = send_email(lead["email"], payload["subject"], body)

        if not success:
            return {"ok": False, "error": f"No se pudo enviar: {msg}"}

        conn.execute(
            """
            INSERT INTO email_logs (campaign_id, recipient_email, sent_at, status, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (-1, lead["email"], now_iso(), "sent", None),
        )

    return {
        "ok": True,
        "message": f"Correo enviado a {lead['email']}",
        "lead_id": lead_id,
    }


# ============================================
# FUNCIONES DE FACTURACIÓN
# ============================================

def generate_invoice_number() -> str:
    """Genera un número de factura único."""
    with db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM invoices").fetchone()["c"]
    return f"INV-{datetime.now().strftime('%Y%m')}-{count + 1:04d}"


def create_invoice(payload: dict[str, Any]) -> dict[str, Any]:
    """Crea una nueva factura a partir de los productos seleccionados."""
    missing = validate_required(payload, ["customer_name", "customer_email", "products", "payment_method", "bank_account_id"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    try:
        products = payload["products"]
        if not isinstance(products, list) or not products:
            return {"ok": False, "error": "Debe seleccionar al menos un producto"}

        subtotal = 0
        product_details = []
        with db_connect() as conn:
            for item in products:
                product_id = item.get("product_id")
                quantity = int(item.get("quantity", 1))
                if not product_id:
                    return {"ok": False, "error": "Cada producto debe tener un ID"}

                product = conn.execute(
                    "SELECT id, code, name, price FROM inventory_products WHERE id = ?",
                    (product_id,)
                ).fetchone()

                if not product:
                    return {"ok": False, "error": f"Producto ID {product_id} no encontrado"}

                if product["price"] is None:
                    return {"ok": False, "error": f"El producto {product['name']} no tiene precio definido"}

                if product["quantity"] < quantity:
                    return {"ok": False, "error": f"Stock insuficiente para {product['name']}. Disponible: {product['quantity']}"}

                unit_price = float(product["price"])
                total_price = unit_price * quantity
                subtotal += total_price

                product_details.append({
                    "product_id": product["id"],
                    "code": product["code"],
                    "name": product["name"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })

                conn.execute(
                    "UPDATE inventory_products SET quantity = quantity - ? WHERE id = ?",
                    (quantity, product["id"])
                )

        tax_rate = 0.19
        tax = subtotal * tax_rate
        total = subtotal + tax

        invoice_number = generate_invoice_number()
        payment_method = str(payload["payment_method"])
        bank_account_id = int(payload["bank_account_id"])

        bank_account = None
        with db_connect() as conn:
            bank_account = conn.execute(
                "SELECT * FROM bank_accounts WHERE id = ? AND active = 1",
                (bank_account_id,)
            ).fetchone()

        if not bank_account:
            return {"ok": False, "error": "Cuenta bancaria no válida o inactiva"}

        with db_connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO invoices (
                    invoice_number, created_at, customer_name, customer_email, customer_phone,
                    customer_rut, products, subtotal, tax, total, payment_method, bank_account,
                    status, notification_sent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_number,
                    now_iso(),
                    str(payload["customer_name"]).strip(),
                    str(payload["customer_email"]).strip(),
                    str(payload.get("customer_phone", "")).strip() or None,
                    str(payload.get("customer_rut", "")).strip() or None,
                    json.dumps(product_details, ensure_ascii=False),
                    subtotal,
                    tax,
                    total,
                    payment_method,
                    json.dumps(dict(bank_account), ensure_ascii=False),
                    "pending",
                    0
                )
            )
            invoice_id = cur.lastrowid

        create_invoice_notification(invoice_id, "pending", f"Nueva factura {invoice_number} creada")
        send_invoice_email(invoice_id, payload["customer_email"])

        return {
            "ok": True,
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "payment_method": payment_method,
            "bank_account": dict(bank_account),
            "message": f"Factura {invoice_number} creada exitosamente. Revisa tu correo para los datos de pago."
        }

    except ValueError as e:
        return {"ok": False, "error": f"Error en los datos: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": f"Error al crear la factura: {str(e)}"}


def send_invoice_email(invoice_id: int, recipient_email: str) -> None:
    """Envía el correo con los datos de la factura."""
    with db_connect() as conn:
        invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not invoice:
            return

        bank_account = json.loads(invoice["bank_account"])
        products = json.loads(invoice["products"])

        product_list = "\n".join([
            f"- {p['name']} x{p['quantity']}: ${p['total_price']:.2f}"
            for p in products
        ])

        body = f"""
        Estimado/a {invoice['customer_name']},

        Gracias por tu compra. Aquí están los detalles de tu factura:

        Número de Factura: {invoice['invoice_number']}
        Fecha: {invoice['created_at']}

        Productos:
        {product_list}

        Subtotal: ${invoice['subtotal']:.2f}
        IVA (19%): ${invoice['tax']:.2f}
        TOTAL: ${invoice['total']:.2f}

        Método de pago: {invoice['payment_method']}

        Datos bancarios para transferencia:
        Banco: {bank_account['bank']}
        Tipo de Cuenta: {bank_account['account_type']}
        Número de Cuenta: {bank_account['account_number']}
        RUT: {bank_account['rut']}
        Email: {bank_account.get('email', 'No especificado')}
        Teléfono: {bank_account.get('phone', 'No especificado')}

        Importante:
        1. Realiza la transferencia por el monto total indicado.
        2. Envía una captura de pantalla del comprobante de pago a {bank_account.get('email', SENDER_EMAIL)}.
        3. Una vez verificado el pago, confirmaremos tu pedido.

        Para cualquier consulta, responde a este correo.

        Saludos cordiales,
        {SENDER_NAME}
        """

        subject = f"Factura {invoice['invoice_number']} - Tu compra en {SENDER_NAME}"

        success, message = send_email(recipient_email, subject, body)
        if success:
            with db_connect() as conn:
                conn.execute(
                    """
                    UPDATE invoices SET notification_sent = 1
                    WHERE id = ?
                    """,
                    (invoice_id,)
                )


def create_invoice_notification(invoice_id: int, notification_type: str, message: str) -> None:
    """Crea una notificación para el administrador sobre una factura."""
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO invoice_notifications (created_at, invoice_id, type, message, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now_iso(), invoice_id, notification_type, message, "pending")
        )


def get_invoices() -> dict[str, Any]:
    """Obtiene todas las facturas."""
    with db_connect() as conn:
        invoices = rows_to_dicts(
            conn.execute("SELECT * FROM invoices ORDER BY created_at DESC").fetchall()
        )
        for invoice in invoices:
            if invoice.get("products"):
                try:
                    invoice["products"] = json.loads(invoice["products"])
                except:
                    pass
            if invoice.get("bank_account"):
                try:
                    invoice["bank_account"] = json.loads(invoice["bank_account"])
                except:
                    pass

    return {"ok": True, "invoices": invoices}


def get_invoice(invoice_id: int) -> dict[str, Any]:
    """Obtiene una factura específica."""
    with db_connect() as conn:
        invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not invoice:
            return {"ok": False, "error": "Factura no encontrada"}

        invoice_dict = dict(invoice)
        if invoice_dict.get("products"):
            try:
                invoice_dict["products"] = json.loads(invoice_dict["products"])
            except:
                pass
        if invoice_dict.get("bank_account"):
            try:
                invoice_dict["bank_account"] = json.loads(invoice_dict["bank_account"])
            except:
                pass

    return {"ok": True, "invoice": invoice_dict}


def update_invoice_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Actualiza el estado de una factura."""
    missing = validate_required(payload, ["invoice_id", "status"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    invoice_id = int(payload["invoice_id"])
    status = str(payload["status"]).lower()
    valid_statuses = ["pending", "paid", "cancelled", "verified"]

    if status not in valid_statuses:
        return {"ok": False, "error": f"Estado inválido. Debe ser: {', '.join(valid_statuses)}"}

    with db_connect() as conn:
        invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not invoice:
            return {"ok": False, "error": "Factura no encontrada"}

        conn.execute(
            """
            UPDATE invoices SET status = ?, verified_at = ?
            WHERE id = ?
            """,
            (status, now_iso() if status == "verified" else None, invoice_id)
        )

        message = f"Factura {invoice['invoice_number']} cambiada a estado: {status}"
        create_invoice_notification(invoice_id, status, message)

        if status == "verified":
            verified_by = payload.get("verified_by", "Sistema")
            conn.execute(
                """
                UPDATE invoices SET verified_by = ?
                WHERE id = ?
                """,
                (verified_by, invoice_id)
            )
            create_invoice_notification(invoice_id, "verified",
                                       f"Factura {invoice['invoice_number']} verificada por {verified_by}")

    return {"ok": True, "message": f"Factura actualizada a estado: {status}"}


def upload_payment_proof(payload: dict[str, Any]) -> dict[str, Any]:
    """Registra que el cliente ha enviado comprobante de pago."""
    missing = validate_required(payload, ["invoice_id", "proof_reference"])
    if missing:
        return {"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}

    invoice_id = int(payload["invoice_id"])
    proof_reference = str(payload["proof_reference"]).strip()

    with db_connect() as conn:
        invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not invoice:
            return {"ok": False, "error": "Factura no encontrada"}

        conn.execute(
            """
            UPDATE invoices SET payment_proof = ?, status = 'pending_verification'
            WHERE id = ?
            """,
            (proof_reference, invoice_id)
        )

        create_invoice_notification(
            invoice_id,
            "payment_received",
            f"Comprobante de pago recibido para factura {invoice['invoice_number']}: {proof_reference}"
        )

    return {
        "ok": True,
        "message": "Comprobante registrado. Un administrador verificará el pago pronto."
    }


def get_bank_accounts() -> dict[str, Any]:
    """Obtiene todas las cuentas bancarias activas."""
    with db_connect() as conn:
        accounts = rows_to_dicts(
            conn.execute("SELECT * FROM bank_accounts WHERE active = 1 ORDER BY name").fetchall()
        )
    return {"ok": True, "bank_accounts": accounts}


def update_bank_account(payload: dict[str, Any]) -> dict[str, Any]:
    """Actualiza o desactiva una cuenta bancaria."""
    missing = validate_required(payload, ["account_id"])
    if missing:
        return {"ok": False, "error": "Falta el ID de la cuenta"}

    account_id = int(payload["account_id"])

    updates = []
    values = []

    if "active" in payload:
        updates.append("active = ?")
        values.append(1 if payload["active"] else 0)

    if "name" in payload:
        updates.append("name = ?")
        values.append(str(payload["name"]).strip())

    if "bank" in payload:
        updates.append("bank = ?")
        values.append(str(payload["bank"]).strip())

    if not updates:
        return {"ok": False, "error": "No hay campos para actualizar"}

    values.append(account_id)

    with db_connect() as conn:
        account = conn.execute("SELECT * FROM bank_accounts WHERE id = ?", (account_id,)).fetchone()
        if not account:
            return {"ok": False, "error": "Cuenta no encontrada"}

        conn.execute(f"UPDATE bank_accounts SET {', '.join(updates)} WHERE id = ?", values)

    return {"ok": True, "message": "Cuenta bancaria actualizada correctamente"}


def get_invoice_notifications() -> dict[str, Any]:
    """Obtiene notificaciones pendientes de facturación."""
    with db_connect() as conn:
        notifications = rows_to_dicts(
            conn.execute(
                """
                SELECT n.*, i.invoice_number, i.customer_name
                FROM invoice_notifications n
                LEFT JOIN invoices i ON n.invoice_id = i.id
                WHERE n.status = 'pending'
                ORDER BY n.created_at DESC
                """
            ).fetchall()
        )

    return {"ok": True, "notifications": notifications}


def mark_notification_sent(notification_id: int) -> dict[str, Any]:
    """Marca una notificación como enviada."""
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE invoice_notifications SET status = 'sent', sent_at = ?
            WHERE id = ?
            """,
            (now_iso(), notification_id)
        )

    return {"ok": True, "message": "Notificación marcada como enviada"}


def get_invoice_assistant_context() -> str:
    """Obtiene contexto de facturación para el asistente."""
    with db_connect() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) as c FROM invoices WHERE status = 'pending'"
        ).fetchone()["c"]

        recent = rows_to_dicts(
            conn.execute(
                "SELECT invoice_number, customer_name, total, status FROM invoices ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
        )

    context = f"""
    SISTEMA DE FACTURACIÓN:
    - Facturas pendientes: {pending}
    - Últimas facturas: {json.dumps(recent, ensure_ascii=False, indent=2)}

    Para crear una factura, el cliente debe proporcionar:
    - Nombre y email del cliente
    - Productos a comprar (IDs o códigos del inventario)
    - Método de pago (transferencia, tarjeta, etc.)
    - Datos bancarios para la transferencia

    Proceso:
    1. Crear factura con los productos seleccionados
    2. Enviar email al cliente con los datos de pago
    3. Cliente realiza transferencia y envía comprobante
    4. Administrador verifica pago y actualiza estado de la factura
    """

    return context


def invoice_assistant_reply(payload: dict[str, Any]) -> dict[str, Any]:
    """Asistente especializado en facturación."""
    question = str(payload.get("question", "")).strip()
    channel = str(payload.get("channel", "web")).strip() or "web"

    if not question:
        return {"ok": False, "error": "Escribe una pregunta sobre facturación."}

    q_lower = question.lower()
    if any(word in q_lower for word in ["comprar", "quiero", "necesito", "cotizar", "factura", "boleta"]):
        return process_purchase_request(question, channel)

    answer, source = call_external_model_with_invoice_context(question, channel)
    return {"ok": True, "answer": answer, "source": source}


def call_external_model_with_invoice_context(question: str, channel: str) -> tuple[str, str]:
    """Llama al modelo con contexto de facturación."""
    context = get_invoice_assistant_context()
    litellm_base = os.environ.get("LITELLM_BASE_URL", "").rstrip("/")
    litellm_key = os.environ.get("LITELLM_API_KEY", "sk-local")
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    system_prompt = f"""Eres un asistente de facturación para Sabrina AI Lab.
Responde preguntas sobre facturación, pagos y estado de órdenes.

CONTEXTO ACTUAL:
{context}

Instrucciones:
1. Sé conciso y profesional
2. Si te preguntan por el estado de una factura, pide el número de factura
3. Si quieren comprar, guía el proceso paso a paso
4. Recuerda que deben enviar comprobante de pago
5. Mantén un tono amable pero formal"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Canal: {channel}\nConsulta: {question}"},
    ]

    if litellm_base:
        url = f"{litellm_base}/chat/completions"
        payload = {"model": os.environ.get("LITELLM_MODEL", "gpt-4o-mini"), "messages": messages}
        headers = {"Authorization": f"Bearer {litellm_key}", "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "litellm"

    if azure_key and azure_endpoint and azure_deployment:
        url = (
            f"{azure_endpoint}/openai/deployments/{azure_deployment}/chat/completions"
            f"?api-version={azure_version}"
        )
        payload = {"messages": messages, "temperature": 0.4, "max_tokens": 650}
        headers = {"api-key": azure_key, "Content-Type": "application/json"}
        return post_chat_completion(url, headers, payload), "azure_openai"

    return local_invoice_answer(question), "local"


def local_invoice_answer(question: str) -> str:
    """Respuesta local para facturación."""
    q_lower = question.lower()

    if "estado" in q_lower or "factura" in q_lower:
        return """
        Para consultar el estado de una factura, necesito el número de factura.
        Puedes encontrarlo en el correo que enviamos o en tu perfil de cliente.
        Formato: INV-2024MM-XXXX

        Una vez que tengas el número, puedo verificarlo en el sistema.
        """

    elif "pago" in q_lower or "transferencia" in q_lower:
        return """
        Los datos bancarios para realizar tu pago son:
        - Banco: Banco Nacional
        - Cuenta Corriente: 1234567890
        - RUT: 12.345.678-9
        - Email: pagos@tunegocio.cl

        Importante: 
        1. Realiza la transferencia por el monto exacto indicado en tu factura
        2. Incluye tu número de factura en la descripción
        3. Envía el comprobante de pago a pagos@tunegocio.cl
        """

    else:
        return """
        Soy el asistente de facturación de Sabrina AI Lab.

        ¿En qué puedo ayudarte?
        - Consultar el estado de una factura
        - Solicitar datos de pago
        - Reportar un comprobante de pago
        - Hacer una cotización de productos

        Para una cotización, indícame qué productos te interesan y te prepararé una cotización formal.
        """


def process_purchase_request(question: str, channel: str) -> dict[str, Any]:
    """Procesa una solicitud de compra del cliente."""
    products = get_inventory_products()

    if not products:
        return {
            "ok": True,
            "answer": "Lo siento, actualmente no tenemos productos disponibles en el inventario. Por favor, contacta a nuestro equipo de ventas directamente.",
            "source": "local",
            "needs_verification": False
        }

    requested_products = []
    q_lower = question.lower()

    for p in products:
        if p["name"].lower() in q_lower or p["code"].lower() in q_lower:
            requested_products.append(p)

    if not requested_products:
        product_list = "\n".join([f"- {p['name']} (Código: {p['code']}, Stock: {p['quantity']})" for p in products[:10]])
        if len(products) > 10:
            product_list += f"\n- ... y {len(products) - 10} productos más"

        return {
            "ok": True,
            "answer": f"""
            No encontré productos específicos en tu mensaje. Estos son los productos disponibles:

            {product_list}

            ¿Cuál te gustaría comprar? Indícame el nombre o código del producto y la cantidad.
            """.strip(),
            "source": "local",
            "needs_verification": False
        }

    subtotal = sum(p["price"] * 1 for p in requested_products if p.get("price"))
    tax = subtotal * 0.19
    total = subtotal + tax

    product_details = "\n".join([f"- {p['name']} (Código: {p['code']}) - ${p['price']:.2f} c/u" for p in requested_products])

    return {
        "ok": True,
        "answer": f"""
        ¡Excelente! He identificado estos productos en tu consulta:

        {product_details}

        Resumen de la cotización:
        Subtotal: ${subtotal:.2f}
        IVA (19%): ${tax:.2f}
        Total: ${total:.2f}

        Para proceder con la compra, por favor:
        1. Confirma que estos productos son los que deseas
        2. Indica las cantidades para cada producto
        3. Proporciona tu nombre completo y email

        Una vez que confirmes, generaré tu factura formal con los datos bancarios para realizar el pago.
        """.strip(),
        "source": "local",
        "needs_verification": True,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "products": requested_products
    }


# ============================================
# RENDER HTML - Función principal (versión simplificada para no exceder límite)
# ============================================

def render_index() -> str:
    """Renderiza la página HTML principal."""
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sabrina AI Lab · MVP IA Humana</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #090b12;
      --panel: rgba(255,255,255,.075);
      --panel-strong: rgba(255,255,255,.12);
      --line: rgba(255,255,255,.16);
      --text: #f6f7fb;
      --muted: #aab2c5;
      --brand: #9b8cff;
      --brand2: #33d6a6;
      --warn: #ffcc66;
      --danger: #ff6b7a;
      --shadow: 0 24px 80px rgba(0,0,0,.35);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at 18% 12%, rgba(155,140,255,.28), transparent 32rem),
                  radial-gradient(circle at 82% 0%, rgba(51,214,166,.16), transparent 30rem),
                  linear-gradient(135deg, #080a12, #111827 48%, #07111d);
      color: var(--text);
      min-height: 100vh;
      padding: 20px;
    }
    .wrap { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
    header {
      position: sticky; top: 0; z-index: 10;
      backdrop-filter: blur(18px);
      background: rgba(9,11,18,.72);
      border-bottom: 1px solid var(--line);
      padding: 10px 0;
    }
    nav { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; gap: 14px; flex-wrap: wrap; }
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 800; letter-spacing: -.03em; }
    .logo { width: 38px; height: 38px; border-radius: 14px; background: linear-gradient(135deg, var(--brand), var(--brand2)); display:grid; place-items:center; box-shadow: var(--shadow); }
    .navlinks { display: flex; gap: 6px; flex-wrap: wrap; }
    .navlinks a { text-decoration: none; color: var(--muted); font-size: 12px; padding: 6px 10px; border-radius: 999px; cursor: pointer; white-space: nowrap; }
    .navlinks a:hover, .navlinks a.active { background: var(--panel); color: var(--text); }
    .hero { padding: 72px 0 36px; display: grid; grid-template-columns: 1.15fr .85fr; gap: 28px; align-items: center; }
    .eyebrow { display:inline-flex; gap: 8px; align-items:center; color: var(--brand2); background: rgba(51,214,166,.09); border:1px solid rgba(51,214,166,.25); padding: 8px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }
    h1 { font-size: clamp(42px, 7vw, 76px); line-height: .92; margin: 20px 0; letter-spacing: -.07em; }
    h2 { font-size: clamp(26px, 4vw, 42px); margin: 0 0 14px; letter-spacing: -.04em; }
    h3 { margin: 0 0 8px; letter-spacing: -.02em; }
    h4 { margin: 8px 0 4px; color: var(--text); }
    p { color: var(--muted); line-height: 1.65; }
    .hero p { font-size: 18px; max-width: 720px; }
    .actions { display: flex; gap: 12px; margin-top: 26px; flex-wrap: wrap; }
    button, .btn {
      border: 0; color: #07111d; background: linear-gradient(135deg, var(--brand2), #b4ffe8);
      padding: 10px 16px; border-radius: 14px; font-weight: 800; cursor: pointer;
      text-decoration: none; display: inline-flex; align-items:center; gap: 8px;
      font-size: 13px;
    }
    button.secondary, .btn.secondary { background: var(--panel-strong); color: var(--text); border: 1px solid var(--line); }
    button.small { padding: 6px 12px; font-size: 11px; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: 24px; padding: 22px; box-shadow: var(--shadow); }
    .grid { display: grid; gap: 18px; }
    .grid.two { grid-template-columns: repeat(2, 1fr); }
    .grid.three { grid-template-columns: repeat(3, 1fr); }
    .metric { font-size: 32px; font-weight: 900; letter-spacing: -.04em; }
    .muted { color: var(--muted); }
    .tag { display:inline-flex; padding: 6px 9px; border-radius: 999px; background: rgba(155,140,255,.13); border: 1px solid rgba(155,140,255,.28); color: #d8d2ff; font-size: 12px; font-weight: 600; }
    section { padding: 38px 0; display: none; }
    section.active { display: block; }
    input, textarea, select {
      width: 100%; background: rgba(0,0,0,.24); color: var(--text);
      border: 1px solid var(--line); border-radius: 14px; padding: 12px 13px;
      outline: none; font: inherit;
    }
    textarea { min-height: 80px; resize: vertical; }
    label { display:block; font-size: 13px; font-weight: 800; color: #dbe2f2; margin: 0 0 7px; }
    .formgrid { display:grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
    .full { grid-column: 1 / -1; }
    table { width:100%; border-collapse: collapse; overflow: hidden; border-radius: 16px; }
    th, td { text-align:left; padding: 10px; border-bottom: 1px solid var(--line); color: var(--muted); vertical-align: top; font-size: 13px; }
    th { color: var(--text); background: rgba(255,255,255,.06); }
    .status-ok { color: var(--brand2); font-weight: 900; }
    .conversation { background: rgba(0,0,0,.2); border-radius: 12px; padding: 14px; margin: 12px 0; border-left: 3px solid var(--brand2); }
    .conversation.user { border-left-color: var(--brand); }
    .conversation strong { color: var(--brand2); }
    .conversation.user strong { color: var(--brand); }
    .conversation p { margin-top: 4px; white-space: pre-wrap; }
    .qcard { margin-bottom: 22px; }
    .qoption {
      display:flex; align-items:center; gap: 10px; padding: 12px 14px;
      border: 1px solid var(--line); border-radius: 14px; margin-bottom: 8px;
      cursor: pointer; transition: background .15s ease;
    }
    .qoption:hover { background: var(--panel-strong); }
    .qoption input { width: auto; accent-color: var(--brand2); }
    .qoption span { color: var(--text); font-size: 14px; }
    #diagnosticResult { display:none; }
    .status-badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
    }
    .status-pending { background: rgba(255,204,102,.15); color: var(--warn); }
    .status-paid { background: rgba(51,214,166,.15); color: var(--brand2); }
    .status-cancelled { background: rgba(255,107,122,.15); color: var(--danger); }
    .status-verified { background: rgba(155,140,255,.15); color: var(--brand); }
    .status-confirmada { background: rgba(51,214,166,.15); color: var(--brand2); }
    .status-cancelada { background: rgba(255,107,122,.15); color: var(--danger); }
    .cat-urgente { background: rgba(255,107,122,.15); color: var(--danger); }
    .cat-ventas { background: rgba(51,214,166,.15); color: var(--brand2); }
    .cat-administrativo { background: rgba(155,140,255,.15); color: var(--brand); }
    .cat-spam { background: rgba(255,255,255,.1); color: var(--muted); }
    .cat-general { background: rgba(255,204,102,.15); color: var(--warn); }
    .priority-alta { background: rgba(255,107,122,.15); color: var(--danger); }
    .priority-media { background: rgba(255,204,102,.15); color: var(--warn); }
    .priority-baja { background: rgba(255,255,255,.1); color: var(--muted); }
    .progress-bar {
      background: rgba(0,0,0,.2);
      border-radius: 12px;
      padding: 4px;
      margin: 10px 0;
    }
    .progress-fill {
      height: 8px;
      background: linear-gradient(90deg, var(--brand), var(--brand2));
      border-radius: 12px;
      transition: width 0.5s ease;
    }
    .stat-card {
      background: rgba(0,0,0,.2);
      padding: 12px;
      border-radius: 12px;
      text-align: center;
    }
    .stat-card .number {
      font-size: 24px;
      font-weight: 800;
    }
    .stat-card .label {
      font-size: 11px;
      color: var(--muted);
    }
    .stat-card .number.green { color: var(--brand2); }
    .stat-card .number.purple { color: var(--brand); }
    .stat-card .number.gold { color: var(--warn); }
    footer { border-top: 1px solid var(--line); margin-top: 36px; padding: 24px 0 36px; color: var(--muted); }
    .toast { position: fixed; right: 18px; bottom: 18px; background: #102018; color: #d9ffe8; border: 1px solid rgba(51,214,166,.38); padding: 12px 14px; border-radius: 14px; opacity:0; transform: translateY(100px); transition: all .3s ease; z-index: 999; }
    .toast.show { opacity:1; transform: translateY(0); }
    .inventory-preview {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }
    .inventory-preview .item {
      display: flex;
      justify-content: space-between;
      padding: 6px 8px;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 13px;
    }
    .inventory-preview .item .stock { color: var(--brand2); }
    @media (max-width: 850px) {
      .hero, .grid.two, .grid.three { grid-template-columns: 1fr; }
      .navlinks { display: none; }
      .inventory-preview { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <nav>
        <div class="brand"><div class="logo">✦</div><span>Sabrina AI Lab</span></div>
        <div class="navlinks">
          <a onclick="showSection('dashboard')" class="active">Dashboard</a>
          <a onclick="showSection('diagnostic')">🧭 Diagnóstico</a>
          <a onclick="showSection('leads')">📋 Leads</a>
          <a onclick="showSection('estimator')">🧮 Calculadora</a>
          <a onclick="showSection('assistant')">🤖 Asistente</a>
          <a onclick="showSection('smartstacks')" style="color: var(--brand2); font-weight: 700;">🏪 Caso 1: SmartStacks</a>
          <a onclick="showSection('middleware')">📡 Automatización</a>
          <a onclick="showSection('consulting')">🗝️ Llave en Mano</a>
          <a onclick="showSection('invoicing')">🧾 Facturación</a>
          <a onclick="showSection('middleware-demo')">🤖 Caso 2</a>
          <a onclick="showSection('demo')">🚀 Proyectos</a>
          <a onclick="showSection('faqs')">❓ FAQs</a>
        </div>
      </nav>
    </header>

    <main>
      <!-- DASHBOARD -->
      <section id="dashboard" class="active">
        <div class="hero">
          <div>
            <span class="eyebrow">✨ SISTEMA INTEGRAL</span>
            <h1>Sabrina AI Lab</h1>
            <p>
              Gestión integral de leads, inventario, facturación y asistentes de IA para comercios.
              Incluye automación de email, inventario en tiempo real y consultor estratégico.
            </p>
            <div class="actions">
              <button onclick="showSection('diagnostic')">🧭 Diagnóstico</button>
              <button onclick="showSection('smartstacks')" style="background: linear-gradient(135deg, var(--brand), var(--brand2));">🏪 SmartStacks</button>
              <button onclick="showSection('leads')" class="secondary">📋 Leads</button>
            </div>
          </div>
          <div class="card">
            <h3>Estado del Sistema</h3>
            <div style="margin: 12px 0; font-size: 12px; color: var(--muted);">
              <p>✓ Base de datos: Activa</p>
              <p id="modeStatus">Cargando...</p>
              <p>Facturas: <span id="invoiceCount">0</span></p>
            </div>
          </div>
        </div>
      </section>

      <!-- DIAGNÓSTICO -->
      <section id="diagnostic">
        <h2>🧭 ¿Qué necesita tu negocio?</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Responde 5 preguntas rápidas y te decimos cuál de nuestras soluciones encaja mejor con tu caso.
        </p>
        <div class="card">
          <form id="diagnosticForm">
            <div class="qcard">
              <label>1. ¿Cuál es el mayor problema que quieres resolver?</label>
              <label class="qoption"><input type="radio" name="q1" value="smartstacks" required><span>Mi equipo pierde tiempo buscando productos, precios o stock</span></label>
              <label class="qoption"><input type="radio" name="q1" value="middleware"><span>Recibo las mismas preguntas todo el día por WhatsApp, redes o email</span></label>
              <label class="qoption"><input type="radio" name="q1" value="llave-en-mano"><span>Quiero digitalizar procesos completos y no sé por dónde empezar</span></label>
            </div>
            <div class="qcard">
              <label>2. ¿Cuántas interacciones o consultas maneja tu negocio al mes?</label>
              <label class="qoption"><input type="radio" name="q2" value="smartstacks" required><span>Menos de 500 — negocio pequeño, pocos vendedores</span></label>
              <label class="qoption"><input type="radio" name="q2" value="middleware"><span>Entre 500 y 5,000 — varios canales, volumen alto</span></label>
              <label class="qoption"><input type="radio" name="q2" value="llave-en-mano"><span>Miles, y sigue creciendo — necesito algo robusto</span></label>
            </div>
            <div class="qcard">
              <label>3. ¿Qué tan importante es tener control total y datos propios?</label>
              <label class="qoption"><input type="radio" name="q3" value="smartstacks" required><span>No es prioridad, solo quiero resolver el problema rápido</span></label>
              <label class="qoption"><input type="radio" name="q3" value="middleware"><span>Me importa el tono y la consistencia de las respuestas</span></label>
              <label class="qoption"><input type="radio" name="q3" value="llave-en-mano"><span>Muy importante, quiero un sistema transferible con mis datos</span></label>
            </div>
            <div class="qcard">
              <label>4. ¿Cuál es tu presupuesto mensual aproximado para esta solución?</label>
              <label class="qoption"><input type="radio" name="q4" value="smartstacks" required><span>Menos de USD 350</span></label>
              <label class="qoption"><input type="radio" name="q4" value="middleware"><span>Entre USD 350 y 500</span></label>
              <label class="qoption"><input type="radio" name="q4" value="llave-en-mano"><span>Más de USD 500, busco una implementación completa</span></label>
            </div>
            <div class="qcard">
              <label>5. ¿Ya tienes canales digitales activos con muchas consultas repetidas?</label>
              <label class="qoption"><input type="radio" name="q5" value="smartstacks" required><span>Tengo mostrador físico principalmente</span></label>
              <label class="qoption"><input type="radio" name="q5" value="middleware"><span>Sí, varios canales digitales simultáneos</span></label>
              <label class="qoption"><input type="radio" name="q5" value="llave-en-mano"><span>Quiero implementar todo desde cero, de forma integral</span></label>
            </div>
            <button type="submit">Ver resultado</button>
          </form>
          <div id="diagnosticResult"></div>
        </div>
      </section>

      <!-- LEADS -->
      <section id="leads">
        <h2>📋 Leads y Campañas</h2>
        <div class="grid two">
          <div class="card">
            <h3>Últimas oportunidades</h3>
            <div style="overflow:auto; max-height: 400px;">
              <table><thead><tr><th>Fecha</th><th>Negocio</th><th>Email</th><th>Caso</th></tr></thead><tbody id="leadRows"></tbody></table>
            </div>
            <div style="margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap;">
              <button onclick="exportLeadsCSV()" class="secondary small">📥 CSV</button>
              <button onclick="exportLeadsJSON()" class="secondary small">📥 JSON</button>
            </div>
          </div>
          <div class="card">
            <h3>Registrar nuevo lead</h3>
            <form id="leadForm" class="formgrid">
              <div class="full"><label>Nombre</label><input name="name" required></div>
              <div class="full"><label>Negocio</label><input name="business" required></div>
              <div class="full"><label>Email</label><input name="email" type="email" required></div>
              <div class="full"><label>Caso</label><select name="use_case"><option>smartstacks</option><option>middleware</option><option>llave-en-mano</option></select></div>
              <div class="full"><label>Presupuesto</label><input name="budget" required></div>
              <div class="full"><label>Dolor</label><textarea name="pain" required></textarea></div>
              <div class="full"><button type="submit">Guardar lead</button></div>
            </form>
          </div>
        </div>
      </section>

      <!-- ESTIMADOR -->
      <section id="estimator">
        <h2>🧮 Calculadora de Valor Comercial</h2>
        <div class="grid two">
          <div class="card">
            <h3>Calcular propuesta</h3>
            <form id="estimateForm" class="formgrid">
              <div class="full">
                <label>Caso de uso</label>
                <select name="use_case">
                  <option value="smartstacks">SmartStacks (Inventario + ventas)</option>
                  <option value="middleware">Automatización Empática Multicanal</option>
                  <option value="llave-en-mano">Digitalización IA Llave en Mano</option>
                </select>
              </div>
              <div><label>Interacciones / mes</label><input name="interactions" type="number" min="1" value="1500" required></div>
              <div><label>Minutos ahorrados / interacción</label><input name="minutes_saved" type="number" min="1" value="4" required></div>
              <div class="full"><label>Costo horario del equipo (USD)</label><input name="hourly_cost" type="number" min="0" step="0.1" value="9.5" required></div>
              <div class="full"><button type="submit">Calcular</button></div>
            </form>
          </div>
          <div class="card">
            <h3>Resultado</h3>
            <div id="estimateResult"><p class="muted">Completa el formulario para ver la estimación.</p></div>
            <div style="margin-top: 22px;">
              <h3>Historial reciente</h3>
              <div style="overflow:auto; max-height: 260px;">
                <table><thead><tr><th>Caso</th><th>Interacciones</th><th>Valor mensual</th><th>Precio sugerido</th></tr></thead><tbody id="estimateRows"></tbody></table>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ASISTENTE ESTRATÉGICO -->
      <section id="assistant">
        <h2>🧭 Asistente Estratégico</h2>
        <div class="grid two">
          <div class="card">
            <h3>Consultar al asistente</h3>
            <form id="assistantForm" class="formgrid">
              <div class="full"><label>Canal</label><input name="channel" value="WhatsApp" required></div>
              <div class="full"><label>Tu pregunta o situación de negocio</label><textarea name="question" placeholder="Ej: Una ferretería recibe muchas preguntas por stock. ¿Cómo lo vuelvo un MVP vendible?" required></textarea></div>
              <div class="full"><button type="submit">Preguntar</button></div>
            </form>
          </div>
          <div class="card">
            <h3>Conversación</h3>
            <div id="assistantHistory" style="overflow:auto; max-height: 460px;"><p class="muted">Sin consultas aún.</p></div>
          </div>
        </div>
      </section>

      <!-- CASO 1: SMARTSTACKS -->
      <section id="smartstacks">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
          <h2 style="margin: 0;">🏪 Caso 1: SmartStacks</h2>
          <span class="tag" style="background: rgba(51,214,166,.15); color: var(--brand2);">Inventario + Asistente IA</span>
        </div>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Gestiona tu inventario en tiempo real y usa el asistente conversacional para responder preguntas al instante.
        </p>

        <!-- Estadísticas -->
        <div class="grid three" style="margin: 16px 0;">
          <div class="stat-card"><div class="number green" id="ssTotalProducts">0</div><div class="label">📦 Productos</div></div>
          <div class="stat-card"><div class="number purple" id="ssTotalStock">0</div><div class="label">📊 Stock Total</div></div>
          <div class="stat-card"><div class="number gold" id="ssConversations">0</div><div class="label">💬 Consultas</div></div>
        </div>

        <!-- Inventario Rápido -->
        <div class="card">
          <h3>📋 Inventario Rápido</h3>
          <div id="inventoryPreview" class="inventory-preview">
            <p style="color:var(--muted); grid-column:1/-1; text-align:center; padding:12px;">Cargando inventario...</p>
          </div>
          <div class="flex" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
            <button class="btn secondary small" onclick="showFullInventory()">📋 Ver Completo</button>
            <button class="btn secondary small" onclick="exportCSV()">📥 CSV</button>
            <button class="btn secondary small" onclick="loadDemo()">📋 Cargar Demo</button>
          </div>
        </div>

        <div class="grid two" style="margin-top:18px;">
          <div class="card">
            <h3>➕ Agregar Producto</h3>
            <form id="productForm" class="formgrid">
              <div class="full"><label>Código</label><input id="pCode" placeholder="EJ-001" required></div>
              <div class="full"><label>Nombre</label><input id="pName" required></div>
              <div><label>Cantidad</label><input id="pQty" type="number" min="0" required></div>
              <div><label>Precio</label><input id="pPrice" type="number" step="0.01" placeholder="0"></div>
              <div><label>Categoría</label><input id="pCategory" placeholder="Herramientas"></div>
              <div><label>Descripción</label><textarea id="pDesc" rows="2"></textarea></div>
              <div class="full"><button class="btn" type="submit">➕ Guardar</button></div>
            </form>
          </div>

          <div class="card">
            <h3>🤖 Asistente IA</h3>
            <p style="color:var(--muted); font-size:13px;">Pregunta sobre tu inventario</p>
            <div id="conversationHistory" style="max-height:300px; overflow:auto;"></div>
            <form id="smartstacksForm" class="mt-12">
              <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
                <button type="button" class="btn secondary small" onclick="setQuestion('¿Tienes martillos?')">🔨 Martillos</button>
                <button type="button" class="btn secondary small" onclick="setQuestion('¿Cuánto cuesta la tubería PVC?')">🔧 Tubería</button>
                <button type="button" class="btn secondary small" onclick="setQuestion('¿Hay stock del código PER-001?')">📦 PER-001</button>
                <button type="button" class="btn secondary small" onclick="setQuestion('¿Qué herramientas tienen?')">🛠️ Herramientas</button>
              </div>
              <input id="questionInput" placeholder="Ej: ¿Hay martillos disponibles?" required>
              <button class="btn mt-12" type="submit">💬 Preguntar</button>
            </form>
          </div>
        </div>

        <!-- Progreso -->
        <div class="card" style="margin-top:18px;">
          <h3>🔄 Progreso de Implementación</h3>
          <div class="progress-bar"><div class="progress-fill" id="ssProgressBar" style="width:0%;"></div></div>
          <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--muted);">
            <span>Inicio</span>
            <span id="ssStepIndicator">Paso 0/4</span>
            <span>Completo</span>
          </div>
          <div id="ssCurrentStep" style="margin-top:10px;">
            <h4 id="ssStepTitle">Cargar Inventario Local</h4>
            <p id="ssStepDesc" style="font-size:14px;">Subimos los datos de tu negocio: productos, códigos, precios y descripciones.</p>
            <div id="ssStepDetails"></div>
          </div>
          <div style="display:flex; gap:10px; margin-top:14px; flex-wrap:wrap;">
            <button onclick="runSmartstacksStep()" class="btn" id="ssStepBtn">▶️ Ejecutar Paso</button>
            <button onclick="resetSmartstacksDemo()" class="btn secondary">🔄 Reiniciar</button>
          </div>
        </div>
      </section>

      <!-- MIDDLEWARE -->
      <section id="middleware">
        <h2>📡 Automatización Empática Multicanal</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Proxy unificado (LiteLLM) que responde con tono empático adaptado a cada canal, controlando el costo estimado por tokens.
        </p>
        <div class="grid two">
          <div class="card">
            <h3>Responder un mensaje entrante</h3>
            <form id="middlewareForm" class="formgrid">
              <div class="full">
                <label>Canal</label>
                <select name="channel">
                  <option value="WhatsApp">WhatsApp</option>
                  <option value="Instagram">Instagram</option>
                  <option value="Email">Email</option>
                  <option value="Web">Web</option>
                </select>
              </div>
              <div class="full"><label>Mensaje del cliente</label><textarea name="message" placeholder="Ej: Hola, ¿tienen envío a regiones? Necesito saber el costo." required></textarea></div>
              <div class="full"><button type="submit">Responder</button></div>
            </form>
          </div>
          <div class="card">
            <h3>💰 Costos estimados</h3>
            <div style="margin-bottom: 12px;">
              <p><strong>Interacciones totales:</strong> <span id="middlewareTotalMessages">0</span></p>
              <p><strong>Costo estimado acumulado:</strong> $<span id="middlewareTotalCost">0</span></p>
            </div>
            <div style="overflow:auto; max-height: 220px;">
              <table><thead><tr><th>Canal</th><th>Mensajes</th><th>Costo</th></tr></thead><tbody id="middlewareByChannel"></tbody></table>
            </div>
          </div>
        </div>
        <div class="grid" style="margin-top: 28px;">
          <div class="card">
            <h3>Historial de conversaciones</h3>
            <div id="middlewareHistory" style="overflow:auto; max-height: 420px;"><p class="muted">Sin mensajes aún.</p></div>
          </div>
        </div>
      </section>

      <!-- CONSULTING -->
      <section id="consulting">
        <h2>🗝️ Digitalización IA Llave en Mano</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Módulos a medida: filtrado automático de correos y gestión de agendas, funcionando con datos reales.
        </p>
        <div class="grid two">
          <div class="card">
            <h3>📬 Filtrado automático de correos</h3>
            <form id="emailClassifyForm" class="formgrid">
              <div class="full"><label>Remitente (opcional)</label><input name="sender" placeholder="cliente@ejemplo.com"></div>
              <div class="full"><label>Asunto</label><input name="subject" required></div>
              <div class="full"><label>Cuerpo del correo</label><textarea name="body" required></textarea></div>
              <div class="full"><button type="submit">Clasificar correo</button></div>
            </form>
            <div id="emailClassifyResult" style="margin-top: 14px;"></div>
          </div>
          <div class="card">
            <h3>📅 Gestión de agendas</h3>
            <form id="appointmentForm" class="formgrid">
              <div class="full"><label>Nombre del cliente</label><input name="client_name" required></div>
              <div class="full"><label>Contacto (email o teléfono)</label><input name="contact" required></div>
              <div><label>Fecha</label><input name="appointment_date" type="date" required></div>
              <div><label>Hora</label><input name="appointment_time" type="time" required></div>
              <div class="full"><label>Notas</label><textarea name="notes" placeholder="Ej: Demo inicial del asistente"></textarea></div>
              <div class="full"><button type="submit">Agendar cita</button></div>
            </form>
          </div>
        </div>
        <div class="grid two" style="margin-top: 28px;">
          <div class="card">
            <h3>Últimos correos clasificados</h3>
            <div style="overflow:auto; max-height: 360px;">
              <table><thead><tr><th>Asunto</th><th>Categoría</th><th>Prioridad</th></tr></thead><tbody id="emailClassifyRows"></tbody></table>
            </div>
          </div>
          <div class="card">
            <h3>Próximas citas (<span id="upcomingCount">0</span>)</h3>
            <div style="overflow:auto; max-height: 360px;">
              <table><thead><tr><th>Fecha</th><th>Cliente</th><th>Estado</th><th></th></tr></thead><tbody id="appointmentRows"></tbody></table>
            </div>
          </div>
        </div>
      </section>

      <!-- FACTURACIÓN -->
      <section id="invoicing">
        <h2>🧾 Facturación y Pagos</h2>
        <div class="grid two">
          <div class="card">
            <h3>📋 Crear Factura</h3>
            <form id="invoiceForm" class="formgrid">
              <div class="full"><label>Nombre del Cliente</label><input id="invoiceCustomerName" name="customer_name" required></div>
              <div class="full"><label>Email del Cliente</label><input id="invoiceCustomerEmail" name="customer_email" type="email" required></div>
              <div><label>Teléfono</label><input id="invoiceCustomerPhone" name="customer_phone"></div>
              <div><label>RUT</label><input id="invoiceCustomerRut" name="customer_rut"></div>
              <div class="full"><label>Seleccionar Productos</label>
                <div id="invoiceProductSelection" style="max-height: 200px; overflow-y: auto; background: rgba(0,0,0,.2); border-radius: 12px; padding: 12px;"></div>
              </div>
              <div class="full"><label>Método de Pago</label>
                <select id="invoicePaymentMethod" name="payment_method">
                  <option value="transferencia">Transferencia Bancaria</option>
                  <option value="tarjeta">Tarjeta de Crédito/Débito</option>
                </select>
              </div>
              <div class="full"><label>Cuenta Bancaria</label>
                <select id="invoiceBankAccount" name="bank_account_id"></select>
              </div>
              <div class="full"><button type="submit">Crear Factura</button></div>
            </form>
          </div>
          <div class="card">
            <h3>📄 Facturas Recientes</h3>
            <div style="overflow:auto; max-height: 500px;">
              <table>
                <thead>
                  <tr><th>N°</th><th>Cliente</th><th>Total</th><th>Estado</th><th>Acción</th></tr>
                </thead>
                <tbody id="invoiceRows"></tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="grid" style="margin-top: 24px;">
          <div class="card">
            <h3>🏦 Configuración de Cuentas Bancarias</h3>
            <div id="bankAccountsList"></div>
            <div style="margin-top: 14px; display: flex; gap: 8px;">
              <button onclick="refreshBankAccounts()" class="secondary">🔄 Actualizar</button>
            </div>
          </div>
        </div>
      </section>

      <!-- CASO 2: MIDDLEWARE DEMO -->
      <section id="middleware-demo">
        <h2>🤖 Simulación: Automatización de Respuestas con Empatía</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Experimenta cómo funciona el proxy unificado LiteLLM que centraliza respuestas para múltiples canales con tono empático.
        </p>
        <div class="grid two" style="margin-bottom: 20px;">
          <div class="card">
            <h3>📊 Dashboard en Vivo</h3>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
              <div class="stat-card"><div class="number" id="mdTotalMessages">0</div><div class="label">Mensajes</div></div>
              <div class="stat-card"><div class="number" id="mdAvgTime">0s</div><div class="label">Tiempo Prom.</div></div>
              <div class="stat-card"><div class="number green" id="mdTotalCost">$0</div><div class="label">Costo</div></div>
              <div class="stat-card"><div class="number purple" id="mdHoursSaved">0h</div><div class="label">Horas Ahorradas</div></div>
            </div>
          </div>
          <div class="card">
            <h3>📈 Estadísticas por Canal</h3>
            <div id="mdChannelStats" style="overflow:auto; max-height: 200px;"><p class="muted">Completa la simulación para ver estadísticas.</p></div>
          </div>
        </div>
        <div class="card">
          <h3>🎯 Simulador de Mensajes</h3>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 14px 0;">
            <div><label>Canal</label><select id="mdChannel"><option value="whatsapp">💬 WhatsApp</option><option value="instagram">📸 Instagram</option><option value="email">📧 Email</option><option value="web">🌐 Web</option></select></div>
            <div><label>Tono Personalizado</label><input id="mdTone" placeholder="Ej: Formal, amigable..." /></div>
          </div>
          <div style="margin: 10px 0;"><label>Mensaje</label><textarea id="mdMessage" rows="3">Hola, ¿tienen stock de martillos?</textarea></div>
          <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button onclick="simulateMiddlewareMessage()" class="btn">🚀 Enviar</button>
            <button onclick="loadMiddlewareExample()" class="btn secondary">📋 Ejemplo</button>
          </div>
          <div id="mdSimulationResult" style="margin-top: 16px; display: none;">
            <div style="background: rgba(0,0,0,.2); border-radius: 12px; padding: 14px;">
              <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--muted);">
                <span>Canal: <strong id="mdResultChannel">WhatsApp</strong></span>
                <span>⏱ <span id="mdResultTime">0</span>s · 💰 $<span id="mdResultCost">0</span></span>
              </div>
              <div class="conversation user"><strong>Cliente:</strong><p id="mdResultMessage"></p></div>
              <div class="conversation"><strong>🤖 Asistente:</strong><p id="mdResultResponse"></p></div>
              <div style="font-size: 11px; color: var(--muted);">Fuente: <span id="mdResultSource">simulada</span> · Tokens: <span id="mdResultTokens">0</span></div>
            </div>
          </div>
        </div>
      </section>

      <!-- DEMO PROYECTOS -->
      <section id="demo">
        <h2>🚀 Simulación de Proyecto Llave en Mano</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Elige un proyecto y te mostraremos paso a paso cómo se construye y funciona.
        </p>
        <div class="grid two">
          <div class="card">
            <h3>Selecciona tu Proyecto</h3>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button onclick="selectDemo('correo')" class="btn secondary small">📬 Correo</button>
              <button onclick="selectDemo('agenda')" class="btn secondary small">📅 Agenda</button>
              <button onclick="selectDemo('whatsapp')" class="btn secondary small">💬 WhatsApp</button>
              <button onclick="selectDemo('facturacion')" class="btn secondary small">🧾 Facturación</button>
            </div>
            <div id="demoDescription" style="margin-top: 12px; color: var(--muted);"><p>Selecciona un proyecto para comenzar.</p></div>
          </div>
          <div class="card">
            <h3>Progreso</h3>
            <div id="demoProgress"><p class="muted">Esperando selección...</p></div>
          </div>
        </div>
        <div class="card" id="demoSimulation" style="display: none; margin-top: 18px;">
          <div id="demoStepContent">
            <h3 id="demoStepTitle">Paso 1</h3>
            <p id="demoStepDesc">Descripción del paso</p>
            <div id="demoDataArea" style="background: rgba(0,0,0,.2); border-radius: 12px; padding: 14px; margin: 12px 0;"></div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <button id="demoStepActionBtn" class="btn" onclick="runDemoStep()">Continuar</button>
              <button class="btn secondary" onclick="resetDemo()">Reiniciar</button>
              <button class="btn secondary" onclick="toggleDemoEdit()">✏️ Usar mis datos</button>
            </div>
            <div id="demoUserInput" style="display: none; margin-top: 14px; border-top: 1px solid var(--line); padding-top: 14px;">
              <textarea id="demoUserDataInput" rows="4" style="width: 100%;" placeholder="Escribe tus datos aquí..."></textarea>
              <button onclick="applyUserData()" class="btn" style="margin-top: 8px;">Aplicar</button>
            </div>
          </div>
        </div>
      </section>

      <!-- FAQS -->
      <section id="faqs">
        <h2>📋 Preguntas Frecuentes</h2>
        <div class="card" style="padding: 10px;">
          <details><summary>🙋 ¿Qué es Sin Pausas?</summary><div class="faq-body"><p>Sin Pausas es una agencia especializada en bajar la Inteligencia Artificial a la realidad cotidiana de las empresas.</p></div></details>
          <details><summary>🎯 ¿A qué nos dedicamos?</summary><div class="faq-body"><p>Diseñamos, implementamos y desplegamos soluciones con IA para digitalización y automatización de procesos empresariales.</p></div></details>
          <details><summary>⏳ ¿Por qué 6 semanas?</summary><div class="faq-body"><p>Nuestro modelo de trabajo tiene un límite de 6 semanas para aprendizaje intensivo y desarrollo de MVP.</p></div></details>
          <details><summary>💰 ¿Cuánto cuesta?</summary><div class="faq-body"><p>Desde $99/mes para SaaS Asistente Experto, $199/mes para Middleware LiteLLM, y desde $1,500 para Consultoría Llave en Mano.</p></div></details>
        </div>
      </section>

    </main>

    <footer>
      <strong>Sabrina AI Lab</strong> · Ejecuta: <code>python3 app.py</code>
    </footer>
  </div>

  <div class="toast" id="toast"></div>

<script>
// ============================================
// ESTADO GLOBAL
// ============================================

let state = {};
let smartstacksState = {};
let middlewareState = {};
let consultingState = {};
let smartstacksDemoState = { currentStep: 0, isComplete: false };
let middlewareDemoState = { currentStep: 0, isComplete: false };
let currentDemoId = null;
let currentStep = 0;
let demoData = [];
let isUsingUserData = false;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const api = async (url, data) => {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  return await res.json();
};

const toast = (msg) => {
  const el = $('#toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
};

function showSection(id) {
  $$('section').forEach(s => s.classList.remove('active'));
  $$('.navlinks a').forEach(a => a.classList.remove('active'));
  const section = $(`#${id}`);
  if (section) section.classList.add('active');
  document.querySelectorAll('.navlinks a').forEach(a => {
    const onclick = a.getAttribute('onclick') || '';
    if (onclick.includes(id) || (id === 'smartstacks' && a.textContent.includes('SmartStacks'))) {
      a.classList.add('active');
    }
  });
  if (id === 'smartstacks') refreshSmartStacks();
  if (id === 'invoicing') { refreshInvoices(); refreshBankAccounts(); }
  if (id === 'middleware') refreshMiddleware();
  if (id === 'consulting') refreshConsulting();
  if (id === 'middleware-demo') loadMiddlewareDemo();
}

function showFullInventory() {
  document.getElementById('fullInventory').style.display = 'block';
  document.getElementById('fullInventory').scrollIntoView({ behavior: 'smooth' });
}

// ============================================
// FUNCIONES DE RENDERIZADO
// ============================================

function renderState() {
  const modeStatus = $('#modeStatus');
  if (modeStatus) modeStatus.textContent = state.integrations?.email_ready ? '✓ Email configurado' : '⚠ Email no configurado';
  const invoiceCount = $('#invoiceCount');
  if (invoiceCount) invoiceCount.textContent = state.metrics?.invoices || 0;
  
  const leadRows = $('#leadRows');
  if (leadRows) {
    leadRows.innerHTML = state.leads?.length ? state.leads.map(l => `
      <tr><td>${new Date(l.created_at).toLocaleString()}</td><td><strong>${l.business}</strong></td><td>${l.email}</td><td>${l.use_case}</td></tr>
    `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin leads</td></tr>';
  }
  
  const estimateRows = $('#estimateRows');
  if (estimateRows) {
    estimateRows.innerHTML = state.estimates?.length ? state.estimates.map(e => `
      <tr><td>${e.use_case}</td><td>${e.interactions}</td><td>$${e.monthly_value}</td><td>$${e.suggested_price}</td></tr>
    `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin cálculos</td></tr>';
  }
  
  const assistantHistory = $('#assistantHistory');
  if (assistantHistory) {
    assistantHistory.innerHTML = state.assistant_events?.length ? state.assistant_events.slice().reverse().map(ev => `
      <div class="conversation user"><strong>Tú (${ev.channel}):</strong><p>${ev.question}</p></div>
      <div class="conversation"><strong>Asistente · ${ev.source}:</strong><p>${ev.answer.replace(/\\n/g, '<br>')}</p></div>
    `).join('') : '<p class="muted">Sin consultas aún.</p>';
  }
}

function renderSmartStacks() {
  const stats = smartstacksState.metrics || {};
  $('#ssTotalProducts').textContent = stats.total_products || 0;
  $('#ssTotalStock').textContent = stats.total_stock || 0;
  $('#ssConversations').textContent = (smartstacksState.conversations || []).length;
  
  // Inventario rápido
  const preview = $('#inventoryPreview');
  const products = smartstacksState.products || [];
  if (products.length) {
    const display = products.slice(0, 8);
    let html = '';
    display.forEach(p => {
      const emoji = p.quantity > 10 ? '✅' : p.quantity > 0 ? '⚠️' : '❌';
      html += `<div class="item"><span><strong>${p.code}</strong> ${p.name}</span><span class="stock">${emoji} ${p.quantity}</span></div>`;
    });
    if (products.length > 8) {
      html += `<div style="grid-column:1/-1; text-align:center; color:var(--muted); font-size:12px; padding:4px;">+ ${products.length - 8} productos más</div>`;
    }
    preview.innerHTML = html;
  } else {
    preview.innerHTML = '<p style="color:var(--muted); grid-column:1/-1; text-align:center; padding:12px;">No hay productos. Carga el demo.</p>';
  }
  
  // Conversaciones
  const convHtml = smartstacksState.conversations?.length ? smartstacksState.conversations.slice().reverse().map(c => `
    <div class="conversation user"><strong>Tú:</strong><p>${c.question}</p></div>
    <div class="conversation"><strong>🤖 Asistente:</strong><p>${(c.answer || '').replace(/\\n/g, '<br>')}</p></div>
  `).join('') : '<p style="color:var(--muted); text-align:center; padding:12px;">Haz una pregunta sobre el inventario.</p>';
  $('#conversationHistory').innerHTML = convHtml;
  
  // Progreso
  const convCount = (smartstacksState.conversations || []).length;
  const progress = Math.min((convCount / 12) * 100, 100);
  $('#ssProgressBar').style.width = progress + '%';
  const steps = ['Cargar Inventario', 'Conectar Asistente', 'Entrenar', 'Asistente en Vivo'];
  const stepIdx = Math.min(Math.floor(convCount / 3), steps.length - 1);
  $('#ssStepIndicator').textContent = convCount > 0 ? `Paso ${stepIdx + 1}/${steps.length}` : 'Paso 0/4';
  $('#ssStepTitle').textContent = steps[stepIdx] || steps[0];
  $('#ssStepDesc').textContent = convCount > 0 ? 'El asistente está aprendiendo de tus consultas.' : 'Comienza haciendo preguntas sobre tu inventario.';
  
  const details = $('#ssStepDetails');
  if (details) {
    details.innerHTML = convCount > 0 ? `
      <ul style="color:var(--muted); list-style:none; padding:0;">
        <li style="padding:4px 0;">✅ ${convCount} consultas respondidas</li>
        <li style="padding:4px 0;">✅ ${products.length} productos en inventario</li>
        <li style="padding:4px 0;">${convCount >= 10 ? '✅ ¡Asistente entrenado!' : '⏳ ' + (10 - convCount) + ' consultas más para entrenar'}</li>
      </ul>
    ` : '<p style="color:var(--muted);">Haz preguntas sobre tu inventario para entrenar al asistente.</p>';
  }
  
  const btn = $('#ssStepBtn');
  if (btn) {
    btn.textContent = convCount >= 10 ? '🎉 Completado' : '▶️ Ejecutar Paso';
    btn.onclick = convCount >= 10 ? resetSmartstacksDemo : runSmartstacksStep;
  }
}

function renderMiddleware() {
  $('#middlewareTotalMessages').textContent = middlewareState.total_messages || 0;
  $('#middlewareTotalCost').textContent = (middlewareState.total_cost || 0).toFixed(5);
  
  const byChannel = $('#middlewareByChannel');
  if (byChannel) {
    byChannel.innerHTML = middlewareState.by_channel?.length ? middlewareState.by_channel.map(c => `
      <tr><td>${c.channel}</td><td>${c.total}</td><td>$${c.cost.toFixed(5)}</td></tr>
    `).join('') : '<tr><td colspan="3" style="text-align:center;">Sin datos</td></tr>';
  }
  
  const history = $('#middlewareHistory');
  if (history) {
    history.innerHTML = middlewareState.messages?.length ? middlewareState.messages.map(m => `
      <div class="conversation user"><strong>Cliente (${m.channel}):</strong><p>${m.customer_message}</p></div>
      <div class="conversation"><strong>Respuesta · ${m.source} (${m.tokens_estimated} tokens ≈ $${m.cost_estimated}):</strong><p>${m.reply.replace(/\\n/g, '<br>')}</p></div>
    `).join('') : '<p class="muted">Sin mensajes aún.</p>';
  }
}

function renderConsulting() {
  $('#upcomingCount').textContent = consultingState.upcoming_count || 0;
  
  const emailRows = $('#emailClassifyRows');
  if (emailRows) {
    emailRows.innerHTML = consultingState.emails?.length ? consultingState.emails.map(e => `
      <tr><td>${e.subject}</td><td><span class="status-badge cat-${e.category}">${e.category}</span></td><td><span class="status-badge priority-${e.priority}">${e.priority}</span></td></tr>
    `).join('') : '<tr><td colspan="3" style="text-align:center;">Sin correos</td></tr>';
  }
  
  const appointmentRows = $('#appointmentRows');
  if (appointmentRows) {
    appointmentRows.innerHTML = consultingState.appointments?.length ? consultingState.appointments.map(a => `
      <tr><td>${a.appointment_date} ${a.appointment_time}</td><td>${a.client_name}</td><td><span class="status-badge status-${a.status}">${a.status}</span></td>
      <td>${a.status === 'confirmada' ? `<button class="secondary small" onclick="cancelAppointment(${a.id})">Cancelar</button>` : ''}</td></tr>
    `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin citas</td></tr>';
  }
}

// ============================================
// FUNCIONES DE REFRESH
// ============================================

async function refresh() {
  try { const res = await fetch('/api/state'); state = await res.json(); renderState(); } catch(e) { console.error(e); }
}

async function refreshSmartStacks() {
  try { const res = await fetch('/api/smartstacks/state'); smartstacksState = await res.json(); renderSmartStacks(); } catch(e) { console.error(e); }
}

async function refreshMiddleware() {
  try { const res = await fetch('/api/middleware/state'); middlewareState = await res.json(); renderMiddleware(); } catch(e) { console.error(e); }
}

async function refreshConsulting() {
  try { const res = await fetch('/api/consulting/state'); consultingState = await res.json(); renderConsulting(); } catch(e) { console.error(e); }
}

async function refreshInvoices() {
  try {
    const res = await fetch('/api/invoices');
    const data = await res.json();
    if (!data.ok) { toast('Error: ' + data.error); return; }
    const invoiceRows = $('#invoiceRows');
    if (invoiceRows) {
      invoiceRows.innerHTML = data.invoices?.length ? data.invoices.map(inv => `
        <tr>
          <td><strong>${inv.invoice_number}</strong></td>
          <td>${inv.customer_name}</td>
          <td>$${inv.total.toFixed(2)}</td>
          <td><span class="status-badge status-${inv.status}">${inv.status}</span></td>
          <td>
            <button onclick="updateInvoiceStatus(${inv.id}, 'verified')" class="secondary small">✓</button>
            <button onclick="updateInvoiceStatus(${inv.id}, 'cancelled')" class="secondary small">✗</button>
          </td>
        </tr>
      `).join('') : '<tr><td colspan="5" style="text-align:center;">Sin facturas</td></tr>';
    }
  } catch(e) { console.error(e); }
}

async function refreshBankAccounts() {
  try {
    const res = await fetch('/api/bank-accounts');
    const data = await res.json();
    if (!data.ok) return;
    const select = $('#invoiceBankAccount');
    if (select) {
      select.innerHTML = data.bank_accounts?.length ? data.bank_accounts.map(acc => `
        <option value="${acc.id}">${acc.name} - ${acc.bank}</option>
      `).join('') : '<option>No hay cuentas</option>';
    }
    const list = $('#bankAccountsList');
    if (list) {
      list.innerHTML = data.bank_accounts?.length ? data.bank_accounts.map(acc => `
        <div style="display:flex; justify-content:space-between; padding:8px; border-bottom:1px solid var(--line);">
          <div><strong>${acc.name}</strong> <span style="color:var(--muted); font-size:12px;">${acc.bank}</span></div>
          <div><span style="color:var(--brand2); font-size:12px;">✓ Activa</span></div>
        </div>
      `).join('') : '<p style="color:var(--muted);">No hay cuentas</p>';
    }
  } catch(e) { console.error(e); }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

function exportLeadsCSV() { window.location.href = '/api/leads/export/csv'; toast('Descargando CSV...'); }
function exportLeadsJSON() { window.location.href = '/api/leads/export/json'; toast('Descargando JSON...'); }
function exportCSV() { window.location.href = '/api/inventory/export/csv'; toast('📥 Descargando CSV...'); }

async function deleteProduct(id) {
  if (!confirm('¿Eliminar este producto?')) return;
  const result = await api('/api/inventory/product/delete', { product_id: id });
  if (!result.ok) { toast('Error: ' + result.error); return; }
  toast(result.message);
  refreshSmartStacks();
}

async function updateInvoiceStatus(invoiceId, status) {
  if (!confirm(`¿Cambiar a "${status}"?`)) return;
  const result = await api('/api/invoice/status', { invoice_id: invoiceId, status, verified_by: 'Admin' });
  if (!result.ok) { toast('Error: ' + result.error); return; }
  toast(result.message);
  refreshInvoices();
}

async function cancelAppointment(id) {
  if (!confirm('¿Cancelar esta cita?')) return;
  const result = await api('/api/consulting/appointment/cancel', { appointment_id: id });
  if (!result.ok) { toast('Error: ' + result.error); return; }
  toast(result.message);
  refreshConsulting();
}

async function loadProductsForInvoice() {
  try {
    const res = await fetch('/api/smartstacks/state');
    const data = await res.json();
    const container = $('#invoiceProductSelection');
    if (!container) return;
    if (!data.products?.length) {
      container.innerHTML = '<p style="color:var(--muted);">No hay productos disponibles.</p>';
      return;
    }
    container.innerHTML = data.products.map(p => `
      <div style="display:flex; align-items:center; gap:12px; padding:6px 0; border-bottom:1px solid var(--line);">
        <input type="checkbox" class="invoice-product-checkbox" data-id="${p.id}" data-price="${p.price || 0}" data-name="${p.name}">
        <span><strong>${p.code}</strong> - ${p.name}</span>
        <span style="color:var(--muted); font-size:12px;">Stock: ${p.quantity}</span>
        <span style="color:var(--brand2);">$${p.price || 0}</span>
        <input type="number" class="invoice-product-qty" data-id="${p.id}" value="1" min="1" max="${p.quantity}" style="width:60px; padding:4px;">
      </div>
    `).join('');
  } catch(e) { console.error(e); }
}

// ============================================
// SMARTSTACKS - FUNCIONES
// ============================================

function setQuestion(text) {
  $('#questionInput').value = text;
  $('#smartstacksForm').dispatchEvent(new Event('submit'));
}

async function loadDemo() {
  const products = [
    {code: 'PER-001', name: 'Perno de Anclaje 3/8"', quantity: 45, price: 2500, category: 'Fijaciones', description: 'Perno galvanizado para hormigón'},
    {code: 'TUB-002', name: 'Tubería PVC 1/2"', quantity: 120, price: 3800, category: 'Tuberías', description: 'Tubería PVC para instalaciones'},
    {code: 'MART-003', name: 'Martillo de Peña', quantity: 12, price: 15900, category: 'Herramientas', description: 'Martillo profesional'},
    {code: 'CIN-004', name: 'Cinta Métrica 5m', quantity: 28, price: 4500, category: 'Medición', description: 'Cinta métrica 5m'},
    {code: 'LLAVE-005', name: 'Llave Francesa 12"', quantity: 15, price: 8900, category: 'Herramientas', description: 'Llave ajustable cromada'},
    {code: 'DIS-006', name: 'Disco de Corte 4"', quantity: 80, price: 3200, category: 'Accesorios', description: 'Disco de corte para metal'},
  ];
  let added = 0;
  for (const p of products) {
    const result = await api('/api/inventory/product/add', p);
    if (result.ok) added++;
  }
  toast(`✅ ${added} productos demo cargados`);
  refreshSmartStacks();
}

async function runSmartstacksStep() {
  toast('🚀 Ejecutando paso...');
  const result = await api('/api/smartstacks/demo/step', { step_index: 0 });
  if (result.ok) toast(result.message);
  refreshSmartStacks();
}

function resetSmartstacksDemo() {
  if (confirm('¿Reiniciar el progreso de SmartStacks?')) {
    toast('🔄 Reiniciado');
    refreshSmartStacks();
  }
}

// ============================================
// MIDDLEWARE DEMO
// ============================================

async function loadMiddlewareDemo() {
  try {
    const res = await fetch('/api/middleware/demo/state');
    const data = await res.json();
    if (data.ok) {
      const demo = data.demo || {};
      if (demo.stats) {
        $('#mdTotalMessages').textContent = demo.stats.total_messages || 0;
        $('#mdAvgTime').textContent = (demo.stats.avg_response_time || 0) + 's';
        $('#mdTotalCost').textContent = '$' + (demo.stats.total_cost || 0).toFixed(2);
        $('#mdHoursSaved').textContent = (demo.stats.hours_saved || 0) + 'h';
        const channelStats = $('#mdChannelStats');
        if (channelStats && demo.channel_stats) {
          let html = '<table><thead><tr><th>Canal</th><th>Mensajes</th><th>Tiempo</th><th>Costo</th></tr></thead><tbody>';
          demo.channel_stats.forEach(ch => {
            html += `<tr><td>${ch.channel}</td><td>${ch.messages}</td><td>${ch.avg_time}s</td><td>$${ch.cost.toFixed(2)}</td></tr>`;
          });
          html += '</tbody></table>';
          channelStats.innerHTML = html;
        }
      }
    }
  } catch(e) { console.error(e); }
}

async function simulateMiddlewareMessage() {
  const channel = $('#mdChannel').value;
  const tone = $('#mdTone').value.trim();
  const message = $('#mdMessage').value.trim();
  if (!message) { toast('Escribe un mensaje'); return; }
  const result = await api('/api/middleware/demo/simulate', { channel, message, tone });
  if (!result.ok) { toast('Error: ' + result.error); return; }
  const div = $('#mdSimulationResult');
  if (div) {
    div.style.display = 'block';
    $('#mdResultChannel').textContent = result.channel || 'WhatsApp';
    $('#mdResultTime').textContent = result.response_time || 0;
    $('#mdResultCost').textContent = result.cost || 0;
    $('#mdResultMessage').textContent = message;
    $('#mdResultResponse').textContent = result.response || 'No se pudo generar';
    $('#mdResultSource').textContent = result.source || 'simulada';
    $('#mdResultTokens').textContent = result.tokens || 0;
    toast('✅ Respuesta generada');
  }
}

function loadMiddlewareExample() {
  const examples = ['Hola, ¿tienen envío a domicilio?', 'Me encantó el producto, ¿hay descuento?', 'Quisiera una cotización para 50 unidades.'];
  $('#mdMessage').value = examples[Math.floor(Math.random() * examples.length)];
}

// ============================================
// DEMO DE PROYECTOS
// ============================================

async function selectDemo(demoId) {
  currentDemoId = demoId;
  currentStep = 0;
  isUsingUserData = false;
  const res = await fetch(`/api/demo/data/${demoId}`);
  const data = await res.json();
  if (data.ok) demoData = data.data;
  $('#demoSimulation').style.display = 'block';
  const desc = $('#demoDescription');
  if (desc) {
    const demos = await (await fetch('/api/demo/state')).json();
    if (demos.demos && demos.demos[demoId]) {
      desc.innerHTML = `<h4>${demos.demos[demoId].icon} ${demos.demos[demoId].name}</h4><p>${demos.demos[demoId].description}</p>`;
    }
  }
  await runDemoStep();
}

async function runDemoStep() {
  if (!currentDemoId) { toast('Selecciona un proyecto'); return; }
  const userData = {};
  if (isUsingUserData) {
    const input = $('#demoUserDataInput');
    if (input && input.value) {
      try {
        const parsed = JSON.parse(input.value);
        if (currentDemoId === 'whatsapp') userData.messages = Array.isArray(parsed) ? parsed : [parsed];
        else if (currentDemoId === 'facturacion') {
          userData.client = parsed.client || 'Cliente';
          userData.products = parsed.products || [];
        }
      } catch(e) { toast('JSON inválido'); return; }
    }
  }
  const result = await api('/api/demo/step', { demo_id: currentDemoId, step_index: currentStep, user_data: userData });
  if (!result.ok) { toast('Error: ' + result.error); return; }
  currentStep = result.step_index + 1;
  $('#demoStepTitle').textContent = result.step.title;
  $('#demoStepDesc').textContent = result.step.desc;
  const dataArea = $('#demoDataArea');
  if (dataArea && result.data) {
    if (result.data.classified_emails) {
      let html = '<table><thead><tr><th>Asunto</th><th>Categoría</th><th>Acción</th></tr></thead><tbody>';
      result.data.classified_emails.forEach(e => {
        html += `<tr><td>${e.subject}</td><td><span class="status-badge cat-${e.category}">${e.category}</span></td><td>${e.action}</td></tr>`;
      });
      html += '</tbody></table>';
      dataArea.innerHTML = html;
    } else if (result.data.appointments) {
      let html = '<table><thead><tr><th>Cliente</th><th>Fecha</th><th>Estado</th></tr></thead><tbody>';
      result.data.appointments.forEach(a => {
        html += `<tr><td>${a.client}</td><td>${a.date}</td><td><span class="status-badge status-${a.status}">${a.status}</span></td></tr>`;
      });
      html += '</tbody></table>';
      dataArea.innerHTML = html;
    } else if (result.data.invoice) {
      const inv = result.data.invoice;
      dataArea.innerHTML = `
        <h4>🧾 Factura</h4>
        <p><strong>Número:</strong> ${inv.number}</p>
        <p><strong>Cliente:</strong> ${inv.client}</p>
        <p><strong>Subtotal:</strong> $${inv.subtotal.toFixed(2)}</p>
        <p><strong>IVA:</strong> $${inv.tax.toFixed(2)}</p>
        <p><strong>Total:</strong> <span class="metric">$${inv.total.toFixed(2)}</span></p>
      `;
    } else {
      dataArea.innerHTML = '<p style="color:var(--muted);">Paso completado. Continúa al siguiente.</p>';
    }
  }
  if (result.completed) {
    toast('🎉 Proyecto completado!');
    $('#demoStepActionBtn').textContent = '🔄 Reiniciar';
    $('#demoStepActionBtn').onclick = resetDemo;
  }
}

function resetDemo() {
  currentStep = 0;
  isUsingUserData = false;
  $('#demoUserInput').style.display = 'none';
  $('#demoStepActionBtn').textContent = 'Continuar';
  $('#demoStepActionBtn').onclick = runDemoStep;
  $('#demoDataArea').innerHTML = '<p style="color:var(--muted);">Reiniciando demo...</p>';
  runDemoStep();
  toast('🔄 Demo reiniciada');
}

function toggleDemoEdit() {
  const area = $('#demoUserInput');
  const btn = $('#demoEditBtn');
  if (area.style.display === 'none') {
    area.style.display = 'block';
    btn.textContent = '✖ Cerrar';
    if (currentDemoId) {
      $('#demoUserDataInput').value = JSON.stringify(demoData, null, 2);
    }
  } else {
    area.style.display = 'none';
    btn.textContent = '✏️ Usar mis datos';
  }
}

function applyUserData() {
  const input = $('#demoUserDataInput');
  if (!input?.value?.trim()) { toast('Escribe tus datos'); return; }
  isUsingUserData = true;
  toast('✅ Datos aplicados');
  runDemoStep();
}

// ============================================
// DIAGNÓSTICO
// ============================================

document.getElementById('diagnosticForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const scores = { smartstacks: 0, middleware: 0, 'llave-en-mano': 0 };
  for (const value of data.values()) {
    if (scores.hasOwnProperty(value)) scores[value]++;
  }
  let bestId = 'smartstacks';
  let bestScore = -1;
  for (const [id, score] of Object.entries(scores)) {
    if (score > bestScore) { bestScore = score; bestId = id; }
  }
  const uc = state.use_cases?.find(u => u.id === bestId);
  const box = $('#diagnosticResult');
  if (uc && box) {
    box.innerHTML = `
      <div class="conversation">
        <span class="tag">${uc.tag}</span>
        <h3>Te recomendamos: ${uc.title}</h3>
        <p><strong>Tu problema:</strong> ${uc.problem}</p>
        <p><strong>Solución:</strong> ${uc.solution}</p>
        <p>Desde $${uc.price}/mes · Setup $${uc.setup}</p>
        <ul>${uc.impact.map(i => `<li>${i}</li>`).join('')}</ul>
        <button onclick="showSection('leads')">Registrar mi negocio</button>
      </div>
    `;
    box.style.display = 'block';
  }
});

// ============================================
// EVENT HANDLERS
// ============================================

document.getElementById('leadForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/leads', Object.fromEntries(data));
  if (!out.ok) { toast('Error: ' + out.error); return; }
  toast(out.message);
  e.target.reset();
  refresh();
});

document.getElementById('estimateForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const payload = Object.fromEntries(data);
  payload.interactions = parseInt(payload.interactions);
  payload.minutes_saved = parseInt(payload.minutes_saved);
  payload.hourly_cost = parseFloat(payload.hourly_cost);
  const out = await api('/api/estimate', payload);
  if (!out.ok) { toast('Error: ' + out.error); return; }
  document.getElementById('estimateResult').innerHTML = `
    <p><strong>Caso:</strong> ${out.use_case}</p>
    <p><strong>Horas ahorradas/mes:</strong> ${out.human_hours_saved}</p>
    <p><strong>Valor mensual:</strong> $${out.monthly_value}</p>
    <p><strong>Precio sugerido:</strong> <span class="metric">$${out.suggested_price}</span></p>
  `;
  toast('Estimación calculada');
  refresh();
});

document.getElementById('assistantForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/assistant', Object.fromEntries(data));
  if (!out.ok) { toast('Error: ' + out.error); return; }
  toast('Respuesta recibida (' + out.source + ')');
  e.target.reset();
  refresh();
});

document.getElementById('productForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = {
    code: $('#pCode').value.trim(),
    name: $('#pName').value.trim(),
    quantity: parseInt($('#pQty').value),
    price: parseFloat($('#pPrice').value) || null,
    category: $('#pCategory').value.trim() || null,
    description: $('#pDesc').value.trim() || null
  };
  if (!data.code || !data.name || isNaN(data.quantity)) {
    toast('Completa código, nombre y cantidad');
    return;
  }
  const out = await api('/api/inventory/product/add', data);
  if (!out.ok) { toast('Error: ' + out.error); return; }
  toast(out.message);
  e.target.reset();
  refreshSmartStacks();
});

document.getElementById('smartstacksForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = $('#questionInput').value.trim();
  if (!question) return;
  const out = await api('/api/smartstacks/assistant', { question });
  if (!out.ok) { toast('Error: ' + out.error); return; }
  $('#questionInput').value = '';
  refreshSmartStacks();
  toast('✅ Respuesta recibida');
});

document.getElementById('middlewareForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/middleware/reply', Object.fromEntries(data));
  if (!out.ok) { toast('Error: ' + out.error); return; }
  toast(`Respuesta · ${out.tokens_estimated} tokens ≈ $${out.cost_estimated}`);
  e.target.reset();
  refreshMiddleware();
});

document.getElementById('emailClassifyForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/consulting/email/classify', Object.fromEntries(data));
  if (!out.ok) { toast('Error: ' + out.error); return; }
  document.getElementById('emailClassifyResult').innerHTML = `
    <div class="conversation">
      <p><span class="status-badge cat-${out.category}">${out.category}</span> <span class="status-badge priority-${out.priority}">prioridad ${out.priority}</span></p>
      <p><strong>Acción:</strong> ${out.suggested_action}</p>
    </div>
  `;
  toast('Correo clasificado');
  e.target.reset();
  refreshConsulting();
});

document.getElementById('appointmentForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/consulting/appointment/create', Object.fromEntries(data));
  if (!out.ok) { toast('Error: ' + out.error); return; }
  toast(out.message);
  e.target.reset();
  refreshConsulting();
});

document.getElementById('invoiceForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const selectedProducts = [];
  document.querySelectorAll('.invoice-product-checkbox:checked').forEach(cb => {
    const id = parseInt(cb.dataset.id);
    const qtyInput = document.querySelector(`.invoice-product-qty[data-id="${id}"]`);
    selectedProducts.push({ product_id: id, quantity: parseInt(qtyInput?.value || 1) });
  });
  if (!selectedProducts.length) { toast('Selecciona al menos un producto'); return; }
  const data = {
    customer_name: $('#invoiceCustomerName').value,
    customer_email: $('#invoiceCustomerEmail').value,
    customer_phone: $('#invoiceCustomerPhone').value,
    customer_rut: $('#invoiceCustomerRut').value,
    products: selectedProducts,
    payment_method: $('#invoicePaymentMethod').value,
    bank_account_id: parseInt($('#invoiceBankAccount').value)
  };
  const out = await api('/api/invoice/create', data);
  if (!out.ok) { toast('Error: ' + out.error); return; }
  toast(out.message);
  e.target.reset();
  refreshInvoices();
  refreshSmartStacks();
});

// ============================================
// INICIALIZACIÓN
// ============================================

renderState();
refreshSmartStacks();
refreshBankAccounts();
loadProductsForInvoice();
loadMiddlewareDemo();

setInterval(refreshSmartStacks, 30000);
setInterval(refreshInvoices, 30000);

</script>
</body>
</html>"""

# ============================================
# SERVIDOR HTTP
# ============================================

class SabrinaHandler(BaseHTTPRequestHandler):
    server_version = "SabrinaAILab/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{now_iso()}] {self.address_string()} {fmt % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "":
            html_response(self, render_index())
            return
        if parsed.path == "/api/state":
            json_response(self, get_dashboard_state())
            return
        if parsed.path == "/api/smartstacks/state":
            json_response(self, get_smartstacks_state())
            return
        if parsed.path == "/api/middleware/state":
            json_response(self, get_middleware_state())
            return
        if parsed.path == "/api/consulting/state":
            json_response(self, get_consulting_state())
            return
        if parsed.path == "/api/leads/export/csv":
            file_response(self, export_leads_csv(), "leads.csv", "text/csv")
            return
        if parsed.path == "/api/leads/export/json":
            file_response(self, export_leads_json(), "leads.json", "application/json")
            return
        if parsed.path == "/api/inventory/export/csv":
            file_response(self, export_inventory_csv(), "inventory.csv", "text/csv")
            return
        if parsed.path == "/api/invoices":
            json_response(self, get_invoices())
            return
        if parsed.path == "/api/bank-accounts":
            json_response(self, get_bank_accounts())
            return
        if parsed.path == "/api/notifications":
            json_response(self, get_invoice_notifications())
            return
        if parsed.path == "/api/demo/state":
            json_response(self, get_demo_state())
            return
        if parsed.path.startswith("/api/demo/data/"):
            demo_id = parsed.path.split("/")[-1]
            json_response(self, get_demo_data(demo_id))
            return
        if parsed.path == "/api/smartstacks/demo/state":
            json_response(self, get_smartstacks_demo_state())
            return
        if parsed.path == "/api/middleware/demo/state":
            json_response(self, get_middleware_demo_state())
            return
        if parsed.path == "/health":
            json_response(self, {"ok": True, "time": now_iso()})
            return
        json_response(self, {"ok": False, "error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = read_json(self)
            
            if parsed.path == "/api/leads":
                result = create_lead(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/estimate":
                result = estimate_cost(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/assistant":
                result = assistant_reply(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/inventory/product/add":
                result = add_inventory_product(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/inventory/product/delete":
                result = delete_inventory_product(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/inventory/product/update":
                result = update_inventory_product(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/smartstacks/assistant":
                result = smartstacks_assistant_reply(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/middleware/reply":
                result = channel_reply(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/consulting/email/classify":
                result = classify_email(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/consulting/appointment/create":
                result = create_appointment(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/consulting/appointment/cancel":
                result = cancel_appointment(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/email/campaign/create":
                result = create_email_campaign(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path.startswith("/api/email/campaign/") and "/send" in parsed.path:
                try:
                    campaign_id = int(parsed.path.split("/")[-2])
                    result = send_email_campaign(campaign_id)
                    json_response(self, result, 200 if result.get("ok") else 400)
                except (ValueError, IndexError):
                    json_response(self, {"ok": False, "error": "ID inválido"}, 400)
                return
            if parsed.path == "/api/email/send":
                result = send_single_email(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/invoice/create":
                result = create_invoice(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/invoice/status":
                result = update_invoice_status(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/invoice/proof":
                result = upload_payment_proof(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/bank-account/update":
                result = update_bank_account(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/invoice/assistant":
                result = invoice_assistant_reply(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/notification/mark":
                notification_id = payload.get("notification_id")
                if notification_id:
                    result = mark_notification_sent(int(notification_id))
                    json_response(self, result, 200 if result.get("ok") else 400)
                else:
                    json_response(self, {"ok": False, "error": "Falta notification_id"}, 400)
                return
            if parsed.path == "/api/demo/step":
                result = run_demo_step(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/smartstacks/demo/step":
                result = run_smartstacks_demo_step(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/smartstacks/demo/simulate":
                result = simulate_smartstacks_question(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/smartstacks/demo/product/add":
                result = add_custom_inventory_product(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/middleware/demo/step":
                result = run_middleware_demo_step(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/middleware/demo/simulate":
                result = simulate_middleware_message(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
                
            json_response(self, {"ok": False, "error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError:
            json_response(self, {"ok": False, "error": "JSON inválido"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            json_response(self, {"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


# ============================================
# MAIN
# ============================================

def main() -> None:
    init_db()
    # Cargar productos demo si no hay productos en la base de datos
    with db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM inventory_products").fetchone()["c"]
        if count == 0:
            demo_products = [
                {"code": "PER-001", "name": 'Perno de Anclaje 3/8"', "quantity": 45, "price": 2500, 
                 "category": "Fijaciones", "description": "Perno de anclaje galvanizado, ideal para fijaciones en hormigón."},
                {"code": "TUB-002", "name": 'Tubería PVC 1/2"', "quantity": 120, "price": 3800, 
                 "category": "Tuberías", "description": "Tubería PVC para instalaciones eléctricas y sanitarias."},
                {"code": "MART-003", "name": "Martillo de Peña", "quantity": 12, "price": 15900, 
                 "category": "Herramientas", "description": "Martillo de peña profesional, mango de fibra de vidrio."},
                {"code": "CIN-004", "name": "Cinta Métrica 5m", "quantity": 28, "price": 4500, 
                 "category": "Medición", "description": "Cinta métrica de 5 metros con sistema de freno."},
                {"code": "LLAVE-005", "name": 'Llave Francesa 12"', "quantity": 15, "price": 8900, 
                 "category": "Herramientas", "description": "Llave francesa ajustable, acero cromado."},
                {"code": "DIS-006", "name": 'Disco de Corte 4"', "quantity": 80, "price": 3200, 
                 "category": "Accesorios", "description": "Disco de corte para metal, diámetro 4 pulgadas."},
            ]
            for p in demo_products:
                try:
                    conn.execute(
                        "INSERT INTO inventory_products (created_at, code, name, quantity, price, description, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (now_iso(), p["code"], p["name"], p["quantity"], p["price"], p["description"], p["category"])
                    )
                except sqlite3.IntegrityError:
                    pass
            print("📦 Productos demo cargados automáticamente")
    
    server = ThreadingHTTPServer((HOST, PORT), SabrinaHandler)
    print(f"✅ Sabrina AI Lab listo en http://{HOST}:{PORT}")
    print(f"📁 Base de datos: {DB_PATH}")
    with db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM inventory_products").fetchone()["c"]
        print(f"📦 Productos en inventario: {count}")
    print("🔄 Presiona Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
