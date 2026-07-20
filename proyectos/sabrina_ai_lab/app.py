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
HOST = os.environ.get("SABRINA_HOST", "127.0.0.1")
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

    # Aproximación comercial: 900 tokens promedio por interacción y costo conservador proxy.
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
            conn.execute("SELECT code, name, quantity, price, description FROM inventory_products ORDER BY name").fetchall()
        )


def format_inventory_context(products: list[dict[str, Any]]) -> str:
    """Convierte la lista de productos en un bloque de texto para dar contexto al modelo."""
    if not products:
        return "El inventario está vacío."

    lines = ["INVENTARIO ACTUAL:\n"]
    for p in products:
        lines.append(f"- Código {p['code']}: {p['name']} (Stock: {p['quantity']} unidades, Precio: ${p['price'] or 'N/A'})")
        if p['description']:
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
    "referencia", "a", "en", "con", "para", "y", "o", "me", "nos", "si", "no", "hola", "buenas",
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


def _term_matches(term: str, haystack: str) -> bool:
    """Compara un término de búsqueda contra el texto del producto, tolerando plurales simples."""
    if term in haystack:
        return True
    for suffix in ("es", "s"):
        if term.endswith(suffix) and len(term) - len(suffix) >= 3:
            stem = term[: -len(suffix)]
            if stem in haystack:
                return True
    return False


