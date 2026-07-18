# Sabrina · Laboratorio IA Humana

Repositorio de trabajo para convertir la infraestructura de la VM Sabrina y Azure AI Foundry en soluciones web funcionales, humanas y comercialmente evaluables por Sin Pausas.

## MVP principal

El MVP funcional está en:

```text
proyectos/sabrina_ai_lab/
```

Ejecutar:

```bash
python3 proyectos/sabrina_ai_lab/app.py
```

Abrir:

```text
http://127.0.0.1:8000
```

## Qué resuelve

Este proyecto toma el manual estratégico de 6 semanas y lo baja a una aplicación real con:

- frontend web responsive;
- backend HTTP en Python;
- APIs JSON;
- SQLite para guardar leads, estimaciones y eventos del asistente;
- calculadora de valor comercial;
- asistente estratégico local;
- integración opcional con LiteLLM o Azure OpenAI;
- documentación para tmux, Nginx, Certbot y GitHub.

## Documentación completa

Ver:

```text
proyectos/sabrina_ai_lab/README.md
```

## Seguridad

No subir claves `.env`, bases SQLite locales ni credenciales de Azure. El `.gitignore` ya excluye datos de runtime y secretos comunes.