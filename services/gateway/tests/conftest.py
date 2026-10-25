import os
import pathlib
import sys

SERVICE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SERVICE_DIR), str(SERVICE_DIR.parents[1] / "libs")]
os.environ["PEDIDOS_URL"] = "http://pedidos"
os.environ["ESTOQUE_URL"] = "http://estoque"
os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def fake_backend(request: httpx.Request) -> httpx.Response:
    if request.url.host == "estoque" and request.url.path == "/produtos":
        return httpx.Response(200, json=[{"sku": "TEN-001"}])
    if request.url.host == "pedidos" and request.url.path == "/pedidos":
        if request.method == "POST":
            return httpx.Response(201, json={"id": "abc", "status": "CONFIRMADO"})
        return httpx.Response(200, json=[], headers={"x-limite": request.url.params.get("limite", "")})
    if request.url.host == "pedidos":
        raise httpx.ConnectError("connection refused", request=request)
    return httpx.Response(404, json={"detail": "não encontrado"})


@pytest.fixture()
def client():
    from app.main import app, get_client

    fake = httpx.AsyncClient(transport=httpx.MockTransport(fake_backend))
    app.dependency_overrides[get_client] = lambda: fake
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
