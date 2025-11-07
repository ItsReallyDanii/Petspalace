"""Basic integration tests for the Pets × AI API.

These tests use FastAPI's ``TestClient`` to exercise a few endpoints and
ensure they behave roughly as expected.  They are not exhaustive and
should be expanded as features mature.  Running ``pytest`` in the
repository root will automatically discover and execute these tests.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_create_case_and_upload_photo_and_search() -> None:
    # Create a new case
    resp = client.post(
        "/v1/cases",
        json={
            "user_id": "user123",
            "type": "lost",
            "species": "dog",
            "geohash6": "abc123",
            "consent": {"shareVectors": True, "sharePhotos": False},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "case_id" in data
    case_id = data["case_id"]
    # Upload a photo (we use a simple text file as placeholder)
    files = {"file": ("dog.jpg", b"fakebytes", "image/jpeg")}
    resp = client.post(f"/v1/cases/{case_id}/photos", files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert "photo_id" in data
    # Run a search
    resp = client.post("/v1/search", json={"case_id": case_id, "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "candidates" in data
    # There should be at least as many candidates as requested (within fixture size)
    assert len(data["candidates"]) == 5


def test_openapi_and_asyncapi_docs_served() -> None:
    resp = client.get("/docs/openapi.yaml")
    assert resp.status_code == 200
    assert "openapi" in resp.text
    resp = client.get("/docs/asyncapi.yaml")
    assert resp.status_code == 200
    assert "asyncapi" in resp.text