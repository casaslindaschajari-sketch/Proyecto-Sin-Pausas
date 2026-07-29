#!/usr/bin/env python3
"""
Sabrina AI Lab - MVP web funcional con backend real.
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


# ============================================
# FUNCIONES PRINCIPALES DEL SERVIDOR
# ============================================

def add_inventory_product(payload: dict[str, Any]) -> dict[str, Any]:
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
    with db_connect() as conn:
        leads = rows_to_dicts(conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall())
    return json.dumps(leads, ensure_ascii=False, indent=2).encode("utf-8")


def export_inventory_csv() -> bytes:
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
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False, "Email no configurado."

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
# FUNCIONES DE FACTURACIÓN SIMPLIFICADAS
# ============================================

def generate_invoice_number() -> str:
    with db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM invoices").fetchone()["c"]
    return f"INV-{datetime.now().strftime('%Y%m')}-{count + 1:04d}"


def create_invoice(payload: dict[str, Any]) -> dict[str, Any]:
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

        tax = subtotal * 0.19
        total = subtotal + tax
        invoice_number = generate_invoice_number()
        payment_method = str(payload["payment_method"])
        bank_account_id = int(payload["bank_account_id"])

        with db_connect() as conn:
            bank_account = conn.execute(
                "SELECT * FROM bank_accounts WHERE id = ? AND active = 1",
                (bank_account_id,)
            ).fetchone()

            if not bank_account:
                return {"ok": False, "error": "Cuenta bancaria no válida o inactiva"}

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

        return {
            "ok": True,
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "message": f"Factura {invoice_number} creada exitosamente."
        }

    except ValueError as e:
        return {"ok": False, "error": f"Error en los datos: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": f"Error al crear la factura: {str(e)}"}


def get_invoices() -> dict[str, Any]:
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


def get_bank_accounts() -> dict[str, Any]:
    with db_connect() as conn:
        accounts = rows_to_dicts(
            conn.execute("SELECT * FROM bank_accounts WHERE active = 1 ORDER BY name").fetchall()
        )
    return {"ok": True, "bank_accounts": accounts}


def update_bank_account(payload: dict[str, Any]) -> dict[str, Any]:
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


# ============================================
# RENDER HTML - Versión simplificada (¡ARREGLADA!)
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
      font-family: system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #090b12;
      color: var(--text);
      min-height: 100vh;
      padding: 20px;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    header {{
      position: sticky; top: 0; z-index: 10;
      backdrop-filter: blur(18px);
      background: rgba(9,11,18,.72);
      border-bottom: 1px solid var(--line);
      padding: 10px 0;
    }}
    nav {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0; gap: 14px; }}
    .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 800; }}
    .logo {{ width: 38px; height: 38px; border-radius: 14px; background: linear-gradient(135deg, var(--brand), var(--brand2)); display:grid; place-items:center; }}
    .navlinks {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .navlinks a {{ text-decoration: none; color: var(--muted); font-size: 14px; padding: 8px 10px; border-radius: 999px; cursor: pointer; }}
    .navlinks a:hover, .navlinks a.active {{ background: var(--panel); color: var(--text); }}
    .hero {{ padding: 40px 0; }}
    h1 {{ font-size: clamp(36px, 5vw, 60px); margin: 10px 0; }}
    h2 {{ font-size: clamp(24px, 3vw, 36px); margin: 0 0 14px; }}
    h3 {{ margin: 0 0 8px; }}
    p {{ color: var(--muted); line-height: 1.65; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 24px; padding: 22px; }}
    .grid {{ display: grid; gap: 18px; }}
    .grid.two {{ grid-template-columns: repeat(2, 1fr); }}
    button, .btn {{
      border: 0; color: #07111d; background: linear-gradient(135deg, var(--brand2), #b4ffe8);
      padding: 12px 16px; border-radius: 14px; font-weight: 800; cursor: pointer;
      text-decoration: none; display: inline-flex; align-items:center; gap: 8px;
    }}
    button.secondary, .btn.secondary {{ background: var(--panel-strong); color: var(--text); border: 1px solid var(--line); }}
    section {{ padding: 30px 0; display: none; }}
    section.active {{ display: block; }}
    input, textarea, select {{
      width: 100%; background: rgba(0,0,0,.24); color: var(--text);
      border: 1px solid var(--line); border-radius: 14px; padding: 12px 13px;
      outline: none; font: inherit;
    }}
    textarea {{ min-height: 80px; resize: vertical; }}
    label {{ display:block; font-size: 13px; font-weight: 800; color: #dbe2f2; margin: 0 0 7px; }}
    .formgrid {{ display:grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .full {{ grid-column: 1 / -1; }}
    table {{ width:100%; border-collapse: collapse; }}
    th, td {{ text-align:left; padding: 10px; border-bottom: 1px solid var(--line); color: var(--muted); }}
    th {{ color: var(--text); background: rgba(255,255,255,.06); }}
    .conversation {{ background: rgba(0,0,0,.2); border-radius: 12px; padding: 14px; margin: 12px 0; border-left: 3px solid var(--brand2); }}
    .conversation.user {{ border-left-color: var(--brand); }}
    .conversation strong {{ color: var(--brand2); }}
    .conversation.user strong {{ color: var(--brand); }}
    .toast {{ position: fixed; right: 18px; bottom: 18px; background: #102018; color: #d9ffe8; border: 1px solid rgba(51,214,166,.38); padding: 12px 14px; border-radius: 14px; opacity:0; transform: translateY(100px); transition: all .3s ease; z-index: 999; }}
    .toast.show {{ opacity:1; transform: translateY(0); }}
    .muted {{ color: var(--muted); }}
    .tag {{ display:inline-flex; padding: 4px 9px; border-radius: 999px; background: rgba(155,140,255,.13); border: 1px solid rgba(155,140,255,.28); color: #d8d2ff; font-size: 12px; font-weight: 600; }}
    .qoption {{
      display:flex; align-items:center; gap: 10px; padding: 10px 14px;
      border: 1px solid var(--line); border-radius: 14px; margin-bottom: 8px;
      cursor: pointer;
    }}
    .qoption:hover {{ background: var(--panel-strong); }}
    .qoption input {{ width: auto; accent-color: var(--brand2); }}
    @media (max-width: 700px) {{
      .grid.two {{ grid-template-columns: 1fr; }}
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
          <a onclick="showSection('leads')">Leads</a>
          <a onclick="showSection('estimator')">Calculadora</a>
          <a onclick="showSection('smartstacks')">SmartStacks</a>
          <a onclick="showSection('invoicing')">Facturación</a>
        </div>
      </nav>
    </header>

    <main>
      <section id="dashboard" class="active">
        <div class="hero">
          <h1>Sabrina AI Lab</h1>
          <p>Gestión integral de leads, inventario y facturación con IA.</p>
          <div class="card" style="max-width:400px; margin-top:20px;">
            <p>✅ Base de datos: Activa</p>
            <p>Facturas: <span id="invoiceCount">0</span></p>
          </div>
        </div>
      </section>

      <section id="leads">
        <h2>📋 Leads</h2>
        <div class="grid two">
          <div class="card">
            <h3>Últimos leads</h3>
            <div style="max-height:300px; overflow:auto;">
              <table><thead><tr><th>Negocio</th><th>Email</th><th>Caso</th></tr></thead><tbody id="leadRows"></tbody></table>
            </div>
          </div>
          <div class="card">
            <h3>Registrar lead</h3>
            <form id="leadForm" class="formgrid">
              <div class="full"><label>Nombre</label><input name="name" required></div>
              <div class="full"><label>Negocio</label><input name="business" required></div>
              <div class="full"><label>Email</label><input name="email" type="email" required></div>
              <div class="full"><label>Caso</label><select name="use_case"><option>smartstacks</option><option>middleware</option><option>llave-en-mano</option></select></div>
              <div class="full"><label>Presupuesto</label><input name="budget" required></div>
              <div class="full"><label>Dolor</label><textarea name="pain" required></textarea></div>
              <div class="full"><button type="submit">Guardar</button></div>
            </form>
          </div>
        </div>
      </section>

      <section id="estimator">
        <h2>🧮 Calculadora</h2>
        <div class="grid two">
          <div class="card">
            <form id="estimateForm" class="formgrid">
              <div class="full"><label>Caso</label><select name="use_case"><option>smartstacks</option><option>middleware</option><option>llave-en-mano</option></select></div>
              <div><label>Interacciones</label><input name="interactions" type="number" min="1" value="1500"></div>
              <div><label>Minutos ahorrados</label><input name="minutes_saved" type="number" min="1" value="4"></div>
              <div class="full"><label>Costo horario (USD)</label><input name="hourly_cost" type="number" step="0.1" value="9.5"></div>
              <div class="full"><button type="submit">Calcular</button></div>
            </form>
          </div>
          <div class="card">
            <h3>Resultado</h3>
            <div id="estimateResult"><p class="muted">Completa el formulario.</p></div>
          </div>
        </div>
      </section>

      <section id="smartstacks">
        <h2>🏪 SmartStacks</h2>
        <div class="grid two">
          <div class="card">
            <h3>Inventario</h3>
            <div style="max-height:300px; overflow:auto;">
              <table><thead><tr><th>Código</th><th>Nombre</th><th>Stock</th></tr></thead><tbody id="productRows"></tbody></table>
            </div>
          </div>
          <div class="card">
            <h3>Agregar producto</h3>
            <form id="productForm" class="formgrid">
              <div class="full"><label>Código</label><input name="code" required></div>
              <div class="full"><label>Nombre</label><input name="name" required></div>
              <div><label>Cantidad</label><input name="quantity" type="number" min="0" required></div>
              <div><label>Precio</label><input name="price" type="number" step="0.01" min="0"></div>
              <div class="full"><label>Descripción</label><textarea name="description"></textarea></div>
              <div class="full"><button type="submit">Guardar</button></div>
            </form>
          </div>
        </div>
      </section>

      <section id="invoicing">
        <h2>🧾 Facturación</h2>
        <div class="grid two">
          <div class="card">
            <h3>Crear factura</h3>
            <form id="invoiceForm" class="formgrid">
              <div class="full"><label>Cliente</label><input id="invoiceCustomerName" name="customer_name" required></div>
              <div class="full"><label>Email</label><input id="invoiceCustomerEmail" name="customer_email" type="email" required></div>
              <div class="full"><label>Seleccionar productos</label>
                <div id="invoiceProductSelection" style="max-height:150px; overflow-y:auto; background:rgba(0,0,0,.2); border-radius:12px; padding:12px;"></div>
              </div>
              <div class="full"><label>Método de pago</label>
                <select id="invoicePaymentMethod" name="payment_method">
                  <option value="transferencia">Transferencia</option>
                  <option value="tarjeta">Tarjeta</option>
                </select>
              </div>
              <div class="full"><label>Cuenta bancaria</label>
                <select id="invoiceBankAccount" name="bank_account_id"></select>
              </div>
              <div class="full"><button type="submit">Crear factura</button></div>
            </form>
          </div>
          <div class="card">
            <h3>Facturas recientes</h3>
            <div style="max-height:400px; overflow:auto;">
              <table><thead><tr><th>N°</th><th>Cliente</th><th>Total</th><th>Estado</th></tr></thead><tbody id="invoiceRows"></tbody></table>
            </div>
          </div>
        </div>
      </section>

    </main>

    <footer style="border-top:1px solid var(--line); margin-top:30px; padding:20px 0; color:var(--muted);">
      Sabrina AI Lab · python3 app.py
    </footer>
  </div>

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
}}

function renderState() {{
  const invoiceCount = $('#invoiceCount');
  if (invoiceCount) invoiceCount.textContent = state.metrics.invoices || 0;
  
  const leadRows = $('#leadRows');
  if (leadRows) {{
    leadRows.innerHTML = state.leads && state.leads.length ? state.leads.map(l => `
      <tr>
        <td>${{l.business}}</td>
        <td>${{l.email}}</td>
        <td>${{l.use_case}}</td>
      </tr>
    `).join('') : '<tr><td colspan="3">Sin leads</td></tr>';
  }}
}}

function renderSmartStacks() {{
  const productRows = $('#productRows');
  if (productRows) {{
    productRows.innerHTML = smartstacksState.products && smartstacksState.products.length ? smartstacksState.products.map(p => `
      <tr>
        <td><strong>${{p.code}}</strong></td>
        <td>${{p.name}}</td>
        <td>${{p.quantity}}</td>
      </tr>
    `).join('') : '<tr><td colspan="3">Sin productos</td></tr>';
  }}
}}

async function refresh() {{
  try {{
    const res = await fetch('/api/state');
    const newState = await res.json();
    Object.assign(state, newState);
    renderState();
  }} catch (e) {{
    console.error(e);
  }}
}}

async function refreshSmartStacks() {{
  try {{
    const res = await fetch('/api/smartstacks/state');
    smartstacksState = await res.json();
    renderSmartStacks();
  }} catch (e) {{
    console.error(e);
  }}
}}

async function refreshInvoices() {{
  try {{
    const res = await fetch('/api/invoices');
    const data = await res.json();
    if (!data.ok) return;
    const invoiceRows = $('#invoiceRows');
    if (invoiceRows) {{
      invoiceRows.innerHTML = data.invoices && data.invoices.length ? data.invoices.map(inv => `
        <tr>
          <td><strong>${{inv.invoice_number}}</strong></td>
          <td>${{inv.customer_name}}</td>
          <td>$${{inv.total.toFixed(2)}}</td>
          <td><span style="background:rgba(51,214,166,.15);color:var(--brand2);padding:2px 8px;border-radius:999px;">${{inv.status}}</span></td>
        </tr>
      `).join('') : '<tr><td colspan="4">Sin facturas</td></tr>';
    }}
  }} catch (e) {{
    console.error(e);
  }}
}}

async function refreshBankAccounts() {{
  try {{
    const res = await fetch('/api/bank-accounts');
    const data = await res.json();
    if (!data.ok) return;
    const select = $('#invoiceBankAccount');
    if (select) {{
      select.innerHTML = data.bank_accounts && data.bank_accounts.length ? data.bank_accounts.map(acc => `
        <option value="${{acc.id}}">${{acc.name}}</option>
      `).join('') : '<option>No hay cuentas</option>';
    }}
  }} catch (e) {{
    console.error(e);
  }}
}}

async function loadProductsForInvoice() {{
  try {{
    const res = await fetch('/api/smartstacks/state');
    const data = await res.json();
    const container = $('#invoiceProductSelection');
    if (!container) return;
    if (!data.products || !data.products.length) {{
      container.innerHTML = '<p class="muted">Sin productos</p>';
      return;
    }}
    container.innerHTML = data.products.map(p => `
      <div style="display:flex;align-items:center;gap:10px;padding:4px 0;border-bottom:1px solid var(--line);">
        <input type="checkbox" class="invoice-product-checkbox" data-id="${{p.id}}">
        <span><strong>${{p.code}}</strong> ${{p.name}}</span>
        <span style="color:var(--muted);font-size:12px;">$${{p.price || 0}}</span>
        <input type="number" class="invoice-product-qty" data-id="${{p.id}}" value="1" min="1" style="width:50px;padding:4px;">
      </div>
    `).join('');
  }} catch (e) {{
    console.error(e);
  }}
}}

// Lead form
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

// Estimate form
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
    const result = $('#estimateResult');
    if (result) {{
      result.innerHTML = `
        <p><strong>Caso:</strong> ${{out.use_case}}</p>
        <p><strong>Horas ahorradas:</strong> ${{out.human_hours_saved}}</p>
        <p><strong>Valor mensual:</strong> $${{out.monthly_value}}</p>
        <p><strong>Precio sugerido:</strong> <span style="font-size:24px;font-weight:900;">$${{out.suggested_price}}</span></p>
      `;
    }}
    toast('Estimación calculada');
    refresh();
  }});
}}

// Product form
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

// Invoice form
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
    if (!selectedProducts.length) {{ toast('Selecciona al menos un producto'); return; }}
    
    const data = {{
      customer_name: $('#invoiceCustomerName').value,
      customer_email: $('#invoiceCustomerEmail').value,
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

// Inicialización
renderState();
refreshSmartStacks();
refreshBankAccounts();
loadProductsForInvoice();
refreshInvoices();

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
        print(f"[{now_iso()}] {fmt % args}")

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
        if parsed.path == "/api/invoices":
            json_response(self, get_invoices())
            return
        if parsed.path == "/api/bank-accounts":
            json_response(self, get_bank_accounts())
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
            if parsed.path == "/api/invoice/create":
                result = create_invoice(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            if parsed.path == "/api/bank-account/update":
                result = update_bank_account(payload)
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
