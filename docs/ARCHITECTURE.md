# Arquitectura técnica

Este documento describe la arquitectura del sistema tal como está implementado en el código (no el diseño aspiracional de `product/` o `docs/Arquitectura.md`, que son la visión funcional). Está pensado como referencia para quien tenga que tocar el código.

---

## 1. Visión general

El sistema tiene tres componentes desplegables y una pieza de infraestructura opcional:

```
┌─────────────┐      HTTPS/JSON       ┌──────────────┐      SQL/asyncpg      ┌──────────────────┐
│   Frontend   │ ────────────────────▶│   Backend    │ ─────────────────────▶│   PostgreSQL      │
│  Next.js PWA │◀──────────────────── │   FastAPI    │◀───────────────────── │   + pgvector      │
└─────────────┘      JWT (Bearer)     └──────┬───────┘                       └──────────────────┘
                                              │
                                              │ HTTPS
                                              ▼
                                    ┌──────────────────┐        webhooks       ┌──────────────┐
                                    │   OpenAI API      │                       │     n8n      │
                                    │ (chat/embeddings/  │◀─────────────────────│ (opcional)   │
                                    │  transcripción)    │────────────────────▶ │              │
                                    └──────────────────┘                       └──────────────┘
```

- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind, PWA instalable. Cliente puro: no tiene lógica de negocio, solo consume la API REST.
- **Backend**: FastAPI (Python 3.11, async). Orquesta todo: autenticación, interpretación de mensajes, memoria, persistencia y automatizaciones. Es el único componente que habla con OpenAI y con la base de datos.
- **PostgreSQL + pgvector**: única fuente de verdad. `pgvector` se usa para memoria semántica (embeddings).
- **n8n**: infraestructura opcional para automatizaciones con servicios externos (Gmail, Calendar, WhatsApp, Slack, etc.). El backend nunca depende de que esté disponible.

Principio rector (de `product/02_ARQUITECTURA.md`): *"la IA interpreta, la base conserva"*. Ningún dato se pierde ni se decide únicamente en memoria del modelo de lenguaje; toda acción de la IA se traduce a escrituras explícitas en Postgres.

---

## 2. Backend (`backend/app`)

### 2.1 Estructura por capas

```
app/
├── main.py              # instancia FastAPI, middlewares, exception handler
├── core/                 # configuración, seguridad (JWT/bcrypt), logging
├── db/                   # engine async, sesión, Base declarativa, mixins
├── models/                # modelos SQLAlchemy (ORM) — el esquema real
├── schemas/               # modelos Pydantic de entrada/salida de la API
├── ai/                    # Motor IA: cliente OpenAI, prompts, Structured Outputs
├── memory/                # las 3 capas de memoria
├── services/              # lógica de negocio (CRUD genérico, ejecución de acciones, auth)
├── integrations/          # clientes hacia sistemas externos (n8n)
└── api/v1/endpoints/       # routers HTTP, uno por recurso
```

Esta separación sigue Clean Architecture de forma pragmática: `models` y `db` no saben nada de HTTP; `schemas` son el contrato público de la API y nunca se exponen los modelos ORM directamente; `services`/`ai`/`memory` contienen la lógica de negocio y son invocables sin FastAPI (de hecho así se prueban); `api/` es la capa más externa, solo orquesta dependencias y traduce a HTTP.

### 2.2 Autenticación

JWT de dos tokens (`app/core/security.py`):

- **Access token**: 30 min, se manda en `Authorization: Bearer`.
- **Refresh token**: 30 días, se usa solo contra `POST /auth/refresh` para pedir un par nuevo.
- Contraseñas con `bcrypt` (nunca se guarda texto plano ni se usa un hash reversible).
- `app/api/deps.py` expone `get_current_active_user`, la dependencia que protege cada endpoint.

### 2.3 Modelo de datos (`app/models/`)

14 entidades mínimas requeridas + memoria semántica:

