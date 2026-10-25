def test_health(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_aprova_valor_dentro_do_limite(client):
    resp = client.post("/pagamentos", json={"pedido_id": "p1", "valor_centavos": 5000})
    assert resp.status_code == 201
    assert resp.json()["status"] == "APROVADO"


def test_recusa_valor_acima_do_limite(client):
    resp = client.post("/pagamentos", json={"pedido_id": "p2", "valor_centavos": 100001})
    assert resp.json()["status"] == "RECUSADO"
    assert resp.json()["motivo"]


def test_metodo_invalido(client):
    resp = client.post(
        "/pagamentos", json={"pedido_id": "p3", "valor_centavos": 10, "metodo": "cheque"}
    )
    assert resp.status_code == 422


def test_falha_do_provedor(client, monkeypatch):
    monkeypatch.setenv("PAGAMENTO_TAXA_FALHA", "1")
    resp = client.post("/pagamentos", json={"pedido_id": "p4", "valor_centavos": 10})
    assert resp.status_code == 503


def test_metrica_de_negocio(client):
    client.post("/pagamentos", json={"pedido_id": "p5", "valor_centavos": 10})
    assert 'pagamentos_total{resultado="aprovado"}' in client.get("/metrics").text
