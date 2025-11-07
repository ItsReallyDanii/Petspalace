"""Event consumers for litter/feeder and playroom alerts."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
import nats
from nats.aio.msg import Msg
from pydantic import ValidationError

from api import database
from api.models import LitterEventPayload, PlayroomAlertPayload

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EdgeSettings:
    """Configuration for the edge consumers."""

    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    database_url: str = os.getenv("POSTGRES_URL", "sqlite:///./pets.db")
    litter_conf_threshold: float = float(os.getenv("LITTER_CONF_THRESHOLD", "0.4"))
    litter_duration_threshold: float = float(os.getenv("LITTER_DURATION_THRESHOLD", "180"))


SETTINGS = EdgeSettings()

database.configure(SETTINGS.database_url)


async def handle_litter_event(msg: Msg) -> None:
    """Handle events on the ``events.litter.*`` subject."""

    try:
        payload = LitterEventPayload.model_validate_json(msg.data.decode("utf-8"))
    except ValidationError as exc:  # pragma: no cover - logging path
        logger.error("Invalid litter event received: %s", exc)
        return

    logger.info("Received litter event on %s for pet %s", msg.subject, payload.pet_id)

    with database.session_scope() as session:
        database.record_litter_event(session, msg.subject, payload)
        duration_breach = payload.duration_s > SETTINGS.litter_duration_threshold
        confidence_breach = payload.conf < SETTINGS.litter_conf_threshold
        if duration_breach or confidence_breach:
            severity = "high" if confidence_breach else "moderate"
            database.create_alert_from_event(
                session,
                pet_id=payload.pet_id,
                kind="litter-anomaly",
                severity=severity,
            )


async def handle_playroom_alert(msg: Msg) -> None:
    """Handle alerts on the ``playroom.alerts.*`` subject."""

    try:
        payload = PlayroomAlertPayload.model_validate_json(msg.data.decode("utf-8"))
    except ValidationError as exc:  # pragma: no cover - logging path
        logger.error("Invalid playroom alert received: %s", exc)
        return

    logger.info("Received playroom alert for room %s", payload.room_id)

    with database.session_scope() as session:
        database.record_playroom_alert(session, payload)


async def main() -> None:
    """Main entrypoint for the consumer process."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    nc = await nats.connect(SETTINGS.nats_url)
    await nc.subscribe("events.litter.*", cb=handle_litter_event)
    await nc.subscribe("playroom.alerts.*", cb=handle_playroom_alert)
    logger.info("Edge consumers listening on %s", SETTINGS.nats_url)
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:  # pragma: no cover - shutdown path
        pass
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