| Modelo | Notas |
|---|---|
| `User` | dueño de todo el resto de las entidades |
| `Person`, `Company` | contactos y organizaciones, referenciables desde otras entidades por nombre |
| `Project` | agrupa tareas/eventos/ideas/gastos; tiene `status` y `priority` |
| `Conversation`, `Message` | historial de chat; `Message` es inmutable (solo `created_at`, sin `updated_at`) |
| `Task`, `Event`, `Reminder`, `Idea`, `Expense` | las "salidas" del producto, cada una con semáforo de prioridad donde aplica |
| `Document` | archivos o contenido entrante (uploads, o inyectado vía automatizaciones) |
| `Tag` + `EntityTag` | etiquetado polimórfico: una tabla de asociación genérica (`entity_type` + `entity_id`) en vez de una tabla de join por entidad |
| `Preference` | pares clave/valor (JSONB) por usuario, con flag `learned_automatically` |
| `MemoryEmbedding` | memoria semántica (ver §4.2) |

Convenciones (`app/db/base.py`):

- `UUIDMixin`: primary key `UUID` generada en Python (`uuid4`), no serial.
- `TimestampMixin`: `created_at`/`updated_at` con `server_default=now()`.
- `SoftDeleteMixin`: columna `deleted_at` nullable. Todo lo que se puede "eliminar" desde la UI hace soft-delete, nunca `DELETE` físico — esto es lo que sostiene el principio del producto de que **toda acción debe poder deshacerse**. `Tag` y `Preference` son la excepción deliberada (no tienen historial que preservar).
- Relaciones circulares entre modelos se resuelven con imports bajo `TYPE_CHECKING` (evita import cíclico en runtime, mantiene el tipado para IDEs/mypy).

Las migraciones viven en `backend/alembic/`, generadas con `alembic revision --autogenerate` y aplicadas con `alembic upgrade head`. `alembic/env.py` importa `app.models.Base` para que el autogenerate vea todas las tablas.

### 2.4 Motor IA (`app/ai/`)

Contrato único de interpretación, sin excepciones:

```
AIEngine.interpret_message(user_message, conversation_history, memory_context)
        │
        ▼
OpenAI chat.completions.parse(response_format=AssistantInterpretation)
        │
        ▼
AssistantInterpretation {
  reply: str
  priority: rojo | amarillo | verde
  actions: list[AssistantAction]
  needs_clarification: bool
}
```

`AssistantAction` (`app/ai/schemas.py`) representa **cualquier** acción posible (crear tarea, evento, recordatorio, idea, gasto, persona, empresa, proyecto, o completar una tarea existente) con un único modelo de campos nullable — no una unión discriminada — porque es el patrón que recomienda OpenAI para Structured Outputs en modo estricto (todo campo debe figurar en `required`, incluso los que son `null` para un `type` dado).

Esto es lo que garantiza la directiva *"nunca parsear texto libre"*: el SDK de OpenAI valida la respuesta contra un JSON Schema estricto y la parsea a Pydantic; el backend nunca hace regex ni parsing manual sobre la respuesta del modelo.

`app/ai/prompts.py` carga `prompts/system_prompt.md` (raíz del repo) como prompt de sistema — no se duplica el texto en el código; si el archivo no está disponible (por ejemplo en un contexto de build atípico) cae a un fallback embebido idéntico.

`app/ai/embeddings.py` y `app/ai/transcription.py` son los otros dos usos de la API de OpenAI (embeddings para memoria semántica, transcripción de audio). Los tres módulos comparten `app/ai/client.py` (`AsyncOpenAI` cacheado con `lru_cache`).

### 2.5 Memoria (`app/memory/`)

Tres capas independientes, combinadas por `MemoryContextBuilder` (`orchestrator.py`) antes de cada llamada al Motor IA:

1. **Estructurada** (`structured.py`): no almacena nada nuevo — construye un snapshot de texto plano a partir de Postgres (tareas pendientes ordenadas por prioridad, próximos eventos, recordatorios, proyectos activos, preferencias). Es la memoria que nunca falla porque es la misma base transaccional.
2. **Semántica** (`semantic.py`): embeddings (`pgvector`) de cualquier entidad indexada — se guarda un `MemoryEmbedding` por entidad (upsert por `source_type` + `source_id`), y se recupera por similitud coseno (`embedding.cosine_distance(query_vector)` de SQLAlchemy + `pgvector`). Índice HNSW (`vector_cosine_ops`) para que la búsqueda escale.
3. **Conversacional** (`conversational.py`): historial de `Message` de la conversación activa (últimos 20 turnos) más un resumen (`Conversation.summary`) que se regenera automáticamente cuando la conversación supera 30 mensajes, comprimiendo los más viejos vía una llamada de texto libre a OpenAI (acá sí es texto libre porque es un resumen, no una extracción de acciones — no hay parsing posterior de esa salida).

