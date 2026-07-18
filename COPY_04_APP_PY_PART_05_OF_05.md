# app.py chunk 5 of 5

Create/edit this path in GitHub:

```text
proyectos/sabrina_ai_lab/app.py
```

Copy this chunk in order. Lines 721-864 of 864.

```python
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
  const entities = {{
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }};
  return String(value).replace(/[&<>"']/g, (ch) => entities[ch]);
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
```
