# Auditoría técnica

Commit auditado originalmente: `375d82b` (`main`). Fecha del informe original: 2026-08-10.

Este informe es una revisión independiente del estado real del código — no un resumen de lo que se pretendía construir. Todo hallazgo listado abajo fue verificado ejecutando el código (tests, linters, `pip-audit`, `npm audit`, grep dirigido) durante esta auditoría, no inferido de la documentación previa (`docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`). Donde este informe contradice esos documentos, este es el que refleja la evidencia más reciente.

No se modificó ningún archivo del repositorio para producir este informe original (secciones 1-7 abajo).

---

## 0. Actualización — remediación técnica y de seguridad (2026-08-10)

Se ejecutó una pasada de corrección enfocada exclusivamente en los hallazgos técnicos y de seguridad listados en este documento (secciones 4 y 6). **No se agregó ninguna funcionalidad nueva, no se conectó OpenAI/Google/WhatsApp/n8n reales, y no se modificó el alcance funcional del producto.** Todo lo corregido fue verificado con la suite de tests completa (backend y frontend en verde), `ruff`, `pip-audit`, `npm audit`, `next build` y `alembic check`.

**Corregido en esta pasada:**

- §6.1 — Dependencias vulnerables actualizadas (`PyJWT`, `python-multipart`, `starlette`/`fastapi`, `pytest`/`pytest-asyncio`/`pytest-cov`). `pip-audit` sobre `requirements.txt` y `requirements-dev.txt`: 0 vulnerabilidades conocidas.
- §4.1 — Paginación real (`limit`/`offset` como query params) expuesta en todos los endpoints de listado (`tasks`, `events`, `projects`, `people`, `companies`, `reminders`, `ideas`, `expenses`, `documents`, `tags`, `preferences`, `conversations`).
- §4.2 — Cobertura de test agregada para `ConversationalMemoryService.maybe_compact` (0% → 92%).
- §4.3 — `max_length` agregado a todos los campos de texto libre sin límite superior (`Task`, `Event`, `Project`, `Expense`, `Idea`, `Company`, `Person`, `Document`, y `InboundAutomationEvent.content`).
- §4.4 — `frontend/next.config.ts` ahora usa `output: "standalone"` y `frontend/Dockerfile` fue reescrito como build multi-stage real (`next build` + `node server.js`), ya no corre `npm run dev` en producción.
- §4.5 — Ambos Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`) corren con usuario no-root dedicado y agregan `HEALTHCHECK`.
- §4.6 — Se agregaron `.dockerignore` (raíz y `frontend/`) que excluyen `.env`, `.venv`, `node_modules`, `.git`, caches y directorios no necesarios en runtime.
- §4.7 — `memory/README.md` actualizado para aclarar que es documentación histórica/conceptual y señala `backend/app/memory/` y `docs/ARCHITECTURE.md` §2.5 como la implementación real.
- §6.2 — Revocación de tokens en el servidor: nueva tabla `revoked_tokens` (denylist por `jti`), claim `jti` agregado a todos los JWT, endpoint `POST /auth/logout` que revoca el refresh token, y **rotación de refresh tokens** en `/auth/refresh` (el token usado queda revocado, se emite uno nuevo). El frontend (`Sidebar.tsx`) ahora llama a `/auth/logout` antes de limpiar `localStorage`.
- §6.3 — Comparación del token de webhook (`/automations/webhook`) cambiada a `hmac.compare_digest` (tiempo constante).
- §6.4 — Rate limiting agregado con `slowapi`: `/auth/register` (5/min), `/auth/login` (10/min), `POST /conversations/{id}/messages` (20/min), `/voice/transcribe` (20/min), `/automations/webhook` (30/min). Límites por IP (`get_remote_address`), en memoria (proceso único).
- §6.7 — Headers de seguridad HTTP (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) agregados a todas las respuestas del backend vía middleware, en paridad con los que ya tenía el frontend.
- §6.8 — Ya cubierto indirectamente por la corrección de §4.3 (`InboundAutomationEvent.content` ahora tiene `max_length=200_000`).

**Verificado pero sin poder validarse end-to-end — reportado con honestidad:**

- Los Dockerfiles reescritos (§4.4, §4.5, §4.6) fueron revisados línea por línea y el `next build` standalone se ejecutó y confirmó localmente (`frontend/.next/standalone/server.js` se genera correctamente), pero **no se pudo correr `docker build` end-to-end en este entorno**: el daemon de Docker no tiene salida a Docker Hub (`production.cloudfront.docker.com` devuelve `403` por política de red del entorno de ejecución, confirmado explícitamente contra el proxy). Recomendación: validar el build real de ambas imágenes en un entorno con acceso a un registro de imágenes antes de desplegar a producción.

**Deliberadamente no corregido en esta pasada (fuera de alcance o requiere decisión de producto):**

- §6.5 — Tokens JWT en `localStorage` en lugar de cookies `httpOnly`: cambiar esto es un cambio de arquitectura de autenticación (no un bug), y el propio informe original lo califica de "aceptable para un producto de un solo usuario". No se tocó para no alterar el alcance funcional.
- §6.6 — Sin verificación de email en el registro: agregar esto es una funcionalidad nueva (flujo de verificación), explícitamente fuera de alcance por instrucción directa de no agregar funcionalidades.
- `list_messages` en `conversations.py` se dejó deliberadamente sin paginar (a diferencia del resto de los listados) porque acotarlo podía alterar el comportamiento visible del historial de chat; no estaba nombrado explícitamente como hallazgo en §4.1, que hablaba de los endpoints de listado de entidades.
- El valor por defecto inseguro de `JWT_SECRET_KEY` en `app/core/config.py` (`CHANGE_ME_IN_PRODUCTION`, usado solo si no se define la variable de entorno) se dejó sin tocar a propósito: la app ya rechaza arrancar en producción con ese valor (validado en `_validate_production_secrets`), por lo que es un valor de desarrollo/test intencional, no un hallazgo nombrado en este documento. Sí se alargó el placeholder de `backend/.env.example` a más de 32 bytes para evitar el `InsecureKeyLengthWarning` de PyJWT al copiarlo directamente.
- Hallazgos de la sección 5 (dependencias externas: OpenAI, hosting, n8n, OAuth, dominio/TLS) no son problemas técnicos ni de seguridad corregibles con código — quedan explícitamente pendientes, tal como los describe la sección 5 original.

Detalle completo de qué persiste marcado inline en las secciones 4 y 6 más abajo.

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

1. ✅ **CORREGIDO.** ~~Paginación de la API inexistente en la práctica.~~ `CRUDBase.list()` acepta `limit`/`offset`, pero ningún router los expone como query params — todos los endpoints `GET` de listado (`/tasks`, `/events`, `/projects`, etc.) llaman a `crud.list(db, user_id=user.id)` sin parámetros, lo que fija `limit=100` de forma dura y sin manera de pedir la página siguiente. Un usuario con más de 100 tareas nunca vería el resto ni en la API ni en el dashboard, y no hay ningún indicador de que existan más resultados. **Ahora todos los endpoints de listado exponen `limit`/`offset` como query params** (`Query(default=50, ge=1, le=100)` / `Query(default=0, ge=0)`). `conversations.py::list_messages` se dejó sin paginar deliberadamente (ver §0).
2. ✅ **CORREGIDO.** ~~Sin cobertura de test para la compactación de memoria conversacional.~~ `ConversationalMemoryService.maybe_compact` tenía 0% de cobertura. **Ahora tiene tests dedicados (92% de cobertura en `app/memory/conversational.py`).**
3. ✅ **CORREGIDO.** ~~Campos de texto libre sin límite superior.~~ `description` en los schemas de `Task`, `Event`, `Project`, `Expense`, y `content` en `InboundAutomationEvent` no tenían `max_length`. **Ahora todos tienen `max_length` acorde al tamaño de columna subyacente**, incluido `InboundAutomationEvent.content` (`max_length=200_000`).
4. ✅ **CORREGIDO.** ~~Imagen Docker del frontend corre el servidor de desarrollo, no un build de producción.~~ `frontend/Dockerfile` terminaba en `CMD ["npm", "run", "dev"]`. **`frontend/next.config.ts` ahora usa `output: "standalone"` y el Dockerfile es un build multi-stage real que corre `node server.js`** (verificado con `next build` local; el `docker build` en sí no pudo ejecutarse en este entorno, ver §0).
5. ✅ **CORREGIDO.** ~~Ambos Dockerfiles corren como `root`, sin usuario dedicado ni `HEALTHCHECK`.~~ **Ambos Dockerfiles ahora crean y usan un usuario no-root dedicado y definen `HEALTHCHECK`.**
6. ✅ **CORREGIDO.** ~~No existe `.dockerignore` en ningún lado del repo.~~ **Se agregaron `.dockerignore` en la raíz y en `frontend/`**, excluyendo `.env`, `.venv`, `node_modules`, `.git`, caches, etc.
7. ✅ **CORREGIDO.** ~~`memory/README.md` es documentación huérfana.~~ **Se actualizó para aclarar que es material histórico/conceptual y apunta a `backend/app/memory/` y `docs/ARCHITECTURE.md` §2.5 como la implementación real.**
8. **PENDIENTE (no es un problema de código).** Al iniciar la auditoría original, la suite de tests falló en su totalidad con `ConnectionRefusedError` porque el servicio local de PostgreSQL no estaba corriendo. Sigue siendo así: **la suite de tests requiere una base de datos activa** y no es autocontenida. Esto no es un bug corregible — es una característica de la arquitectura elegida (Postgres + pgvector real, sin doble en memoria) y no se modificó.

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

1. ✅ **CORREGIDO.** ~~27 vulnerabilidades conocidas en dependencias Python pineadas~~ (`pip-audit` corrido en la auditoría original, contra `requirements.txt`):
   - `PyJWT==2.10.1` — múltiples CVEs/advisories, fix disponible en `2.12.0`+ / `2.13.0`.
   - `python-multipart==0.0.20` — múltiples advisories, fix en `0.0.22`+ (usado por el endpoint de subida de audio y por el parseo de forms de FastAPI).
   - `starlette==0.41.3` (dependencia transitiva de `fastapi==0.115.6`) — múltiples advisories, fix en versiones `0.47.2`+.
   **Actualizado: `fastapi` 0.115.6→0.141.1, `starlette` fijado explícitamente en `1.6.0`, `PyJWT` 2.10.1→2.13.0, `python-multipart` 0.0.20→0.0.32 (también `pytest`/`pytest-asyncio`/`pytest-cov` en `requirements-dev.txt`). `pip-audit` re-ejecutado sobre ambos archivos tras la actualización: 0 vulnerabilidades conocidas. Suite completa de tests re-verificada en verde tras el cambio.**
2. ✅ **CORREGIDO.** ~~Sin revocación de tokens en el servidor.~~ El "logout" era enteramente client-side. **Se agregó una tabla `revoked_tokens` (denylist por `jti`), claim `jti` en todos los JWT emitidos, endpoint `POST /auth/logout` que revoca el refresh token entregado, y rotación de refresh tokens en `POST /auth/refresh`** (el refresh token usado se revoca inmediatamente y se emite un par nuevo, de forma que un refresh token robado y ya usado por el dueño legítimo deja de servir). El frontend llama a `/auth/logout` antes de limpiar `localStorage`. Migración de Alembic generada y aplicada (`fca0430c1e9a_agregar_tabla_revoked_tokens`).
3. ✅ **CORREGIDO.** ~~Comparación no constante en el token del webhook.~~ `automations.py` comparaba el token con `!=` estándar. **Ahora usa `hmac.compare_digest`.**
4. ✅ **CORREGIDO.** ~~Sin rate limiting en ningún endpoint.~~ **Se agregó rate limiting con `slowapi` (por IP, en memoria) en los endpoints sensibles/costosos**: `/auth/register` (5/min), `/auth/login` (10/min), `POST /conversations/{id}/messages` (20/min), `/voice/transcribe` (20/min), `/automations/webhook` (30/min). Nota: al ser en memoria y por proceso, no persiste entre reinicios ni se comparte entre múltiples workers/instancias — suficiente para un despliegue de proceso único, pero requeriría un backend compartido (Redis) si se escala horizontalmente.
5. **PENDIENTE (decisión de arquitectura, no un bug).** Tokens JWT en `localStorage`, no en cookies `httpOnly`. Es un patrón común en SPAs y aceptable para un producto de un solo usuario, pero significa que cualquier XSS futura tendría acceso directo a los tokens. No se tocó en esta pasada porque migrar a cookies `httpOnly` es un cambio de arquitectura de autenticación, no una corrección puntual, y no estaba dentro del alcance de "corregir problemas técnicos y de seguridad ya identificados" sin alterar el alcance funcional.
6. **PENDIENTE (requiere funcionalidad nueva, fuera de alcance).** Sin verificación de email en el registro. Agregar esto implica un flujo nuevo (envío de email, endpoint de confirmación), explícitamente excluido por la instrucción de no agregar funcionalidades.
7. ✅ **CORREGIDO.** ~~Sin headers de seguridad HTTP en las respuestas del backend.~~ **Se agregó un middleware (`SecurityHeadersMiddleware`) que agrega `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: strict-origin-when-cross-origin` a toda respuesta**, en paridad con los headers que ya tenía el frontend.
8. ✅ **CORREGIDO** (indirectamente, junto con §4.3). ~~Endpoint de automatizaciones sin límite de tamaño de payload.~~ `InboundAutomationEvent.content` ahora tiene `max_length=200_000`, acotando el tamaño máximo de un evento de webhook individual. No se agregó un límite de tamaño de body a nivel de aplicación (ASGI) para *todos* los endpoints — ese es un endurecimiento más amplio, no nombrado específicamente en este hallazgo, y se deja fuera de esta pasada.

Sin hallazgos de inyección SQL (todo el acceso a datos pasa por el ORM de SQLAlchemy con parámetros bindeados), sin secretos hardcodeados en el código ni en el historial de git, sin archivos `.env` commiteados.

---

## 7. Qué hace falta para ponerlo a funcionar de verdad

En orden de bloqueo:

1. **Conseguir una `OPENAI_API_KEY` real con billing activo** y correr al menos un smoke test manual de punta a punta (registrarse, mandar un mensaje de chat real, confirmar que el Motor IA interpreta y ejecuta una acción real) — hoy esto literalmente nunca sucedió.
2. ✅ **CORREGIDO (2026-08-10).** ~~Actualizar `PyJWT`, `python-multipart` y `starlette`/`fastapi`~~ a versiones sin vulnerabilidades conocidas — ver §0 y §6.1.
3. **Sigue pendiente.** Decidir y provisionar hosting para backend, Postgres y frontend; generar un `JWT_SECRET_KEY` real; fijar `CORS_ORIGINS` y `NEXT_PUBLIC_API_URL` al dominio real. (No es corregible con código — requiere decisiones de infraestructura fuera del alcance de esta pasada.)
4. ✅ **CORREGIDO (2026-08-10).** ~~Construir un Dockerfile de frontend de producción real~~ — ver §0 y §4.4. Nota: el `docker build` no se validó end-to-end en este entorno (sin acceso a registro de imágenes), aunque el `next build` standalone sí se verificó localmente.
5. ✅ **CORREGIDO (2026-08-10).** ~~Agregar rate limiting~~ al menos en `/auth/login`, `/auth/register` y el endpoint de chat — ver §0 y §6.4 (se cubrieron también `/voice/transcribe` y `/automations/webhook`).
6. ✅ **CORREGIDO (2026-08-10).** ~~Exponer paginación real~~ en los endpoints de listado — ver §0 y §4.1.
7. **Sigue pendiente.** Si se quieren automatizaciones reales: levantar una instancia de n8n con `N8N_ENCRYPTION_KEY` fija, registrar las apps OAuth necesarias (Google/Meta/Microsoft) y construir al menos un workflow real que llame a `/automations/webhook`. (Explícitamente fuera de alcance por instrucción directa de no conectar servicios externos todavía.)
8. ✅ **CORREGIDO (2026-08-10).** ~~Cambiar la comparación del token de webhook a `hmac.compare_digest` y considerar agregar un endpoint de logout con invalidación de refresh tokens~~ — ver §0, §6.2 y §6.3.
