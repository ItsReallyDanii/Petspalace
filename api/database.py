"""Database helpers for the Pets × AI API."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Generator, List, Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from .models import (
    Alert,
    AlertsResponse,
    CaseDetail,
    CaseDetailResponse,
    CaseEraseResponse,
    CaseExport,
    CaseReview,
    CaseReviewList,
    CandidateDecision,
    Consent,
    CreateCaseRequest,
    CreateCaseResponse,
    EventRecord,
    EventsResponse,
    PhotoMetadata,
    PhotoUploadResponse,
    SearchCandidate,
)

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from .models import LitterEventPayload, PlayroomAlertPayload


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


class CaseRecord(Base):
    """ORM model for ``cases``."""

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    species: Mapped[str] = mapped_column(String, nullable=False)
    geohash6: Mapped[str] = mapped_column(String, nullable=False)
    consent_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    photos: Mapped[List["PhotoRecord"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    reviews: Mapped[List["CaseReviewRecord"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class PhotoRecord(Base):
    """ORM model for ``photos``."""

    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    url_encrypted: Mapped[Optional[str]] = mapped_column(String)
    view: Mapped[Optional[str]] = mapped_column(String)
    hash: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    case: Mapped[CaseRecord] = relationship(back_populates="photos")


class EventRecordORM(Base):
    """ORM model for ``events``."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(String, nullable=False)
    pet_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_s: Mapped[Optional[float]] = mapped_column(Float)
    conf: Mapped[Optional[float]] = mapped_column(Float)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AlertRecord(Base):
    """ORM model for ``alerts``."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    pet_id: Mapped[str] = mapped_column(String, nullable=False)
    room_id: Mapped[Optional[str]] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    evidence_url: Mapped[Optional[str]] = mapped_column(String)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CaseReviewRecord(Base):
    """ORM model for reviewer decisions."""

    __tablename__ = "case_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    candidate_pet_id: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    band: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    case: Mapped[CaseRecord] = relationship(back_populates="reviews")


_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


def configure(database_url: str) -> None:
    """Initialise the SQLAlchemy engine and create tables."""

    global _engine, _SessionFactory

    if _engine is not None:
        return

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
    _SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(_engine)


def get_session_factory() -> sessionmaker[Session]:
    """Return the configured session factory."""

    if _SessionFactory is None:  # pragma: no cover - defensive
        raise RuntimeError("Database has not been configured")
    return _SessionFactory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope for non-FastAPI consumers."""

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - defensive
        session.rollback()
        raise
    finally:
        session.close()


def create_case(session: Session, data: CreateCaseRequest) -> CreateCaseResponse:
    """Persist a new case and return its identifier."""

    record = CaseRecord(
        user_id=data.user_id,
        type=data.type,
        species=data.species,
        geohash6=data.geohash6,
        consent_json=json.loads(data.consent.model_dump_json()),
    )
    session.add(record)
    session.commit()
    return CreateCaseResponse(case_id=record.id)


def get_case(session: Session, case_id: str) -> Optional[CaseRecord]:
    """Retrieve a case by identifier."""

    return session.get(CaseRecord, case_id)


def add_photo(
    session: Session,
    case_id: str,
    filename: str,
    payload: bytes,
    view: Optional[str],
    bucket: str,
) -> PhotoUploadResponse:
    """Persist metadata for a photo upload."""

    digest = hashlib.sha256(payload).hexdigest()
    photo = PhotoRecord(
        case_id=case_id,
        url_encrypted=f"s3://{bucket}/{case_id}/{filename}",
        view=view,
        hash=digest,
    )
    session.add(photo)
    session.commit()
    return PhotoUploadResponse(photo_id=photo.id)


def hydrate_case_detail(case: CaseRecord) -> CaseDetail:
    """Convert an ORM record into a :class:`CaseDetail`."""

    consent = Consent.model_validate(case.consent_json)
    return CaseDetail(
        id=case.id,
        user_id=case.user_id,
        type=case.type,  # type: ignore[arg-type]
        species=case.species,
        geohash6=case.geohash6,
        consent=consent,
        status=case.status,
        created_at=case.created_at,
        expires_at=case.expires_at,
    )


def get_case_detail(session: Session, case_id: str) -> Optional[CaseDetailResponse]:
    """Fetch a case and its associated photos."""

    case = get_case(session, case_id)
    if case is None:
        return None
    photos = [PhotoMetadata.model_validate(photo, from_attributes=True) for photo in case.photos]
    return CaseDetailResponse(case=hydrate_case_detail(case), photos=photos)