def _search_inventory_products(products: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    if not terms:
        return []
    matches = []
    for p in products:
        haystack = _normalize_text(f"{p['code']} {p['name']} {p.get('description') or ''}")
        if all(_term_matches(term, haystack) for term in terms):
            matches.append(p)
    return matches


def local_inventory_answer(question: str, products: list[dict[str, Any]], channel: str) -> str:
    """Respuesta local simulada basada en inventario, con búsqueda real por producto."""
    if not products:
        return "Nuestro inventario está vacío por ahora. Agrega productos desde el panel de SmartStacks para poder responder consultas."

    terms = _extract_search_terms(question)

    # Pregunta genérica ("qué tienes", "qué hay disponible") sin producto específico -> catálogo completo.
    if not terms:
        return f"Claro, este es nuestro catálogo actual:\n\n{format_inventory_context(products)}\n\n¿Buscas algo en particular?"

    matches = _search_inventory_products(products, terms)

    if not matches:
        catalog_names = ", ".join(p["name"] for p in products)
        return (
            f"No tenemos '{' '.join(terms)}' en nuestro inventario actual. "
            f"Estos son los productos que sí tenemos disponibles: {catalog_names}."
        )

    lines = [f"Sí, tenemos {len(matches)} producto(s) que coinciden con '{' '.join(terms)}':\n"]
    for p in matches:
        stock_line = f"Stock: {p['quantity']} unidades" if p["quantity"] > 0 else "Sin stock por el momento"
        price_line = f"Precio: ${p['price']}" if p["price"] else "Precio: no definido"
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
            success, msg = send_email(email, campaign["subject"], campaign["body"])
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
    }}
    a {{ color: inherit; }}
    .wrap {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; }}
    header {{
      position: sticky; top: 0; z-index: 10;
      backdrop-filter: blur(18px);
      background: rgba(9,11,18,.72);
      border-bottom: 1px solid var(--line);
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
    .conversation.user {{ border-left-color: var(--brand); }}
    .conversation strong {{ color: var(--brand2); }}
    .conversation.user strong {{ color: var(--brand); }}
    footer {{ border-top: 1px solid var(--line); margin-top: 36px; padding: 24px 0 36px; color: var(--muted); }}
    .toast {{ position: fixed; right: 18px; bottom: 18px; background: #102018; color: #d9ffe8; border: 1px solid rgba(51,214,166,.38); padding: 12px 14px; border-radius: 14px; opacity:0; transform: translateY(100px); transition: all .3s ease; z-index: 999; }}
    .toast.show {{ opacity:1; transform: translateY(0); }}
    .checkbox-group {{ display:flex; gap: 8px; flex-wrap:wrap; margin: 8px 0; }}
    .checkbox-group label {{ display:flex; align-items:center; gap: 6px; margin: 0; font-weight: normal; color: var(--muted); }}
    .checkbox-group input[type="checkbox"] {{ width: auto; }}
    @media (max-width: 850px) {{
      .hero, .grid.two {{ grid-template-columns: 1fr; }}
      .navlinks {{ display:none; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <nav>
        <div class="brand"><div class="logo">✦</div><span>Sabrina AI Lab</span></div>
        <div class="navlinks">
          <a onclick="showSection('dashboard')" class="active">Dashboard</a>
          <a onclick="showSection('leads')">Leads</a>
          <a onclick="showSection('estimator')">Calculadora</a>
          <a onclick="showSection('assistant')">Asistente</a>
          <a onclick="showSection('smartstacks')">SmartStacks</a>
          <a onclick="showSection('campaigns')">Campañas</a>
        </div>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <section id="dashboard" class="active">
      <div class="hero">
        <div>
          <span class="eyebrow">✨ SISTEMA INTEGRAL</span>
          <h1>Sabrina AI Lab</h1>
          <p>
            Gestión integral de leads, inventario y asistentes de IA para comercios.
            Incluye automación de email, inventario en tiempo real y consultor estratégico.
          </p>
        </div>
        <div class="card">
          <h3>Estado del Sistema</h3>
          <div style="margin: 12px 0; font-size: 12px; color: var(--muted);">
            <p>✓ Base de datos: Activa</p>
            <p id="modeStatus">Cargando...</p>
          </div>
        </div>
      </div>
    </section>

    <section id="leads">
      <h2>📋 Gestión de Leads</h2>
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

    <section id="campaigns">
      <h2>📧 Campañas de Email</h2>
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
  </main>

  <footer>
    <div class="wrap">
      <strong>Sabrina AI Lab</strong> · Ejecuta: <code>python3 proyectos/sabrina_ai_lab/app.py</code>
    </div>
  </footer>

  <div class="toast" id="toast"></div>

<script>
const state = {state_json};
let smartstacksState = {{}};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const api = async (url, data) => {{
  const res = await fetch(url, {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data)}});
  return await res.json();
}};
const toast = (msg) => {{
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}};

function showSection(id) {{
  $$('section').forEach(s => s.classList.remove('active'));
  $$('.navlinks a').forEach(a => a.classList.remove('active'));
  $(`#${{id}}`).classList.add('active');
  event.target.classList.add('active');
}}

function renderState() {{
  $('#modeStatus').textContent = state.integrations.email_ready ? 
    '✓ Email configurado' : 
    '⚠ Email no configurado';
    
  $('#leadRows').innerHTML = state.leads.length ? state.leads.map(l => `
    <tr>
      <td>${{new Date(l.created_at).toLocaleString()}}</td>
      <td><strong>${{l.business}}</strong></td>
      <td>${{l.email}}</td>
      <td>${{l.use_case}}</td>
    </tr>
  `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin leads registrados</td></tr>';
  
  $('#leadCheckboxes').innerHTML = state.leads.length ? state.leads.map(l => `
    <label><input type="checkbox" class="lead-checkbox" value="${{l.email}}"> <strong>${{l.business}}</strong> (${{l.email}})</label>
  `).join('<br>') : '<p style="color:var(--muted);">Registra leads primero</p>';
  
  $('#singleLeadSelect').innerHTML = state.leads.length ? state.leads.map(l => `
    <option value="${{l.id}}">${{l.business}} - ${{l.name}}</option>
  `).join('') : '<option>Sin leads</option>';

  $('#estimateRows').innerHTML = state.estimates.length ? state.estimates.map(e => `
    <tr>
      <td>${{e.use_case}}</td>
      <td>${{e.interactions}}</td>
      <td>$${{e.monthly_value}}</td>
      <td>$${{e.suggested_price}}</td>
    </tr>
  `).join('') : '<tr><td colspan="4" style="text-align:center;">Sin cálculos aún</td></tr>';

  $('#assistantHistory').innerHTML = state.assistant_events.length ? state.assistant_events.slice().reverse().map(ev => `
    <div class="conversation user"><strong>Tú (${{ev.channel}}):</strong><p>${{ev.question}}</p></div>
    <div class="conversation"><strong>Asistente · ${{ev.source}}:</strong><p>${{ev.answer.replace(/\\n/g, '<br>')}}</p></div>
  `).join('') : '<p class="muted">Sin consultas aún.</p>';
}}

function renderSmartStacks() {{
  $('#productCount').textContent = smartstacksState.metrics.total_products;
  $('#totalStock').textContent = smartstacksState.metrics.total_stock;
  
  $('#productRows').innerHTML = smartstacksState.products.length ? smartstacksState.products.map(p => `
    <tr>
      <td><strong>${{p.code}}</strong></td>
      <td>${{p.name}}</td>
      <td>${{p.quantity}}</td>
      <td>${{p.price ? '$' + p.price : 'N/A'}}</td>
      <td><button class="secondary" onclick="deleteProduct(${{p.id}})" style="padding: 6px 8px; font-size: 12px;">Eliminar</button></td>
    </tr>
  `).join('') : '<tr><td colspan="5" style="text-align:center;">Sin productos</td></tr>';
  
  $('#conversationHistory').innerHTML = smartstacksState.conversations.length ? smartstacksState.conversations.reverse().map((c, i) => `
    <div class="conversation ${{i % 2 === 0 ? 'user' : 'assistant'}}">
      <strong>${{i % 2 === 0 ? 'Tú' : 'Asistente'}}:</strong>
      <p>${{i % 2 === 0 ? c.question : c.answer}}</p>
    </div>
  `).join('') : '<p style="color: var(--muted); text-align: center;">Sin conversaciones aún</p>';
}}

async function refresh() {{
  const res = await fetch('/api/state');
  const newState = await res.json();
  Object.assign(state, newState);
  renderState();
}}

async function refreshSmartStacks() {{
  const res = await fetch('/api/smartstacks/state');
  smartstacksState = await res.json();
  renderSmartStacks();
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

$('#leadForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/leads', Object.fromEntries(data));
  if (!out.ok) {{ toast('Error: ' + out.error); return; }}
  toast(out.message);
  e.target.reset();
  refresh();
}});

$('#estimateForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const data = new FormData(e.target);
  const payload = Object.fromEntries(data);
  payload.interactions = parseInt(payload.interactions);
  payload.minutes_saved = parseInt(payload.minutes_saved);
  payload.hourly_cost = parseFloat(payload.hourly_cost);
  const out = await api('/api/estimate', payload);
  if (!out.ok) {{ toast('Error: ' + out.error); return; }}
  $('#estimateResult').innerHTML = `
    <p><strong>Caso:</strong> ${{out.use_case}}</p>
    <p><strong>Horas humanas ahorradas/mes:</strong> ${{out.human_hours_saved}}</p>
    <p><strong>Valor mensual generado:</strong> $${{out.monthly_value}}</p>
    <p><strong>Costo estimado de IA:</strong> $${{out.estimated_ai_cost}}</p>
    <p><strong>Precio mensual sugerido:</strong> <span class="metric">$${{out.suggested_price}}</span></p>
    <p><strong>Setup sugerido:</strong> $${{out.setup}}</p>
    <p class="muted">Margen aproximado: $${{out.margin_hint}}</p>
  `;
  toast('Estimación calculada');
  refresh();
}});

$('#assistantForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/assistant', Object.fromEntries(data));
  if (!out.ok) {{ toast('Error: ' + out.error); return; }}
  toast('Respuesta recibida (' + out.source + ')');
  e.target.reset();
  refresh();
}});

$('#productForm').addEventListener('submit', async (e) => {{
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

$('#smartstacksForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/smartstacks/assistant', Object.fromEntries(data));
  if (!out.ok) {{ toast('Error: ' + out.error); return; }}
  toast('Respuesta recibida');
  e.target.reset();
  refreshSmartStacks();
}});

$('#emailForm').addEventListener('submit', async (e) => {{
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
    toast(`✓ ${{sent.sent}} enviados, ${{sent.failed}} fallos`);
  }}
  
  e.target.reset();
  refresh();
}});

$('#singleEmailForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const data = new FormData(e.target);
  const out = await api('/api/email/send', {{
    lead_id: parseInt(data.get('lead_id')),
    subject: data.get('subject'),
    body: data.get('body')
  }});
  
  if (!out.ok) {{ toast('Error: ' + out.error); return; }}
  toast(out.message);
  e.target.reset();
  refresh();
}});

renderState();
refreshSmartStacks();
setInterval(refreshSmartStacks, 5000);
</script>
</body>
</html>"""


class SabrinaHandler(BaseHTTPRequestHandler):
    server_version = "SabrinaAILab/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{now_iso()}] {self.address_string()} {fmt % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html_response(self, render_index())
            return
        if parsed.path == "/api/state":
            json_response(self, get_dashboard_state())
            return
        if parsed.path == "/api/smartstacks/state":
            json_response(self, get_smartstacks_state())
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
    print("Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
