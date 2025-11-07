# Pets × AI — App-Gen Scaffold README

**Purpose:** Give an AI code-generation tool a *single source of truth* to scaffold a working repo for three features while enforcing stable interfaces via contracts.

## Scope (build exactly this)
- **Feature 1 — Lost‑Pet Visual Search (HTTP):** create/close cases, upload photos, run `/v1/search`, review top‑K candidates. **Mock ANN** responses first.
- **Feature 2 — Multi‑Pet Attribution (HTTP + Events):** enroll pets, ingest litter/feeder events from edge, surface anomaly alerts.
- **Feature 3 — Daycare Risk Analytics (Events):** consume playroom alerts from edge, show live alert feed and downloadable incident clips.

**Non‑goals (for now):** real ML models, billing, user‑facing auth flows beyond OAuth2 PKCE, production observability, vendor SDKs.

---

## Monorepo layout
```
/contracts/
  openapi.yaml      # HTTP: Lost‑Pet + Multi‑Pet (enrollment/alerts)
  asyncapi.yaml     # Events: Multi‑Pet + Daycare alerts
/api/               # FastAPI (Python) HTTP service generated from OpenAPI
/edge/              # Python edge/event consumers (stubs for now)
/web/               # Next.js dashboard: Lost search UI + Alerts views
/infra/
  compose.yaml      # Postgres + MinIO + NATS; local dev only
  migrations/       # SQL migrations
/tests/             # Contract & AC tests
README.md
```

> **Contracts are the source of truth.** Code must be generated from `/contracts/*` and **must not** change request/response shapes without editing the contracts first.

---

## Stack & conventions
- **API:** FastAPI + Pydantic models **generated from OpenAPI**.
- **Events:** NATS (or MQTT) consumers **generated/validated from AsyncAPI**.
- **DB:** Postgres (core tables), MinIO/S3 (encrypted blobs), Vector search is **mocked** for now.
- **Auth:** OAuth2 PKCE (device code acceptable for local dev). JWT for service‑to‑service.
- **Privacy defaults:** store **embeddings only**, photos optional; geolocation rounded to **geohash6**; export/erase endpoints required.

---

## Contracts
- Put the previously supplied YAML snippets into:
  - `contracts/openapi.yaml`
  - `contracts/asyncapi.yaml`
- The app must **generate server stubs and type‑safe clients** from these files at build time.
- CI must fail on **contract drift** (when handlers/types don’t match contracts).

---

## Agent tasks (checklist)
- [ ] **Bootstrap repo** with workspaces (pnpm or yarn) and Python API project.
- [ ] **Provision infra** via `infra/compose.yaml` for Postgres, MinIO, NATS.
- [ ] **Codegen** API server & clients from `openapi.yaml`; event types from `asyncapi.yaml`.
- [ ] **Implement minimal handlers**:
  - `POST /v1/cases` → persist case; return `{ case_id }`.
  - `POST /v1/cases/{id}/photos` → accept uploads (presigned S3/MinIO); store metadata.
  - `POST /v1/search` → return **deterministic mocked** candidates (fixture JSON).
  - Async consumers for `events.litter.*` and `playroom.alerts.*` → validate payloads → write `/events` & `/alerts` tables.
- [ ] **Web UI**:
  - Lost case form + Top‑K review table with bands (**strong/moderate/weak**).
  - Alerts pages: Multi‑Pet health alerts and Daycare playroom alerts with clip links.
- [ ] **Privacy console**: show consent flags (`shareVectors`, `sharePhotos`) and a one‑click **export/erase** action.
- [ ] **Tests**: Contract conformance + Acceptance Criteria (below).
- [ ] **Docs**: Serve rendered OpenAPI/AsyncAPI at `/docs` with redacted examples.

---

## Minimal data model (API layer)
Tables (simplified, use migrations):
- `users(id, role, email, phone_hash)`
- `cases(id, user_id, type, species, geohash6, consent_json, status, created_at, expires_at)`
- `photos(id, case_id, url_encrypted, view, hash)`
- `events(id, source, pet_id, type, ts, duration_s, conf, payload_json)`
- `alerts(id, pet_id, room_id, kind, severity, state, evidence_url, ts)`

---

## Acceptance Criteria (AC)
**Performance/UX**
- **AC‑LP‑1:** `POST /v1/search` returns **≤900 ms P95** (with mocked ANN) and **≥5 candidates** with confidence bands.
- **AC‑LP‑2:** Reviewer UI displays top‑K with band coloring; confirm/deny writes to DB.
- **AC‑MP‑1:** On receiving a valid `events.litter.*` message, an alert is created when thresholds are breached; UI shows it within **2 s**.
- **AC‑DK‑1:** On receiving a valid `playroom.alerts.*` message, an alert card renders within **2 s** with `clip_url` link.
- **AC‑PRIV‑1:** Export/erase endpoint cascades delete for a case; redacted lists when `sharePhotos=false`.

**Correctness**
- **AC‑CONTRACT‑1:** Schemas served by the API match `/contracts/openapi.yaml` (no additional/omitted fields).
- **AC‑CONTRACT‑2:** Event payloads are validated against `/contracts/asyncapi.yaml`; invalid messages are rejected and logged.

---

## Fixtures & mocks
- Place deterministic ANN fixtures at `tests/fixtures/search_candidates.json` (10 items with `score` and `band`).
- Provide example event JSON:
  - `tests/fixtures/litter_event.json`
  - `tests/fixtures/playroom_alert.json`

---

## Local development
**Prereqs:** Docker, Node 20+, Python 3.11+.

```bash
# 1) Infra
docker compose -f infra/compose.yaml up -d

# 2) Install
pnpm -w install

# 3) Run API
uvicorn api.main:app --reload

# 4) Run web
pnpm --filter web dev

# 5) Seed fixtures
python tests/seed_fixtures.py
```

**Env (.env example)**
```
POSTGRES_URL=postgres://pets:pets@localhost:5432/pets
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=pets-local
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
NATS_URL=nats://localhost:4222
JWT_ISSUER=http://localhost
JWT_AUDIENCE=pets-local
```

---

## Privacy & security defaults
- Store **embeddings only** by default; photos are opt‑in and encrypted at rest.
- Round locations to **geohash6** in public responses; never expose exact addresses.
- Support **export/erase** with cascade deletion; maintain audit logs for access.

---

## CI rules
- Contract check: regenerate clients on CI and fail if diffs exist.
- Run AC test suite and linters; block merge on failures.

---

## Out of scope (defer)
- Real vector search & re‑rank models, push notifications to devices, payments, multi‑tenant org management, production SSO.

---

## Ownership
- Contracts: **single source of truth.**
- Any change to request/response/event shapes must start with a PR to `/contracts/*`.
