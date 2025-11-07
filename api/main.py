"""FastAPI application for the Pets × AI HTTP API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from . import database
from .models import (
    AlertsResponse,
    CaseDetailResponse,
    CaseEraseResponse,
    CaseExport,
    CaseReview,
    CaseReviewList,
    CandidateDecision,
    CreateCaseRequest,
    CreateCaseResponse,
    EventsResponse,
    PhotoUploadResponse,
    SearchRequest,
    SearchResponse,
)


@dataclass(frozen=True)
class Settings:
    """Application configuration."""

    database_url: str
    search_fixture: str
    s3_bucket: str
    contracts_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings loaded from environment variables."""

    project_root = Path(__file__).resolve().parents[1]
    contracts_dir = project_root / "contracts"
    default_db_path = project_root / "pets.db"
    return Settings(
        database_url=os.getenv("POSTGRES_URL", f"sqlite:///{default_db_path}"),
        search_fixture=str(project_root / "tests/fixtures/search_candidates.json"),
        s3_bucket=os.getenv("S3_BUCKET", "pets-local"),
        contracts_dir=contracts_dir,
    )


def get_session() -> Generator[Session, None, None]:
    """Yield a database session for request handling."""

    session = database.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


app = FastAPI(title="Pets × AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialise database connections and preload fixtures."""

    settings = get_settings()
    database.configure(settings.database_url)
    # Preload candidates so subsequent requests are fast.
    database.load_search_candidates(settings.search_fixture)


@app.post("/v1/cases", response_model=CreateCaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(request: CreateCaseRequest, session: Session = Depends(get_session)) -> CreateCaseResponse:
    """Create a new lost-pet case."""

    return database.create_case(session, request)


@app.post(
    "/v1/cases/{case_id}/photos",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    case_id: str,
    file: UploadFile = File(...),
    view: str | None = Form(None),
    session: Session = Depends(get_session),
) -> PhotoUploadResponse:
    """Upload a photo for an existing case."""

    if database.get_case(session, case_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload")
    settings = get_settings()
    return database.add_photo(session, case_id, file.filename or "upload.bin", contents, view, settings.s3_bucket)


@app.post("/v1/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    """Run a deterministic visual search and return the top-K candidates."""

    settings = get_settings()
    candidates = database.load_search_candidates(settings.search_fixture)
    k = request.top_k or len(candidates)
    if k <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="top_k must be positive")
    return SearchResponse(candidates=candidates[:k])


@app.get("/docs/openapi.yaml", response_class=PlainTextResponse)
def serve_openapi_yaml() -> str:
    """Serve the raw OpenAPI contract."""

    settings = get_settings()
    return (settings.contracts_dir / "openapi.yaml").read_text(encoding="utf-8")


@app.get("/docs/asyncapi.yaml", response_class=PlainTextResponse)
def serve_asyncapi_yaml() -> str:
    """Serve the raw AsyncAPI contract."""

    settings = get_settings()
    return (settings.contracts_dir / "asyncapi.yaml").read_text(encoding="utf-8")


@app.get("/internal/alerts", response_model=AlertsResponse)
def list_alerts(session: Session = Depends(get_session)) -> AlertsResponse:
    """Return the most recent alerts for dashboard consumption."""

    return database.list_recent_alerts(session)


@app.get("/internal/events", response_model=EventsResponse)
def list_events(session: Session = Depends(get_session)) -> EventsResponse:
    """Return the most recent litter/feeder events."""

    return database.list_recent_events(session)


@app.get("/internal/cases/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(case_id: str, session: Session = Depends(get_session)) -> CaseDetailResponse:
    """Return detailed case information for the privacy console."""

    detail = database.get_case_detail(session, case_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return detail


@app.get("/internal/cases/{case_id}/reviews", response_model=CaseReviewList)
def get_case_reviews(case_id: str, session: Session = Depends(get_session)) -> CaseReviewList:
    """Return the review history for a case."""

    return database.list_case_reviews(session, case_id)


@app.post("/internal/cases/{case_id}/reviews", response_model=CaseReview, status_code=status.HTTP_201_CREATED)
def record_review(
    case_id: str,
    payload: CandidateDecision,
    session: Session = Depends(get_session),
) -> CaseReview:
    """Persist a reviewer decision for a candidate pet."""

    if database.get_case(session, case_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return database.record_candidate_review(session, case_id, payload)


@app.get("/internal/cases/{case_id}/export", response_model=CaseExport)
def export_case(case_id: str, session: Session = Depends(get_session)) -> CaseExport:
    """Export case data for privacy compliance."""

    payload = database.export_case(session, case_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return payload


@app.post("/internal/cases/{case_id}/erase", response_model=CaseEraseResponse)
def erase_case(case_id: str, session: Session = Depends(get_session)) -> CaseEraseResponse:
    """Cascade delete a case and associated artefacts."""

    return database.delete_case(session, case_id)


@app.get("/alerts.json")
def get_alerts_json(session: Session = Depends(get_session)) -> JSONResponse:
    """Legacy endpoint used by earlier UI prototypes."""

    alerts = database.list_recent_alerts(session).alerts
    return JSONResponse({"alerts": [alert.model_dump() for alert in alerts]})
