"""Obligation classifier: keyword heuristic, input records, features and pipelines.

Shared by ml/obligation/export_for_labelling.py (heuristic), ml/obligation/train.py (fit)
and app/rules/classify.py (predict). Saved models pickle references to the functions in
this module, so their names and import path must not move. Bump FEATURES_VERSION whenever
the record layout or features change: classify refuses a model built for another version.

A model's input is a list of records, one per paragraph, built by make_records() from a
whole document so each paragraph can see its parent and the keyword guess.
"""

import re
from collections.abc import Iterable, Sequence

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

LABELS = ("requirement", "definition", "information")
FEATURES_VERSION = 2
MODEL_NAMES = ("logreg", "linear_svc")
PARENT_CHARS = 200
FRAGMENT_WORDS = 15

Record = dict[str, str]

_WS = re.compile(r"\s+")

# ---------------------------------------------------------------------------------------
# Keyword heuristic (the baseline, and a feature of the model)
# ---------------------------------------------------------------------------------------

# A paragraph that opens a definitions section, e.g. "following definitions shall apply" or
# "the terms herein shall bear the meaning assigned to them below". Its sub-paragraphs
# (same base number) are definitions.
_DEFINITIONS_INTRO = re.compile(
    r"\bdefinitions\s+shall\s+apply\b|\bfollowing\s+definitions\b"
    r"|\bmeaning\s+assigned\s+to\s+them\s+below\b",
    re.IGNORECASE,
)
_DEFINITION = re.compile(
    r"\bshall\s+mean\b"
    r"|\bshall\s+have\s+the\s+same\s+meaning\b"
    r"|(?<!\bby\s)(?<!\bsimilar\s)(?<!\bother\s)\bmeans?\b(?!\s+of\b)"
    r"|^\W*for\s+the\s+purposes?\s+of\b",
    re.IGNORECASE,
)
_REQUIREMENT = re.compile(
    r"\bshall\b|\bmust\b|\bnot\s+exceed\b|\bat\s+least\b|\brequired\s+to\b"
    r"|\bno\b[^.;]{0,80}\bshall\b",
    re.IGNORECASE,
)


def one_line(text: str) -> str:
    """Same normalisation as labels.csv: newlines and runs of whitespace become one space."""
    return _WS.sub(" ", text).strip()


def base_number(number: str | None) -> str | None:
    """'6(3)' -> '6'; '105A' -> '105A'; None -> None."""
    if not number:
        return None
    return number.split("(", 1)[0]


def definition_sections(rows: Iterable[tuple[str | None, str]]) -> set[str]:
    """Base numbers of paragraphs that introduce a definitions section."""
    return {
        b for number, text in rows if (b := base_number(number)) and _DEFINITIONS_INTRO.search(text)
    }


def suggest_label(text: str, in_definitions_section: bool = False) -> str:
    """Keyword guess. Definitions are checked first: they often say 'shall have the same meaning'."""
    if in_definitions_section or _DEFINITION.search(text):
        return "definition"
    if _REQUIREMENT.search(text):
        return "requirement"
    return "information"


# ---------------------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------------------


def make_records(paragraphs: Sequence[tuple[str | None, str]]) -> list[Record]:
    """One record per (number, text) of ONE document, in the same order.

    text       the paragraph on one line
    parent     first PARENT_CHARS of the parent paragraph for a sub-paragraph like 22(1)
               (the paragraph numbered 22 in the same document), else ""
    suggested  the keyword heuristic's label
    """
    numbers = [n for n, _ in paragraphs]
    texts = [one_line(t) for _, t in paragraphs]
    by_number = {n: t for n, t in zip(numbers, texts, strict=True) if n}
    sections = definition_sections(zip(numbers, texts, strict=True))
    records = []
    for number, text in zip(numbers, texts, strict=True):
        base = base_number(number)
        parent = by_number.get(base, "") if base and base != number else ""
        records.append(
            {
                "text": text,
                "parent": parent[:PARENT_CHARS],
                "suggested": suggest_label(text, base in sections),
            }
        )
    return records


# ---------------------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------------------

_HAND = {
    "shall": re.compile(r"\bshall\b", re.IGNORECASE),
    "shall_not": re.compile(r"\bshall\s+not\b", re.IGNORECASE),
    "must": re.compile(r"\bmust\b", re.IGNORECASE),
    "not_exceed": re.compile(r"\bnot\s+exceed\b", re.IGNORECASE),
    "may": re.compile(r"\bmay\b", re.IGNORECASE),
    "means": re.compile(r"\b(?:means|mean|shall\s+mean)\b", re.IGNORECASE),
}
HAND_FEATURE_NAMES = (
    *_HAND,
    "heading_like",
    "log_words",
    "short_fragment",
    "ends_with_colon",
    "has_parent",
)


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


def short_fragment(text: str) -> bool:
    """FRAGMENT_WORDS words or fewer: a list item or heading rather than a full provision."""
    return len(text.split()) <= FRAGMENT_WORDS


def get_text(records: Iterable[Record]) -> list[str]:
    return [r["text"] for r in records]


def get_parent(records: Iterable[Record]) -> list[str]:
    return [r["parent"] for r in records]


def hand_features(records: Iterable[Record]) -> np.ndarray:
    rows = []
    for r in records:
        t = r["text"]
        rows.append(
            [float(bool(rx.search(t))) for rx in _HAND.values()]
            + [
                float(heading_like(t)),
                float(np.log1p(len(t.split())) / 6.0),
                float(short_fragment(t)),
                float(t.rstrip().endswith(":")),
                float(bool(r["parent"])),
            ]
        )
    return np.asarray(rows, dtype=float)


def suggested_onehot(records: Iterable[Record]) -> np.ndarray:
    return np.asarray([[float(r["suggested"] == lab) for lab in LABELS] for r in records])


def _tfidf_on(getter, vectorizer: TfidfVectorizer) -> Pipeline:
    return Pipeline([("get", FunctionTransformer(getter)), ("tfidf", vectorizer)])


def _features() -> FeatureUnion:
    return FeatureUnion(
        [
            ("word", _tfidf_on(get_text, TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True))),
            (
                "char",
                _tfidf_on(
                    get_text,
                    TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True),
                ),
            ),
            (
                "parent",
                _tfidf_on(get_parent, TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ),
            ("hand", FunctionTransformer(hand_features)),
            ("suggested", FunctionTransformer(suggested_onehot)),
        ]
    )


def build_pipeline(seed: int, model: str = "logreg") -> Pipeline:
    """model: 'logreg' or 'linear_svc'. LinearSVC has no probabilities, so it is wrapped in
    sigmoid calibration (3 inner folds) to give classify a confidence."""
    if model == "logreg":
        clf = LogisticRegression(class_weight="balanced", max_iter=5000, random_state=seed)
    elif model == "linear_svc":
        clf = CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", max_iter=20000, random_state=seed),
            method="sigmoid",
            cv=3,
        )
    else:
        raise ValueError(f"unknown model {model!r}, expected one of {MODEL_NAMES}")
    return Pipeline([("features", _features()), ("clf", clf)])
