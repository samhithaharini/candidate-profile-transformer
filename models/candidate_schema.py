from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError


class LocationSchema(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None  # ISO-3166 alpha-2


class LinksSchema(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = Field(default_factory=list)


class SkillSchema(BaseModel):
    name: str
    confidence: float
    sources: List[str] = Field(default_factory=list)


class ExperienceSchema(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None  # YYYY-MM
    end: Optional[str] = None    # YYYY-MM
    summary: Optional[str] = None


class EducationSchema(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None


class ProvenanceRecord(BaseModel):
    field: str
    source: str
    method: str
    selected_value: Optional[Any] = None


class CanonicalCandidate(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    emails: Optional[List[str]] = None
    phones: Optional[List[str]] = None
    location: Optional[LocationSchema] = None
    links: Optional[LinksSchema] = None
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: Optional[List[SkillSchema]] = None
    experience: Optional[List[ExperienceSchema]] = None
    education: Optional[List[EducationSchema]] = None
    field_confidence: Dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    provenance: Optional[List[ProvenanceRecord]] = None
    metadata: Optional[Dict[str, Any]] = None


def validate_candidate(candidate_data: dict) -> CanonicalCandidate:
    try:
        return CanonicalCandidate.model_validate(candidate_data)
    except ValidationError as error:
        raise ValueError(error) from error
