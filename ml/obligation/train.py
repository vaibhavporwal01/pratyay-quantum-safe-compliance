"""Train the obligation classifier from ml/obligation/labels.csv.

Usage (from the repo root):

    uv run --project apps/api python ml/obligation/train.py
    uv run --project apps/api python ml/obligation/train.py --seed 42 --no-save

Reads the `label` column. Features and pipelines live in
apps/api/app/rules/obligation_features.py:
  - TF-IDF word 1-2 grams and char 3-5 grams on the paragraph
  - TF-IDF word 1-2 grams on the parent paragraph's first 200 characters (sub-paragraphs)
  - hand features: shall / shall not / must / not exceed / may / means, heading-like,
    length, short fragment, ends with ":", has a parent
  - the keyword heuristic's label, one-hot
Candidates: logistic regression and LinearSVC (sigmoid-calibrated for confidences), both
with balanced class weights.

Protocol:
  1. Stratified 80/20 split with a fixed seed (the same split as model 1.0.0).
  2. 5-fold stratified CV (macro F1) of each candidate on the 80% only.
     The candidate with the higher CV mean is chosen. The 20% plays no part in the choice.
  3. Each candidate is fitted on the 80% and scored on the 20%, next to the keyword
     baseline on the same 20%, for reporting.

Writes:
    ml/obligation/results.json             selection, CV and held-out metrics
    ml/obligation/models/obligation.joblib the chosen model (gitignored)
"""

import argparse
import csv
import hashlib
import json
import sys
from itertools import groupby
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "apps" / "api"))

from app.rules.obligation_features import (
    FEATURES_VERSION,
    LABELS,
    MODEL_NAMES,
    build_pipeline,
    make_records,
)

SEED = 42
MODEL_VERSION = "2.0.0"
LABELS_CSV = HERE / "labels.csv"
RESULTS_JSON = HERE / "results.json"
MODEL_PATH = HERE / "models" / "obligation.joblib"
BASELINE = "keyword_baseline"


def load_labelled(path: Path) -> tuple[list[dict], list[str], list[str], str]:
    """Records (with document context) for rows with a valid label.

    Context is built from every row of the document, labelled or not, so parents are found.
    Returns records, labels, the CSV's suggested_label column, and sha256 of the file.
    """
    raw = path.read_bytes()
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    records, labels, suggested = [], [], []
    for _, doc_rows in groupby(rows, key=lambda r: r["doc_ref"]):
        doc_rows = list(doc_rows)
        doc_records = make_records([(r["number"] or None, r["text"]) for r in doc_rows])
        for row, rec in zip(doc_rows, doc_records, strict=True):
            label = row["label"].strip().lower()
            if label in LABELS:
                records.append(rec)
                labels.append(label)
                suggested.append(row["suggested_label"].strip().lower())
    return records, labels, suggested, hashlib.sha256(raw).hexdigest()


def metrics(y_true: list[str], y_pred: list[str]) -> dict:
    p, r, f, s = precision_recall_fscore_support(
        y_true, y_pred, labels=list(LABELS), zero_division=0
    )
    return {
        "per_class": {
            lab: {
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f[i]), 4),
                "support": int(s[i]),
            }
            for i, lab in enumerate(LABELS)
        },
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=list(LABELS), average="macro")), 4),
        "accuracy": round(float(np.mean(np.array(y_true) == np.array(y_pred))), 4),
        "confusion_matrix": {
            "labels": list(LABELS),
            "rows_true_cols_pred": confusion_matrix(y_true, y_pred, labels=list(LABELS)).tolist(),
        },
    }


def train(labels_csv: Path = LABELS_CSV, seed: int = SEED) -> tuple[dict, object]:
    records, y, suggested_csv, sha = load_labelled(labels_csv)
    suggested = [r["suggested"] for r in records]
    if suggested != suggested_csv:
        raise SystemExit("labels.csv suggested_label no longer matches the keyword heuristic")

    idx = np.arange(len(records))
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=seed)
    x_tr = [records[i] for i in tr]
    y_tr = [y[i] for i in tr]
    x_te = [records[i] for i in te]
    y_te = [y[i] for i in te]

    # 1. Model selection: CV on the training 80% only.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    cv_results = {}
    for name in MODEL_NAMES:
        scores = cross_val_score(build_pipeline(seed, name), x_tr, y_tr, cv=cv, scoring="f1_macro")
        cv_results[name] = {
            "scores": [round(float(s), 4) for s in scores],
            "mean": round(float(scores.mean()), 4),
            "std": round(float(scores.std()), 4),
        }
    chosen = max(MODEL_NAMES, key=lambda n: (cv_results[n]["mean"], -cv_results[n]["std"]))

    # 2. Reporting: every candidate and the baseline on the same held-out 20%.
    fitted = {name: build_pipeline(seed, name).fit(x_tr, y_tr) for name in MODEL_NAMES}
    held_out = {name: metrics(y_te, fitted[name].predict(x_te).tolist()) for name in MODEL_NAMES}
    held_out[BASELINE] = metrics(y_te, [suggested[i] for i in te])

    results = {
        "status": "draft: labels are unreviewed AI drafts",
        "model_version": f"{MODEL_VERSION}+labels.{sha[:8]}",
        "features_version": FEATURES_VERSION,
        "seed": seed,
        "labels_csv_sha256": sha,
        "n_labelled": len(records),
        "n_train": len(tr),
        "n_test": len(te),
        "class_counts": {lab: y.count(lab) for lab in LABELS},
        "selection": {
            "criterion": "highest mean macro F1, 5-fold stratified CV on the training 80%",
            "cv_on_train": cv_results,
            "chosen": chosen,
        },
        "held_out_test": held_out,
        "per_class_f1_held_out": {
            lab: {name: held_out[name]["per_class"][lab]["f1"] for name in held_out}
            for lab in LABELS
        },
        "macro_f1_held_out": {name: held_out[name]["macro_f1"] for name in held_out},
        "chosen_macro_f1_gain_over_baseline": round(
            held_out[chosen]["macro_f1"] - held_out[BASELINE]["macro_f1"], 4
        ),
    }
    return results, fitted[chosen]


def save_model(pipeline, version: str, path: Path = MODEL_PATH, model: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "labels": list(LABELS),
            "version": version,
            "features_version": FEATURES_VERSION,
            "model": model,
        },
        path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--labels", type=Path, default=LABELS_CSV)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--no-save", action="store_true", help="do not write results or model")
    args = parser.parse_args()

    results, pipeline = train(args.labels, args.seed)
    print(json.dumps(results, indent=2))
    if not args.no_save:
        RESULTS_JSON.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        chosen = results["selection"]["chosen"]
        save_model(pipeline, results["model_version"], model=chosen)
        print(f"Saved {RESULTS_JSON} and {MODEL_PATH} ({chosen})")


if __name__ == "__main__":
    main()
