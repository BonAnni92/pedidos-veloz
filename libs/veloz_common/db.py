"""Criação do engine SQLAlchemy a partir de variáveis de ambiente (12-Factor, fator III)."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable

from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.pool import StaticPool

log = logging.getLogger(__name__)


def database_url() -> str | URL:
    """DATABASE_URL tem prioridade (usado nos testes); senão monta a URL por partes.

    Montar por partes permite que a senha venha de um Secret do Kubernetes
    separado do restante da configuração (ConfigMap).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "veloz"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "postgres"),
    )


def make_engine() -> Engine:
    url = database_url()
    if str(url) in ("sqlite://", "sqlite:///:memory:"):
        # Banco em memória com conexão única compartilhada (apenas testes unitários).
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    if str(url).startswith("sqlite"):
        # Arquivo SQLite (execução local sem Docker): uma conexão por thread.
        return create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def ping(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def wait_for_db(engine: Engine, init: Callable[[], None], attempts: int = 30) -> None:
    """Aguarda o banco ficar disponível antes de inicializar o schema.

    Em Kubernetes os Pods podem subir antes do banco; em vez de falhar de vez,
    tentamos algumas vezes (o Pod fica "not ready" enquanto isso).
    """
    for attempt in range(1, attempts + 1):
        try:
            ping(engine)
            init()
            return
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "banco indisponível, tentando novamente",
                extra={"fields": {"attempt": attempt, "error": str(exc)}},
            )
            time.sleep(2)
    raise RuntimeError("não foi possível conectar ao banco de dados")
