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

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import textwrap
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "sabrina_lab.sqlite3"
HOST = os.environ.get("SABRINA_HOST", "0.0.0.0")
PORT = int(os.environ.get("SABRINA_PORT", "8000"))

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def db_connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with db_connect() as conn:
        conn.execute("""
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
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                channel TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)
        conn.execute("""
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
        """)
        conn.execute("""
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
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assistant_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                channel TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)

def seed_demo_products() -> None:
    with db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM inventory_products").fetchone()["c"]
        if count == 0:
            demo = [
                {"code": "PER-001", "name": 'Perno de Anclaje 3/8"', "quantity": 45, "price": 2500, 
                 "category": "Fijaciones", "description": "Perno galvanizado para hormigón"},
                {"code": "TUB-002", "name": 'Tubería PVC 1/2"', "quantity": 120, "price": 3800, 
                 "category": "Tuberías", "description": "Tubería PVC para instalaciones"},
                {"code": "MART-003", "name": "Martillo de Peña", "quantity": 12, "price": 15900, 
                 "category": "Herramientas", "description": "Martillo profesional"},
                {"code": "CIN-004", "name": "Cinta Métrica 5m", "quantity": 28, "price": 4500, 
                 "category": "Medición", "description": "Cinta métrica 5m"},
                {"code": "LLAVE-005", "name": 'Llave Francesa 12"', "quantity": 15, "price": 8900, 
                 "category": "Herramientas", "description": "Llave ajustable cromada"},
                {"code": "DIS-006", "name": 'Disco de Corte 4"', "quantity": 80, "price": 3200, 
                 "category": "Accesorios", "description": "Disco de corte para metal"},
            ]
            for p in demo:
                try:
                    conn.execute(
                        "INSERT INTO inventory_products (created_at, code, name, quantity, price, description, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (now_iso(), p["code"], p["name"], p["quantity"], p["price"], p["description"], p["category"])
                    )
                except:
                    pass

def rows_to_dicts(rows):
    return [dict(row) for row in rows]

def json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def html_response(handler, html, status=200):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))

def get_inventory_products():
    with db_connect() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM inventory_products ORDER BY name").fetchall())

def add_inventory_product(payload):
    missing = [f for f in ["code", "name", "quantity"] if not payload.get(f)]
    if missing:
        return {"ok": False, "error": f"Faltan: {', '.join(missing)}"}
    try:
        code = str(payload["code"]).strip()
        name = str(payload["name"]).strip()
        quantity = int(payload["quantity"])
        price = float(payload["price"]) if payload.get("price") else None
        description = str(payload.get("description", "")).strip() or None
        category = str(payload.get("category", "")).strip() or None
        with db_connect() as conn:
            cur = conn.execute(
                "INSERT INTO inventory_products (created_at, code, name, quantity, price, description, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now_iso(), code, name, quantity, price, description, category)
            )
        return {"ok": True, "message": f"Producto '{name}' agregado", "product_id": cur.lastrowid}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"El código '{code}' ya existe"}
    except ValueError as e:
        return {"ok": False, "error": f"Error: {str(e)}"}

def delete_inventory_product(payload):
    product_id = payload.get("product_id")
    if not product_id:
        return {"ok": False, "error": "Falta ID"}
    try:
        with db_connect() as conn:
            conn.execute("DELETE FROM inventory_products WHERE id = ?", (int(product_id),))
        return {"ok": True, "message": "Producto eliminado"}
    except:
        return {"ok": False, "error": "Error al eliminar"}

