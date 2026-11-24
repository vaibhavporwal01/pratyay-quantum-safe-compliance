"""Obligation classifier: label rules.paragraphs as requirement / definition / information.

The model is trained by ml/obligation/train.py and loaded once per process. Each paragraph
gets `label` (the top class) and `confidence` (its probability, 3 decimals). A confidence
below REVIEW_THRESHOLD means a person must check the label.

CLI (from apps/api):

    uv run python -m app.rules.classify --doc all
    uv run python -m app.rules.classify --doc <source_doc uuid>
"""

import argparse
import asyncio
import uuid
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rules.models import Paragraph, SourceDoc
from app.rules.obligation_features import FEATURES_VERSION, LABELS, Record, make_records

REVIEW_THRESHOLD = Decimal("0.800")
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[4] / "ml" / "obligation" / "models" / "obligation.joblib"
)


class ModelNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadedModel:
    pipeline: Any
    labels: tuple[str, ...]
    version: str


@dataclass
class ClassifyResult:
    doc_id: uuid.UUID
    model_version: str
    total: int = 0
    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(LABELS, 0))
    needs_review: list[uuid.UUID] = field(default_factory=list)


def model_path() -> Path:
    return Path(settings.obligation_model_path or DEFAULT_MODEL_PATH)


@cache
def load_model(path: Path | None = None) -> LoadedModel:
    """Load the joblib bundle once. Only load model files this project trained:
    joblib files are pickles and run code when loaded."""
    path = path or model_path()
    if not path.is_file():
        raise ModelNotFound(f"No obligation model at {path}. Run ml/obligation/train.py.")
    bundle = joblib.load(path)
    if bundle.get("features_version") != FEATURES_VERSION:
        raise ModelNotFound(
            f"Model at {path} was built for features version {bundle.get('features_version')}, "
            f"this code needs {FEATURES_VERSION}. Run ml/obligation/train.py."
        )
    labels = tuple(bundle["labels"])
    if set(labels) != set(LABELS):
        raise ModelNotFound(f"Model labels {labels} do not match {LABELS}")
    return LoadedModel(bundle["pipeline"], labels, str(bundle["version"]))


def needs_review(confidence: Decimal | None) -> bool:
    return confidence is None or confidence < REVIEW_THRESHOLD


def predict(records: list[Record], model: LoadedModel) -> list[tuple[str, Decimal]]:
    """records come from make_records() over a whole document."""
    if not records:
        return []
    probs = model.pipeline.predict_proba(records)
    classes = list(model.pipeline.classes_)
    out = []
    for row in probs:
        best = int(row.argmax())
        conf = Decimal(str(float(row[best]))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        out.append((classes[best], conf))
    return out


async def classify_paragraphs(
    session: AsyncSession, doc_id: uuid.UUID, model: LoadedModel | None = None
) -> ClassifyResult:
    """Fill label and confidence for every paragraph of the document, then commit."""
    model = model or load_model()
    paragraphs = list(await session.scalars(select(Paragraph).where(Paragraph.doc_id == doc_id)))
    records = make_records([(p.number, p.text) for p in paragraphs])
    result = ClassifyResult(doc_id=doc_id, model_version=model.version)
    for p, (label, conf) in zip(paragraphs, predict(records, model), strict=True):
        p.label = label
        p.confidence = conf
        result.total += 1
        result.counts[label] += 1
        if needs_review(conf):
            result.needs_review.append(p.id)
    await session.commit()
    return result


async def _run(doc: str) -> list[ClassifyResult]:
    from app.core.db import SessionLocal, engine

    try:
        async with SessionLocal() as session:
            if doc == "all":
                doc_ids = list(await session.scalars(select(SourceDoc.id)))
            else:
                doc_id = uuid.UUID(doc)
                if await session.get(SourceDoc, doc_id) is None:
                    raise SystemExit(f"No source doc {doc_id}")
                doc_ids = [doc_id]
            return [await classify_paragraphs(session, d) for d in doc_ids]
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify rules.paragraphs by obligation type.")
    parser.add_argument("--doc", required=True, help="source doc uuid, or 'all'")
    args = parser.parse_args()
    results = asyncio.run(_run(args.doc))
    for r in results:
        counts = ", ".join(f"{k} {v}" for k, v in r.counts.items())
        print(
            f"{r.doc_id}  model {r.model_version}  {r.total} paragraphs ({counts}); "
            f"{len(r.needs_review)} below {REVIEW_THRESHOLD} need a person"
        )


if __name__ == "__main__":
    main()
