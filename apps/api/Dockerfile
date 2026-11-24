# Build from the REPO ROOT (the classifier's labels live in ml/):
#   docker build -f apps/api/Dockerfile -t pratyay-api .
# Render: Dockerfile path apps/api/Dockerfile, Docker build context directory "." (repo root).
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
# Same layout as the repo, so ml/obligation/train.py and app/rules/classify.py find each other.
WORKDIR /repo/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/ ./
COPY ml/obligation/train.py ml/obligation/labels.csv /repo/ml/obligation/
# Train the obligation classifier from the committed labels, so uploads get labelled in
# production. Any failure here fails the build.
RUN .venv/bin/python /repo/ml/obligation/train.py > /tmp/train.log \
 && test -s /repo/ml/obligation/models/obligation.joblib \
 && tail -n 3 /tmp/train.log
ENV PATH="/repo/apps/api/.venv/bin:$PATH"
EXPOSE 8000
# Render sets $PORT. Migrate, then serve. /health and /health/db stay unauthenticated.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
