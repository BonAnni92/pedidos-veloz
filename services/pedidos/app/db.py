from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from veloz_common.db import make_engine

from .models import Base

log = logging.getLogger(__name__)

engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    try:
        Base.metadata.create_all(engine)
    except (ProgrammingError, OperationalError, IntegrityError):
        log.info("schema já criado por outra réplica")


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
