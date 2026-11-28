# Build from the repository root:
# docker build -f apps/api/Dockerfile -t pratyay-api .

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH=/usr/local/lib

# Native liboqs build dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      cmake \
      ninja-build \
      gcc \
      g++ \
      make \
      libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# Build and install pinned liboqs native library
ARG LIBOQS_VERSION=0.16.0

RUN git clone --depth 1 --branch ${LIBOQS_VERSION} \
      https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
 && cmake -S /tmp/liboqs -B /tmp/liboqs/build -GNinja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DBUILD_SHARED_LIBS=ON \
      -DOQS_BUILD_ONLY_LIB=ON \
      -DOQS_DIST_BUILD=ON \
 && cmake --build /tmp/liboqs/build --parallel 2 \
 && cmake --install /tmp/liboqs/build \
 && ldconfig \
 && rm -rf /tmp/liboqs

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /bin/uv

WORKDIR /repo/apps/api

COPY apps/api/pyproject.toml apps/api/uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

# Verify Python wrapper and native algorithms during image build
RUN .venv/bin/python -c "import oqs; print('liboqs:', oqs.oqs_python_version()); assert 'ML-DSA-65' in oqs.get_enabled_sig_mechanisms(); assert 'ML-KEM-768' in oqs.get_enabled_kem_mechanisms(); print('PQC algorithms verified')"

COPY apps/api/ ./
COPY data/sources/ /repo/data/sources/
COPY ml/obligation/train.py ml/obligation/labels.csv /repo/ml/obligation/

RUN .venv/bin/python /repo/ml/obligation/train.py > /tmp/train.log \
 && test -s /repo/ml/obligation/models/obligation.joblib \
 && tail -n 3 /tmp/train.log

ENV PATH="/repo/apps/api/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
