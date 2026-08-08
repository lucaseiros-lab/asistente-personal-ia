FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# El contexto de build es la raíz del repo (ver docker-compose.yml) para poder
# incluir prompts/, fuente única de verdad de los prompts del sistema.
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY prompts/ ./prompts/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
