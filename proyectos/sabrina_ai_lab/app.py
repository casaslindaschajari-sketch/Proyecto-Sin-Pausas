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
HOST = os.environ.get("SABRINA_HOST", "0.0.0.0")  # Cambiado a 0.0.0.0 para Codespaces
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

# Configuración de métodos de pago
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
        # Tablas existentes...
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

        # NUEVA TABLA · SERVICIO 2: Automatización Empática Multicanal (Middleware LiteLLM)
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

        # NUEVAS TABLAS · SERVICIO 3: Digitalización IA Llave en Mano
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

        # NUEVAS TABLAS PARA FACTURACIÓN
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

        # Insertar datos iniciales de cuentas bancarias si no existen
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

        # Insertar métodos de pago iniciales
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
    """Obtiene el estado del módulo smartstacks (inventario + asistente)."""
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
    """Obtiene los productos actuales del inventario como lista de dicts."""
    with db_connect() as conn:
        return rows_to_dicts(
            conn.execute("SELECT id, code, name, quantity, price, description, category FROM inventory_products ORDER BY name").fetchall()
        )


def format_inventory_context(products: list[dict[str, Any]]) -> str:
    """Convierte la lista de productos en un bloque de texto para dar contexto al modelo."""
    if not products:
        return "El inventario está vacío."

    lines = ["INVENTARIO ACTUAL:\n"]
    for p in products:
        lines.append(f"- Código {p['code']}: {p['name']} (Stock: {p['quantity']} unidades, Precio: ${p['price'] or 'N/A'})")
        if p.get('description'):
            lines.append(f"  Descripción: {p['description']}")

    return "\n".join(lines)


def get_inventory_context() -> str:
    """Obtiene un contexto de inventario para pasar al asistente."""
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
    """Minúsculas, sin tildes y sin signos de puntuación, para comparar de forma tolerante."""
    replacements = str.maketrans("áéíóúñü", "aeiounu")
    cleaned = text.lower().translate(replacements)
    for ch in "¿?¡!.,;:()[]{}\"'":
        cleaned = cleaned.replace(ch, " ")
    return cleaned


def _extract_search_terms(question: str) -> list[str]:
    words = _normalize_text(question).split()
    return [w for w in words if w and w not in _INVENTORY_STOPWORDS]


