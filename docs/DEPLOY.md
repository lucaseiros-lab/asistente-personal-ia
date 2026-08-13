# Despliegue en producción (gratis)

Guía paso a paso para tener la app corriendo en internet, disponible en
cualquier momento, sin pagar nada. Usa tres servicios gratuitos, cada uno
para una parte distinta del sistema:

| Parte | Servicio | Por qué |
|---|---|---|
| Base de datos (Postgres + pgvector) | [Supabase](https://supabase.com) | Free tier con `pgvector` incluido, sin tarjeta |
| Backend (FastAPI) | [Render](https://render.com) | Free tier con Docker, sin tarjeta |
| Frontend (Next.js) | [Vercel](https://vercel.com) | Free tier pensado para Next.js, sin tarjeta |

La parte de IA (entender mensajes, memoria semántica, transcripción de voz)
usa la API de **Google Gemini**, que sí tiene una capa gratuita real y
duradera — no hace falta tarjeta ni gastar nada.

## Antes de empezar: las limitaciones del plan gratis

- El backend en Render **se duerme tras 15 minutos sin uso**. El primer
  mensaje después de estar inactivo tarda 30-60 segundos en responder
  (se despierta solo). Los mensajes siguientes van normal.
- La base de datos en Supabase **se pausa tras 7 días sin ninguna
  actividad**. No se pierde nada, pero hay que entrar al panel de Supabase
  y tocar "Resume project" antes de volver a usar la app.
- La capa gratuita de Gemini tiene un límite de uso (para `gemini-2.5-flash`:
  10 solicitudes por minuto, 250 por día). Para uso personal (unos pocos
  mensajes por día) es más que suficiente; si algún día lo superás, la API
  simplemente devuelve un error temporal hasta el minuto/día siguiente, no
  se cobra nada de golpe.

No hay forma de evitar la parte de Render/Supabase sin pagar. Si en algún
momento eso empieza a molestar, la app entera se puede migrar a un plan
pago (Render/Railway) sin cambiar código.

## Paso 1 — Base de datos en Supabase

1. Crear cuenta gratis en [supabase.com](https://supabase.com) (sin tarjeta).
2. **New Project** → elegir nombre, contraseña de base de datos (guardarla,
   se usa más abajo) y una región cercana.
3. Una vez creado, ir a **Database → Extensions**, buscar `vector` y
   habilitarlo (un toggle). Esto es obligatorio: sin esto, la memoria
   semántica del asistente no funciona.
4. Ir a **Project Settings → Database → Connection string**, modo **URI**.
   Copiar la cadena, que se ve así:

   ```
   postgresql://postgres:[TU-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```

   De ahí salen las dos variables que necesita el backend (mismo dato, dos
   formatos porque el proyecto usa un driver async y uno sync):

   ```
   DATABASE_URL=postgresql+asyncpg://postgres:[TU-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   DATABASE_URL_SYNC=postgresql+psycopg2://postgres:[TU-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```

## Paso 2 — Backend en Render

1. Crear cuenta gratis en [render.com](https://render.com) (sin tarjeta),
   conectando tu cuenta de GitHub.
2. **New → Web Service** → elegir el repo `asistente-personal-ia`.
3. Configuración del servicio:
   - **Root Directory**: dejar vacío (la raíz del repo — el Dockerfile
     necesita ver también la carpeta `prompts/`, no solo `backend/`).
   - **Runtime**: Docker.
   - **Dockerfile Path**: `backend/Dockerfile`.
   - **Instance Type**: Free.
4. Variables de entorno (**Environment**), cargar una por una:

   ```
   ENVIRONMENT=production
   DATABASE_URL=<el de Supabase, formato asyncpg de arriba>
   DATABASE_URL_SYNC=<el de Supabase, formato psycopg2 de arriba>
   JWT_SECRET_KEY=<generar uno propio, ver abajo>
   GEMINI_API_KEY=<tu clave de Google AI Studio>
   GEMINI_CHAT_MODEL=gemini-2.5-flash
   GEMINI_EMBEDDING_MODEL=gemini-embedding-001
   GEMINI_EMBEDDING_DIMENSIONS=768
   GEMINI_TRANSCRIBE_MODEL=gemini-2.5-flash
   CORS_ORIGINS=["http://localhost:3000"]
   ```

   La clave de Gemini se saca gratis, sin tarjeta, en
   [aistudio.google.com/apikey](https://aistudio.google.com/apikey) con
   cualquier cuenta de Google — "Create API key".

   Para generar un `JWT_SECRET_KEY` seguro, usar el botón **"Generate"** que
   Render muestra al lado del campo (no hace falta inventarlo a mano).

   `CORS_ORIGINS` se deja así por ahora — se actualiza en el Paso 4 con el
   dominio real del frontend.

5. Deploy. Al terminar, Render da una URL pública tipo
   `https://asistente-personal-ia.onrender.com`. Las migraciones de base de
   datos (`alembic upgrade head`) corren solas al arrancar el contenedor.
6. Verificar que responde: abrir `https://<tu-url>.onrender.com/health` en
   el navegador.

## Paso 3 — Frontend en Vercel

1. Crear cuenta gratis en [vercel.com](https://vercel.com) (sin tarjeta),
   conectando GitHub.
2. **Add New → Project** → elegir el mismo repo.
3. **Root Directory**: `frontend` (Vercel detecta Next.js solo).
4. Variable de entorno:

   ```
   NEXT_PUBLIC_API_URL=https://<tu-url-de-render>.onrender.com/api/v1
   ```

5. Deploy. Vercel da un dominio tipo `https://asistente-personal-ia.vercel.app`.

## Paso 4 — Conectar frontend y backend (CORS)

Volver a Render → el servicio del backend → **Environment**, y actualizar:

```
CORS_ORIGINS=["https://asistente-personal-ia.vercel.app"]
```

(reemplazando por tu dominio real de Vercel). Guardar — Render vuelve a
desplegar solo con el cambio.

## Paso 5 — Probar

1. Entrar a tu dominio de Vercel.
2. Registrarte con tu email.
3. Escribirle al asistente algo como *"Agendame reunión el lunes a las
   10am"* y confirmar que responde y queda guardado.

Si hace más de 15 minutos que nadie usa la app, la primera respuesta va a
tardar hasta un minuto (Render despertándose) — es normal, no está roto.
