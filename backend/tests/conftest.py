import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configurer l'environnement de test avant d'importer l'app
os.environ.setdefault("DATABASE_URL", "postgresql://agent_user:agent_password@postgres:5432/agent_db")
os.environ.setdefault("APP_API_KEY", "test-api-key")

from app.domain.enums.offer_state import OfferState  # noqa: E402
from app.domain.enums.work_mode import WorkMode  # noqa: E402
from app.infrastructure.db.base import Base  # noqa: E402
from app.infrastructure.db.models.company import Company  # noqa: E402
from app.infrastructure.db.models.offer import Offer  # noqa: E402
from app.infrastructure.db.models.source import Source  # noqa: E402
from app.infrastructure.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# Utiliser la même DB que l'app pour les tests d'intégration
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    # Ne pas supprimer — base partagée avec le seed


@pytest.fixture()
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture()
def sample_offer(db):
    """Crée une offre de test et la retourne."""
    source = Source(
        id=uuid.uuid4(),
        name="Test Source",
        source_type="test",
        is_active=True,
        check_frequency_hours=3,
    )
    company = Company(
        id=uuid.uuid4(),
        name="Test Company",
        sector="Tech",
        main_location="Paris",
    )
    db.add_all([source, company])
    db.flush()

    offer = Offer(
        id=uuid.uuid4(),
        normalized_title="Stage Test Développeur",
        normalized_description="Description de test",
        contract_type="Stage",
        duration_months=6,
        location_text="Paris",
        work_mode=WorkMode.HYBRID,
        current_state=OfferState.QUALIFIED,
        is_active=True,
        global_score=80.0,
        action_score=75.0,
        score_justification={"résumé": "Bon match test"},
        company_id=company.id,
        primary_source_id=source.id,
        offer_url=f"https://test.example.com/stage/{uuid.uuid4()}",
    )
    db.add(offer)
    db.flush()
    return offer
