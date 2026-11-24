# Pratyay

Quantum-safe, intelligent regulatory compliance and risk assessment for digital lending.

RBI documents become executable rules, the rules that apply decide each loan, and every decision is signed with ML-DSA-65 so anyone can verify it.

B.Tech CSE project, Gautam Buddha University.
Vaibhav Porwal, Vishnukant Yadav, Lokesh Singh, Pulkit Kumar Talan. Supervisor: Dr. Isha.

## Structure

| Path | What |
| --- | --- |
| `apps/web` | Next.js web app |
| `apps/api` | FastAPI service: `rules` (Policy-to-Code), `identity`, `origination`, `decision`, `trust`, `audit` |
| `ml/` | Obligation classifier training |
| `data/` | Source regulation PDFs and the field dictionary |

## Run locally

```bash
cp .env.example .env
docker compose up -d
cd apps/api && uv sync && uv run alembic upgrade head && uv run fastapi dev app/main.py
cd apps/web && pnpm install && pnpm dev
```

Web: http://localhost:3000 · API docs: http://localhost:8000/docs · DB check: http://localhost:8000/health/db

Not affiliated with RBI, NPCI, MFIN or any lender.
