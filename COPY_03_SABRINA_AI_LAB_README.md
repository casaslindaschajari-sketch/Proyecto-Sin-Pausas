# Copy this into `proyectos/sabrina_ai_lab/README.md`

Create/edit this path in GitHub:

```text
proyectos/sabrina_ai_lab/README.md
```

Copy everything between the code fences:

```markdown
# Sabrina AI Lab · MVP web funcional

MVP creado a partir del manual de configuración y orientación estratégica del laboratorio de IA de Sabrina.

La idea central es convertir la infraestructura técnica —VM Ubuntu, Azure AI Foundry, LiteLLM, Docker, Nginx, tmux y una ventana de 6 semanas— en una herramienta web funcional para validar soluciones humanas y monetizables ante Sin Pausas.

## Qué incluye

- Página web responsive.
- Backend real en Python, sin dependencias externas.
- API JSON.
- Persistencia con SQLite.
- Captura de oportunidades comerciales/leads.
- Calculadora de valor mensual, costo IA aproximado y precio sugerido.
- Asistente estratégico:
  - funciona localmente sin claves;
  - puede usar LiteLLM si se configura `LITELLM_BASE_URL`;
  - puede usar Azure OpenAI si se configuran las variables de Azure.
- Endpoint de salud `/health`.
- Monitor básico de disco desde el backend, alineado con la advertencia del manual.

## Estructura

```text
proyectos/sabrina_ai_lab/
├── app.py              # Servidor web + backend + frontend embebido
├── README.md           # Esta documentación
└── data/               # Se crea automáticamente al ejecutar; contiene SQLite
```

## Ejecución local

Desde `/home/Sabrina`:

```bash
python3 proyectos/sabrina_ai_lab/app.py
```

Abrir:

```text
http://127.0.0.1:8000
```

Para escuchar en todas las interfaces de la VM:

```bash
SABRINA_HOST=0.0.0.0 SABRINA_PORT=8000 python3 proyectos/sabrina_ai_lab/app.py
```

## APIs disponibles

### Estado general

```bash
curl http://127.0.0.1:8000/api/state
```

### Salud

```bash
curl http://127.0.0.1:8000/health
```

### Registrar oportunidad

```bash
curl -X POST http://127.0.0.1:8000/api/leads \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Cliente piloto",
    "business": "Ferretería Central",
    "email": "cliente@example.com",
    "use_case": "smartstacks",
    "pain": "Pierden tiempo buscando stock y fichas técnicas.",
    "budget": "USD 300-600/mes"
  }'
```

### Calcular propuesta comercial

```bash
curl -X POST http://127.0.0.1:8000/api/estimate \
  -H 'Content-Type: application/json' \
  -d '{
    "use_case": "smartstacks",
    "interactions": 1800,
    "minutes_saved": 4,
    "hourly_cost": 9.5
  }'
```

### Asistente estratégico

```bash
curl -X POST http://127.0.0.1:8000/api/assistant \
  -H 'Content-Type: application/json' \
  -d '{
    "channel": "WhatsApp",
    "question": "Una ferretería recibe muchas preguntas por stock. ¿Cómo lo vuelvo un MVP vendible?"
  }'
```

## Integración opcional con LiteLLM

Si tienes LiteLLM corriendo como proxy compatible con OpenAI:

```bash
export LITELLM_BASE_URL="http://127.0.0.1:4000/v1"
export LITELLM_API_KEY="tu_key_si_aplica"
export LITELLM_MODEL="gpt-4o-mini"
python3 proyectos/sabrina_ai_lab/app.py
```

El backend llamará a:

```text
POST {LITELLM_BASE_URL}/chat/completions
```

## Integración opcional con Azure AI Foundry / Azure OpenAI

Configurar variables:

```bash
export AZURE_OPENAI_API_KEY="TU_API_KEY"
export AZURE_OPENAI_ENDPOINT="https://TU_RECURSO.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="NOMBRE_DEL_MODELO_DESPLEGADO"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
python3 proyectos/sabrina_ai_lab/app.py
```

Si esas variables no están presentes, el asistente usa modo local para que la demo siga funcionando.

## Mantener corriendo con tmux

```bash
tmux new -s sabrina-ai-lab
SABRINA_HOST=0.0.0.0 SABRINA_PORT=8000 python3 proyectos/sabrina_ai_lab/app.py
```

Desacoplar:

```text
Ctrl+B, luego D
```

Reconectar:

```bash
tmux attach -t sabrina-ai-lab
```

## Producción con Nginx y HTTPS

Ejemplo conceptual de reverse proxy:

```nginx
server {
    server_name tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Luego usar Certbot para HTTPS:

```bash
sudo certbot --nginx -d tu-dominio.com
```

## Monitoreo de almacenamiento

El manual advierte que la VM usa solo el disco principal del SO. Revisar periódicamente:

```bash
df -h
```

La web también muestra un indicador básico de uso de disco leído desde el backend.

## Copiar a un repositorio de GitHub

### Opción A: con GitHub CLI

Si `gh` está instalado y autenticado:

```bash
cd /home/Sabrina
git init
git add proyectos/sabrina_ai_lab
git commit -m "Add Sabrina AI Lab MVP"
gh repo create sabrina-ai-lab --private --source=. --remote=origin --push
```

### Opción B: con repositorio ya creado en GitHub

1. Crear un repositorio vacío en GitHub, por ejemplo `sabrina-ai-lab`.
2. Copiar la URL SSH o HTTPS.
3. Ejecutar:

```bash
cd /home/Sabrina
git init
git add proyectos/sabrina_ai_lab
git commit -m "Add Sabrina AI Lab MVP"
git branch -M main
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
```

Ejemplo con SSH:

```bash
git remote add origin git@github.com:TU_USUARIO/sabrina-ai-lab.git
```

Ejemplo con HTTPS:

```bash
git remote add origin https://github.com/TU_USUARIO/sabrina-ai-lab.git
```

## Próximos pasos estratégicos

1. Validar con 2 o 3 comercios reales.
2. Cargar preguntas reales de clientes.
3. Medir:
   - tiempo ahorrado;
   - precisión de respuestas;
   - intención de pago;
   - costo aproximado por respuesta.
4. Preparar una propuesta comercial para Sin Pausas antes de que termine la ventana de 6 semanas.
```