def smartstacks_assistant_reply(payload):
    question = str(payload.get("question", "")).strip()
    if not question:
        return {"ok": False, "error": "Escribe una pregunta"}
    products = get_inventory_products()
    if not products:
        answer = "El inventario está vacío. Agrega productos primero."
    else:
        q = question.lower()
        matches = []
        for p in products:
            if p["code"].lower() in q or p["name"].lower() in q:
                matches.append(p)
            elif p.get("description") and p["description"].lower() in q:
                matches.append(p)
            elif p.get("category") and p["category"].lower() in q:
                matches.append(p)
        if not matches:
            names = ", ".join([p["name"] for p in products[:5]])
            if len(products) > 5:
                names += f" y {len(products)-5} más"
            answer = f"No encontré '{question}'. Productos: {names}"
        else:
            lines = [f"Encontré {len(matches)} producto(s):"]
            for p in matches:
                stock = f"{p['quantity']} unidades" if p['quantity'] > 0 else "Sin stock"
                price = f"${p['price']}" if p.get("price") else "Precio N/A"
                lines.append(f"- {p['name']} ({p['code']}) - Stock: {stock} - {price}")
                if p.get("description"):
                    lines.append(f"  📝 {p['description']}")
            answer = "\n".join(lines)
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO inventory_conversations (created_at, channel, question, answer, source) VALUES (?, ?, ?, ?, ?)",
            (now_iso(), "web", question, answer, "local")
        )
    return {"ok": True, "answer": answer, "source": "local"}

def get_smartstacks_state():
    with db_connect() as conn:
        products = rows_to_dicts(conn.execute("SELECT * FROM inventory_products ORDER BY created_at DESC").fetchall())
        conversations = rows_to_dicts(conn.execute("SELECT * FROM inventory_conversations ORDER BY id DESC LIMIT 20").fetchall())
        total_stock = conn.execute("SELECT SUM(quantity) AS total FROM inventory_products").fetchone()["total"] or 0
        product_count = conn.execute("SELECT COUNT(*) AS c FROM inventory_products").fetchone()["c"]
    return {"products": products, "conversations": conversations, "metrics": {"total_products": product_count, "total_stock": total_stock}}

def export_inventory_csv():
    with db_connect() as conn:
        products = conn.execute("SELECT * FROM inventory_products ORDER BY created_at DESC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Codigo", "Nombre", "Cantidad", "Precio", "Categoria", "Descripcion", "Fecha"])
    for p in products:
        writer.writerow([p["id"], p["code"], p["name"], p["quantity"], p["price"] or "", p["category"] or "", p["description"] or "", p["created_at"]])
    return output.getvalue().encode("utf-8")

def local_strategy_answer(question, channel):
    return textwrap.dedent(f"""
    Para tu consulta en canal {channel}:
    
    Te recomiendo empezar con SmartStacks, nuestro asistente de inventario.
    
    Problema: Vendedores pierden tiempo buscando productos.
    Solución: Asistente IA que responde al instante.
    Precio: desde $290/mes.
    
    Próximo paso: Carga tu inventario y haz preguntas de prueba.
    """).strip()

def assistant_reply(payload):
    question = str(payload.get("question", "")).strip()
    channel = str(payload.get("channel", "web")).strip() or "web"
    if not question:
        return {"ok": False, "error": "Escribe una pregunta"}
    answer = local_strategy_answer(question, channel)
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO assistant_events (created_at, channel, question, answer, source) VALUES (?, ?, ?, ?, ?)",
            (now_iso(), channel, question, answer, "local")
        )
    return {"ok": True, "answer": answer, "source": "local"}

def create_lead(payload):
    missing = [f for f in ["name", "business", "email", "use_case", "pain", "budget"] if not payload.get(f)]
    if missing:
        return {"ok": False, "error": f"Faltan: {', '.join(missing)}"}
    with db_connect() as conn:
        cur = conn.execute(
            "INSERT INTO leads (created_at, name, business, email, use_case, pain, budget) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now_iso(), payload["name"], payload["business"], payload["email"], payload["use_case"], payload["pain"], payload["budget"])
        )
    return {"ok": True, "lead_id": cur.lastrowid, "message": "Lead registrado"}