Diseño defensivo importante: si la memoria semántica falla (sin red, sin cuota, `EmbeddingError`), `MemoryContextBuilder.build()` lo captura y sigue con lo que la memoria estructurada pudo construir — la conversación **nunca** se cae por un fallo de OpenAI en esta capa (bug real encontrado y corregido durante el desarrollo).

### 2.6 Ejecución de acciones (`app/services/action_executor.py`)

`ActionExecutor` es la única capa autorizada a traducir una `AssistantAction` en escrituras reales. Por cada tipo de acción:

- Resuelve `related_project_name` / `related_person_name` / `related_company_name` con **find-or-create** (busca por nombre exacto dentro del usuario; si no existe, lo crea e indexa en memoria semántica). Así ninguna mención en una conversación se pierde, aunque la entidad no exista todavía.
- `completar_tarea` busca la tarea existente más parecida por `ILIKE` sobre el título (`target_reference`); si no encuentra ninguna, crea una tarea ya completada como registro (nunca descarta la intención del usuario).
- Al crear una tarea con prioridad `rojo` o un evento, dispara un evento hacia n8n (best-effort, no bloqueante — ver §5).
- Cada creación relevante se indexa en memoria semántica (`_index`), con manejo de errores propio para que un fallo de indexado no rompa la acción principal.

### 2.7 API (`app/api/v1/`)

- Un router por recurso (`people`, `companies`, `projects`, `tasks`, `events`, `reminders`, `ideas`, `expenses`, `documents`, `tags`, `preferences`) construido sobre `CRUDBase` genérico (`app/services/crud_base.py`): list/get/create/update/delete parametrizado por modelo + schemas Pydantic, con soft-delete automático cuando el modelo lo soporta y scoping por `user_id` en cada query (aislamiento entre usuarios verificado en tests).
- `conversations.py` es el router central: además del CRUD de conversaciones, expone `POST /conversations/{id}/messages`, que orquesta todo el flujo de chat (persistir mensaje → construir contexto de memoria → Motor IA → persistir respuesta → ejecutar acciones → compactar memoria conversacional si corresponde).
- `voice.py`: `POST /voice/transcribe`, recibe un archivo de audio (`UploadFile`), lo manda a `TranscriptionService` y devuelve texto — nunca interpreta ahí mismo, el texto transcripto se manda después al mismo pipeline de chat que un mensaje de texto.
- `automations.py`: `POST /automations/webhook`, punto de entrada único para integraciones externas vía n8n (ver §5).

Todas las respuestas se validan contra `schemas/*.py` (nunca se serializa un modelo ORM directamente), y toda dependencia de negocio (`AIEngine`, `MemoryContextBuilder`, `ActionExecutor`, etc.) se inyecta vía funciones `get_*` en `app/api/deps.py` — lo que permite reemplazarlas en tests con `app.dependency_overrides` sin tocar el código de producción.

---

## 3. Frontend (`frontend/src`)

Next.js 16 (App Router), un cliente delgado sobre la API REST — toda la lógica de negocio vive en el backend.

```
app/
├── layout.tsx, page.tsx, manifest.ts       # shell, redirect inicial según sesión, manifest PWA
├── login/, register/                        # auth
└── (app)/                                    # route group protegido (no agrega segmento a la URL)
    ├── layout.tsx                            # valida sesión, redirige a /login si no hay token
    ├── chat/page.tsx                         # estado vacío / crear conversación
    ├── chat/[conversationId]/page.tsx         # chat real
    └── dashboard/page.tsx                     # listas agrupadas por semáforo

components/    Sidebar, MessageBubble, MessageInput (con grabación de audio), PriorityBadge
lib/           api.ts (cliente HTTP + refresh de JWT), auth-store.ts (zustand), types.ts
```

Decisiones relevantes:

