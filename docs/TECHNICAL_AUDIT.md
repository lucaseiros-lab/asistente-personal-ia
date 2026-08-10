# Auditoría técnica

Commit auditado: `375d82b` (`main`). Fecha: 2026-08-10.

Este informe es una revisión independiente del estado real del código — no un resumen de lo que se pretendía construir. Todo hallazgo listado abajo fue verificado ejecutando el código (tests, linters, `pip-audit`, `npm audit`, grep dirigido) durante esta auditoría, no inferido de la documentación previa (`docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`). Donde este informe contradice esos documentos, este es el que refleja la evidencia más reciente.

No se modificó ningún archivo del repositorio para producir este informe.

---

## 1. Arquitectura real

```
Frontend (Next.js 16 PWA) ──HTTPS/JSON+JWT──▶ Backend (FastAPI async) ──asyncpg──▶ PostgreSQL 16 + pgvector
                                                      │
                                                      ├──HTTPS──▶ OpenAI API (chat / embeddings / audio)
                                                      └──HTTPS──▶ n8n (opcional, webhooks en ambas direcciones)
```

- **Backend** (`backend/app`): FastAPI + SQLAlchemy 2.0 async + Alembic. Organizado en capas: `models` (ORM), `schemas` (contratos Pydantic de la API), `ai` (cliente OpenAI + Structured Outputs), `memory` (3 capas), `services` (CRUD genérico, ejecución de acciones, auth), `integrations` (n8n), `api/v1/endpoints` (routers HTTP). Las capas de negocio (`ai`, `memory`, `services`) no dependen de FastAPI y son invocables/testeables de forma aislada.
- **Frontend** (`frontend/src`): Next.js 16 App Router, cliente delgado — toda la lógica vive en el backend. Estado de auth en `zustand` + `localStorage`. Un único cliente HTTP (`lib/api.ts`) centraliza el manejo de JWT.
- **Base de datos**: PostgreSQL con extensión `vector` (pgvector). 15 tablas (14 entidades de negocio + `memory_embeddings`), migradas con Alembic, sin drift respecto al código actual (`alembic check` verificado en esta auditoría).
- **`memory/` y `prompts/` en la raíz del repo**: `prompts/system_prompt.md` está activamente en uso (lo carga `app/ai/prompts.py` en tiempo de ejecución). `memory/README.md`, en cambio, es un artefacto huérfano del scaffolding inicial del producto — describe el concepto de memoria pero no tiene ninguna relación con la implementación real, que vive enteramente en `backend/app/memory/`.
- **`docker-compose.yml`**: cuatro servicios (`db`, `backend`, `frontend`, `n8n`), pensado para desarrollo local (el propio comando del backend corre `alembic upgrade head` y luego `uvicorn --reload`; el del frontend corre `npm run dev`). No existe una configuración de Compose ni Dockerfiles separados para producción.
- **CI** (`.github/workflows/ci.yml`): dos jobs (`backend`, `frontend`) que corren lint + tests en cada push/PR a `main`. No hay job de build/push de imágenes ni de despliegue.

---

## 2. Funcionalidades realmente implementadas

Verificado con tests automatizados ejecutados en esta auditoría (36/36 backend, 7/7 frontend, ambos en verde) y con lectura directa del código:

- Registro, login, refresh de JWT, endpoint `/auth/me`. Contraseñas con `bcrypt`.
- CRUD completo y aislado por usuario para las 11 entidades que lo requieren (`people`, `companies`, `projects`, `tasks`, `events`, `reminders`, `ideas`, `expenses`, `documents`, `tags`, `preferences`), con soft-delete donde el modelo lo soporta.
- Endpoint de chat (`POST /conversations/{id}/messages`) que persiste el mensaje, arma el contexto de memoria, llama al Motor IA, persiste la respuesta y ejecuta las acciones devueltas.
- `ActionExecutor`: creación de tarea/evento/recordatorio/idea/gasto, resolución find-or-create de persona/empresa/proyecto mencionados, y "completar tarea" por coincidencia difusa de título.
- Memoria estructurada (snapshot de Postgres) y memoria conversacional (historial + resumen automático al superar 30 mensajes) — ambas funcionan sin depender de que la capa semántica esté disponible.
- Migraciones de base de datos aplicadas y consistentes con los modelos actuales.
- Frontend: login/registro, sidebar con conversaciones, envío de mensajes, grabación de audio con `MediaRecorder` + subida al backend, dashboard agrupado por semáforo de prioridad, manifest + service worker de PWA.
- CI en verde en ambos proyectos.

---

## 3. Funcionalidades simuladas o con mocks

Esto es lo que un lector casual de `docs/PROJECT_STATUS.md` podría no captar con suficiente énfasis: **ninguna parte de este sistema fue ejecutada nunca contra la API real de OpenAI**. Todo lo que sigue está probado con dobles de prueba (`unittest.mock`), no con la integración real:

