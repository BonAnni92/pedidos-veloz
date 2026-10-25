import os
import pathlib
import sys

SERVICE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SERVICE_DIR), str(SERVICE_DIR.parents[1] / "libs")]
os.environ["PAGAMENTO_LATENCIA_MAX_MS"] = "0"
os.environ["PAGAMENTO_TAXA_FALHA"] = "0"
os.environ["PAGAMENTO_LIMITE_CENTAVOS"] = "100000"
os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
