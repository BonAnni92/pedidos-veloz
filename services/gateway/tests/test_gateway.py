def test_health(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_raiz(client):
    assert "rotas" in client.get("/").json()


def test_roteia_produtos_para_estoque(client):
    resp = client.get("/api/produtos")
    assert resp.status_code == 200
    assert resp.json() == [{"sku": "TEN-001"}]
    assert resp.headers["x-request-id"]


def test_roteia_criacao_de_pedido(client):
    resp = client.post("/api/pedidos", json={"sku": "TEN-001", "quantidade": 1})
    assert resp.status_code == 201
    assert resp.json()["status"] == "CONFIRMADO"


def test_propaga_request_id(client):
    resp = client.get("/api/produtos", headers={"x-request-id": "teste-123"})
    assert resp.headers["x-request-id"] == "teste-123"


def test_servico_fora_do_ar_retorna_503(client):
    resp = client.get("/api/pedidos/qualquer")
    assert resp.status_code == 503
    assert "pedidos" in resp.json()["detail"]


def test_repassa_status_de_erro(client):
    assert client.get("/api/produtos/XYZ").status_code == 404


def test_valida_pedido_na_borda(client):
    resp = client.post("/api/pedidos", json={"sku": "TEN-001", "quantidade": 0})
    assert resp.status_code == 422