- `AIEngine.interpret_message` (interpretación de mensajes vía Structured Outputs) — probado con un `AsyncOpenAI` simulado que devuelve objetos `AssistantInterpretation` fabricados a mano.
- `EmbeddingService.embed_text` (memoria semántica) — probado con vectores fijos inventados, nunca con un embedding real de OpenAI.
- `TranscriptionService.transcribe` (voz) — probado con un servicio que devuelve un string fijo, nunca se llamó a la API de transcripción real.
- El resumen automático de conversación (`ConversationalMemoryService.maybe_compact`), que hace una llamada de texto libre a OpenAI, **no tiene ningún test** que lo ejerza (0% de cobertura en esa función específica).
- El webhook saliente hacia n8n (`N8nClient.dispatch_event`) está probado con `httpx.AsyncClient.post` mockeado — nunca se disparó contra una instancia real de n8n.
- El webhook entrante (`/automations/webhook`) fue probado end-to-end a nivel HTTP, pero simulando el payload que "n8n" mandaría — no existe ningún workflow de n8n real que lo llame.

En síntesis: el **contrato** entre las piezas está validado exhaustivamente; el **comportamiento real de los tres servicios externos** (OpenAI chat, OpenAI embeddings, OpenAI transcripción) no se validó ni una sola vez en todo el desarrollo, porque no hay una `OPENAI_API_KEY` real disponible en este entorno.

---

## 4. Errores o problemas técnicos

Hallazgos concretos de esta revisión, no reportados antes en `PROJECT_STATUS.md`:

1. **Paginación de la API inexistente en la práctica.** `CRUDBase.list()` acepta `limit`/`offset`, pero ningún router los expone como query params — todos los endpoints `GET` de listado (`/tasks`, `/events`, `/projects`, etc.) llaman a `crud.list(db, user_id=user.id)` sin parámetros, lo que fija `limit=100` de forma dura y sin manera de pedir la página siguiente. Un usuario con más de 100 tareas nunca vería el resto ni en la API ni en el dashboard, y no hay ningún indicador de que existan más resultados.
2. **Sin cobertura de test para la compactación de memoria conversacional.** `ConversationalMemoryService.maybe_compact` (la función que resume conversaciones largas) tiene 0% de cobertura — nunca se ejecutó, ni siquiera con mocks.
3. **Campos de texto libre sin límite superior.** `description` en los schemas de `Task`, `Event`, `Project`, `Expense`, y `content` en `InboundAutomationEvent` (el webhook de automatizaciones) no tienen `max_length`. Combinado con la ausencia de límite de tamaño de body a nivel de aplicación, un cliente (o una automatización de n8n mal configurada) puede escribir campos de texto arbitrariamente grandes en la base.
4. **Imagen Docker del frontend corre el servidor de desarrollo, no un build de producción.** `frontend/Dockerfile` termina en `CMD ["npm", "run", "dev"]` — no hay un stage que corra `next build` + `next start`. Tal como está, no es apto para desplegar en producción (el `docker-compose.yml` lo usa a propósito así para desarrollo, pero no existe ninguna variante de producción).
5. **Ambos Dockerfiles corren como `root`**, sin usuario dedicado ni `HEALTHCHECK`. No es explotable por sí solo, pero es una desviación de buenas prácticas de hardening de contenedores.
6. **No existe `.dockerignore`** en ningún lado del repo. `COPY . .` / `COPY backend/ .` copian todo el contexto de build; si alguien construye la imagen localmente con un `.env` real presente (no versionado, pero sí presente en disco), ese archivo puede terminar dentro de una capa de la imagen.
7. **`memory/README.md` es documentación huérfana** — describe un concepto que no tiene relación con el código real de memoria (`backend/app/memory/`). No rompe nada, pero puede confundir a quien lo lea esperando encontrar ahí la implementación.
8. Al iniciar esta auditoría, la suite de tests falló en su totalidad con `ConnectionRefusedError` porque el servicio local de PostgreSQL no estaba corriendo (se había detenido, no es un problema del código). Una vez reiniciado el servicio, los 36 tests pasaron sin cambios de código. Se documenta para que quede claro que **la suite de tests requiere una base de datos activa** y no es autocontenida — no hay una base en memoria ni SQLite de respaldo para correr tests sin infraestructura externa.

---

## 5. Dependencias externas pendientes

(Confirmado, coincide con `docs/PROJECT_STATUS.md` §4, sin cambios desde esa revisión)

1. **OpenAI**: cuenta con billing activo — bloqueante para que cualquier funcionalidad de IA deje de ser simulada.
2. **Hosting** para backend + Postgres + frontend: no hay proveedor contratado.
3. **Instancia de n8n accesible**: no hay ninguna corriendo fuera del `docker-compose.yml` local.
4. **Apps OAuth** en Google Cloud Console / Meta for Developers / Microsoft Entra, según qué integraciones (Gmail, Calendar, WhatsApp, Outlook) se quieran habilitar.
5. **Dominio propio + TLS** para exponer el sistema fuera de `localhost`.

---

## 6. Riesgos de seguridad

Ordenados de mayor a menor relevancia práctica dado que el producto es hoy de un solo usuario, pero relevantes si se expone a internet o se piensa multi-usuario:

