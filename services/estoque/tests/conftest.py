import os
import pathlib
import sys

SERVICE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SERVICE_DIR), str(SERVICE_DIR.parents[1] / "libs")]
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.db import engine, init_db
    from app.main import app
    from app.models import Base

    Base.metadata.drop_all(engine)
    init_db()
    with TestClient(app) as c:
        yield c
