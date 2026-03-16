"""Tests for candidate profile API endpoints."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.db.models.candidate_profile import DEFAULT_CANDIDATE_ID


client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-api-key-changeme"}


def test_get_candidate_profile_creates_default(db_session, monkeypatch):
    from app.repositories.candidate_profile_repository import CandidateProfileRepository
    from app.infrastructure.db.models.candidate_profile import CandidateProfile

    # Ensure no profile exists
    repo = CandidateProfileRepository(db_session)
    profile = repo.get_default()
    if profile:
        db_session.delete(profile)
        db_session.commit()

    response = client.get("/v1/candidate", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(DEFAULT_CANDIDATE_ID)


def test_update_candidate_profile(db_session):
    payload = {
        "full_name": "Alice Martin",
        "current_level": "Master 2 Data Science",
        "school": "Paris Dauphine",
        "skills": ["Python", "SQL", "Machine Learning"],
        "tech_stack": ["Python", "Pandas", "scikit-learn"],
        "availability": "April 2026",
    }
    response = client.put("/v1/candidate", headers=HEADERS, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Alice Martin"
    assert "Python" in data["skills"]
    assert data["availability"] == "April 2026"


def test_update_candidate_profile_partial(db_session):
    # First create a profile
    client.put("/v1/candidate", headers=HEADERS, json={"full_name": "Bob"})

    # Partial update — only update availability
    response = client.put("/v1/candidate", headers=HEADERS, json={"availability": "June 2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["availability"] == "June 2026"
