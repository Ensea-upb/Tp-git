def test_health_returns_200(client):
    """GET /v1/health doit retourner 200 sans authentification."""
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client):
    """GET /v1/health doit retourner {"status": "ok"}."""
    response = client.get("/v1/health")
    data = response.json()
    assert data["status"] == "ok"


def test_health_no_auth_required(client):
    """GET /v1/health ne requiert pas de clé API."""
    response = client.get("/v1/health")
    assert response.status_code != 401
    assert response.status_code != 403
