import logging

log = logging.getLogger("pratyay.stub")


async def log_event(session, actor_id, action: str, target: str, meta: dict | None = None) -> None:
    """STUB until Lokesh's audit module lands (see docs/contracts.md)."""
    log.warning("STUB audit.log %s %s", action, target)
