"""Import all ORM models to ensure they are registered with SQLAlchemy metadata."""
from app.infrastructure.db.models.application_event import ApplicationEvent  # noqa: F401
from app.infrastructure.db.models.candidate_profile import CandidateProfile  # noqa: F401
from app.infrastructure.db.models.company import Company  # noqa: F401
from app.infrastructure.db.models.ingestion_run import IngestionRun  # noqa: F401
from app.infrastructure.db.models.llm_cache import LLMCache  # noqa: F401
from app.infrastructure.db.models.offer import Offer  # noqa: F401
from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis  # noqa: F401
from app.infrastructure.db.models.offer_raw import OfferRaw  # noqa: F401
from app.infrastructure.db.models.offer_user_status import OfferUserStatus  # noqa: F401
from app.infrastructure.db.models.profile_match_llm import ProfileMatchLLM  # noqa: F401
from app.infrastructure.db.models.source import Source  # noqa: F401
from app.infrastructure.db.models.user_preference import UserPreference  # noqa: F401
