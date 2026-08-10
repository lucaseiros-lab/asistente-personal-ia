# Asistente Personal IA

> Un Secretario Ejecutivo basado en Inteligencia Artificial.

## Visión

El objetivo de este proyecto es construir un asistente personal inteligente que reduzca la carga mental del usuario.

No pretende ser un chatbot.

No pretende ser simplemente una agenda.

No pretende ser un gestor de tareas.

Su función es actuar como un Secretario Ejecutivo Digital capaz de comprender información en lenguaje natural, recordar contexto, priorizar automáticamente, anticipar necesidades y ayudar al usuario a tomar decisiones.

---

# Objetivos

El asistente deberá ser capaz de:

- Comprender mensajes escritos y de voz.
- Detectar automáticamente la intención del usuario.
- Registrar tareas, recordatorios, eventos, gastos, ideas y notas.
- Organizar la información por proyectos y contexto.
- Recordar conversaciones anteriores.
- Priorizar automáticamente la información.
- Anticipar acciones futuras.
- Integrarse con calendarios, correo electrónico, contactos y otras herramientas.
- Aprender las preferencias del usuario.

---

# Filosofía

El sistema debe actuar como un Chief of Staff personal.

Su objetivo principal es reducir el esfuerzo cognitivo del usuario.

Debe decidir qué información mostrar y en qué momento.

El usuario no debería tener que organizar manualmente sus tareas.

---

# Principios

- Voz como método principal de entrada.
- Texto como alternativa equivalente.
- Mostrar únicamente la información relevante.
- Priorizar automáticamente.
- Nunca pedir información que ya conoce.
- Toda acción debe poder deshacerse.
- Los datos pertenecen al usuario.
- Arquitectura modular.
- Memoria persistente.
- Explicar siempre las acciones realizadas.

---

# Estado del proyecto

🚧 En desarrollo activo (ver `product/` para directivas y arquitectura).

## Cómo correr el proyecto

Requisitos: Docker y Docker Compose.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# completar OPENAI_API_KEY y JWT_SECRET_KEY en backend/.env

docker compose up --build
```

- Backend: http://localhost:8000 (docs interactivas en `/docs`)
- Frontend: http://localhost:3000

Las migraciones de base de datos (Alembic) se aplican automáticamente al iniciar el contenedor `backend`.

### Desarrollo sin Docker

```bash
# Backend
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
. .venv/bin/activate
pytest
```

La suite normal (`pytest`) usa siempre dobles de prueba (`unittest.mock`) para las llamadas a OpenAI — nunca pega contra la API real ni consume crédito. Requiere una base Postgres con `pgvector` accesible vía `DATABASE_URL`.

#### Pruebas end-to-end contra la API real de OpenAI

`backend/tests/test_openai_e2e.py` ejercita `AIEngine`, `EmbeddingService`, `TranscriptionService` y el endpoint de chat completo contra la API real de OpenAI (sin mocks). Se saltean automáticamente salvo que se corran así:

```bash
cd backend
. .venv/bin/activate
OPENAI_API_KEY=sk-... RUN_OPENAI_E2E_TESTS=1 pytest tests/test_openai_e2e.py -v
```

Hacen llamadas reales y pagas (chat, embeddings, texto-a-voz y transcripción), así que no corren en la suite normal ni en CI.

---

# Roadmap

## Fase 1

Diseño funcional.

## Fase 2

Arquitectura técnica.

## Fase 3

MVP.

- Audio
- Texto
- Recordatorios
- Agenda
- Gastos
- Prioridades

## Fase 4

Integraciones.

- Google Calendar
- Apple Calendar
- Gmail
- Outlook
- WhatsApp
- Telegram

## Fase 5

Asistente proactivo.

- Memoria a largo plazo.
- Preparación automática de reuniones.
- Anticipación de tareas.
- Resúmenes inteligentes.
- Automatizaciones.

---

# Tecnologías (definitivas)

Ver `product/02_ARQUITECTURA.md`.

- Backend: Python + FastAPI + SQLAlchemy (async) + Alembic
- Frontend: Next.js + React + TypeScript + Tailwind (PWA)
- Base de datos: PostgreSQL + pgvector
- IA: OpenAI (Structured Outputs)
- Automatizaciones: n8n
- Infraestructura: Docker + GitHub Actions (CI)

---

# Licencia

En definición.
