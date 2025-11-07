"""Pydantic models derived from the OpenAPI and AsyncAPI specifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Consent(BaseModel):
    """Consent flags controlling privacy behaviour."""

    model_config = ConfigDict(extra="forbid")

    shareVectors: bool = Field(..., description="Whether embeddings may be shared with other cases")
    sharePhotos: bool = Field(..., description="Whether photos may be shared with other cases")


class CreateCaseRequest(BaseModel):
    """Request model for creating a new case."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="Identifier of the owner submitting the case")
    type: Literal["lost", "found"] = Field(..., description="Nature of the case (lost/found)")
    species: str = Field(..., description="Species of animal (e.g. dog, cat)")
    geohash6: str = Field(..., min_length=6, max_length=12, description="Approximate location encoded as a geohash")
    consent: Consent


class CreateCaseResponse(BaseModel):
    """Response model for case creation."""

    case_id: str


class PhotoUploadResponse(BaseModel):
    """Response model for photo uploads."""

    photo_id: str


class SearchRequest(BaseModel):
    """Request model for running a search."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="Identifier of the case to search against")
    top_k: Optional[int] = Field(10, description="Number of candidates to return", ge=1)


class SearchCandidate(BaseModel):
    """Candidate result item returned from a search."""

    model_config = ConfigDict(extra="forbid")

    pet_id: str
    score: float
    band: Literal["strong", "moderate", "weak"]


class SearchResponse(BaseModel):
    """Response model for search results."""

    candidates: List[SearchCandidate]


class PhotoMetadata(BaseModel):
    """Metadata about a stored photo."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    url_encrypted: Optional[str]
    view: Optional[str]
    hash: Optional[str]
    created_at: datetime


class CaseDetail(BaseModel):
    """Detailed representation of a case suitable for console views."""

    id: str
    user_id: str
    type: Literal["lost", "found"]
    species: str
    geohash6: str
    consent: Consent
    status: str
    created_at: datetime
    expires_at: Optional[datetime]


class CaseDetailResponse(BaseModel):
    """Response wrapper for case detail lookups."""

    case: CaseDetail
    photos: List[PhotoMetadata]


class EventRecord(BaseModel):
    """Representation of a multi-pet event consumed from the edge."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    pet_id: str
    type: str
    ts: datetime
    duration_s: Optional[float]
    conf: Optional[float]
    payload_json: Dict[str, Any]
    created_at: datetime


class EventsResponse(BaseModel):
    """Collection of recent events."""

    events: List[EventRecord]


class Alert(BaseModel):
    """Alert raised either from litter anomalies or daycare playrooms."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    pet_id: str
    room_id: Optional[str]
    kind: str
    severity: str
    state: str
    evidence_url: Optional[HttpUrl]
    ts: datetime
    created_at: datetime


class AlertsResponse(BaseModel):
    """Collection of recent alerts."""

    alerts: List[Alert]


class CandidateDecision(BaseModel):
    """A reviewer decision against a candidate result."""

    model_config = ConfigDict(extra="forbid")

    candidate_pet_id: str = Field(..., description="Identifier of the candidate pet")
    band: Literal["strong", "moderate", "weak"]
    score: float
    decision: Literal["confirmed", "rejected"]


class CandidateReviewResponse(BaseModel):
    """Response payload when a review has been recorded."""

    review_id: str


class CaseExport(BaseModel):
    """Serialized export payload for privacy tooling."""

    case: CaseDetail
    photos: List[PhotoMetadata]
    alerts: List[Alert]
    events: List[EventRecord]


class CaseEraseResponse(BaseModel):
    """Response payload confirming a cascade erase."""

    case_id: str
    deleted: bool


class CaseReview(BaseModel):
    """Review record returned to the UI."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    candidate_pet_id: str
    decision: Literal["confirmed", "rejected"]
    band: Literal["strong", "moderate", "weak"]
    score: float
    created_at: datetime


class CaseReviewList(BaseModel):
    """Wrapper for returning review history."""

    reviews: List[CaseReview]


class LitterEventPayload(BaseModel):
    """Event payload defined in the AsyncAPI contract for litter devices."""

    model_config = ConfigDict(extra="forbid")

    pet_id: str
    type: str
    ts: datetime
    duration_s: float
    conf: float
    payload: Dict[str, Any]


class PlayroomAlertPayload(BaseModel):
    """Alert payload defined in the AsyncAPI contract for daycare playrooms."""

    model_config = ConfigDict(extra="forbid")

    pet_id: str
    room_id: str
    kind: str
    severity: str
    state: str
    evidence_url: HttpUrl
    ts: datetime