1. **27 vulnerabilidades conocidas en dependencias Python pineadas** (`pip-audit` corrido en esta auditoría, contra `requirements.txt`):
   - `PyJWT==2.10.1` — múltiples CVEs/advisories, fix disponible en `2.12.0`+ / `2.13.0`.
   - `python-multipart==0.0.20` — múltiples advisories, fix en `0.0.22`+ (usado por el endpoint de subida de audio y por el parseo de forms de FastAPI).
   - `starlette==0.41.3` (dependencia transitiva de `fastapi==0.115.6`) — múltiples advisories, fix en versiones `0.47.2`+.
   Ninguna de estas se explotó ni se confirmó explotable en este entorno; se reportan porque `pip-audit` las señala como versiones con vulnerabilidades conocidas publicadas. Requiere revisión caso por caso antes de actualizar (algunas de estas fijaciones probablemente correspondan a CVEs de rango de fecha futura a este commit y ameritan doble verificación antes de tratarlas como explotables).
2. **Sin revocación de tokens en el servidor.** El "logout" es enteramente client-side (borra `localStorage`). No existe endpoint de logout en el backend ni una lista de revocación/denylist de JWT. Un refresh token robado sigue siendo válido por sus 30 días completos incluso después de que el usuario "cierra sesión"; la única forma de invalidar tokens masivamente es rotar `JWT_SECRET_KEY`, lo que desloguea a todos los usuarios a la vez.
3. **Comparación no constante en el token del webhook.** `automations.py` compara `x_webhook_token != settings.N8N_WEBHOOK_TOKEN` con el operador estándar de Python, no con `hmac.compare_digest` — teóricamente vulnerable a un ataque de timing para adivinar el token carácter por carácter. De riesgo bajo en la práctica (requiere medir latencia de red con muchísima precisión), pero es una desviación de la práctica recomendada para comparar secretos.
4. **Sin rate limiting en ningún endpoint.** `/auth/login`, `/auth/register` y el endpoint de chat (que dispara una llamada paga a OpenAI por request) no tienen ningún límite de tasa. Expuesto a internet sin un proxy/WAF delante, esto habilita fuerza bruta de contraseñas y abuso de costos de OpenAI.
5. **Tokens JWT en `localStorage`**, no en cookies `httpOnly`. Es un patrón común en SPAs y aceptable para un producto de un solo usuario, pero significa que cualquier XSS futura (hoy no se encontró ninguna — no hay `dangerouslySetInnerHTML` en el frontend) tendría acceso directo a los tokens de acceso y refresco.
6. **Sin verificación de email en el registro.** Cualquiera puede registrarse con cualquier dirección de correo sin probar que le pertenece. No es explotable de forma directa hoy (no hay flujo de "recuperar contraseña" que dependa del email), pero es relevante si se agrega uno.
7. **Sin headers de seguridad HTTP en las respuestas del backend.** El frontend sí los tiene (`next.config.ts`: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`), pero las respuestas de FastAPI no agregan ningún header equivalente.
8. **Endpoint de automatizaciones sin límite de tamaño de payload** (ver hallazgo 3 de la sección 4) — combinado con la falta de rate limiting, es un vector de llenado de disco/base de datos si el token del webhook se filtra.

Sin hallazgos de inyección SQL (todo el acceso a datos pasa por el ORM de SQLAlchemy con parámetros bindeados), sin secretos hardcodeados en el código ni en el historial de git, sin archivos `.env` commiteados.

---

## 7. Qué hace falta para ponerlo a funcionar de verdad

En orden de bloqueo:

1. **Conseguir una `OPENAI_API_KEY` real con billing activo** y correr al menos un smoke test manual de punta a punta (registrarse, mandar un mensaje de chat real, confirmar que el Motor IA interpreta y ejecuta una acción real) — hoy esto literalmente nunca sucedió.
2. **Actualizar `PyJWT`, `python-multipart` y `starlette`/`fastapi`** a versiones sin vulnerabilidades conocidas, revalidando la suite de tests después (hallazgo §6.1).
3. **Decidir y provisionar hosting** para backend, Postgres y frontend; generar un `JWT_SECRET_KEY` real (la app ya rechaza arrancar en producción con el valor por defecto); fijar `CORS_ORIGINS` y `NEXT_PUBLIC_API_URL` al dominio real.
4. **Construir un Dockerfile de frontend de producción real** (`next build` + `next start`, o export estático si aplica) — el actual solo sirve para desarrollo.
5. **Agregar rate limiting** al menos en `/auth/login`, `/auth/register` y el endpoint de chat, antes de exponer el sistema a internet.
6. **Exponer paginación real** en los endpoints de listado (hallazgo §4.1) — funcional, no solo cosmético, en cuanto un usuario acumule más de 100 registros de cualquier entidad.
7. Si se quieren automatizaciones reales: levantar una instancia de n8n con `N8N_ENCRYPTION_KEY` fija, registrar las apps OAuth necesarias (Google/Meta/Microsoft) y construir al menos un workflow real que llame a `/automations/webhook`.
8. Cambiar la comparación del token de webhook a `hmac.compare_digest` y considerar agregar un endpoint de logout con invalidación de refresh tokens antes de operar con más de un usuario real.
