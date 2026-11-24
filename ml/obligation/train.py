"""Train the obligation classifier from ml/obligation/labels.csv.

Usage (from the repo root):

    uv run --project apps/api python ml/obligation/train.py
    uv run --project apps/api python ml/obligation/train.py --seed 42 --no-save

Reads the `label` column (suggested_label is only used as the keyword baseline).
Features and pipeline live in apps/api/app/rules/obligation_features.py:
TF-IDF word 1-2 grams + TF-IDF char 3-5 grams + hand features, logistic regression
with balanced class weights.

Protocol: stratified 80/20 split with a fixed seed, 5-fold stratified cross-validation
(macro F1) on the 80%, then fit on the 80% and score the held-out 20%. The keyword
baseline is scored on the same 20%.

Writes:
    ml/obligation/results.json             metrics for the model and the baseline
    ml/obligation/models/obligation.joblib {"pipeline", "labels", "version", ...} (gitignored)
"""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "apps" / "api"))

from app.rules.obligation_features import LABELS, build_pipeline

SEED = 42
MODEL_VERSION = "1.0.0"
LABELS_CSV = HERE / "labels.csv"
RESULTS_JSON = HERE / "results.json"
MODEL_PATH = HERE / "models" / "obligation.joblib"


def load_labelled(path: Path) -> tuple[list[str], list[str], list[str], str]:
    """Rows with a valid label. Returns texts, labels, suggested labels, sha256 of the file."""
    raw = path.read_bytes()
    texts, labels, suggested = [], [], []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip().lower()
            if label not in LABELS:
                continue
            texts.append(row["text"])
            labels.append(label)
            suggested.append(row["suggested_label"].strip().lower())
    return texts, labels, suggested, hashlib.sha256(raw).hexdigest()


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
    texts, y, suggested, sha = load_labelled(labels_csv)
    idx = np.arange(len(texts))
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=seed)
    x_tr = [texts[i] for i in tr]
    y_tr = [y[i] for i in tr]
    x_te = [texts[i] for i in te]
    y_te = [y[i] for i in te]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    cv_scores = cross_val_score(build_pipeline(seed), x_tr, y_tr, cv=cv, scoring="f1_macro")

    pipeline = build_pipeline(seed).fit(x_tr, y_tr)
    y_pred = pipeline.predict(x_te).tolist()

    results = {
        "model_version": f"{MODEL_VERSION}+labels.{sha[:8]}",
        "seed": seed,
        "labels_csv_sha256": sha,
        "n_labelled": len(texts),
        "n_train": len(tr),
        "n_test": len(te),
        "class_counts": {lab: y.count(lab) for lab in LABELS},
        "cv_on_train": {
            "folds": 5,
            "scoring": "f1_macro",
            "scores": [round(float(s), 4) for s in cv_scores],
            "mean": round(float(cv_scores.mean()), 4),
            "std": round(float(cv_scores.std()), 4),
        },
        "model_test": metrics(y_te, y_pred),
        "baseline_test": metrics(y_te, [suggested[i] for i in te]),
    }
    results["macro_f1_gain_over_baseline"] = round(
        results["model_test"]["macro_f1"] - results["baseline_test"]["macro_f1"], 4
    )
    return results, pipeline


def save_model(pipeline, version: str, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "labels": list(LABELS), "version": version}, path)


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
        save_model(pipeline, results["model_version"])
        print(f"Saved {RESULTS_JSON} and {MODEL_PATH}")


if __name__ == "__main__":
    main()