- **Estado de auth**: `zustand` + `localStorage` (`lib/auth-store.ts`). El cliente HTTP (`lib/api.ts`) intercepta 401, pide un access token nuevo con el refresh token, y reintenta la request una sola vez.
- **PWA real**: `app/manifest.ts` (convención de Next.js, genera `manifest.webmanifest`), `public/sw.js` (service worker con cache de shell, registrado desde un client component), íconos 192/512 reales.
- **Voz**: `MessageInput` usa `MediaRecorder` del navegador, sube el blob a `/voice/transcribe`, y el texto transcripto se envía como un mensaje más (mismo endpoint de chat que un mensaje escrito).
- **Next.js 16**: `params`/`searchParams` de las páginas son `Promise` — donde hace falta leer un parámetro de ruta en un Client Component se usa el hook `useParams()` en vez de recibir la prop `params` (que requeriría `use()` para desenvolver la promesa en un componente cliente).

---

## 4. Infraestructura

`docker-compose.yml` define cuatro servicios: `db` (`pgvector/pgvector:pg16`), `backend`, `frontend`, `n8n`. El build del backend usa como contexto la raíz del repo (no `backend/`) específicamente para poder copiar `prompts/` dentro de la imagen sin duplicar ese contenido.

CI (`.github/workflows/ci.yml`): dos jobs independientes.

- **backend**: levanta un servicio de Postgres con pgvector, habilita la extensión, corre `ruff check`, aplica las migraciones y corre `pytest --cov=app`.
- **frontend**: `npm run lint`, `npm run test` (Vitest), `npm run build`.

---

## 5. Automatizaciones (n8n)

El backend nunca asume que n8n está corriendo:

- **Saliente** (`app/integrations/n8n_client.py`): `N8nClient.dispatch_event(event_type, payload)` hace `POST {N8N_BASE_URL}/webhook/{event_type}`. Si `N8N_BASE_URL` no está configurado, es un no-op silencioso; si la request falla, se loguea el error pero nunca se propaga (una automatización caída no puede romper la acción principal del usuario).
- **Entrante** (`POST /api/v1/automations/webhook`): contrato único y normalizado (`user_email`, `source`, `title`, `content`) protegido por un token compartido (`N8N_WEBHOOK_TOKEN`, header `x-webhook-token`). Cualquier integración real (Gmail, Drive, WhatsApp, Slack, Outlook) se resuelve como un workflow de n8n que traduce el evento nativo del proveedor a este contrato; el backend lo persiste como `Document` y lo indexa en memoria semántica. Así, conectar una integración nueva no requiere tocar el backend, solo agregar un workflow.

---

## 6. Testing

- **Backend**: `pytest` + `pytest-asyncio`, contra una base Postgres+pgvector real (nunca mocks de base de datos) con `OpenAI` mockeado. Aislamiento entre tests por email único (`uuid4`) en vez de transacciones anidadas o triggers de limpieza.
  - Nota técnica: el engine async usa `NullPool` cuando corre bajo pytest (detectado con `"pytest" in sys.modules`, ver `app/db/session.py`), porque `TestClient` y los fixtures async de `pytest-asyncio` pueden correr en event loops distintos; un pool con conexiones persistentes termina reusando una conexión de un loop ya cerrado.
- **Frontend**: `vitest` + `@testing-library/react`, cobertura mínima pero real (lógica de `auth-store`, render de `PriorityBadge`).

---

## 7. Seguridad

- JWT con expiración corta para access token (30 min) y refresh token de larga duración (30 días) que solo sirve para pedir un par nuevo.
- Contraseñas con `bcrypt`.
- El arranque de la app **falla** si `ENVIRONMENT=production` y `JWT_SECRET_KEY` sigue en su valor por defecto (`app/core/config.py`, validador de Pydantic).
- Documentación interactiva (`/docs`) deshabilitada en producción.
- CORS restringido a `CORS_ORIGINS` (por defecto solo `localhost:3000`).
- Headers de seguridad HTTP en el frontend (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) vía `next.config.ts`.
- Todo endpoint de escritura valida que el recurso pertenezca al usuario autenticado (scoping por `user_id` en cada query de `CRUDBase`).

## 8. Deuda técnica conocida

- No hay rate limiting en la API.
- Las integraciones reales con Gmail/Calendar/WhatsApp no están conectadas — requieren credenciales OAuth que no se pueden generar desde este entorno; el contrato de integración (§5) ya está listo para recibirlas vía n8n.
- Sin OpenAI API key configurada, todo el pipeline de IA fue validado con mocks; falta una corrida end-to-end contra la API real.
