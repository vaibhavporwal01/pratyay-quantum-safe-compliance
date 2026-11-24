"""Obligation classifier: reproducible training, and classify against the real Directions."""

import csv
import importlib.util
from decimal import Decimal
from itertools import groupby
from pathlib import Path

import joblib
import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.rules import classify as classify_mod
from app.rules.classify import REVIEW_THRESHOLD, LoadedModel, classify_paragraphs, needs_review
from app.rules.ingest import ingest_pdf
from app.rules.obligation_features import LABELS, MODEL_NAMES, make_records
from app.rules.service import list_paragraphs

ROOT = Path(__file__).resolve().parents[3]
TRAIN_PY = ROOT / "ml" / "obligation" / "train.py"
LABELS_CSV = ROOT / "ml" / "obligation" / "labels.csv"
SOURCES = ROOT / "data" / "sources"
CREDIT = SOURCES / "rbi-nbfc-credit-facilities-directions-2025.pdf"
CONDUCT = SOURCES / "rbi-nbfc-responsible-business-conduct-directions-2025.pdf"

pytestmark = pytest.mark.skipif(not LABELS_CSV.is_file(), reason="labels.csv not present")


def _load_train():
    spec = importlib.util.spec_from_file_location("obligation_train", TRAIN_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def train_mod():
    return _load_train()


@pytest.fixture(scope="module")
def trained(train_mod):
    return train_mod.train(LABELS_CSV, seed=42)


@pytest.fixture(scope="module")
def model(trained, train_mod, tmp_path_factory) -> LoadedModel:
    """Save with train.save_model and load through classify, as production does."""
    results, pipeline = trained
    path = tmp_path_factory.mktemp("model") / "obligation.joblib"
    train_mod.save_model(pipeline, results["model_version"], path)
    return classify_mod.load_model(path)


def test_training_is_reproducible(trained, train_mod):
    results_a, pipe_a = trained
    results_b, pipe_b = train_mod.train(LABELS_CSV, seed=42)
    assert results_a == results_b
    sample = make_records(
        [("5", "An NBFC shall not charge penal interest."), ("5(1)", "Microfinance Loans")]
    )
    np.testing.assert_array_equal(pipe_a.predict_proba(sample), pipe_b.predict_proba(sample))


def test_results_shape(trained):
    results, _ = trained
    assert results["n_train"] + results["n_test"] == results["n_labelled"]
    for key in (*MODEL_NAMES, "keyword_baseline"):
        m = results["held_out_test"][key]
        assert set(m["per_class"]) == set(LABELS)
        matrix = np.array(m["confusion_matrix"]["rows_true_cols_pred"])
        assert matrix.shape == (3, 3) and matrix.sum() == results["n_test"]

    assert set(results["per_class_f1_held_out"]) == set(LABELS)
    assert results["status"].startswith("draft")


def test_model_is_chosen_by_cv_on_train_only(trained):
    sel = trained[0]["selection"]
    assert set(sel["cv_on_train"]) == set(MODEL_NAMES)
    assert all(len(v["scores"]) == 5 for v in sel["cv_on_train"].values())
    assert sel["chosen"] == max(MODEL_NAMES, key=lambda n: sel["cv_on_train"][n]["mean"])


def test_heuristic_matches_csv_suggested_label():
    """Training uses the heuristic computed in make_records; it must equal the CSV column."""
    with LABELS_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for _, doc_rows in groupby(rows, key=lambda r: r["doc_ref"]):
        doc_rows = list(doc_rows)
        records = make_records([(r["number"], r["text"]) for r in doc_rows])
        assert [r["suggested"] for r in records] == [r["suggested_label"] for r in doc_rows]


def test_make_records_context():
    long_parent = "Each NBFC shall ensure the following: " + "x" * 300
    records = make_records(
        [
            ("22", long_parent),
            ("22(1)", "Board\napproved policy"),
            ("23", "Definitions"),
            ("24(1)", "Orphan item"),
        ]
    )
    assert records[0]["parent"] == ""
    assert records[1] == {
        "text": "Board approved policy",
        "parent": long_parent[:200],
        "suggested": "information",
    }
    assert records[2]["parent"] == "" and records[3]["parent"] == ""


def test_saved_bundle_has_labels_and_version(model, trained):
    assert set(model.labels) == set(LABELS)
    assert model.version == trained[0]["model_version"]


async def test_classify_fills_every_paragraph_of_both_documents(
    session: AsyncSession, model: LoadedModel
) -> None:
    for path, ref in ((CREDIT, "RBI/DOR/2025-26/347"), (CONDUCT, "RBI/DOR/2025-26/362")):
        doc = (await ingest_pdf(session, path, title=path.stem, ref_no=ref)).doc
        result = await classify_paragraphs(session, doc.id, model)
        paras = await list_paragraphs(session, doc.id)

        assert result.total == len(paras) > 100
        assert all(p.label in LABELS for p in paras)
        assert all(p.confidence is not None and 0 < p.confidence <= 1 for p in paras)
        assert sum(result.counts.values()) == len(paras)
        flagged = {p.id for p in paras if p.confidence < REVIEW_THRESHOLD}
        assert set(result.needs_review) == flagged


class _UnsureModel:
    """Stands in for the pipeline: low confidence on one text, high on the other."""

    classes_ = np.array(LABELS)

    def predict_proba(self, texts):
        return np.array(
            [[0.5, 0.3, 0.2] if "unsure" in t["text"] else [0.05, 0.05, 0.9] for t in texts]
        )


async def test_low_confidence_rows_are_flagged(session: AsyncSession, model: LoadedModel) -> None:
    doc = (await ingest_pdf(session, CREDIT, title="credit", ref_no="RBI/DOR/2025-26/347")).doc
    paras = await list_paragraphs(session, doc.id)
    unsure_ids = {p.id for p in paras[:5]}
    for p in paras[:5]:
        p.text = "unsure " + p.text

    fake = LoadedModel(_UnsureModel(), LABELS, "test")
    result = await classify_paragraphs(session, doc.id, fake)

    assert set(result.needs_review) == unsure_ids
    for p in await list_paragraphs(session, doc.id):
        if p.id in unsure_ids:
            assert (p.label, p.confidence) == ("requirement", Decimal("0.500"))
        else:
            assert (p.label, p.confidence) == ("information", Decimal("0.900"))


def test_needs_review_threshold():
    assert needs_review(Decimal("0.799"))
    assert not needs_review(Decimal("0.800"))
    assert needs_review(None)


def test_model_for_old_features_is_refused(tmp_path):
    path = tmp_path / "old.joblib"
    joblib.dump({"pipeline": None, "labels": list(LABELS), "version": "1.0.0"}, path)
    with pytest.raises(classify_mod.ModelNotFound, match="features version"):
        classify_mod.load_model(path)


def test_missing_model_raises(tmp_path):
    with pytest.raises(classify_mod.ModelNotFound):
        classify_mod.load_model(tmp_path / "nope.joblib")
