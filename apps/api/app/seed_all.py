"""Seed everything every role's pages need, against DATABASE_URL (local or Neon).

    uv run python -m app.seed_all

Users, the two RBI Directions in data/sources, their approved rules (with stages), and six
fictional Lender A applications taken through the loan flow, which writes the evaluations,
decisions and step history (and calls the audit log). Safe to run again: nothing is duplicated.
Run migrations first (uv run alembic upgrade head).
"""

import asyncio
import sys

from app.core.db import SessionLocal
from app.loans.seed import seed_loans
from app.rules.seed import seed as seed_rules


async def main() -> int:
    async with SessionLocal() as session:
        report = await seed_rules(session)
        await session.flush()
        if report.problems:
            await session.rollback()
            for line in report.problems:
                print(f"Problem: {line}")
            return 1
        created, present = await seed_loans(session)
        await session.commit()
    print(f"Users added: {report.users_added}")
    for key, line in report.docs.items():
        print(f"{key}: {line}")
    print(f"Rules created: {', '.join(report.created) or 'none'}")
    print(f"Rules already present: {', '.join(report.skipped) or 'none'}")
    for line in report.corrected + report.left_out + report.skipped_steps:
        print(f"Note: {line}")
    print(f"Applications created: {', '.join(created) or 'none'}")
    print(f"Applications already present: {', '.join(present) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
