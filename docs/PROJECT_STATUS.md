# Estado del proyecto

Última actualización: revisión del código en `main` al commit `8ab6130`.

Este documento es un inventario honesto de qué funciona de verdad, qué está a medio camino y qué no existe todavía. Para el diseño técnico ver `docs/ARCHITECTURE.md`; para la visión de producto, `product/`.

---

## 1. Terminado

Verificado con tests automatizados y/o pruebas manuales end-to-end (Playwright contra la app real).

### Backend
- **Monorepo, Docker Compose, CI**: backend (FastAPI), frontend (Next.js), Postgres+pgvector, n8n. GitHub Actions corre lint + tests en cada push.
- **Modelo de datos completo**: 14 entidades (`Usuario`, `Persona`, `Empresa`, `Proyecto`, `Conversación`, `Mensaje`, `Tarea`, `Evento`, `Recordatorio`, `Idea`, `Gasto`, `Documento`, `Etiqueta`, `Preferencia`) + `MemoryEmbedding`. Migraciones de Alembic aplicadas y sin drift.
- **Autenticación**: registro, login, refresh de JWT, `bcrypt` para contraseñas. Endpoints protegidos.
- **Motor IA**: interpretación de mensajes 100% vía OpenAI Structured Outputs (`AssistantInterpretation`), sin parseo de texto libre. Probado con cliente de OpenAI simulado (ver §3).
- **Memoria en 3 capas**: estructurada (snapshot de Postgres), semántica (embeddings + `pgvector`, búsqueda por similitud coseno), conversacional (historial + resumen automático al superar 30 mensajes). Degrada con gracia si la capa semántica falla.
- **Ejecución de acciones**: creación de tareas/eventos/recordatorios/ideas/gastos, find-or-create de personas/empresas/proyectos mencionados, completar tarea por referencia difusa.
- **API REST completa**: CRUD para las 11 entidades que lo requieren, aislado por usuario (verificado en tests), endpoint de chat que orquesta todo el pipeline.
- **Transcripción de voz**: `POST /voice/transcribe`, probado con servicio de transcripción simulado.
- **Automatizaciones**: webhook entrante genérico (`/automations/webhook`, con autenticación por token) y dispatcher saliente hacia n8n (no-op seguro si n8n no está configurado).
- **Tests backend**: 36 tests con `pytest`, 82% de cobertura, corridos contra Postgres+pgvector real.
- **Hardening**: falla al arrancar si `ENVIRONMENT=production` con el `JWT_SECRET_KEY` por defecto; `/docs` deshabilitado en producción; CORS restringido por config.

### Frontend
- **PWA real**: manifest, íconos, service worker con cache de shell — instalable.
- **Chat estilo ChatGPT**: sidebar con conversaciones, historial de mensajes, envío de texto.
- **Botón de audio funcional**: graba con `MediaRecorder`, transcribe contra el backend, envía el texto como mensaje.
- **Dashboard**: tareas/eventos/recordatorios/ideas agrupados por semáforo (🔴🟡🟢).
- **Auth**: login, registro, JWT con refresh automático en el cliente HTTP.
- **Tests frontend**: 7 tests con Vitest (auth-store, `PriorityBadge`).

---

## 2. Parcialmente terminado

Existe el código y la arquitectura está lista, pero falta la pieza externa (credenciales, datos, o ejecución real) para darlo por completo.

| Área | Qué hay | Qué falta |
|---|---|---|
| **Motor IA / embeddings / transcripción** | Código completo, contrato validado, manejo de errores probado | Nunca se ejecutó contra la API real de OpenAI — todos los tests usan un cliente simulado porque no hay `OPENAI_API_KEY` configurada en este entorno |
| **Integraciones externas (Gmail, Calendar, WhatsApp, Drive, Slack, Outlook)** | Contrato de integración genérico y funcional (`/automations/webhook` + `N8nClient`), `Document` como destino normalizado, indexado automático en memoria semántica | Cero workflows de n8n creados; cero apps OAuth registradas en Google/Meta/Microsoft; nadie probó el camino con datos reales de un proveedor |
| **n8n** | Servicio en `docker-compose.yml`, contrato de webhook definido en ambas direcciones | Nunca se levantó una instancia real ni se armó un workflow; no hay `N8N_ENCRYPTION_KEY` fijada (n8n genera una al azar si falta, lo que rompe la persistencia de credenciales entre reinicios si no se fija a mano) |
| **Despliegue / hosting** | Docker Compose funcional para desarrollo local, Dockerfiles de producción para backend y frontend | No hay ambiente de staging/producción real desplegado en ningún proveedor; no hay dominio, HTTPS, ni backups configurados |
| **Recordatorios como notificaciones reales** | El modelo `Reminder` y su CRUD existen y funcionan | No hay ningún mecanismo que dispare la notificación en el momento (`remind_at`) — hoy es solo un registro que el usuario puede consultar, no hay scheduler ni push notification |