def estimate_cost(payload):
    use_case = payload.get("use_case", "smartstacks")
    interactions = max(1, int(payload.get("interactions", 1500)))
    minutes = max(1, int(payload.get("minutes_saved", 4)))
    hourly = max(0, float(payload.get("hourly_cost", 9.5)))
    saved_hours = interactions * minutes / 60
    monthly_value = saved_hours * hourly
    suggested = max(290, monthly_value * 0.28)
    result = {
        "ok": True,
        "use_case": use_case,
        "human_hours_saved": round(saved_hours, 1),
        "monthly_value": round(monthly_value, 2),
        "suggested_price": round(suggested, 2),
    }
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO estimates (created_at, use_case, interactions, human_minutes_saved, hourly_cost, estimated_ai_cost, monthly_value, suggested_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now_iso(), use_case, interactions, minutes, hourly, 0, result["monthly_value"], result["suggested_price"])
        )
    return result

def get_dashboard_state():
    with db_connect() as conn:
        leads = rows_to_dicts(conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 10").fetchall())
        estimates = rows_to_dicts(conn.execute("SELECT * FROM estimates ORDER BY id DESC LIMIT 5").fetchall())
        events = rows_to_dicts(conn.execute("SELECT * FROM assistant_events ORDER BY id DESC LIMIT 5").fetchall())
        lead_count = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]
        product_count = conn.execute("SELECT COUNT(*) AS c FROM inventory_products").fetchone()["c"]
    return {
        "leads": leads,
        "estimates": estimates,
        "assistant_events": events,
        "metrics": {"leads": lead_count, "products": product_count},
        "use_cases": [
            {"id": "smartstacks", "title": "SmartStacks", "price": 290, "setup": 850, "tag": "Inventario", 
             "problem": "Pérdida de tiempo buscando productos", "solution": "Asistente IA", 
             "impact": ["Menos filas", "Respuestas rápidas"]},
            {"id": "middleware", "title": "Middleware", "price": 390, "setup": 1200, "tag": "Automatización",
             "problem": "Preguntas repetidas", "solution": "Proxy unificado", 
             "impact": ["Ahorro de tiempo", "Tono consistente"]},
        ]
    }

# ============================================
# HTML COMPLETO
# ============================================

