"""Seed helper for loading example events into a local database."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import asyncpg


DB_DSN = "postgresql://app:password@localhost:5432/pets"


async def seed_events(conn: asyncpg.Connection) -> None:
    """Insert example events into the ``events`` table."""

    fixture_path = Path(__file__).resolve().parent / "fixtures/litter_event.json"
    with open(fixture_path, "r", encoding="utf-8") as fp:
        event = json.load(fp)
    await conn.execute(
        """
        INSERT INTO events (source, pet_id, type, ts, duration_s, conf, payload_json)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        "litter_device_1",
        event["pet_id"],
        event["type"],
        event["ts"],
        event["duration_s"],
        event["conf"],
        json.dumps(event["payload"]),
    )


async def seed_alerts(conn: asyncpg.Connection) -> None:
    """Insert example alerts into the ``alerts`` table."""

    fixture_path = Path(__file__).resolve().parent / "fixtures/playroom_alert.json"
    with open(fixture_path, "r", encoding="utf-8") as fp:
        alert = json.load(fp)
    await conn.execute(
        """
        INSERT INTO alerts (pet_id, room_id, kind, severity, state, evidence_url, ts)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        alert["pet_id"],
        alert["room_id"],
        alert["kind"],
        alert["severity"],
        alert["state"],
        alert["evidence_url"],
        alert["ts"],
    )


async def main() -> None:
    conn = await asyncpg.connect(DB_DSN)
    try:
        await seed_events(conn)
        await seed_alerts(conn)
        print("Seeded fixtures successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