def _word_variants(word: str) -> set[str]:
    """Genera variantes de un token (forma singular/plural simple) para comparar de forma tolerante."""
    variants = {word}
    for suffix in ("es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            variants.add(word[: -len(suffix)])
    return variants


def _term_matches(term: str, haystack_words: set[str]) -> bool:
    """True si el término (o su forma singular/plural) coincide con alguna palabra COMPLETA
    del producto. Se usa coincidencia por palabra (no subcadena) para poder distinguir
    productos con nombres parecidos, por ejemplo 'Cinta Marca A' vs 'Cinta Marca B'."""
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
    """Respuesta local simulada basada en inventario, con búsqueda real por producto."""
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
    """Asistente que responde consultando el inventario."""
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
    """Llama al modelo externo con contexto de inventario."""
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
# SERVICIO 2 · AUTOMATIZACIÓN EMPÁTICA MULTICANAL (LiteLLM Middleware)
# ============================================

CHANNEL_COST_PER_1K_TOKENS = float(os.environ.get("CHANNEL_COST_PER_1K_TOKENS", "0.002"))
CHANNEL_TONE_HINTS = {
    "whatsapp": "cercano, breve y directo, como un mensaje de chat",
    "instagram": "casual, amigable y con emojis moderados",
    "email": "formal, bien estructurado y completo",
    "web": "claro, profesional y directo",
}


def estimate_tokens(text: str) -> int:
    """Estimación simple de tokens (~4 caracteres por token) para mostrar control de costos."""
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
    """Busca la mayor cantidad mencionada en el mensaje (dígitos o número escrito en español).

    Se toma el número más grande entre todas las coincidencias (en vez del primero) porque
    palabras como 'una' (de 'una empresa') no deben ganarle a la cifra de negocio real,
    por ejemplo 'cien' en 'realizamos cien envíos diarios'.
    """
    candidates = [int(n) for n in re.findall(r"\b(\d{1,6})\b", normalized_text)]
    for word, value in _SPANISH_NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", normalized_text):
            candidates.append(value)
    return str(max(candidates)) if candidates else None


# Intenciones ordenadas por prioridad: la primera que coincida gana.
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
        None,  # se arma dinámicamente más abajo
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
    """Respuesta empática simulada cuando no hay LiteLLM/Azure configurado.

    A diferencia de una versión anterior más simple, esta detecta un conjunto amplio
    de intenciones (reclamos, logística/automatización, agendar, precio, agradecimiento,
    saludo) y, si no reconoce ninguna, arma una respuesta que sí hace referencia concreta
    a lo que la persona escribió en vez de una plantilla genérica repetida.
    """
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

    # Fallback: sin coincidencias claras, pero evitamos la respuesta genérica muerta.
    # Referenciamos lo que la persona escribió para demostrar que sí se leyó el mensaje.
    trimmed = message.strip()
    excerpt = trimmed if len(trimmed) <= 140 else trimmed[:137].rstrip() + "..."
    return (
        f"Gracias por escribirnos. (tono {tone})\n\n"
        f'Anoté lo que nos compartes: "{excerpt}". Para darte una respuesta precisa, '
        "¿me confirmas si esto es una consulta comercial, un tema de soporte, o quieres agendar una llamada? "
        "Con esa info te conecto con la persona indicada de inmediato."
    )


def call_external_model_channel(message: str, channel: str) -> tuple[str, str]:
    """Llama al modelo externo (LiteLLM/Azure) con un prompt de atención al cliente multicanal."""
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
    """Responde un mensaje entrante de cualquier canal y registra el costo estimado en tokens."""
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
# (filtrado automático de correos + gestión de agendas)
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
    """Clasificación local basada en reglas: categoría, prioridad y acción sugerida."""
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
    """Pide al modelo externo (si está configurado) una acción sugerida más específica."""
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
# RENDER HTML - Versión simplificada
# ============================================

def render_index() -> str:
    state_json = json.dumps(get_dashboard_state(), ensure_ascii=False)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sabrina AI Lab · MVP IA Humana</title>
  <style>
    :root {{
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
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at 18% 12%, rgba(155,140,255,.28), transparent 32rem),
        radial-gradient(circle at 82% 0%, rgba(51,214,166,.16), transparent 30rem),
        linear-gradient(135deg, #080a12, #111827 48%, #07111d);
      color: var(--text);
      min-height: 100vh;
      padding: 20px;
    }}
    a {{ color: inherit; }}
    .wrap {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; }}
    header {{
      position: sticky; top: 0; z-index: 10;
      backdrop-filter: blur(18px);
      background: rgba(9,11,18,.72);
      border-bottom: 1px solid var(--line);
      padding: 10px 0;
    }}
    nav {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0; gap: 14px; }}
    .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 800; letter-spacing: -.03em; }}
    .logo {{ width: 38px; height: 38px; border-radius: 14px; background: linear-gradient(135deg, var(--brand), var(--brand2)); display:grid; place-items:center; box-shadow: var(--shadow); }}
    .navlinks {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .navlinks a {{ text-decoration: none; color: var(--muted); font-size: 14px; padding: 8px 10px; border-radius: 999px; cursor: pointer; }}
    .navlinks a:hover, .navlinks a.active {{ background: var(--panel); color: var(--text); }}
    .hero {{ padding: 72px 0 36px; display: grid; grid-template-columns: 1.15fr .85fr; gap: 28px; align-items: center; }}
    .eyebrow {{ display:inline-flex; gap: 8px; align-items:center; color: var(--brand2); background: rgba(51,214,166,.09); border:1px solid rgba(51,214,166,.25); padding: 8px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }}
    h1 {{ font-size: clamp(42px, 7vw, 76px); line-height: .92; margin: 20px 0; letter-spacing: -.07em; }}
    h2 {{ font-size: clamp(26px, 4vw, 42px); margin: 0 0 14px; letter-spacing: -.04em; }}
    h3 {{ margin: 0 0 8px; letter-spacing: -.02em; }}
    p {{ color: var(--muted); line-height: 1.65; }}
    .hero p {{ font-size: 18px; max-width: 720px; }}
    .actions {{ display: flex; gap: 12px; margin-top: 26px; flex-wrap: wrap; }}
    button, .btn {{
      border: 0; color: #07111d; background: linear-gradient(135deg, var(--brand2), #b4ffe8);
      padding: 12px 16px; border-radius: 14px; font-weight: 800; cursor: pointer;
      text-decoration: none; display: inline-flex; align-items:center; gap: 8px;
    }}
    button.secondary, .btn.secondary {{ background: var(--panel-strong); color: var(--text); border: 1px solid var(--line); }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 24px; padding: 22px; box-shadow: var(--shadow); }}
    .grid {{ display: grid; gap: 18px; }}
    .grid.two {{ grid-template-columns: repeat(2, 1fr); }}
    .metric {{ font-size: 32px; font-weight: 900; letter-spacing: -.04em; }}
    .muted {{ color: var(--muted); }}
    .tag {{ display:inline-flex; padding: 6px 9px; border-radius: 999px; background: rgba(155,140,255,.13); border: 1px solid rgba(155,140,255,.28); color: #d8d2ff; font-size: 12px; font-weight: 600; }}
    section {{ padding: 38px 0; display: none; }}
    section.active {{ display: block; }}
    input, textarea, select {{
      width: 100%; background: rgba(0,0,0,.24); color: var(--text);
      border: 1px solid var(--line); border-radius: 14px; padding: 12px 13px;
      outline: none; font: inherit;
    }}
    textarea {{ min-height: 110px; resize: vertical; }}
    label {{ display:block; font-size: 13px; font-weight: 800; color: #dbe2f2; margin: 0 0 7px; }}
    .formgrid {{ display:grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .full {{ grid-column: 1 / -1; }}
    table {{ width:100%; border-collapse: collapse; overflow: hidden; border-radius: 16px; }}
    th, td {{ text-align:left; padding: 12px; border-bottom: 1px solid var(--line); color: var(--muted); vertical-align: top; }}
    th {{ color: var(--text); background: rgba(255,255,255,.06); }}
    .status-ok {{ color: var(--brand2); font-weight: 900; }}
    .conversation {{ background: rgba(0,0,0,.2); border-radius: 12px; padding: 14px; margin: 12px 0; border-left: 3px solid var(--brand2); }}
    .qcard {{ margin-bottom: 22px; }}
    .qoption {{
      display:flex; align-items:center; gap: 10px; padding: 12px 14px;
      border: 1px solid var(--line); border-radius: 14px; margin-bottom: 8px;
      cursor: pointer; transition: background .15s ease;
    }}
    .qoption:hover {{ background: var(--panel-strong); }}
    .qoption input {{ width: auto; accent-color: var(--brand2); }}
    .qoption span {{ color: var(--text); font-size: 14px; }}
    #diagnosticResult {{ display:none; }}
    #diagnosticResult ul {{ color: var(--muted); padding-left: 20px; margin: 10px 0; }}
    #diagnosticResult ul li {{ margin-bottom: 4px; }}
    .conversation.user {{ border-left-color: var(--brand); }}
    .conversation strong {{ color: var(--brand2); }}
    .conversation.user strong {{ color: var(--brand); }}
    details {{
      border: 1px solid var(--line);
      border-radius: 16px;
      margin-bottom: 10px;
      background: rgba(0,0,0,.18);
      overflow: hidden;
    }}
    summary {{
      list-style: none;
      cursor: pointer;
      padding: 16px 18px;
      font-weight: 800;
      font-size: 15px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--text);
    }}
    summary::-webkit-details-marker {{ display: none; }}
    summary::after {{
      content: '+';
      font-size: 20px;
      font-weight: 400;
      color: var(--brand2);
      transition: transform .2s ease;
      flex-shrink: 0;
    }}
    details[open] summary::after {{ transform: rotate(45deg); }}
    details[open] summary {{ border-bottom: 1px solid var(--line); }}
    .faq-body {{ padding: 16px 18px 20px; color: var(--muted); line-height: 1.7; font-size: 14.5px; }}
    .faq-body p {{ margin: 0 0 12px; }}
    .faq-body p:last-child {{ margin-bottom: 0; }}
    .faq-body table {{ width: 100%; border-collapse: collapse; margin: 10px 0 14px; border-radius: 12px; overflow: hidden; }}
    .faq-body th, .faq-body td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; font-size: 13.5px; }}
    .faq-body th {{ color: var(--text); background: rgba(255,255,255,.06); }}
    .faq-body strong {{ color: #dbe2f2; }}
    .closing {{ margin-top: 26px; text-align: center; color: var(--muted); }}
    footer {{ border-top: 1px solid var(--line); margin-top: 36px; padding: 24px 0 36px; color: var(--muted); }}
    .toast {{ position: fixed; right: 18px; bottom: 18px; background: #102018; color: #d9ffe8; border: 1px solid rgba(51,214,166,.38); padding: 12px 14px; border-radius: 14px; opacity:0; transform: translateY(100px); transition: all .3s ease; z-index: 999; }}
    .toast.show {{ opacity:1; transform: translateY(0); }}
    .status-badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }}
    .status-pending {{ background: rgba(255,204,102,.15); color: var(--warn); }}
    .status-paid {{ background: rgba(51,214,166,.15); color: var(--brand2); }}
    .status-cancelled {{ background: rgba(255,107,122,.15); color: var(--danger); }}
    .status-verified {{ background: rgba(155,140,255,.15); color: var(--brand); }}
    .status-confirmada {{ background: rgba(51,214,166,.15); color: var(--brand2); }}
    .status-cancelada {{ background: rgba(255,107,122,.15); color: var(--danger); }}
    .cat-urgente {{ background: rgba(255,107,122,.15); color: var(--danger); }}
    .cat-ventas {{ background: rgba(51,214,166,.15); color: var(--brand2); }}
    .cat-administrativo {{ background: rgba(155,140,255,.15); color: var(--brand); }}
    .cat-spam {{ background: rgba(255,255,255,.1); color: var(--muted); }}
    .cat-general {{ background: rgba(255,204,102,.15); color: var(--warn); }}
    .priority-alta {{ background: rgba(255,107,122,.15); color: var(--danger); }}
    .priority-media {{ background: rgba(255,204,102,.15); color: var(--warn); }}
    .priority-baja {{ background: rgba(255,255,255,.1); color: var(--muted); }}
    @media (max-width: 850px) {{
      .hero, .grid.two {{ grid-template-columns: 1fr; }}
      .navlinks {{ display:none; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <nav>
        <div class="brand"><div class="logo">✦</div><span>Sabrina AI Lab</span></div>
        <div class="navlinks">
          <a onclick="showSection('dashboard')" class="active">Dashboard</a>
          <a onclick="showSection('diagnostic')">¿Qué necesito?</a>
          <a onclick="showSection('leads')">Leads y Campañas</a>
          <a onclick="showSection('estimator')">Calculadora</a>
          <a onclick="showSection('assistant')">Asistente</a>
          <a onclick="showSection('smartstacks')">SmartStacks</a>
          <a onclick="showSection('middleware')">Automatización</a>
          <a onclick="showSection('consulting')">Llave en Mano</a>
          <a onclick="showSection('invoicing')">Facturación</a>
          <a onclick="showSection('faqs')">FAQs</a>
        </div>
      </nav>
    </header>

    <main>
      <section id="dashboard" class="active">
        <div class="hero">
          <div>
            <span class="eyebrow">✨ SISTEMA INTEGRAL</span>
            <h1>Sabrina AI Lab</h1>
            <p>
              Gestión integral de leads, inventario, facturación y asistentes de IA para comercios.
              Incluye automación de email, inventario en tiempo real y consultor estratégico.
            </p>
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

      <section id="diagnostic">
        <h2>🧭 ¿Qué necesita tu negocio?</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Responde 5 preguntas rápidas y te decimos cuál de nuestras soluciones encaja mejor con tu caso: SmartStacks, Automatización Empática o Digitalización Llave en Mano.
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

      <section id="leads">
        <h2>📋 Leads y Campañas</h2>

        <h3 style="margin-top:0; color: var(--muted); font-weight:600; font-size:13px; letter-spacing:.04em; text-transform:uppercase;">1. Registro de leads</h3>
        <div class="grid two">
          <div class="card">
            <h3>Últimas oportunidades</h3>
            <div style="overflow:auto; max-height: 400px;">
              <table><thead><tr><th>Fecha</th><th>Negocio</th><th>Email</th><th>Caso</th></tr></thead><tbody id="leadRows"></tbody></table>
            </div>
            <div style="margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap;">
              <button onclick="exportLeadsCSV()" class="secondary">📥 CSV</button>
              <button onclick="exportLeadsJSON()" class="secondary">📥 JSON</button>
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

        <h3 style="margin-top:32px; color: var(--muted); font-weight:600; font-size:13px; letter-spacing:.04em; text-transform:uppercase;">2. Envío de campañas</h3>
        <div class="grid two">
          <div class="card">
            <h3>Email masivo (múltiples leads)</h3>
            <form id="emailForm" class="formgrid">
              <div class="full"><label for="emailSubject">Asunto</label><input id="emailSubject" name="subject" required></div>
              <div class="full"><label for="emailBody">Cuerpo (usa {{name}} y {{email}})</label><textarea id="emailBody" name="body" required>Hola {{name}},

Vimos que tu negocio es {{email}} y tenemos una solución ideal para ti...</textarea></div>
              <div class="full"><label>Selecciona leads:</label><div id="leadCheckboxes"></div></div>
              <div class="full"><button type="submit">Enviar campaña</button></div>
            </form>
          </div>
          <div class="card">
            <h3>Email individual (un lead)</h3>
            <form id="singleEmailForm" class="formgrid">
              <div class="full"><label for="singleLeadSelect">Lead</label><select id="singleLeadSelect" name="lead_id" required></select></div>
              <div class="full"><label for="singleEmailSubject">Asunto</label><input id="singleEmailSubject" name="subject" required></div>
              <div class="full"><label for="singleEmailBody">Mensaje</label><textarea id="singleEmailBody" name="body" required>Hola {{name}}...</textarea></div>
              <div class="full"><button type="submit">Enviar email</button></div>
            </form>
          </div>
        </div>
      </section>

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

      <section id="smartstacks">
        <h2>🏪 SmartStacks - Asistente de Inventario</h2>
        <div class="grid two">
          <div class="card">
            <h3>📊 Inventario Actual</h3>
            <div style="margin-bottom: 12px;">
              <p><strong>Total de productos:</strong> <span id="productCount">0</span></p>
              <p><strong>Stock total:</strong> <span id="totalStock">0</span> unidades</p>
            </div>
            <div style="overflow:auto; max-height: 500px;">
              <table>
                <thead>
                  <tr><th>Código</th><th>Nombre</th><th>Stock</th><th>Precio</th><th>Acción</th></tr>
                </thead>
                <tbody id="productRows"></tbody>
              </table>
            </div>
            <div style="margin-top: 14px;">
              <button onclick="exportInventoryCSV()" class="secondary">📥 CSV</button>
            </div>
          </div>
          <div class="card">
            <h3>➕ Agregar Producto</h3>
            <form id="productForm" class="formgrid">
              <div class="full"><label>Código (ej: E404)</label><input name="code" required></div>
              <div class="full"><label>Nombre</label><input name="name" required></div>
              <div class="full"><label>Cantidad</label><input name="quantity" type="number" min="0" required></div>
              <div><label>Precio</label><input name="price" type="number" step="0.01" min="0"></div>
              <div><label>Categoría</label><input name="category"></div>
              <div class="full"><label>Descripción</label><textarea name="description" style="min-height: 80px;"></textarea></div>
              <div class="full"><button type="submit">Guardar Producto</button></div>
            </form>
          </div>
        </div>
        <div class="grid" style="margin-top: 28px;">
          <div class="card">
            <h3>🤖 Asistente de Inventario</h3>
            <div id="conversationHistory" style="overflow:auto; max-height: 400px; margin-bottom: 14px;"></div>
            <form id="smartstacksForm" class="formgrid">
              <div class="full"><label>Tu pregunta sobre inventario</label><textarea id="smartQuestion" name="question" placeholder="Ej: ¿Hay martillos disponibles? ¿Cuál es el stock del código E404?" required></textarea></div>
              <div class="full"><button type="submit">Hacer pregunta</button></div>
            </form>
          </div>
        </div>
      </section>

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

      <section id="faqs">
        <h2>📋 Preguntas Frecuentes</h2>
        <p class="muted" style="max-width:640px; margin-top:-6px;">
          Todo lo que necesitas saber sobre Sin Pausas: qué hacemos, cuánto cuesta y cómo empezar.
        </p>

        <div class="card" style="padding: 10px;">

          <details>
            <summary>🙋 ¿Qué es exactamente Sin Pausas?</summary>
            <div class="faq-body">
              <p>Sin Pausas es una agencia especializada en bajar la Inteligencia Artificial a la realidad cotidiana de las empresas. No somos un laboratorio de ciencia ficción ni una consultora abstracta. Somos un equipo que entiende que la tecnología solo tiene sentido cuando resuelve problemas humanos concretos: reducir el estrés de los vendedores, responder más rápido a los clientes o automatizar tareas repetitivas que roban tiempo valioso.</p>
              <p>Nuestra filosofía es simple: usamos el poder de la IA (42 GiB de RAM y modelos GPT de Azure Foundry) para que las personas trabajen mejor, no para reemplazarlas.</p>
            </div>
          </details>

          <details>
            <summary>🎯 ¿A qué nos dedicamos realmente?</summary>
            <div class="faq-body">
              <p>Nos dedicamos a diseñar, implementar y desplegar soluciones técnicas con IA para la digitalización y automatización de procesos empresariales. Pero no lo hacemos desde lo abstracto: lo hacemos desde la trinchera del día a día.</p>
              <p>Nuestro enfoque se centra en tres áreas concretas:</p>
              <table>
                <thead><tr><th>Área</th><th>¿Qué hacemos?</th></tr></thead>
                <tbody>
                  <tr><td>Asistentes inteligentes para comercios</td><td>Convertimos el inventario, los manuales y los catálogos de una tienda en un asistente conversacional que responde al instante por WhatsApp o tablet.</td></tr>
                  <tr><td>Automatización de respuestas con empatía</td><td>Centralizamos y gestionamos las interacciones de redes sociales y páginas web con un tono humano, personalizado y eficiente, usando un proxy unificado (LiteLLM) que administra múltiples modelos GPT.</td></tr>
                  <tr><td>Digitalización 'llave en mano'</td><td>Creamos sistemas modulares (con Docker) para flujos como filtrado de correos, gestión de agendas o atención al cliente, y los dejamos funcionando de forma nativa en los equipos de nuestros clientes.</td></tr>
                </tbody>
              </table>
            </div>
          </details>

          <details>
            <summary>🧰 ¿Qué servicios concretos pueden contratar con nosotros?</summary>
            <div class="faq-body">
              <p>Nuestra cartera de servicios está diseñada para adaptarse a diferentes necesidades y presupuestos. Estos son nuestros modelos comerciales:</p>
              <p><strong>1. SaaS de Asistente Experto (SmartStacks de Cercanía)</strong><br>
              ¿Qué es? Una suscripción mensual que convierte los datos de tu negocio (inventario, precios, manuales) en un asistente de IA accesible por WhatsApp o dispositivo en tienda.<br>
              ¿Para quién? Pymes, comercios locales, ferreterías industriales, almacenes y cualquier negocio con catálogo de productos.<br>
              Beneficio clave: Tus vendedores dejan de buscar códigos y hojas técnicas. Preguntan en lenguaje natural y obtienen respuestas en 1 segundo. Menos filas, menos estrés, más ventas.</p>
              <p><strong>2. Infraestructura Centralizada de Respuestas (LiteLLM Middleware)</strong><br>
              ¿Qué es? Un motor unificado que conecta tus canales (web, WhatsApp, redes sociales) a los modelos GPT más avanzados, administrando el consumo de tokens para optimizar costos.<br>
              ¿Para quién? Agencias de marketing, equipos de community management o desarrolladores que quieran ofrecer respuestas inteligentes a sus clientes sin lidiar con la complejidad técnica.<br>
              Beneficio clave: Respondes con empatía y personalización a gran escala, sin descuidar tu negocio principal ni tu tiempo libre.</p>
              <p><strong>3. Consultorías de Implementación 'Llave en Mano'</strong><br>
              ¿Qué es? Un proyecto único donde diseñamos y configuramos un sistema a medida para tu empresa: desde el filtrado automático de correos hasta la gestión de agendas con IA.<br>
              ¿Para quién? Empresas tradicionales que quieren dar el salto a la IA pero necesitan acompañamiento total y soluciones que funcionen "de cajón" en su propio entorno.<br>
              Beneficio clave: Te olvidas de la complejidad técnica. Nosotros instalamos, configuramos y te formamos. Tú solo usas la solución.</p>
            </div>
          </details>

          <details>
            <summary>⏳ ¿Por qué el plazo de 6 semanas es importante?</summary>
            <div class="faq-body">
              <p>Nuestro modelo de trabajo tiene un límite estricto de 6 semanas porque operamos en un entorno de aprendizaje intensivo con recursos de alto rendimiento (los 42 GiB de RAM y los modelos GPT de Azure Foundry). Este es nuestro "laboratorio vivo".</p>
              <p>El proceso es el siguiente:</p>
              <p>Semanas 1-2: Aprendemos a fondo tu negocio y configuramos el entorno técnico.<br>
              Semanas 3-4: Desarrollamos un MVP (producto mínimo viable) funcional.<br>
              Semanas 5-6: Lo probamos en vivo contigo, recogemos feedback y armamos la propuesta comercial definitiva.</p>
              <p>Pasado este plazo, los accesos expiran. La única forma de continuar es que la solución haya demostrado su valor real y consolidemos una propuesta de negocio con sentido para ambas partes. Esto nos asegura que solo trabajamos en proyectos que realmente marcan la diferencia.</p>
            </div>
          </details>

          <details>
            <summary>💰 ¿Cuánto cuesta trabajar con Sin Pausas?</summary>
            <div class="faq-body">
              <p>Nuestros precios varían según el modelo de servicio:</p>
              <table>
                <thead><tr><th>Servicio</th><th>Modelo de Pago</th><th>Rango Aproximado</th></tr></thead>
                <tbody>
                  <tr><td>SaaS Asistente Experto</td><td>Suscripción mensual</td><td>Desde $99/mes (dependiendo del volumen de datos y consultas)</td></tr>
                  <tr><td>Middleware LiteLLM</td><td>Membresía fija o fee por interacción</td><td>Desde $199/mes por volumen básico</td></tr>
                  <tr><td>Consultoría Llave en Mano</td><td>Pago único (setup + implementación)</td><td>Desde $1,500 (según complejidad del flujo)</td></tr>
                </tbody>
              </table>
              <p>Nota: Los precios son referenciales y se ajustan en la propuesta comercial final, que se construye durante las 6 semanas de trabajo conjunto.</p>
            </div>
          </details>

          <details>
            <summary>🛡️ ¿Qué pasa con la seguridad y privacidad de mis datos?</summary>
            <div class="faq-body">
              <p>Es una prioridad absoluta. Al trabajar con nosotros:</p>
              <p><strong>Datos locales:</strong> Tu información (inventarios, manuales, correos) se almacena de forma local en la VM o en tus propios servidores. No compartimos tus datos con terceros.</p>
              <p><strong>Cifrado:</strong> Todas las comunicaciones con los modelos GPT de Azure se realizan bajo estándares de seguridad empresarial (HTTPS, tokens cifrados).</p>
              <p><strong>Control total:</strong> En los proyectos 'llave en mano', el sistema se despliega en tu propia infraestructura, dándote el control absoluto de tus datos.</p>
            </div>
          </details>

          <details>
            <summary>🤝 ¿Cómo empiezo a trabajar con Sin Pausas?</summary>
            <div class="faq-body">
              <p>El proceso es sencillo y directo:</p>
              <p>Contacto inicial: Nos cuentas tu negocio, tus dolores y tus objetivos. Sin compromiso.<br>
              Diagnóstico rápido: Evaluamos si nuestro modelo de 6 semanas es adecuado para ti.<br>
              Firma de acuerdo: Definimos alcance, fechas y condiciones.<br>
              Comenzamos el laboratorio: Entramos en las 6 semanas de trabajo intensivo.<br>
              Evaluación y continuidad: Al finalizar, decidimos juntos si la solución escala a un contrato comercial formal.</p>
            </div>
          </details>

          <details>
            <summary>📞 ¿Puedo probar la solución antes de comprometerme?</summary>
            <div class="faq-body">
              <p>¡Sí! Durante las semanas 5 y 6 del laboratorio, montamos una interfaz web con protección HTTPS para que puedas probar la solución en vivo con tus propios datos y usuarios reales. Recogemos sus opiniones y las usamos para ajustar la propuesta final. Es una prueba de concepto real antes de cualquier compromiso económico.</p>
            </div>
          </details>

          <details>
            <summary>❓ ¿Qué tipo de empresas se benefician más con Sin Pausas?</summary>
            <div class="faq-body">
              <p>Principalmente:</p>
              <p>Comercios minoristas y mayoristas (ferreterías, tiendas de ropa, almacenes de suministros).<br>
              Empresas de servicios (consultorías, estudios legales, agencias de marketing).<br>
              Negocios tradicionales que quieren digitalizarse pero no saben por dónde empezar.<br>
              Startups y emprendedores que necesitan automatizar su atención al cliente sin perder el toque humano.</p>
            </div>
          </details>

          <details>
            <summary>🧠 ¿Qué tecnología usan exactamente?</summary>
            <div class="faq-body">
              <p>Nuestro stack tecnológico está diseñado para ser potente y escalable:</p>
              <p><strong>Hardware:</strong> Máquina virtual con 42 GiB de RAM, ideal para almacenar y procesar grandes volúmenes de datos locales (inventarios, históricos, documentos).</p>
              <p><strong>Modelos de IA:</strong> Acceso a 3 modelos GPT de Azure Foundry, lo que nos permite elegir el mejor modelo para cada tarea (velocidad, costo o calidad de respuesta).</p>
              <p><strong>Orquestación:</strong> Usamos LiteLLM como proxy unificado para administrar los modelos y balancear el consumo de tokens.</p>
              <p><strong>Despliegue:</strong> Contenedores Docker para sistemas modulares y portables.</p>
              <p><strong>Interfaces:</strong> Integración con WhatsApp Business API, web con HTTPS y tablets en tienda.</p>
            </div>
          </details>

          <details>
            <summary>🚀 ¿Qué diferencia a Sin Pausas de otras agencias de IA?</summary>
            <div class="faq-body">
              <p>Lo que nos hace únicos es nuestra visión humana y nuestro modelo de validación comercial:</p>
              <p><strong>No vendemos humo:</strong> Solo trabajamos en proyectos que han sido probados y validados en el mundo real durante nuestras 6 semanas de laboratorio.</p>
              <p><strong>Enfoque en la persona:</strong> Medimos el éxito en reducción de estrés, tiempo recuperado y mejora de la calidad de vida de los equipos, no solo en métricas técnicas.</p>
              <p><strong>Transparencia total:</strong> Te mostramos los costos reales de cada respuesta de IA (consumo de tokens) para que tomes decisiones informadas.</p>
              <p><strong>Compromiso con la continuidad:</strong> Si la solución no demuestra su valor, no forzamos una relación comercial. Tu éxito es el nuestro.</p>
            </div>
          </details>

          <details>
            <summary>📬 ¿Cómo puedo contactarlos?</summary>
            <div class="faq-body">
              <p>Puedes escribirnos a través del formulario de contacto en nuestra página web, o directamente a nuestro correo: contacto@sinpausas.ia (ejemplo). También puedes seguirnos en nuestras redes sociales para estar al día de nuestros casos de éxito y novedades.</p>
            </div>
          </details>

        </div>

        <p class="closing">¿Tienes más preguntas? Estamos aquí para escucharte y construir juntos la solución que tu negocio necesita. ¡Sin pausas, pero con propósito! 🤖💙</p>
      </section>

    </main>

    <footer>
      <strong>Sabrina AI Lab</strong> · Ejecuta: <code>python3 proyectos/sabrina_ai_lab/app.py</code>
    </footer>
  </div>

  <div class="toast" id="toast"></div>

<script>
const state = {state_json};
let smartstacksState = {{}};
let middlewareState = {{}};
let consultingState = {{}};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const api = async (url, data) => {{
  const res = await fetch(url, {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data)}});
  return await res.json();
}};
const toast = (msg) => {{
  const el = $('#toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}};

function showSection(id) {{
  $$('section').forEach(s => s.classList.remove('active'));
  $$('.navlinks a').forEach(a => a.classList.remove('active'));
  const section = $(`#${{id}}`);
  if (section) section.classList.add('active');
  if (event && event.target) event.target.classList.add('active');
  
  if (id === 'invoicing') {{
    refreshInvoices();
    refreshBankAccounts();
  }}
  if (id === 'middleware') {{
    refreshMiddleware();
  }}
  if (id === 'consulting') {{
    refreshConsulting();
  }}
}}

function renderState() {{
  const modeStatus = $('#modeStatus');
  if (modeStatus) {{
    modeStatus.textContent = state.integrations.email_ready ? 
      '✓ Email configurado' : 
      '⚠ Email no configurado';
  }}
  
  const invoiceCount = $('#invoiceCount');
  if (invoiceCount) {{
    invoiceCount.textContent = state.metrics.invoices || 0;
  }}
  
  const leadRows = $('#leadRows');
  if (leadRows) {{
    leadRows.innerHTML = state.leads && state.leads.length ? state.leads.map(l => `
      <tr>
        <td>${{new Date(l.created_at).toLocaleString()}}</td>
        <td><strong>${{l.business}}</strong></td>
        <td>${{l.email}}</td>
        <td>${{l.use_case}}</td>
      </tr>
    `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin leads registrados</td></tr>';
  }}
  
  const leadCheckboxes = $('#leadCheckboxes');
  if (leadCheckboxes) {{
    leadCheckboxes.innerHTML = state.leads && state.leads.length ? state.leads.map(l => `
      <label><input type="checkbox" class="lead-checkbox" value="${{l.email}}"> <strong>${{l.business}}</strong> (${{l.email}})</label>
    `).join('<br>') : '<p style="color:var(--muted);">Registra leads primero</p>';
  }}
  
  const singleLeadSelect = $('#singleLeadSelect');
  if (singleLeadSelect) {{
    singleLeadSelect.innerHTML = state.leads && state.leads.length ? state.leads.map(l => `
      <option value="${{l.id}}">${{l.business}} - ${{l.name}}</option>
    `).join('') : '<option>Sin leads</option>';
  }}

  const estimateRows = $('#estimateRows');
  if (estimateRows) {{
    estimateRows.innerHTML = state.estimates && state.estimates.length ? state.estimates.map(e => `
      <tr>
        <td>${{e.use_case}}</td>
        <td>${{e.interactions}}</td>
        <td>$${{e.monthly_value}}</td>
        <td>$${{e.suggested_price}}</td>
      </tr>
    `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin cálculos aún</td></tr>';
  }}

  const assistantHistory = $('#assistantHistory');
  if (assistantHistory) {{
    assistantHistory.innerHTML = state.assistant_events && state.assistant_events.length ? state.assistant_events.slice().reverse().map(ev => `
      <div class="conversation user"><strong>Tú (${{ev.channel}}):</strong><p>${{ev.question}}</p></div>
      <div class="conversation"><strong>Asistente · ${{ev.source}}:</strong><p>${{ev.answer.replace(/\\n/g, '<br>')}}</p></div>
    `).join('') : '<p class="muted">Sin consultas aún.</p>';
  }}
}}

function renderSmartStacks() {{
  const productCount = $('#productCount');
  const totalStock = $('#totalStock');
  if (productCount) productCount.textContent = smartstacksState.metrics?.total_products || 0;
  if (totalStock) totalStock.textContent = smartstacksState.metrics?.total_stock || 0;
  
  const productRows = $('#productRows');
  if (productRows) {{
    productRows.innerHTML = smartstacksState.products && smartstacksState.products.length ? smartstacksState.products.map(p => `
      <tr>
        <td><strong>${{p.code}}</strong></td>
        <td>${{p.name}}</td>
        <td>${{p.quantity}}</td>
        <td>${{p.price ? '$' + p.price : 'N/A'}}</td>
        <td><button class="secondary" onclick="deleteProduct(${{p.id}})" style="padding: 6px 8px; font-size: 12px;">Eliminar</button></td>
      </tr>
    `).join('') : '<tr><td colspan="5" style="text-align:center;">Sin productos</td></tr>';
  }}
  
  const conversationHistory = $('#conversationHistory');
  if (conversationHistory) {{
    conversationHistory.innerHTML = smartstacksState.conversations && smartstacksState.conversations.length ? smartstacksState.conversations.slice().reverse().map(c => `
      <div class="conversation user">
        <strong>Tú (${{c.channel}}):</strong>
        <p>${{c.question}}</p>
      </div>
      <div class="conversation">
        <strong>Asistente:</strong>
        <p>${{(c.answer || '').replace(/\\n/g, '<br>')}}</p>
      </div>
    `).join('') : '<p style="color: var(--muted); text-align: center;">Sin conversaciones aún</p>';
  }}
}}

async function refresh() {{
  try {{
    const res = await fetch('/api/state');
    const newState = await res.json();
    Object.assign(state, newState);
    renderState();
  }} catch (e) {{
    console.error('Error refreshing state:', e);
  }}
}}

async function refreshSmartStacks() {{
  try {{
    const res = await fetch('/api/smartstacks/state');
    smartstacksState = await res.json();
    renderSmartStacks();
  }} catch (e) {{
    console.error('Error refreshing smartstacks:', e);
  }}
}}

function renderMiddleware() {{
  const totalMessages = $('#middlewareTotalMessages');
  const totalCost = $('#middlewareTotalCost');
  if (totalMessages) totalMessages.textContent = middlewareState.total_messages || 0;
  if (totalCost) totalCost.textContent = (middlewareState.total_cost || 0).toFixed(5);

  const byChannel = $('#middlewareByChannel');
  if (byChannel) {{
    byChannel.innerHTML = middlewareState.by_channel && middlewareState.by_channel.length ? middlewareState.by_channel.map(c => `
      <tr><td>${{c.channel}}</td><td>${{c.total}}</td><td>$${{c.cost.toFixed(5)}}</td></tr>
    `).join('') : '<tr><td colspan="3" style="text-align:center;">Sin datos aún</td></tr>';
  }}

  const history = $('#middlewareHistory');
  if (history) {{
    history.innerHTML = middlewareState.messages && middlewareState.messages.length ? middlewareState.messages.map(m => `
      <div class="conversation user"><strong>Cliente (${{m.channel}}):</strong><p>${{m.customer_message}}</p></div>
      <div class="conversation"><strong>Respuesta · ${{m.source}} (${{m.tokens_estimated}} tokens ≈ $${{m.cost_estimated}}):</strong><p>${{m.reply.replace(/\\n/g, '<br>')}}</p></div>
    `).join('') : '<p class="muted">Sin mensajes aún.</p>';
  }}
}}

async function refreshMiddleware() {{
  try {{
    const res = await fetch('/api/middleware/state');
    middlewareState = await res.json();
    renderMiddleware();
  }} catch (e) {{
    console.error('Error refreshing middleware:', e);
  }}
}}

function renderConsulting() {{
  const upcomingCount = $('#upcomingCount');
  if (upcomingCount) upcomingCount.textContent = consultingState.upcoming_count || 0;

  const emailRows = $('#emailClassifyRows');
  if (emailRows) {{
    emailRows.innerHTML = consultingState.emails && consultingState.emails.length ? consultingState.emails.map(e => `
      <tr>
        <td>${{e.subject}}</td>
        <td><span class="status-badge cat-${{e.category}}">${{e.category}}</span></td>
        <td><span class="status-badge priority-${{e.priority}}">${{e.priority}}</span></td>
      </tr>
    `).join('') : '<tr><td colspan="3" style="text-align:center;">Sin correos clasificados</td></tr>';
  }}

  const appointmentRows = $('#appointmentRows');
  if (appointmentRows) {{
    appointmentRows.innerHTML = consultingState.appointments && consultingState.appointments.length ? consultingState.appointments.map(a => `
      <tr>
        <td>${{a.appointment_date}} ${{a.appointment_time}}</td>
        <td>${{a.client_name}}</td>
        <td><span class="status-badge status-${{a.status}}">${{a.status}}</span></td>
        <td>${{a.status === 'confirmada' ? `<button class="secondary" onclick="cancelAppointment(${{a.id}})" style="padding: 6px 8px; font-size: 12px;">Cancelar</button>` : ''}}</td>
      </tr>
    `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin citas agendadas</td></tr>';
  }}
}}

async function refreshConsulting() {{
  try {{
    const res = await fetch('/api/consulting/state');
    consultingState = await res.json();
    renderConsulting();
  }} catch (e) {{
    console.error('Error refreshing consulting:', e);
  }}
}}

async function cancelAppointment(id) {{
  if (!confirm('¿Cancelar esta cita?')) return;
  const result = await api('/api/consulting/appointment/cancel', {{ appointment_id: id }});
  if (!result.ok) {{ toast('Error: ' + result.error); return; }}
  toast(result.message);
  refreshConsulting();
}}

function exportLeadsCSV() {{ window.location.href = '/api/leads/export/csv'; toast('Descargando CSV...'); }}
function exportLeadsJSON() {{ window.location.href = '/api/leads/export/json'; toast('Descargando JSON...'); }}
function exportInventoryCSV() {{ window.location.href = '/api/inventory/export/csv'; toast('Descargando CSV...'); }}

async function deleteProduct(id) {{
  if (!confirm('¿Eliminar este producto?')) return;
  const result = await api('/api/inventory/product/delete', {{ product_id: id }});
  if (!result.ok) {{ toast('Error: ' + result.error); return; }}
  toast(result.message);
  refreshSmartStacks();
}}

async function refreshInvoices() {{
  try {{
    const res = await fetch('/api/invoices');
    const data = await res.json();
    if (!data.ok) {{ toast('Error: ' + data.error); return; }}
    
    const invoiceRows = $('#invoiceRows');
    if (invoiceRows) {{
      invoiceRows.innerHTML = data.invoices && data.invoices.length ? data.invoices.map(inv => `
        <tr>
          <td><strong>${{inv.invoice_number}}</strong></td>
          <td>${{inv.customer_name}}</td>
          <td>$${{inv.total.toFixed(2)}}</td>
          <td><span class="status-badge status-${{inv.status}}">${{inv.status}}</span></td>
          <td>
            <button onclick="updateInvoiceStatus(${{inv.id}}, 'verified')" class="secondary" style="padding: 4px 8px; font-size: 11px;">✓ Verificar</button>
            <button onclick="updateInvoiceStatus(${{inv.id}}, 'cancelled')" class="secondary" style="padding: 4px 8px; font-size: 11px;">✗ Cancelar</button>
          </td>
        </tr>
      `).join('') : '<tr><td colspan="5" style="text-align:center;">Sin facturas</td></tr>';
    }}
  }} catch (e) {{
    console.error('Error refreshing invoices:', e);
  }}
}}

async function refreshBankAccounts() {{
  try {{
    const res = await fetch('/api/bank-accounts');
    const data = await res.json();
    if (!data.ok) {{ toast('Error: ' + data.error); return; }}
    
    const select = $('#invoiceBankAccount');
    if (select) {{
      select.innerHTML = data.bank_accounts && data.bank_accounts.length ? data.bank_accounts.map(acc => `
        <option value="${{acc.id}}">${{acc.name}} - ${{acc.bank}} - ${{acc.account_number}}</option>
      `).join('') : '<option>No hay cuentas activas</option>';
    }}
    
    const bankAccountsList = $('#bankAccountsList');
    if (bankAccountsList) {{
      bankAccountsList.innerHTML = data.bank_accounts && data.bank_accounts.length ? data.bank_accounts.map(acc => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid var(--line);">
          <div>
            <strong>${{acc.name}}</strong>
            <span style="color: var(--muted); font-size: 12px;">${{acc.bank}} - ${{acc.account_number}}</span>
          </div>
          <div>
            <span style="color: var(--brand2); font-size: 12px;">✓ Activa</span>
            <button onclick="toggleBankAccount(${{acc.id}})" class="secondary" style="padding: 4px 8px; font-size: 11px;">Desactivar</button>
          </div>
        </div>
      `).join('') : '<p style="color: var(--muted);">No hay cuentas bancarias configuradas</p>';
    }}
  }} catch (e) {{
    console.error('Error refreshing bank accounts:', e);
  }}
}}

async function toggleBankAccount(accountId) {{
  if (!confirm('¿Desactivar esta cuenta bancaria?')) return;
  const result = await api('/api/bank-account/update', {{
    account_id: accountId,
    active: 0
  }});
  if (!result.ok) {{ toast('Error: ' + result.error); return; }}
  toast('Cuenta desactivada');
  refreshBankAccounts();
}}

async function updateInvoiceStatus(invoiceId, status) {{
  if (!confirm(`¿Cambiar estado de factura a "${{status}}"?`)) return;
  const result = await api('/api/invoice/status', {{
    invoice_id: invoiceId,
    status: status,
    verified_by: 'Admin Web'
  }});
  if (!result.ok) {{ toast('Error: ' + result.error); return; }}
  toast(result.message);
  refreshInvoices();
}}

async function loadProductsForInvoice() {{
  try {{
    const res = await fetch('/api/smartstacks/state');
    const data = await res.json();
    const container = $('#invoiceProductSelection');
    if (!container) return;
    
    if (!data.products || !data.products.length) {{
      container.innerHTML = '<p style="color: var(--muted);">No hay productos disponibles en el inventario.</p>';
      return;
    }}
    
    container.innerHTML = data.products.map(p => `
      <div style="display: flex; align-items: center; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--line);">
        <input type="checkbox" class="invoice-product-checkbox" data-id="${{p.id}}" data-price="${{p.price || 0}}" data-name="${{p.name}}">
        <span><strong>${{p.code}}</strong> - ${{p.name}}</span>
        <span style="color: var(--muted); font-size: 12px;">Stock: ${{p.quantity}}</span>
        <span style="color: var(--brand2);">$${{p.price || 0}}</span>
        <input type="number" class="invoice-product-qty" data-id="${{p.id}}" value="1" min="1" max="${{p.quantity}}" style="width: 60px; padding: 4px;">
      </div>
    `).join('');
  }} catch (e) {{
    console.error('Error loading products:', e);
  }}
}}

// Event Handlers

const diagnosticForm = $('#diagnosticForm');
if (diagnosticForm) {{
  diagnosticForm.addEventListener('submit', (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const scores = {{'smartstacks': 0, 'middleware': 0, 'llave-en-mano': 0}};
    for (const value of data.values()) {{
      if (scores.hasOwnProperty(value)) scores[value]++;
    }}
    let bestId = 'smartstacks';
    let bestScore = -1;
    for (const [id, score] of Object.entries(scores)) {{
      if (score > bestScore) {{ bestScore = score; bestId = id; }}
    }}
    renderDiagnosticResult(bestId);
  }});
}}

function renderDiagnosticResult(useCaseId) {{
  const uc = (state.use_cases || []).find(u => u.id === useCaseId);
  const box = $('#diagnosticResult');
  if (!uc || !box) return;

  box.innerHTML = `
    <div class="conversation">
      <span class="tag">${{uc.tag}}</span>
      <h3 style="margin-top:10px;">Te recomendamos: ${{uc.title}}</h3>
      <p><strong>Tu problema:</strong> ${{uc.problem}}</p>
      <p><strong>Solución:</strong> ${{uc.solution}}</p>
      <p class="muted">Desde $${{uc.price}}/mes · Setup desde $${{uc.setup}}</p>
      <ul>${{uc.impact.map(i => `<li>${{i}}</li>`).join('')}}</ul>
      <button onclick="applyDiagnosticToLead('${{uc.id}}')">Registrar mi negocio con este caso</button>
    </div>
  `;
  box.style.display = 'block';
  box.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
}}

function applyDiagnosticToLead(useCaseId) {{
  $$('section').forEach(s => s.classList.remove('active'));
  $$('.navlinks a').forEach(a => a.classList.remove('active'));
  const leadsSection = $('#leads');
  if (leadsSection) leadsSection.classList.add('active');
  const leadsLink = Array.from($$('.navlinks a')).find(a => (a.getAttribute('onclick') || '').includes("'leads'"));
  if (leadsLink) leadsLink.classList.add('active');

  const select = document.querySelector('#leadForm select[name="use_case"]');
  if (select) select.value = useCaseId;

  const leadFormEl = $('#leadForm');
  if (leadFormEl) leadFormEl.scrollIntoView({{behavior: 'smooth', block: 'center'}});
  toast('Caso preseleccionado: ' + useCaseId);
}}

const leadForm = $('#leadForm');
if (leadForm) {{
  leadForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/leads', Object.fromEntries(data));
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast(out.message);
    e.target.reset();
    refresh();
  }});
}}

const estimateForm = $('#estimateForm');
if (estimateForm) {{
  estimateForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const payload = Object.fromEntries(data);
    payload.interactions = parseInt(payload.interactions);
    payload.minutes_saved = parseInt(payload.minutes_saved);
    payload.hourly_cost = parseFloat(payload.hourly_cost);
    const out = await api('/api/estimate', payload);
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    const estimateResult = $('#estimateResult');
    if (estimateResult) {{
      estimateResult.innerHTML = `
        <p><strong>Caso:</strong> ${{out.use_case}}</p>
        <p><strong>Horas humanas ahorradas/mes:</strong> ${{out.human_hours_saved}}</p>
        <p><strong>Valor mensual generado:</strong> $${{out.monthly_value}}</p>
        <p><strong>Costo estimado de IA:</strong> $${{out.estimated_ai_cost}}</p>
        <p><strong>Precio mensual sugerido:</strong> <span class="metric">$${{out.suggested_price}}</span></p>
        <p><strong>Setup sugerido:</strong> $${{out.setup}}</p>
        <p class="muted">Margen aproximado: $${{out.margin_hint}}</p>
      `;
    }}
    toast('Estimación calculada');
    refresh();
  }});
}}

const assistantForm = $('#assistantForm');
if (assistantForm) {{
  assistantForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/assistant', Object.fromEntries(data));
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast('Respuesta recibida (' + out.source + ')');
    e.target.reset();
    refresh();
  }});
}}

const productForm = $('#productForm');
if (productForm) {{
  productForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const payload = Object.fromEntries(data);
    payload.quantity = parseInt(payload.quantity);
    if (payload.price) payload.price = parseFloat(payload.price);
    const out = await api('/api/inventory/product/add', payload);
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast(out.message);
    e.target.reset();
    refreshSmartStacks();
  }});
}}

const smartstacksForm = $('#smartstacksForm');
if (smartstacksForm) {{
  smartstacksForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/smartstacks/assistant', Object.fromEntries(data));
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast('Respuesta recibida');
    e.target.reset();
    refreshSmartStacks();
  }});
}}

const middlewareForm = $('#middlewareForm');
if (middlewareForm) {{
  middlewareForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/middleware/reply', Object.fromEntries(data));
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast(`Respuesta generada · ${{out.tokens_estimated}} tokens ≈ $${{out.cost_estimated}}`);
    e.target.reset();
    refreshMiddleware();
  }});
}}

const emailClassifyForm = $('#emailClassifyForm');
if (emailClassifyForm) {{
  emailClassifyForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/consulting/email/classify', Object.fromEntries(data));
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    const resultBox = $('#emailClassifyResult');
    if (resultBox) {{
      resultBox.innerHTML = `
        <div class="conversation">
          <p><span class="status-badge cat-${{out.category}}">${{out.category}}</span> <span class="status-badge priority-${{out.priority}}">prioridad ${{out.priority}}</span></p>
          <p><strong>Acción sugerida:</strong> ${{out.suggested_action}}</p>
        </div>
      `;
    }}
    toast('Correo clasificado');
    e.target.reset();
    refreshConsulting();
  }});
}}

const appointmentForm = $('#appointmentForm');
if (appointmentForm) {{
  appointmentForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/consulting/appointment/create', Object.fromEntries(data));
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast(out.message);
    e.target.reset();
    refreshConsulting();
  }});
}}

const invoiceForm = $('#invoiceForm');
if (invoiceForm) {{
  invoiceForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    
    const selectedProducts = [];
    document.querySelectorAll('.invoice-product-checkbox:checked').forEach(cb => {{
      const id = parseInt(cb.dataset.id);
      const qtyInput = document.querySelector(`.invoice-product-qty[data-id="${{id}}"]`);
      const quantity = parseInt(qtyInput ? qtyInput.value : 1);
      selectedProducts.push({{product_id: id, quantity: quantity}});
    }});
    
    if (!selectedProducts.length) {{
      toast('Selecciona al menos un producto');
      return;
    }}
    
    const data = {{
      customer_name: $('#invoiceCustomerName').value,
      customer_email: $('#invoiceCustomerEmail').value,
      customer_phone: $('#invoiceCustomerPhone').value,
      customer_rut: $('#invoiceCustomerRut').value,
      products: selectedProducts,
      payment_method: $('#invoicePaymentMethod').value,
      bank_account_id: parseInt($('#invoiceBankAccount').value)
    }};
    
    const out = await api('/api/invoice/create', data);
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    
    toast(out.message);
    invoiceForm.reset();
    refreshInvoices();
    refreshSmartStacks();
  }});
}}

const emailForm = $('#emailForm');
if (emailForm) {{
  emailForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const emails = Array.from(document.querySelectorAll('.lead-checkbox:checked')).map(cb => cb.value);
    if (!emails.length) {{ toast('Selecciona al menos un lead'); return; }}
    
    const subject = $('#emailSubject').value;
    const body = $('#emailBody').value;
    
    const out = await api('/api/email/campaign/create', {{
      subject: subject,
      body: body,
      recipient_emails: emails
    }});
    
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    
    if (confirm(`Campaña creada para ${{emails.length}} contactos. ¿Enviar ahora?`)) {{
      const sent = await api(`/api/email/campaign/${{out.campaign_id}}/send`, {{}});
      if (!sent.ok) {{ toast('Error: ' + sent.error); return; }}
      if (sent.failed > 0 && sent.errors && sent.errors.length) {{
        alert(`✓ ${{sent.sent}} enviados, ${{sent.failed}} fallos.\\n\\nDetalle de fallos:\\n` + sent.errors.join('\\n'));
      }} else {{
        toast(`✓ ${{sent.sent}} enviados, ${{sent.failed}} fallos`);
      }}
    }}
    
    emailForm.reset();
    refresh();
  }});
}}

const singleEmailForm = $('#singleEmailForm');
if (singleEmailForm) {{
  singleEmailForm.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const data = new FormData(e.target);
    const out = await api('/api/email/send', {{
      lead_id: parseInt(data.get('lead_id')),
      subject: data.get('subject'),
      body: data.get('body')
    }});
    
    if (!out.ok) {{ toast('Error: ' + out.error); return; }}
    toast(out.message);
    singleEmailForm.reset();
    refresh();
  }});
}}

// Inicialización
renderState();
refreshSmartStacks();
refreshBankAccounts();
loadProductsForInvoice();

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
            csv_data = export_leads_csv()
            file_response(self, csv_data, "leads.csv", "text/csv")
            return
        if parsed.path == "/api/leads/export/json":
            json_data = export_leads_json()
            file_response(self, json_data, "leads.json", "application/json")
            return
        if parsed.path == "/api/inventory/export/csv":
            csv_data = export_inventory_csv()
            file_response(self, csv_data, "inventory.csv", "text/csv")
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
            if parsed.path == "/api/inventory/product/update":
                result = update_inventory_product(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/inventory/product/delete":
                result = delete_inventory_product(payload)
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
                
            json_response(self, {"ok": False, "error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError:
            json_response(self, {"ok": False, "error": "JSON inválido"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            json_response(self, {"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), SabrinaHandler)
    print(f"Sabrina AI Lab listo en http://{HOST}:{PORT}")
    print(f"Base de datos: {DB_PATH}")
    print(f"Cuentas bancarias configuradas: {len(BANK_ACCOUNTS)}")
    print("Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