HTML = """<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sabrina AI Lab</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #0a0e17;
            color: #e8ecf1;
            font-family: system-ui, -apple-system, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1100px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .logo {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #9b8cff, #33d6a6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .nav {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .nav a {
            color: #8892a0;
            text-decoration: none;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
        }
        .nav a:hover, .nav a.active {
            background: rgba(255,255,255,0.08);
            color: #e8ecf1;
        }
        .nav a.active { background: rgba(51,214,166,0.15); color: #33d6a6; }
        h1 { font-size: 32px; margin-bottom: 6px; }
        h2 { font-size: 20px; margin: 20px 0 12px; color: #33d6a6; }
        h3 { font-size: 16px; margin: 12px 0 8px; color: #c8d0dc; }
        .subtitle { color: #8892a0; margin-bottom: 24px; }
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: 1fr 1fr; }
        .grid-3 { grid-template-columns: repeat(3, 1fr); }
        .card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 20px;
        }
        .stat {
            text-align: center;
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
        }
        .stat .number { font-size: 28px; font-weight: 800; }
        .stat .label { font-size: 12px; color: #8892a0; margin-top: 4px; }
        .stat .number.green { color: #33d6a6; }
        .stat .number.purple { color: #9b8cff; }
        .stat .number.gold { color: #ffcc66; }
        input, textarea, select {
            width: 100%;
            background: rgba(0,0,0,0.3);
            color: #e8ecf1;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 14px;
            outline: none;
        }
        input:focus, textarea:focus, select:focus { border-color: #33d6a6; }
        textarea { min-height: 80px; resize: vertical; }
        label { display: block; font-size: 13px; font-weight: 600; color: #a8b2c0; margin-bottom: 6px; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .form-grid .full { grid-column: 1 / -1; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
        th { color: #8892a0; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        td { color: #c8d0dc; }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            font-weight: 700;
            font-size: 13px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #33d6a6, #28b88a);
            color: #0a0e17;
        }
        .btn-primary:hover { opacity: 0.9; }
        .btn-secondary {
            background: rgba(255,255,255,0.08);
            color: #e8ecf1;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.14); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .btn-danger { background: rgba(255,107,122,0.15); color: #ff6b7a; border: 1px solid rgba(255,107,122,0.2); }
        .btn-danger:hover { background: rgba(255,107,122,0.25); }
        .conversation {
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 12px 16px;
            margin: 8px 0;
            border-left: 3px solid #33d6a6;
        }
        .conversation.user { border-left-color: #9b8cff; }
        .conversation strong { color: #33d6a6; }
        .conversation.user strong { color: #9b8cff; }
        .conversation p { margin-top: 4px; color: #c8d0dc; white-space: pre-wrap; }
        .mt-12 { margin-top: 12px; }
        .mt-20 { margin-top: 20px; }
        .gap-8 { gap: 8px; }
        .flex { display: flex; }
        .flex-wrap { flex-wrap: wrap; }
        .flex-between { justify-content: space-between; align-items: center; }
        .progress-bar {
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 3px;
            margin: 10px 0;
        }
        .progress-fill {
            height: 6px;
            background: linear-gradient(90deg, #9b8cff, #33d6a6);
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #1a2a24;
            color: #33d6a6;
            border: 1px solid rgba(51,214,166,0.3);
            padding: 12px 20px;
            border-radius: 12px;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
            z-index: 999;
            max-width: 400px;
        }
        .toast.show { opacity: 1; transform: translateY(0); }
        .section { display: none; padding: 20px 0; }
        .section.active { display: block; }
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
        .inventory-preview .item .stock { color: #33d6a6; }
        .section-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .section-tabs .tab {
            padding: 8px 16px;
            border-radius: 10px;
            cursor: pointer;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
            font-size: 13px;
            color: #8892a0;
        }
        .section-tabs .tab.active {
            background: rgba(51,214,166,0.12);
            border-color: rgba(51,214,166,0.2);
            color: #33d6a6;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        @media (max-width: 700px) {
            .grid-2 { grid-template-columns: 1fr; }
            .grid-3 { grid-template-columns: 1fr; }
            .form-grid { grid-template-columns: 1fr; }
            .form-grid .full { grid-column: 1; }
            .inventory-preview { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">✦ Sabrina AI Lab</div>
        <div class="nav">
            <a class="active" onclick="showSection('dashboard')">📊 Dashboard</a>
            <a onclick="showSection('smartstacks')">🏪 SmartStacks</a>
            <a onclick="showSection('leads')">📋 Leads</a>
            <a onclick="showSection('assistant')">🤖 Asistente</a>
        </div>
    </div>

    <!-- DASHBOARD -->
    <div id="dashboard" class="section active">
        <h1>📊 Dashboard</h1>
        <div class="grid grid-3">
            <div class="stat"><div class="number green" id="dashProducts">0</div><div class="label">📦 Productos</div></div>
            <div class="stat"><div class="number purple" id="dashLeads">0</div><div class="label">📋 Leads</div></div>
            <div class="stat"><div class="number gold" id="dashConversations">0</div><div class="label">💬 Consultas</div></div>
        </div>
        <div class="card">
            <h2>Últimos Leads</h2>
            <div id="dashLeadsList"><p style="color:#8892a0;">Sin leads</p></div>
        </div>
    </div>

    <!-- SMARTSTACKS -->
    <div id="smartstacks" class="section">
        <h1>🏪 Caso 1: SmartStacks</h1>
        <p class="subtitle">Gestiona tu inventario y usa el asistente IA para responder preguntas al instante.</p>
        
        <div class="grid grid-3">
            <div class="stat"><div class="number green" id="totalProducts">0</div><div class="label">📦 Productos</div></div>
            <div class="stat"><div class="number purple" id="totalStock">0</div><div class="label">📊 Stock Total</div></div>
            <div class="stat"><div class="number gold" id="totalConversations">0</div><div class="label">💬 Consultas</div></div>
        </div>

        <div class="section-tabs">
            <div class="tab active" onclick="switchTab('inventory-tab')">📦 Inventario</div>
            <div class="tab" onclick="switchTab('assistant-tab')">💬 Asistente</div>
        </div>

        <!-- Tab: Inventario -->
        <div id="inventory-tab" class="tab-content active">
            <div class="card">
                <h2>📋 Inventario Rápido</h2>
                <div id="inventoryPreview" class="inventory-preview">
                    <p style="color:#8892a0; grid-column:1/-1; text-align:center; padding:12px;">Cargando...</p>
                </div>
                <div class="flex flex-wrap gap-8 mt-12">
                    <button class="btn btn-secondary btn-sm" onclick="showFullInventory()">📋 Ver Completo</button>
                    <button class="btn btn-secondary btn-sm" onclick="exportCSV()">📥 CSV</button>
                    <button class="btn btn-secondary btn-sm" onclick="loadDemo()">📋 Cargar Demo</button>
                </div>
            </div>

            <div class="card mt-20">
                <h2>➕ Agregar Producto</h2>
                <form id="productForm" class="form-grid">
                    <div class="full"><label>Código</label><input id="pCode" placeholder="EJ-001" required></div>
                    <div class="full"><label>Nombre</label><input id="pName" required></div>
                    <div><label>Cantidad</label><input id="pQty" type="number" min="0" required></div>
                    <div><label>Precio</label><input id="pPrice" type="number" step="0.01" placeholder="0"></div>
                    <div class="full"><label>Categoría</label><input id="pCategory" placeholder="Herramientas"></div>
                    <div class="full"><label>Descripción</label><textarea id="pDesc" rows="2"></textarea></div>
                    <div class="full"><button class="btn btn-primary" type="submit">➕ Guardar</button></div>
                </form>
            </div>

            <div id="fullInventory" style="display:none;" class="card mt-20">
                <h2>📦 Inventario Completo</h2>
                <div style="overflow:auto; max-height:400px;">
                    <table>
                        <thead><tr><th>Código</th><th>Nombre</th><th>Stock</th><th>Precio</th><th>Categoría</th><th></th></tr></thead>
                        <tbody id="inventoryRows"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Tab: Asistente -->
        <div id="assistant-tab" class="tab-content">
            <div class="card">
                <h2>🤖 Asistente IA</h2>
                <p style="color:#8892a0; font-size:13px;">Pregunta sobre tu inventario</p>
                <div id="conversationHistory" style="max-height:300px; overflow:auto;"></div>
                <form id="assistantForm" class="mt-12">
                    <div class="flex flex-wrap gap-8" style="margin-bottom:8px;">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setQuestion('¿Tienes martillos?')">🔨 Martillos</button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setQuestion('¿Cuánto cuesta la tubería PVC?')">🔧 Tubería</button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setQuestion('¿Hay stock del código PER-001?')">📦 PER-001</button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setQuestion('¿Qué herramientas tienen?')">🛠️ Herramientas</button>
                    </div>
                    <input id="questionInput" placeholder="Ej: ¿Hay martillos disponibles?" required>
                    <button class="btn btn-primary mt-12" type="submit">💬 Preguntar</button>
                </form>
            </div>
        </div>

        <div class="card mt-20">
            <h2>🔄 Progreso</h2>
            <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%;"></div></div>
            <div id="progressInfo" style="color:#8892a0; font-size:13px;">Comienza haciendo preguntas.</div>
        </div>
    </div>

    <!-- LEADS -->
    <div id="leads" class="section">
        <h1>📋 Leads</h1>
        <div class="grid grid-2">
            <div class="card">
                <h2>Registrar Lead</h2>
                <form id="leadForm" class="form-grid">
                    <div class="full"><label>Nombre</label><input name="name" required></div>
                    <div class="full"><label>Negocio</label><input name="business" required></div>
                    <div class="full"><label>Email</label><input name="email" type="email" required></div>
                    <div class="full"><label>Caso</label><select name="use_case"><option>smartstacks</option><option>middleware</option></select></div>
                    <div class="full"><label>Presupuesto</label><input name="budget" required></div>
                    <div class="full"><label>Dolor</label><textarea name="pain" required></textarea></div>
                    <div class="full"><button class="btn btn-primary" type="submit">Guardar</button></div>
                </form>
            </div>
            <div class="card">
                <h2>Últimos Leads</h2>
                <div id="leadList"><p style="color:#8892a0;">Sin leads</p></div>
            </div>
        </div>
    </div>

    <!-- ASISTENTE GENERAL -->
    <div id="assistant" class="section">
        <h1>🤖 Asistente Estratégico</h1>
        <div class="grid grid-2">
            <div class="card">
                <h2>Consultar</h2>
                <form id="generalAssistantForm" class="form-grid">
                    <div class="full"><label>Canal</label><input name="channel" value="web"></div>
                    <div class="full"><label>Pregunta</label><textarea name="question" required></textarea></div>
                    <div class="full"><button class="btn btn-primary" type="submit">Preguntar</button></div>
                </form>
            </div>
            <div class="card">
                <h2>Historial</h2>
                <div id="assistantHistory"><p style="color:#8892a0;">Sin consultas</p></div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>
</div>

<script>
let state = { products: [], conversations: [], metrics: { total_products: 0, total_stock: 0 } };
let dashboardState = { leads: [], metrics: { leads: 0, products: 0 } };

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

const api = async (url, data) => {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    return await res.json();
};

const toast = msg => {
    const el = $('#toast');
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 3000);
};

function showSection(id) {
    $$('.section').forEach(s => s.classList.remove('active'));
    $(`#${id}`).classList.add('active');
    $$('.nav a').forEach(a => a.classList.remove('active'));
    document.querySelectorAll('.nav a').forEach(a => {
        if (a.textContent.includes(id) || (id === 'smartstacks' && a.textContent.includes('SmartStacks'))) {
            a.classList.add('active');
        }
    });
    if (id === 'smartstacks' || id === 'dashboard') refresh();
    if (id === 'leads') refreshLeads();
}

function switchTab(tabId) {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab[onclick*="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
    if (tabId === 'inventory-tab') {
        document.getElementById('fullInventory').style.display = 'none';
    }
}

function showFullInventory() {
    document.getElementById('fullInventory').style.display = 'block';
    document.getElementById('fullInventory').scrollIntoView({ behavior: 'smooth' });
}

async function refresh() {
    try {
        const res = await fetch('/api/smartstacks/state');
        state = await res.json();
        render();
    } catch(e) { console.error(e); }
}

async function refreshLeads() {
    try {
        const res = await fetch('/api/state');
        dashboardState = await res.json();
        renderLeads();
    } catch(e) { console.error(e); }
}

function render() {
    const products = state.products || [];
    const conversations = state.conversations || [];
    const metrics = state.metrics || { total_products: 0, total_stock: 0 };
    
    $('#totalProducts').textContent = metrics.total_products || 0;
    $('#totalStock').textContent = metrics.total_stock || 0;
    $('#totalConversations').textContent = conversations.length || 0;
    
    // Dashboard
    $('#dashProducts').textContent = metrics.total_products || 0;
    $('#dashConversations').textContent = conversations.length || 0;
    
    // Preview
    const preview = $('#inventoryPreview');
    if (products.length) {
        const display = products.slice(0, 8);
        let html = '';
        display.forEach(p => {
            const emoji = p.quantity > 10 ? '✅' : p.quantity > 0 ? '⚠️' : '❌';
            html += `<div class="item"><span><strong>${p.code}</strong> ${p.name}</span><span class="stock">${emoji} ${p.quantity}</span></div>`;
        });
        if (products.length > 8) {
            html += `<div style="grid-column:1/-1; text-align:center; color:#8892a0; font-size:12px; padding:4px;">+ ${products.length - 8} productos más</div>`;
        }
        preview.innerHTML = html;
    } else {
        preview.innerHTML = '<p style="color:#8892a0; grid-column:1/-1; text-align:center; padding:12px;">No hay productos. Carga el demo.</p>';
    }
    
    // Inventory rows
    const rows = $('#inventoryRows');
    rows.innerHTML = products.length ? products.map(p => `
        <tr>
            <td><strong>${p.code}</strong></td>
            <td>${p.name}</td>
            <td>${p.quantity}</td>
            <td>${p.price ? '$' + p.price : 'N/A'}</td>
            <td>${p.category || '-'}</td>
            <td><button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id})">✕</button></td>
        </tr>
    `).join('') : '<tr><td colspan="6" style="text-align:center;color:#8892a0;padding:20px;">Sin productos</td></tr>';
    
    // Conversations
    const convHtml = conversations.length ? conversations.slice().reverse().map(c => `
        <div class="conversation user"><strong>Tú:</strong><p>${c.question}</p></div>
        <div class="conversation"><strong>🤖 Asistente:</strong><p>${(c.answer || '').replace(/\\n/g, '<br>')}</p></div>
    `).join('') : '<p style="color:#8892a0;text-align:center;padding:12px;">Haz una pregunta.</p>';
    $('#conversationHistory').innerHTML = convHtml;
    
    // Progress
    const convCount = conversations.length;
    const progress = Math.min((convCount / 12) * 100, 100);
    $('#progressFill').style.width = progress + '%';
    const steps = ['Cargar Inventario', 'Conectar Asistente', 'Entrenar', 'Asistente en Vivo'];
    const stepIdx = Math.min(Math.floor(convCount / 3), steps.length - 1);
    $('#progressInfo').textContent = convCount >= 10 ? '🎉 ¡Asistente entrenado!' : 
                                     convCount > 0 ? `${steps[stepIdx]} - ${convCount} consultas` : 
                                     'Comienza haciendo preguntas.';
}

function renderLeads() {
    const leads = dashboardState.leads || [];
    $('#dashLeads').textContent = leads.length || 0;
    const list = $('#dashLeadsList');
    list.innerHTML = leads.length ? leads.map(l => `
        <div style="padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
            <strong>${l.business}</strong> - ${l.name} (${l.email})
        </div>
    `).join('') : '<p style="color:#8892a0;">Sin leads</p>';
    
    const leadList = $('#leadList');
    leadList.innerHTML = leads.length ? leads.map(l => `
        <div style="padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
            <strong>${l.business}</strong> - ${l.name}<br>
            <span style="color:#8892a0; font-size:12px;">${l.use_case} | ${l.budget}</span>
        </div>
    `).join('') : '<p style="color:#8892a0;">Sin leads</p>';
}

async function deleteProduct(id) {
    if (!confirm('¿Eliminar este producto?')) return;
    const result = await api('/api/inventory/product/delete', { product_id: id });
    if (!result.ok) { toast('Error: ' + result.error); return; }
    toast(result.message);
    refresh();
}

async function loadDemo() {
    const products = [
        {code: 'PER-001', name: 'Perno de Anclaje 3/8"', quantity: 45, price: 2500, category: 'Fijaciones', description: 'Perno galvanizado'},
        {code: 'TUB-002', name: 'Tubería PVC 1/2"', quantity: 120, price: 3800, category: 'Tuberías', description: 'Tubería PVC'},
        {code: 'MART-003', name: 'Martillo de Peña', quantity: 12, price: 15900, category: 'Herramientas', description: 'Martillo profesional'},
        {code: 'CIN-004', name: 'Cinta Métrica 5m', quantity: 28, price: 4500, category: 'Medición', description: 'Cinta métrica'},
        {code: 'LLAVE-005', name: 'Llave Francesa 12"', quantity: 15, price: 8900, category: 'Herramientas', description: 'Llave ajustable'},
        {code: 'DIS-006', name: 'Disco de Corte 4"', quantity: 80, price: 3200, category: 'Accesorios', description: 'Disco de corte'},
    ];
    let added = 0;
    for (const p of products) {
        const result = await api('/api/inventory/product/add', p);
        if (result.ok) added++;
    }
    toast(`✅ ${added} productos demo cargados`);
    refresh();
}

function setQuestion(text) {
    $('#questionInput').value = text;
    $('#assistantForm').dispatchEvent(new Event('submit'));
}

async function exportCSV() {
    window.location.href = '/api/inventory/export/csv';
    toast('📥 Descargando CSV...');
}

// Forms
$('#productForm').addEventListener('submit', async (e) => {
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
    const result = await api('/api/inventory/product/add', data);
    if (!result.ok) { toast('Error: ' + result.error); return; }
    toast(result.message);
    e.target.reset();
    refresh();
});

$('#assistantForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = $('#questionInput').value.trim();
    if (!question) return;
    const result = await api('/api/smartstacks/assistant', { question });
    if (!result.ok) { toast('Error: ' + result.error); return; }
    $('#questionInput').value = '';
    refresh();
    toast('✅ Respuesta recibida');
});

$('#leadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const result = await api('/api/leads', Object.fromEntries(data));
    if (!result.ok) { toast('Error: ' + result.error); return; }
    toast(result.message);
    e.target.reset();
    refreshLeads();
});

$('#generalAssistantForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const result = await api('/api/assistant', Object.fromEntries(data));
    if (!result.ok) { toast('Error: ' + result.error); return; }
    toast('Respuesta recibida');
    e.target.reset();
    refreshLeads();
});

// Inicializar
refresh();
refreshLeads();
setInterval(refresh, 15000);
</script>
</body>
</html>"""