def list_case_reviews(session: Session, case_id: str, limit: int = 20) -> CaseReviewList:
    """Return recent reviewer decisions for a case."""

    rows = (
        session.execute(
            select(CaseReviewRecord)
            .where(CaseReviewRecord.case_id == case_id)
            .order_by(CaseReviewRecord.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    reviews = [CaseReview.model_validate(row, from_attributes=True) for row in rows]
    return CaseReviewList(reviews=reviews)


def record_candidate_review(session: Session, case_id: str, payload: CandidateDecision) -> CaseReview:
    """Persist a reviewer decision."""

    record = CaseReviewRecord(
        case_id=case_id,
        candidate_pet_id=payload.candidate_pet_id,
        decision=payload.decision,
        band=payload.band,
        score=payload.score,
    )
    session.add(record)
    session.commit()
    return CaseReview.model_validate(record, from_attributes=True)


def list_recent_alerts(session: Session, limit: int = 25) -> AlertsResponse:
    """Return the most recent alerts."""

    rows = (
        session.execute(select(AlertRecord).order_by(AlertRecord.ts.desc()).limit(limit))
        .scalars()
        .all()
    )
    alerts = [Alert.model_validate(row, from_attributes=True) for row in rows]
    return AlertsResponse(alerts=alerts)


def list_recent_events(session: Session, limit: int = 50) -> EventsResponse:
    """Return the most recent litter/feeder events."""

    rows = (
        session.execute(select(EventRecordORM).order_by(EventRecordORM.ts.desc()).limit(limit))
        .scalars()
        .all()
    )
    events = [EventRecord.model_validate(row, from_attributes=True) for row in rows]
    return EventsResponse(events=events)


def export_case(session: Session, case_id: str) -> Optional[CaseExport]:
    """Serialize a case and related artefacts for export."""

    detail = get_case_detail(session, case_id)
    if detail is None:
        return None
    alerts = list_recent_alerts(session).alerts
    events = list_recent_events(session).events
    return CaseExport(case=detail.case, photos=detail.photos, alerts=alerts, events=events)


def delete_case(session: Session, case_id: str) -> CaseEraseResponse:
    """Cascade delete a case and related artefacts."""

    case = get_case(session, case_id)
    if case is None:
        return CaseEraseResponse(case_id=case_id, deleted=False)
    session.delete(case)
    session.commit()
    return CaseEraseResponse(case_id=case_id, deleted=True)


@lru_cache(maxsize=1)
def _cached_candidates(fixture_path: str) -> List[SearchCandidate]:
    """Load deterministic search candidates from disk."""

    path = Path(fixture_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SearchCandidate.model_validate(item) for item in data]


def load_search_candidates(fixture_path: str) -> List[SearchCandidate]:
    """Return search candidates, copying cached models to avoid mutation."""

    return [candidate.model_copy(deep=True) for candidate in _cached_candidates(fixture_path)]


def record_litter_event(session: Session, subject: str, payload: "LitterEventPayload") -> EventRecord:
    """Persist a litter or feeder event."""

    record = EventRecordORM(
        source=subject,
        pet_id=payload.pet_id,
        type=payload.type,
        ts=payload.ts,
        duration_s=payload.duration_s,
        conf=payload.conf,
        payload_json=payload.payload,
    )
    session.add(record)
    session.commit()
    return EventRecord.model_validate(record, from_attributes=True)


def record_playroom_alert(session: Session, payload: "PlayroomAlertPayload") -> Alert:
    """Persist an alert emitted from daycare playrooms."""

    record = AlertRecord(
        pet_id=payload.pet_id,
        room_id=payload.room_id,
        kind=payload.kind,
        severity=payload.severity,
        state=payload.state,
        evidence_url=str(payload.evidence_url),
        ts=payload.ts,
    )
    session.add(record)
    session.commit()
    return Alert.model_validate(record, from_attributes=True)


def create_alert_from_event(
    session: Session,
    pet_id: str,
    kind: str,
    severity: str,
    state: str = "open",
    room_id: Optional[str] = None,
    evidence_url: Optional[str] = None,
    ts: Optional[datetime] = None,
) -> Alert:
    """Create an alert record derived from anomaly detection."""

    record = AlertRecord(
        pet_id=pet_id,
        room_id=room_id,
        kind=kind,
        severity=severity,
        state=state,
        evidence_url=evidence_url,
        ts=ts or _utcnow(),
    )
    session.add(record)
    session.commit()
    return Alert.model_validate(record, from_attributes=True)
