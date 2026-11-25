"""rules.params: add the fact fields the template engine reads. Values unchanged.

The engine now evaluates by template and reads which fact to check from each rule's params
(app.rules.facts). This adds those fields to the seeded rules that existed before it. It only
ADDS keys that are absent; it never changes an existing key, so every number in params stays
as it was (tests/test_migration_0008.py checks this). One audit event per rule changed:
"params schema updated, values unchanged".

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.util import await_only

from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

# (code, template) -> fields to add. Only rules with a catalogue fact are listed; servicing
# and recovery rules (KF-02, MF-06, MF-05) have nothing to add.
ADD: dict[tuple[str, str], dict] = {
    ("MF-01", "max_amount"): {"fact": "household_income_annual_paise",
                              "must_be_false": "collateral", "decides_scope": True},
    ("MF-02", "max_ratio"): {"numerator_fact": "monthly_repayments_paise",
                             "denominator_fact": "household_income_monthly_paise",
                             "offer_on_fail": True},
    ("MF-04", "prohibited_charge"): {"fact": "prepayment_charge_paise"},
    ("KF-01", "min_days"): {"fact": "kfs_validity_working_days"},
    ("KF-03", "required_disclosure"): {"fact": "apr_computation_sheet"},
}
ACTION = "rule_params_schema_updated"
NOTE = "params schema updated, values unchanged"

rules = sa.table(
    'rules',
    sa.column('id'), sa.column('code'), sa.column('template'), sa.column('params', JSONB),
    schema='rules',
)


def _log(bind, rule_id, code: str, added: list[str]) -> None:
    """One audit event through audit.service.log_event, inside this migration's transaction."""
    from app.audit import service as audit

    proxy = AsyncConnection._retrieve_proxy_for_target(bind)
    session = AsyncSession(bind=proxy) if proxy is not None else None
    await_only(audit.log_event(session, None, ACTION, f"rule:{rule_id}",
                               {"code": code, "note": NOTE, "added": added}))


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(rules.c.id, rules.c.code, rules.c.template, rules.c.params)
                        .order_by(rules.c.code, rules.c.id)).all()
    for row in rows:
        fields = ADD.get((row.code, row.template))
        if not fields:
            continue
        params = dict(row.params or {})
        added = [k for k in fields if k not in params]
        if not added:
            continue
        params |= {k: fields[k] for k in added}
        bind.execute(sa.update(rules).where(rules.c.id == row.id)
                     .values(params=params))
        _log(bind, row.id, row.code, added)


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(rules.c.id, rules.c.code, rules.c.template, rules.c.params)).all()
    for row in rows:
        fields = ADD.get((row.code, row.template))
        if not fields:
            continue
        params = {k: v for k, v in (row.params or {}).items()
                  if not (k in fields and v == fields[k])}
        bind.execute(sa.update(rules).where(rules.c.id == row.id)
                     .values(params=params))
