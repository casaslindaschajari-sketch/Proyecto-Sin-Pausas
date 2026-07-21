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

## Información Clave de la Agencia (Sin Pausas)
## Misión y Filosofía
La agencia cree que el verdadero desafío de la IA no es técnico, sino humano. Su misión es usar el poder de la tecnología (42 GiB de RAM + 3 modelos GPT de Azure Foundry) para resolver problemas cotidianos de personas y negocios, aliviando la carga de trabajo diaria y mejorando la calidad de vida de los equipos.

## El Vínculo Técnico-Comercial (El "Por Qué")
La tecnología es el medio, no el fin. La RAM permite recordar datos masivos (catálogos, inventarios, historiales), mientras que la IA externa procesa el lenguaje para dar respuestas cercanas y empáticas. Al unirlas, se crean soluciones que hablan el idioma del cliente y agilizan sus operaciones.

## Casos de Uso "Humanos" y Monetizables (Estructura para la Web)
La web debe presentar estos 3 casos de uso como los servicios estrella de la agencia:

Caso 1: El Asistente Experto para Negocios y Pymes (SmartStacks de Cercanía)
El Problema Humano: Vendedores de tiendas locales, almacenes o ferreterías pierden tiempo buscando códigos de productos o explicando hojas técnicas, generando filas y estrés.

La Solución en la Práctica: Usar los 42 GiB de RAM para almacenar inventario y manuales localmente. Con los modelos GPT de Azure, se crea un asistente conversacional por WhatsApp o tablet. El vendedor pregunta: "¿Me queda el perno de anclaje de 3/8?" y obtiene la respuesta exacta en un segundo.

Modelo Comercial: Suscripción mensual (SaaS) para comercios. El éxito del proyecto se evaluará en Sin Pausas para financiar el servicio de manera permanente.

Caso 2: Automatización de Respuestas con Empatía y Centralización (LiteLLM Middleware)
El Problema Humano: Emprendedores y creadores de contenido pasan horas respondiendo las mismas preguntas en redes, descuidando su negocio principal.

La Solución en la Práctica: Configurar un proxy unificado (LiteLLM) en la VM que administre los 3 modelos GPT. Esto permite atender diferentes canales (WhatsApp, web, redes) con un tono empático y natural, optimizando el consumo de tokens para cuidar el presupuesto.

Modelo Comercial: Infraestructura centralizada para agencias de marketing o desarrolladores. Se cobra una membresía fija o un fee por volumen de interacciones resueltas.

Caso 3: Digitalización Acelerada y Soluciones 'Llave en Mano'
El Problema Humano: Dueños de empresas tradicionales quieren sumarse a la IA pero les asusta la complejidad técnica y los costos ocultos.

La Solución en la Práctica: Usar el laboratorio de 6 semanas para diseñar sistemas modulares en Docker que resuelvan flujos reales (atención, filtrado de correos, gestión de agendas). La VM sirve como entorno de prueba vivo con los datos del cliente.

Modelo Comercial: Consultorías de implementación únicas (proyectos llave en mano). Se cobra un setup alto a empresas medianas por dejar el sistema configurado y funcionando en sus propios equipos.

Plan de Acción de Aprendizaje y Validación Comercial (Hoja de Ruta)
La web debe transmitir que el proceso tiene un límite de 6 semanas, lo que genera urgencia y valor:

Semanas 1 y 2: Full Aprendizaje: Dominio de terminal, conexión de LiteLLM, prueba de los 3 modelos GPT de Azure Foundry. Enfoque en entender costos por respuesta para armar presupuestos reales.

Semanas 3 y 4: Creación del MVP: Despliegue de un caso de uso real (ej. recomendador para tienda o gestor de mensajes) corriendo en segundo plano con tmux.

Semanas 5 y 6: Pruebas en Vivo y Propuesta Comercial: Montaje de una interfaz web con HTTPS. Invitación a potenciales usuarios para pruebas en vivo, recopilación de opiniones y creación de la propuesta de negocio formal para evaluación final en Sin Pausas.

Nota Crítica: Pasado el plazo de 6 semanas, los accesos expiran por completo. La única forma de continuar es consolidar una propuesta comercial con sentido real que sea evaluada estratégicamente en la agencia.

Instrucción Final para la IA (Lo que debe generar)
A partir de la información anterior, genera el código completo (HTML, CSS y JavaScript) para una página web de una sola página (landing page) que cumpla con los siguientes requisitos:

Diseño: Moderno, limpio, profesional y con un enfoque "humano" (colores cálidos o corporativos, tipografía legible).

Estructura:

Hero: Título y subtítulo que capturen la esencia (ej. "Bajamos la IA a tu realidad").

Sección "El Problema Humano": Explicar que la IA no es fría, es una herramienta para aliviar cargas.

Sección "Nuestras Soluciones": Presentar los 3 casos de uso con iconos, descripción del problema, solución y modelo comercial.

Sección "El Método Sin Pausas": Visualizar el plan de acción de 6 semanas (línea de tiempo o tarjetas).

Sección "Tecnología que Impulsa": Mencionar los 42 GiB de RAM y los modelos GPT de Azure Foundry como ventajas técnicas.

Llamada a la Acción (CTA): Botón claro para contactar o solicitar una demo (simulado, solo estilo).

Responsive: Que se vea bien en móviles, tablets y escritorio.

Interactividad (Opcional pero recomendado): Incluir un poco de JavaScript para animaciones suaves al hacer scroll o un menú hamburguesa.

Entregable: El código debe estar listo para ser copiado y pegado en un archivo .html y funcionar de inmediato. Incluye comentarios en el código para explicar las secciones.
