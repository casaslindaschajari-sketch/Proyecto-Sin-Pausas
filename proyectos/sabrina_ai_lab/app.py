#!/usr/bin/env python3
"""
Sabrina AI Lab - MVP web funcional con backend real.

Servidor web sin dependencias externas:
- Frontend responsive embebido.
- Backend HTTP/JSON con persistencia SQLite.
- Calculadora comercial para casos de IA.
- Captura de oportunidades/leads.
- Asistente estratégico local con integración opcional Azure OpenAI / LiteLLM compatible.

Ejecutar:
    python3 proyectos/sabrina_ai_lab/app.py
Abrir:
    http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import textwrap
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "sabrina_lab.sqlite3"
HOST = os.environ.get("SABRINA_HOST", "127.0.0.1")
PORT = int(os.environ.get("SABRINA_PORT", "8000"))


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

    azure_ready = all(
        [
            os.environ.get("AZURE_OPENAI_API_KEY"),
            os.environ.get("AZURE_OPENAI_ENDPOINT"),
            os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        ]
    )
    litellm_ready = bool(os.environ.get("LITELLM_BASE_URL"))

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
            "mode": "Azure/OpenAI real" if azure_ready or litellm_ready else "Simulador local sin credenciales",
        },
        "use_cases": USE_CASES,
        "roadmap": ROADMAP,
        "metrics": {
            "leads": lead_count,
            "estimates": estimate_count,
            "events": len(events),
        },
        "leads": leads,
        "estimates": estimates,
        "assistant_events": events,
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
    .navlinks a {{ text-decoration: none; color: var(--muted); font-size: 14px; padding: 8px 10px; border-radius: 999px; }}
    .navlinks a:hover {{ background: var(--panel); color: var(--text); }}
    .hero {{ padding: 72px 0 36px; display: grid; grid-template-columns: 1.15fr .85fr; gap: 28px; align-items: center; }}
    .eyebrow {{ display:inline-flex; gap: 8px; align-items:center; color: var(--brand2); background: rgba(51,214,166,.09); border:1px solid rgba(51,214,166,.25); padding: 8px 12px; border-radius: 999px; font-size: 13px; font-weight: 700; }}
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
    .grid.three {{ grid-template-columns: repeat(3, 1fr); }}
    .grid.two {{ grid-template-columns: repeat(2, 1fr); }}
    .metric {{ font-size: 32px; font-weight: 900; letter-spacing: -.04em; }}
    .muted {{ color: var(--muted); }}
    .tag {{ display:inline-flex; padding: 6px 9px; border-radius: 999px; background: rgba(155,140,255,.13); border: 1px solid rgba(155,140,255,.28); color: #d8d2ff; font-size: 12px; font-weight: 800; }}
    section {{ padding: 38px 0; }}
    .case {{ display:flex; flex-direction:column; gap: 14px; }}
    .case ul, .road ul {{ padding-left: 20px; color: var(--muted); line-height: 1.7; margin: 0; }}
    input, textarea, select {{
      width: 100%; background: rgba(0,0,0,.24); color: var(--text);
      border: 1px solid var(--line); border-radius: 14px; padding: 12px 13px;
      outline: none; font: inherit;
    }}
    textarea {{ min-height: 110px; resize: vertical; }}
    label {{ display:block; font-size: 13px; font-weight: 800; color: #dbe2f2; margin: 0 0 7px; }}
    .formgrid {{ display:grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .full {{ grid-column: 1 / -1; }}
    .result {{
      white-space: pre-wrap; background: rgba(0,0,0,.28); border: 1px solid var(--line);
      border-radius: 18px; padding: 16px; color: #eaf0ff; min-height: 72px;
    }}
    table {{ width:100%; border-collapse: collapse; overflow: hidden; border-radius: 16px; }}
    th, td {{ text-align:left; padding: 12px; border-bottom: 1px solid var(--line); color: var(--muted); vertical-align: top; }}
    th {{ color: var(--text); background: rgba(255,255,255,.06); }}
    .status-ok {{ color: var(--brand2); font-weight: 900; }}
    .status-warn {{ color: var(--warn); font-weight: 900; }}
    .progress {{ height: 12px; border-radius: 999px; background: rgba(255,255,255,.10); overflow:hidden; }}
    .bar {{ height: 100%; width: 0%; background: linear-gradient(90deg, var(--brand2), var(--warn)); transition: width .4s ease; }}
    footer {{ border-top: 1px solid var(--line); margin-top: 36px; padding: 24px 0 36px; color: var(--muted); }}
    .toast {{ position: fixed; right: 18px; bottom: 18px; background: #102018; color: #d9ffe8; border: 1px solid rgba(51,214,166,.38); padding: 12px 14px; border-radius: 14px; opacity:0; transform: translateY(10px); transition:.25s; z-index: 20; }}
    .toast.show {{ opacity:1; transform: translateY(0); }}
    @media (max-width: 850px) {{
      .hero, .grid.two, .grid.three, .formgrid {{ grid-template-columns: 1fr; }}
      .navlinks {{ display:none; }}
      .hero {{ padding-top: 44px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <nav>
        <div class="brand"><div class="logo">✦</div><span>Sabrina AI Lab</span></div>
        <div class="navlinks">
          <a href="#casos">Casos</a>
          <a href="#asistente">Asistente</a>
          <a href="#calculadora">Calculadora</a>
          <a href="#leads">Leads</a>
          <a href="#roadmap">Roadmap</a>
        </div>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <section class="hero">
      <div>
        <span class="eyebrow">Laboratorio intensivo · 6 semanas · IA con sentido humano</span>
        <h1>De infraestructura IA a propuestas reales para Sin Pausas.</h1>
        <p>
          MVP funcional con backend, SQLite, calculadora de valor, captura de oportunidades y asistente estratégico.
          Está diseñado para convertir la VM Sabrina, Azure AI Foundry y LiteLLM en soluciones monetizables para personas y negocios.
        </p>
        <div class="actions">
          <a class="btn" href="#asistente">Probar asistente</a>
          <a class="btn secondary" href="#leads">Registrar oportunidad</a>
        </div>
      </div>
      <div class="card">
        <h3>Estado operativo</h3>
        <p id="integrationMode">Cargando...</p>
        <div class="grid two">
          <div><div class="metric" id="leadCount">0</div><div class="muted">leads guardados</div></div>
          <div><div class="metric" id="estimateCount">0</div><div class="muted">estimaciones</div></div>
        </div>
        <hr style="border:0;border-top:1px solid var(--line);margin:18px 0">
        <div class="muted">Disco usado</div>
        <div class="progress" aria-label="uso de disco"><div class="bar" id="diskBar"></div></div>
        <p id="diskText"></p>
      </div>
    </section>

    <section id="casos">
      <h2>Casos de uso humanos y monetizables</h2>
      <div class="grid three" id="cases"></div>
    </section>

    <section id="asistente" class="grid two">
      <div class="card">
        <span class="tag">Backend /api/assistant</span>
        <h2>Asistente estratégico</h2>
        <p>
          Describe una situación real. Si configuras Azure OpenAI o LiteLLM, responderá con modelo real.
          Si no, usa un motor local para orientar la propuesta sin romper la demo.
        </p>
        <form id="assistantForm">
          <label for="channel">Canal</label>
          <select id="channel" name="channel">
            <option>web</option>
            <option>WhatsApp</option>
            <option>Instagram</option>
            <option>Tablet en tienda</option>
            <option>Email</option>
          </select>
          <br><br>
          <label for="question">Situación o pregunta</label>
          <textarea id="question" name="question" required>Una ferretería recibe muchas preguntas por stock y medidas de productos. ¿Cómo lo vuelvo un MVP vendible?</textarea>
          <br><br>
          <button type="submit">Generar orientación</button>
        </form>
      </div>
      <div class="card">
        <h3>Respuesta</h3>
        <div class="result" id="assistantResult">La respuesta aparecerá aquí.</div>
      </div>
    </section>

    <section id="calculadora" class="grid two">
      <div class="card">
        <span class="tag">Backend /api/estimate</span>
        <h2>Calculadora de valor comercial</h2>
        <p>Estima costo IA, horas humanas ahorradas, valor mensual y precio sugerido para armar una propuesta comercial.</p>
        <form id="estimateForm" class="formgrid">
          <div class="full">
            <label for="estimateCase">Caso</label>
            <select id="estimateCase" name="use_case"></select>
          </div>
          <div>
            <label for="interactions">Interacciones mensuales</label>
            <input id="interactions" name="interactions" type="number" value="1800" min="1">
          </div>
          <div>
            <label for="minutesSaved">Minutos ahorrados por interacción</label>
            <input id="minutesSaved" name="minutes_saved" type="number" value="4" min="1">
          </div>
          <div class="full">
            <label for="hourlyCost">Costo hora humana estimado (USD)</label>
            <input id="hourlyCost" name="hourly_cost" type="number" value="9.5" min="0" step="0.1">
          </div>
          <div class="full"><button type="submit">Calcular propuesta</button></div>
        </form>
      </div>
      <div class="card">
        <h3>Resultado comercial</h3>
        <div class="result" id="estimateResult">Completa la calculadora para generar números.</div>
      </div>
    </section>

    <section id="leads" class="grid two">
      <div class="card">
        <span class="tag">Backend /api/leads</span>
        <h2>Registrar oportunidad piloto</h2>
        <p>Guarda negocios reales para probar durante las semanas 5 y 6 y alimentar la propuesta a Sin Pausas.</p>
        <form id="leadForm" class="formgrid">
          <div><label>Nombre</label><input name="name" required placeholder="Nombre contacto"></div>
          <div><label>Negocio</label><input name="business" required placeholder="Empresa o pyme"></div>
          <div><label>Email</label><input name="email" type="email" required placeholder="contacto@empresa.com"></div>
          <div><label>Presupuesto</label><select name="budget"><option>Exploratorio</option><option>USD 300-600/mes</option><option>USD 600-1200/mes</option><option>Proyecto llave en mano</option></select></div>
          <div class="full"><label>Caso de uso</label><select name="use_case" id="leadCase"></select></div>
          <div class="full"><label>Dolor principal</label><textarea name="pain" required placeholder="Qué proceso genera estrés, repetición o pérdida de ventas..."></textarea></div>
          <div class="full"><button type="submit">Guardar lead</button></div>
        </form>
      </div>
      <div class="card">
        <h3>Últimas oportunidades</h3>
        <div style="overflow:auto"><table><thead><tr><th>Fecha</th><th>Negocio</th><th>Caso</th><th>Dolor</th></tr></thead><tbody id="leadRows"></tbody></table></div>
      </div>
    </section>

    <section id="roadmap">
      <h2>Plan de acción de 6 semanas</h2>
      <div class="grid three" id="roadmapCards"></div>
    </section>
  </main>

  <footer>
    <div class="wrap">
      <strong>Sabrina AI Lab</strong> · Ejecuta con <code>python3 proyectos/sabrina_ai_lab/app.py</code>.
      Para producción: tmux + Nginx + Certbot + variables de Azure/LiteLLM.
    </div>
  </footer>

  <div class="toast" id="toast"></div>

<script>
const initialState = {state_json};
let state = initialState;

const $ = (sel) => document.querySelector(sel);
const api = async (url, data) => {{
  const res = await fetch(url, {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(data)
  }});
  return await res.json();
}};
const toast = (msg) => {{
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2800);
}};
const formData = (form) => Object.fromEntries(new FormData(form).entries());

function renderState() {{
  $('#integrationMode').innerHTML = `<span class="${{state.integrations.azure_openai_ready || state.integrations.litellm_ready ? 'status-ok' : 'status-warn'}}">● ${{state.integrations.mode}}</span>`;
  $('#leadCount').textContent = state.metrics.leads;
  $('#estimateCount').textContent = state.metrics.estimates;
  $('#diskBar').style.width = `${{state.server.disk.used_percent}}%`;
  $('#diskText').textContent = `${{state.server.disk.used_gb}} GB usados de ${{state.server.disk.total_gb}} GB · libres: ${{state.server.disk.free_gb}} GB`;

  $('#cases').innerHTML = state.use_cases.map(c => `
    <article class="card case">
      <span class="tag">${{c.tag}}</span>
      <h3>${{c.title}}</h3>
      <p><strong>Problema:</strong> ${{c.problem}}</p>
      <p><strong>Solución:</strong> ${{c.solution}}</p>
      <p><strong>Modelo:</strong> ${{c.model}}</p>
      <ul>${{c.impact.map(i => `<li>${{i}}</li>`).join('')}}</ul>
      <div class="muted">Desde USD ${{c.price}}/mes · setup USD ${{c.setup}}</div>
    </article>
  `).join('');

  const options = state.use_cases.map(c => `<option value="${{c.id}}">${{c.title}}</option>`).join('');
  $('#estimateCase').innerHTML = options;
  $('#leadCase').innerHTML = options;

  $('#roadmapCards').innerHTML = state.roadmap.map(r => `
    <article class="card road">
      <span class="tag">Semanas ${{r.weeks}}</span>
      <h3>${{r.title}}</h3>
      <ul>${{r.items.map(i => `<li>${{i}}</li>`).join('')}}</ul>
    </article>
  `).join('');

  $('#leadRows').innerHTML = state.leads.length ? state.leads.map(l => `
    <tr><td>${{new Date(l.created_at).toLocaleString()}}</td><td>${{escapeHtml(l.business)}}</td><td>${{escapeHtml(l.use_case)}}</td><td>${{escapeHtml(l.pain)}}</td></tr>
  `).join('') : '<tr><td colspan="4">Aún no hay oportunidades guardadas.</td></tr>';
}}

function escapeHtml(value) {{
  return String(value).replace(/[&<>"']/g, (ch) => ({{'&':'&','<':'<','>':'>','"':'"',"'":'&#039;'}}[ch]));
}}

async function refresh() {{
  const res = await fetch('/api/state');
  state = await res.json();
  renderState();
}}

$('#assistantForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  $('#assistantResult').textContent = 'Generando...';
  const out = await api('/api/assistant', formData(e.currentTarget));
  if (!out.ok) {{
    $('#assistantResult').textContent = out.error;
    return;
  }}
  $('#assistantResult').textContent = `${{out.answer}}\\n\\nFuente: ${{out.source}}`;
  toast('Orientación generada y guardada.');
  refresh();
}});

$('#estimateForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const out = await api('/api/estimate', formData(e.currentTarget));
  if (!out.ok) {{
    $('#estimateResult').textContent = out.error || 'No se pudo calcular.';
    return;
  }}
  $('#estimateResult').textContent =
`Caso: ${{out.use_case}}
Interacciones: ${{out.interactions}}/mes
Horas humanas ahorradas: ${{out.human_hours_saved}} h/mes
Costo IA estimado: USD ${{out.estimated_ai_cost}}
Valor humano recuperado: USD ${{out.monthly_value}}
Precio mensual sugerido: USD ${{out.suggested_price}}
Setup sugerido: USD ${{out.setup}}
Margen técnico aproximado: USD ${{out.margin_hint}}`;
  toast('Estimación guardada.');
  refresh();
}});

$('#leadForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const out = await api('/api/leads', formData(e.currentTarget));
  if (!out.ok) {{
    toast(out.error);
    return;
  }}
  e.currentTarget.reset();
  toast(out.message);
  refresh();
}});

renderState();
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
                json_response(self, estimate_cost(payload))
                return
            if parsed.path == "/api/assistant":
                result = assistant_reply(payload)
                json_response(self, result, 200 if result.get("ok") else 400)
                return
            json_response(self, {"ok": False, "error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError:
            json_response(self, {"ok": False, "error": "JSON inválido"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 - servidor demo debe responder con error útil
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