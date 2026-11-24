"""Obligation classifier: features and pipeline.

Shared by ml/obligation/train.py (fit) and app/rules/classify.py (predict). The saved model
pickles a reference to `hand_features` in this module, so its import path must not move.
"""

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer

LABELS = ("requirement", "definition", "information")

_WS = re.compile(r"\s+")
_HAND = {
    "shall": re.compile(r"\bshall\b", re.IGNORECASE),
    "shall_not": re.compile(r"\bshall\s+not\b", re.IGNORECASE),
    "must": re.compile(r"\bmust\b", re.IGNORECASE),
    "not_exceed": re.compile(r"\bnot\s+exceed\b", re.IGNORECASE),
    "may": re.compile(r"\bmay\b", re.IGNORECASE),
    "means": re.compile(r"\b(?:means|mean|shall\s+mean)\b", re.IGNORECASE),
}
HAND_FEATURE_NAMES = (*_HAND, "heading_like", "log_words")


def one_line(text: str) -> str:
    """Same normalisation as labels.csv: newlines and runs of whitespace become one space."""
    return _WS.sub(" ", text).strip()


def heading_like(text: str) -> bool:
    """A short line with no sentence ending and no modal verb, e.g. 'Microfinance Loans'.
    The CSV text is one line, so this looks at the whole paragraph."""
    words = text.split()
    return (
        0 < len(words) <= 12
        and not text.rstrip().endswith((".", ";", ":"))
        and not _HAND["shall"].search(text)
        and not _HAND["must"].search(text)
    )


def hand_features(texts) -> np.ndarray:
    rows = []
    for raw in texts:
        t = one_line(raw)
        rows.append(
            [float(bool(rx.search(t))) for rx in _HAND.values()]
            + [float(heading_like(t)), float(np.log1p(len(t.split())) / 6.0)]
        )
    return np.asarray(rows, dtype=float)


def build_pipeline(seed: int) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True, min_df=1),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True
                ),
            ),
            ("hand", FunctionTransformer(hand_features, validate=False)),
        ]
    )
    model = LogisticRegression(class_weight="balanced", max_iter=5000, random_state=seed)
    return Pipeline([("features", features), ("clf", model)])
