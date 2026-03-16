import uuid


def test_list_offers_requires_auth(client):
    """GET /v1/offers sans auth doit retourner 403."""
    response = client.get("/v1/offers")
    assert response.status_code == 403


def test_list_offers_with_auth(client, api_headers, sample_offer):
    """GET /v1/offers avec auth doit retourner la liste paginée."""
    response = client.get("/v1/offers", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "has_next" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


def test_list_offers_pagination_defaults(client, api_headers, sample_offer):
    """GET /v1/offers doit retourner page=1, page_size=20 par défaut."""
    response = client.get("/v1/offers", headers=api_headers)
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_list_offers_filter_by_state(client, api_headers, sample_offer):
    """GET /v1/offers?state=QUALIFIED doit filtrer par état."""
    response = client.get("/v1/offers?state=QUALIFIED", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["current_state"] == "QUALIFIED"


def test_get_offer_by_id(client, api_headers, sample_offer):
    """GET /v1/offers/{id} doit retourner le détail de l'offre."""
    response = client.get(f"/v1/offers/{sample_offer.id}", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_offer.id)
    assert data["normalized_title"] == sample_offer.normalized_title
    assert data["current_state"] == sample_offer.current_state


def test_get_offer_not_found(client, api_headers):
    """GET /v1/offers/{uuid_inconnu} doit retourner 404."""
    unknown_id = uuid.uuid4()
    response = client.get(f"/v1/offers/{unknown_id}", headers=api_headers)
    assert response.status_code == 404


def test_get_offer_requires_auth(client, sample_offer):
    """GET /v1/offers/{id} sans auth doit retourner 403."""
    response = client.get(f"/v1/offers/{sample_offer.id}")
    assert response.status_code == 403


def test_offer_has_state_in_english(client, api_headers, sample_offer):
    """Les états retournés doivent être en anglais (nomenclature V2)."""
    response = client.get(f"/v1/offers/{sample_offer.id}", headers=api_headers)
    data = response.json()
    valid_states = [
        "DETECTED", "RAW_STORED", "NORMALIZED", "DEDUPLICATED",
        "ANALYZED", "REJECTED", "QUALIFIED", "DRAFT_REQUESTED",
        "DRAFT_PREPARED", "READY_FOR_REVIEW", "SUBMISSION_IN_PROGRESS",
        "SUBMITTED", "CLOSED",
    ]
    assert data["current_state"] in valid_states
