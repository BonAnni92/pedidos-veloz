from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from veloz_common.db import make_engine

from .models import Base, Produto

log = logging.getLogger(__name__)

engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

CATALOGO_INICIAL = [
    Produto(sku="TEN-001", nome="Tênis Corrida Veloz", preco_centavos=29990, disponivel=50),
    Produto(sku="CAM-002", nome="Camiseta Dry Fit", preco_centavos=7990, disponivel=200),
    Produto(sku="MOC-003", nome="Mochila Urbana 20L", preco_centavos=15990, disponivel=5),
]


def init_db() -> None:
    """Cria o schema e carrega o catálogo de exemplo (idempotente).

    Em produção o schema seria versionado com migrações (ex.: Alembic) e
    aplicado por um Job antes do deploy; aqui simplificamos para o MVP.
    """
    try:
        Base.metadata.create_all(engine)
    except (ProgrammingError, OperationalError, IntegrityError):
        # Outra réplica criou as tabelas ao mesmo tempo.
        log.info("schema já criado por outra réplica")
    with SessionLocal() as session:
        if session.scalar(select(Produto).limit(1)) is None:
            session.add_all(
                Produto(
                    sku=p.sku,
                    nome=p.nome,
                    preco_centavos=p.preco_centavos,
                    disponivel=p.disponivel,
                    reservado=0,
                )
                for p in CATALOGO_INICIAL
            )
            try:
                session.commit()
                log.info("catálogo inicial carregado")
            except IntegrityError:
                session.rollback()


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
