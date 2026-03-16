from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class ExperienceItem(BaseModel):
    title: str
    company: str
    duration: Optional[str] = None
    description: Optional[str] = None


class ProjectItem(BaseModel):
    name: str
    description: Optional[str] = None
    tech: Optional[list[str]] = None


class CandidateProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: Optional[str] = None
    current_level: Optional[str] = None
    school: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    experiences: Optional[list[dict]] = None
    projects: Optional[list[dict]] = None
    target_domains: Optional[list[str]] = None
    availability: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    current_level: Optional[str] = None
    school: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    experiences: Optional[list[dict]] = None
    projects: Optional[list[dict]] = None
    target_domains: Optional[list[str]] = None
    availability: Optional[str] = None
