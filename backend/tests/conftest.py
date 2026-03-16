import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- Variables d'environnement de test ---
# Définie avant tout import de l'app pour que pydantic-settings les lise
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://agent_user:agent_password@postgres:5432/agent_db_test",
)
os.environ.setdefault("APP_API_KEY", "test-api-key")

from app.domain.enums.offer_state import OfferState  # noqa: E402
from app.domain.enums.work_mode import WorkMode  # noqa: E402
from app.infrastructure.db.base import Base  # noqa: E402
from app.infrastructure.db.models.company import Company  # noqa: E402
from app.infrastructure.db.models.ingestion_run import IngestionRun  # noqa: E402, F401
from app.infrastructure.db.models.offer import Offer  # noqa: E402
from app.infrastructure.db.models.offer_user_status import OfferUserStatus  # noqa: E402, F401
from app.infrastructure.db.models.source import Source  # noqa: E402
from app.infrastructure.db.models.user_preference import UserPreference  # noqa: E402, F401
from app.infrastructure.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# --- Base de test isolée ---
# Utilise agent_db_test au lieu de agent_db pour ne jamais toucher la base prod/seed.
# La base agent_db_test est créée dynamiquement si elle n'existe pas.
TEST_DATABASE_URL = os.environ["DATABASE_URL"]

_admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
_test_db_name = TEST_DATABASE_URL.rsplit("/", 1)[1].split("?")[0]


def _ensure_test_db_exists() -> None:
    """Crée la base de test si elle n'existe pas encore."""
    admin_engine = create_engine(_admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": _test_db_name},
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{_test_db_name}"'))
    admin_engine.dispose()


_ensure_test_db_exists()

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_schema():
    """Crée le schéma complet dans la base de test (une seule fois par session)."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db(setup_test_schema):
    """
    Session de test avec rollback automatique après chaque test.
    Chaque test obtient une transaction propre — isolation garantie.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """Client HTTP avec override de la dépendance DB pointant vers la session de test."""
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
    """Crée une offre de test isolée dans la transaction courante."""
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


@pytest.fixture()
def default_prefs(db):
    """Crée un profil de préférences par défaut pour les tests de scoring personnalisé."""
    from app.infrastructure.db.models.user_preference import DEFAULT_PROFILE_ID, UserPreference

    prefs = UserPreference(
        id=DEFAULT_PROFILE_ID,
        preferred_contract_types=["Stage", "Alternance"],
        preferred_work_modes=["REMOTE", "HYBRID"],
        preferred_locations=["Paris"],
        preferred_keywords=["python", "data"],
        preferred_domains=["data", "ml"],
        exclude_keywords=["PHP legacy"],
        minimum_duration_months=4,
    )
    db.add(prefs)
    db.flush()
    return prefs
