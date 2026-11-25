"""Migration 0008 adds the fact fields to rule params and never changes an existing number."""

import asyncio
import json
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic import command
from app.audit import service as audit
from tests.conftest import alembic_config
from tests.rule_fixtures import FACT_FIELDS, ISSUED, RULES


def numbers(value: Any, path: str = "") -> dict[str, Any]:
    """Every numeric leaf in params, by path: ints, floats and numeric strings ("50")."""
    if isinstance(value, dict):
        return {k: v for key, item in value.items() for k, v in numbers(item, f"{path}.{key}").items()}
    if isinstance(value, list):
        return {k: v for i, item in enumerate(value) for k, v in numbers(item, f"{path}.{i}").items()}
    if isinstance(value, bool):
        return {}
    if isinstance(value, int | float):
        return {path: value}
    if isinstance(value, str):
        try:
            Decimal(value)
        except InvalidOperation:
            return {}
        return {path: value}
    return {}


async def _insert(url: str) -> tuple[list[str], list[str]]:
    engine = create_async_engine(url)
    rule_ids, doc_ids = [], []
    async with engine.begin() as c:
        docs = {}
        for code in ("CF", "RBC"):
            doc_id = str(uuid.uuid4())
            short = f"M8{code}"[:12]
            await c.execute(text("INSERT INTO rules.source_docs (id, title, short_code) "
                                 "VALUES (:id, :t, :s)"),
                            {"id": doc_id, "t": f"Migration test {code}", "s": short})
            docs[code] = doc_id
            doc_ids.append(doc_id)
        maker, checker = str(uuid.uuid4()), str(uuid.uuid4())
        for doc, para, code, template, applies, stage, params, para_text in RULES:
            rule_id = str(uuid.uuid4())
            await c.execute(text(
                "INSERT INTO rules.rules (id, code, title, template, params, applies_to, stage, "
                "effective_from, status, source_doc_id, source_para, para_text, origin, made_by, "
                "checked_by) VALUES (:id, :code, :code, :template, CAST(:params AS jsonb), "
                ":applies, :stage, :eff, 'approved', :doc, :para, :text, 'manual', :maker, "
                ":checker)"),
                {"id": rule_id, "code": code, "template": template, "params": json.dumps(params),
                 "applies": applies, "stage": stage, "eff": ISSUED, "doc": docs[doc],
                 "para": para, "text": para_text, "maker": maker, "checker": checker})
            rule_ids.append(rule_id)
    await engine.dispose()
    return rule_ids, doc_ids


async def _params(url: str, ids: list[str]) -> dict[str, dict]:
    engine = create_async_engine(url)
    async with engine.connect() as c:
        rows = (await c.execute(text("SELECT code, params FROM rules.rules WHERE id::text = ANY(:ids)"),
                                {"ids": ids})).all()
    await engine.dispose()
    return {r.code: r.params for r in rows}


async def _cleanup(url: str, rule_ids: list[str], doc_ids: list[str]) -> None:
    engine = create_async_engine(url)
    async with engine.begin() as c:
        await c.execute(text("DELETE FROM rules.rules WHERE id::text = ANY(:ids)"), {"ids": rule_ids})
        await c.execute(text("DELETE FROM rules.source_docs WHERE id::text = ANY(:ids)"),
                        {"ids": doc_ids})
    await engine.dispose()


def test_0008_adds_fact_fields_and_keeps_every_number(migrated_db, monkeypatch) -> None:
    events: list[tuple] = []

    async def record(session, actor_id, action, target, meta=None):
        events.append((type(session), actor_id, action, target, meta))

    monkeypatch.setattr(audit, "log_event", record)
    cfg = alembic_config()
    command.downgrade(cfg, "0007")
    rule_ids, doc_ids = asyncio.run(_insert(migrated_db))
    try:
        before = asyncio.run(_params(migrated_db, rule_ids))
        command.upgrade(cfg, "0008")
        after = asyncio.run(_params(migrated_db, rule_ids))

        assert set(before) == set(after) == {r[2] for r in RULES}
        for code, old in before.items():
            new = after[code]
            # Every number identical, and no number added.
            assert numbers(new) == numbers(old), code
            # Every existing key unchanged; only the fact fields were added.
            assert {k: new[k] for k in old} == old, code
            assert {k: v for k, v in new.items() if k not in old} == FACT_FIELDS.get(code, {})

        # One audit event per rule changed, in the migration's own transaction.
        assert sorted(e[4]["code"] for e in events) == sorted(FACT_FIELDS)
        assert all(e[2] == "rule_params_schema_updated" for e in events)
        assert all(e[4]["note"] == "params schema updated, values unchanged" for e in events)
        assert all(e[0] is AsyncSession for e in events)

        # Downgrade removes exactly what it added.
        command.downgrade(cfg, "0007")
        assert asyncio.run(_params(migrated_db, rule_ids)) == before
    finally:
        command.upgrade(cfg, "head")
        asyncio.run(_cleanup(migrated_db, rule_ids, doc_ids))
