import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models.company import Company


class CompanyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        return self.db.execute(
            select(Company).where(Company.id == company_id)
        ).scalar_one_or_none()

    def get_by_name(self, name: str) -> Company | None:
        """Recherche insensible à la casse."""
        return self.db.execute(
            select(Company).where(func.lower(Company.name) == name.lower().strip())
        ).scalar_one_or_none()

    def get_or_create(self, name: str, sector: str | None = None, location: str | None = None) -> Company:
        """Retourne l'entreprise existante ou en crée une nouvelle."""
        existing = self.get_by_name(name)
        if existing:
            return existing
        company = Company(
            name=name.strip(),
            sector=sector,
            main_location=location,
            company_status="neutre",
        )
        self.db.add(company)
        self.db.flush()
        return company
