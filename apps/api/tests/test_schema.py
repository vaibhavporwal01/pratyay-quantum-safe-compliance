"""P1 schema: the migration creates every table and enforces its constraints."""

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from alembic import command
from tests.conftest import alembic_config

EXPECTED_TABLES = {
    ("rules", "source_docs"),
    ("rules", "paragraphs"),
    ("rules", "rule_sets"),
    ("rules", "rules"),
    ("rules", "change_proposals"),
    ("origination", "applications"),
    ("decision", "decisions"),
    ("decision", "rule_results"),
}

TABLES_SQL = text(
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_schema IN ('rules', 'origination', 'decision')"
)


async def _tables(url: str) -> set[tuple[str, str]]:
    engine = create_async_engine(url)
    async with engine.connect() as c:
        rows = (await c.execute(TABLES_SQL)).all()
    await engine.dispose()
    return {(r[0], r[1]) for r in rows}


# ---- helpers: each insert returns the new row's id -------------------------------------


async def _scalar(conn: AsyncConnection, sql: str, **params) -> uuid.UUID:
    return (await conn.execute(text(sql), params)).scalar_one()


async def make_rule_set(conn: AsyncConnection, org_id: uuid.UUID, version: int) -> uuid.UUID:
    return await _scalar(
        conn,
        "INSERT INTO rules.rule_sets (org_id, version) VALUES (:org, :v) RETURNING id",
        org=org_id,
        v=version,
    )


async def make_source_doc(conn: AsyncConnection) -> uuid.UUID:
    return await _scalar(
        conn, "INSERT INTO rules.source_docs (title) VALUES ('Test circular') RETURNING id"
    )


async def make_rule(
    conn: AsyncConnection, rule_set_id: uuid.UUID, doc_id: uuid.UUID, code: str
) -> uuid.UUID:
    return await _scalar(
        conn,
        "INSERT INTO rules.rules (rule_set_id, code, title, body, effective_from, "
        "source_doc_id, source_para, origin) VALUES (:rs, :code, 'Title', '{}'::jsonb, "
        ":eff, :doc, '4.1', 'manual') RETURNING id",
        rs=rule_set_id,
        code=code,
        eff=date(2026, 1, 1),
        doc=doc_id,
    )


async def make_application(conn: AsyncConnection, org_id: uuid.UUID) -> uuid.UUID:
    return await _scalar(
        conn,
        "INSERT INTO origination.applications (org_id, borrower_id, amount_paise, "
        "tenure_months, status) VALUES (:org, :b, 5000000, 12, 'submitted') RETURNING id",
        org=org_id,
        b=uuid.uuid4(),
    )


async def make_decision(
    conn: AsyncConnection,
    app_id: uuid.UUID,
    rule_set_id: uuid.UUID,
    maker_id: uuid.UUID,
    checker_id: uuid.UUID | None,
) -> uuid.UUID:
    return await _scalar(
        conn,
        "INSERT INTO decision.decisions (application_id, rule_set_id, outcome, maker_id, "
        "checker_id) VALUES (:a, :rs, 'pass', :m, :c) RETURNING id",
        a=app_id,
        rs=rule_set_id,
        m=maker_id,
        c=checker_id,
    )


async def assert_rejected(conn: AsyncConnection, coro, constraint: str) -> None:
    """Run the insert in a savepoint so the outer test transaction stays usable."""
    with pytest.raises(IntegrityError) as exc:
        async with conn.begin_nested():
            await coro
    assert constraint in str(exc.value)


# ---- tests ------------------------------------------------------------------------------


async def test_all_tables_exist(migrated_db: str) -> None:
    assert await _tables(migrated_db) == EXPECTED_TABLES


def test_downgrade_then_upgrade_round_trip(migrated_db: str) -> None:
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    assert asyncio.run(_tables(migrated_db)) == set()
    command.upgrade(cfg, "head")
    assert asyncio.run(_tables(migrated_db)) == EXPECTED_TABLES


async def test_maker_checker_rejects_same_person(conn: AsyncConnection) -> None:
    org = uuid.uuid4()
    rs = await make_rule_set(conn, org, 1)
    app_id = await make_application(conn, org)
    maker = uuid.uuid4()

    await assert_rejected(
        conn, make_decision(conn, app_id, rs, maker, maker), "ck_decisions_maker_checker"
    )
    # No checker yet, and a different checker, are both allowed.
    assert await make_decision(conn, app_id, rs, maker, None)
    assert await make_decision(conn, app_id, rs, maker, uuid.uuid4())


async def test_rule_set_version_unique_per_org(conn: AsyncConnection) -> None:
    org = uuid.uuid4()
    await make_rule_set(conn, org, 1)
    await assert_rejected(conn, make_rule_set(conn, org, 1), "uq_rule_sets_org_id_version")
    # Same version in another org is fine.
    assert await make_rule_set(conn, uuid.uuid4(), 1)


async def test_rule_code_unique_per_rule_set(conn: AsyncConnection) -> None:
    doc = await make_source_doc(conn)
    rs1 = await make_rule_set(conn, uuid.uuid4(), 1)
    rs2 = await make_rule_set(conn, uuid.uuid4(), 1)
    await make_rule(conn, rs1, doc, "LTV-01")
    await assert_rejected(conn, make_rule(conn, rs1, doc, "LTV-01"), "uq_rules_rule_set_id_code")
    assert await make_rule(conn, rs2, doc, "LTV-01")


async def test_rule_result_primary_key(conn: AsyncConnection) -> None:
    org = uuid.uuid4()
    doc = await make_source_doc(conn)
    rs = await make_rule_set(conn, org, 1)
    rule = await make_rule(conn, rs, doc, "KYC-01")
    dec = await make_decision(conn, await make_application(conn, org), rs, uuid.uuid4(), None)
    sql = text(
        "INSERT INTO decision.rule_results (decision_id, rule_id, result) "
        "VALUES (:d, :r, 'pass')"
    )
    await conn.execute(sql, {"d": dec, "r": rule})
    await assert_rejected(conn, conn.execute(sql, {"d": dec, "r": rule}), "pk_rule_results")


async def test_enum_check_rejects_unknown_value(conn: AsyncConnection) -> None:
    coro = conn.execute(
        text(
            "INSERT INTO rules.rule_sets (org_id, version, status) "
            "VALUES (:o, 1, 'archived')"
        ),
        {"o": uuid.uuid4()},
    )
    await assert_rejected(conn, coro, "ck_rule_sets_status")


async def test_server_defaults(conn: AsyncConnection) -> None:
    row = (
        await conn.execute(
            text(
                "INSERT INTO rules.source_docs (title) VALUES ('Defaults') "
                "RETURNING id, uploaded_at"
            )
        )
    ).one()
    assert isinstance(row.id, uuid.UUID)
    assert row.uploaded_at.tzinfo is not None
    status = (
        await conn.execute(
            text("SELECT status FROM rules.rule_sets WHERE id = :id"),
            {"id": await make_rule_set(conn, uuid.uuid4(), 1)},
        )
    ).scalar_one()
    assert status == "draft"


async def test_source_doc_hash_is_unique(conn: AsyncConnection) -> None:
    sql = text("INSERT INTO rules.source_docs (title, sha3_256) VALUES ('Doc', :h)")
    await conn.execute(sql, {"h": b"\x01" * 32})
    await assert_rejected(conn, conn.execute(sql, {"h": b"\x01" * 32}), "ix_source_docs_sha3_256")
    # Documents without a hash yet do not collide with each other.
    await conn.execute(text("INSERT INTO rules.source_docs (title) VALUES ('A'), ('B')"))