---

## 3. Falta desarrollar

Cosas que no tienen código todavía, más allá de estar habilitado el terreno para construirlas.

- **Rate limiting** en la API (nada impide hoy hacer spam de requests a `/auth/login` o al endpoint de chat).
- **Scheduler/worker en background** para recordatorios y para cualquier tarea proactiva ("preparación de reuniones", "anticipación de tareas" — Fase 5 del roadmap de `docs/Roadmap.md`). Todo el sistema actual es puramente reactivo a requests HTTP.
- **Notificaciones push** (Web Push) hacia el navegador/PWA — el service worker actual solo cachea assets, no maneja `push`/`notificationclick`.
- **Ingesta de PDF/imágenes** mencionada como entrada futura en `product/01_PRODUCT.md` — no hay endpoint ni lógica para procesar adjuntos, solo el modelo `Document` como contenedor de texto ya extraído.
- **OAuth propio del backend** para que el usuario conecte su cuenta de Google/Microsoft/Meta desde la UI — hoy la única vía de integración es que un tercero (n8n) ya tenga las credenciales y llame al webhook genérico.
- **Panel de administración de integraciones** (ver qué automatizaciones están conectadas, activarlas/desactivarlas desde la UI).
- **Exportación de datos del usuario** (principio de `docs/Principios.md`: "el usuario es dueño de sus datos, toda la información debe ser exportable") — no hay endpoint de export.
- **Ambiente de staging/producción**, dominio, certificados, pipeline de deploy automático (el CI solo corre lint/tests, no despliega).

---

## 4. Dependencias externas que faltan

Servicios/cuentas que hay que crear o contratar para que el sistema funcione más allá de un entorno local:

1. **OpenAI**: cuenta con billing activo (usado para chat, embeddings y transcripción de audio).
2. **Proveedor de hosting** para backend + Postgres + frontend (ej. Railway, Fly.io, Render, un VPS propio, o servicios separados tipo Vercel + Supabase). No hay ninguno contratado todavía.
3. **Instancia de n8n accesible públicamente** (o self-hosted) si se quiere usar automatizaciones — hoy solo existe la definición en `docker-compose.yml` para desarrollo local.
4. **Apps OAuth registradas** en Google Cloud Console (Gmail + Calendar + Drive), Meta for Developers (WhatsApp Business API) y/o Microsoft Entra (Outlook/Calendar), según qué integraciones se quieran habilitar.
5. **Dominio propio** y certificado TLS para exponer el backend/frontend fuera de `localhost`.

---

## 5. APIs / variables de entorno que faltan configurar

Todas están declaradas en `backend/.env.example` y `frontend/.env.local.example`; lo que falta es completarlas con valores reales fuera de desarrollo local.

### Backend (`backend/.env`)

| Variable | Estado actual | Acción requerida |
|---|---|---|
| `OPENAI_API_KEY` | vacía | completar con una key real — **bloqueante para que el Motor IA funcione** |
| `JWT_SECRET_KEY` | valor de ejemplo (`CHANGE_ME_IN_PRODUCTION`) | generar un secreto real antes de correr con `ENVIRONMENT=production` (la app rechaza arrancar si no se cambia) |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | apuntan a `db` (nombre del servicio en Docker Compose) | actualizar al host de Postgres real en producción |
| `N8N_BASE_URL` | vacía | completar con la URL de la instancia de n8n si se quieren automatizaciones activas (si queda vacía, el sistema sigue funcionando sin automatizaciones) |
| `N8N_WEBHOOK_TOKEN` | vacía | definir un token compartido entre el backend y los workflows de n8n |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | agregar el dominio real del frontend en producción |

### Frontend (`frontend/.env.local`)

| Variable | Estado actual | Acción requerida |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | actualizar a la URL pública del backend en producción |

### n8n (`docker-compose.yml`)

| Variable | Estado actual | Acción requerida |
|---|---|---|
| `N8N_ENCRYPTION_KEY` | no está definida | fijar un valor propio antes de usar n8n en serio (sin esto, n8n genera una clave al azar en cada arranque y las credenciales guardadas se vuelven ilegibles al reiniciar) |
| Credenciales por integración (Gmail, Calendar, WhatsApp, etc.) | no existen | se configuran dentro de n8n una vez que haya apps OAuth registradas (ver §4) |
