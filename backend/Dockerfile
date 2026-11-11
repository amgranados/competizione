# syntax=docker/dockerfile:1

# ---------- Etapa builder: compila e instala dependencias en un venv ----------
FROM python:3.15-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# build-essential/libpq-dev sólo se necesitan para COMPILAR ruedas (asyncpg, etc.);
# no se arrastran a la imagen final.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# venv aislado que copiaremos íntegro a la etapa runtime.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install -r requirements.txt

# ---------- Etapa runtime: imagen slim, sin toolchain, usuario no root ----------
FROM python:3.15-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# libpq5 es la dependencia de RUNTIME de asyncpg (no el paquete -dev).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --no-create-home --home-dir /app appuser

WORKDIR /app

# Copia el venv ya construido (sin compiladores).
COPY --from=builder /opt/venv /opt/venv

# Código de la aplicación.
COPY app ./app
COPY alembic.ini ./
COPY pyproject.toml ./
COPY docker-entrypoint.sh ./

# Normaliza CRLF (checkouts Windows con core.autocrlf=true: sin esto el shebang
# leería `/bin/sh\r` y exec fallaría con "no such file or directory"),
# da permisos y asigna la propiedad antes de bajar privilegios.
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && chown -R appuser:app /app

# L-03: ejecutar como usuario sin privilegios.
USER appuser

EXPOSE 8000

CMD ["./docker-entrypoint.sh"]
