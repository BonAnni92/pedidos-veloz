# syntax=docker/dockerfile:1.7
# =============================================================================
# Imagem do serviço "pedidos" - build multi-stage
# Contexto de build: raiz do repositório (para copiar libs/veloz_common)
#   docker build -f services/pedidos/Dockerfile -t pedidos-veloz-pedidos:local .
# =============================================================================
ARG PYTHON_VERSION=3.12

# ---------- Estágio 1: builder (instala dependências em um virtualenv) -------
FROM python:${PYTHON_VERSION}-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Copiar só o requirements primeiro aproveita o cache de camadas:
# se o código mudar mas as dependências não, esta etapa não é refeita.
COPY services/pedidos/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ---------- Estágio 2: runtime (somente o necessário para executar) ----------
FROM python:${PYTHON_VERSION}-slim AS runtime
ARG VERSION=dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="pedidos-veloz-pedidos" \
      org.opencontainers.image.description="Pedidos Veloz - serviço pedidos" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_VERSION=${VERSION} \
    OTEL_SERVICE_NAME=pedidos

# Usuário sem privilégios com UID fixo (exigido pelo runAsNonRoot do Kubernetes)
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=root:root libs/veloz_common ./veloz_common
COPY --chown=root:root services/pedidos/app ./app

USER 10001:10001
EXPOSE 8000

# Healthcheck para "docker run"/Compose (o Kubernetes usa as probes do manifest)
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"]

# Forma "exec": o uvicorn é o PID 1 e recebe o SIGTERM do Kubernetes,
# permitindo desligamento gracioso (12-Factor, fator IX - descartabilidade).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "20"]