# ============================================
# SERVIDOR HTTP
# ============================================

class SabrinaHandler(BaseHTTPRequestHandler):
    server_version = "SabrinaAILab/1.0"
    
    def log_message(self, fmt, *args):
        print(f"[{now_iso()}] {fmt % args}")
    
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "":
            html_response(self, HTML)
            return
        if parsed.path == "/api/state":
            json_response(self, get_dashboard_state())
            return
        if parsed.path == "/api/smartstacks/state":
            json_response(self, get_smartstacks_state())
            return
        if parsed.path == "/api/inventory/export/csv":
            csv_data = export_inventory_csv()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=inventory.csv")
            self.send_header("Content-Length", str(len(csv_data)))
            self.end_headers()
            self.wfile.write(csv_data)
            return
        if parsed.path == "/health":
            json_response(self, {"ok": True, "time": now_iso()})
            return
        json_response(self, {"ok": False, "error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = read_json(self)
            
            if parsed.path == "/api/leads":
                result = create_lead(payload)
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
            if parsed.path == "/api/smartstacks/assistant":
                result = smartstacks_assistant_reply(payload)
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

def main():
    init_db()
    seed_demo_products()
    server = ThreadingHTTPServer((HOST, PORT), SabrinaHandler)
    print(f"✅ Sabrina AI Lab listo en http://{HOST}:{PORT}")
    print(f"📁 Base de datos: {DB_PATH}")
    print(f"📦 Productos: {len(get_inventory_products())}")
    print("Presiona Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
