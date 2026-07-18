# app.py chunk 4 of 5

Create/edit this path in GitHub:

```text
proyectos/sabrina_ai_lab/app.py
```

Copy this chunk in order. Lines 541-720 of 864.

```python
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
```
