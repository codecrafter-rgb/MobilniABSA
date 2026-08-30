#!/usr/bin/env python3
"""Inter-annotator agreement and descriptive statistics for ABSA datasets."""

from __future__ import annotations

import argparse
import json
import math
import warnings
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Sequence

try:
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    from sklearn.metrics import cohen_kappa_score
    from statsmodels.stats.inter_rater import fleiss_kappa
except ModuleNotFoundError:  # Dataset statistics do not require the optional IAA stack.
    np = None  # type: ignore[assignment]
    linear_sum_assignment = None  # type: ignore[assignment]
    cohen_kappa_score = None  # type: ignore[assignment]
    fleiss_kappa = None  # type: ignore[assignment]


CATEGORIES = [
    "Baterija",
    "Kamera",
    "Ekran",
    "Memorija",
    "Zvučnici",
    "Izgled",
    "Hardver",
    "Softver",
    "Performanse",
    "Cena",
    "Opšta ocena",
]
SENTIMENTS = ["Pozitivan", "Negativan", "Neutralan", "Konflikt"]
SENTIMENT_ALIASES = {
    "P": "Pozitivan",
    "N": "Negativan",
    "K": "Konflikt",
    "Konfliktan": "Konflikt",
}
# Linear-kappa order: positive and negative are the endpoints; neutral is closer
# to positive and conflict is closer to negative.
MISSING_CATEGORY = "__MISSING__"
SENTIMENT_BITS = {
    "Pozitivan": (1, 0),
    "Negativan": (0, 1),
    "Neutralan": (0, 0),
    "Konflikt": (1, 1),
}


@dataclass(frozen=True)
class Annotation:
    target: str | None
    start: int | None
    end: int | None
    category: str
    sentiment: str

    @property
    def implicit(self) -> bool:
        return self.target is None or self.target.upper() == "NULL" or self.start is None or self.start < 0

    @property
    def span(self) -> tuple[int, int] | None:
        return None if self.implicit else (self.start, self.end)  # type: ignore[return-value]


@dataclass(frozen=True)
class Review:
    source_id: str | None
    url: str
    text: str
    is_noise: bool
    annotations: tuple[Annotation, ...]


ReviewKey = tuple[str, str]


def _mean(values: Iterable[float | None]) -> float | None:
    usable = [value for value in values if value is not None and math.isfinite(value)]
    return fmean(usable) if usable else None


def _cohen(labels_a: Sequence[Any], labels_b: Sequence[Any], **kwargs: Any) -> float | None:
    if not labels_a:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = cohen_kappa_score(labels_a, labels_b, **kwargs)
    return None if not math.isfinite(value) else float(value)


def _gwet_ac1(
    labels_a: Sequence[Any], labels_b: Sequence[Any], rating_scale: Sequence[Any]
) -> float | None:
    """Multi-category Gwet AC1 using pooled marginal probabilities."""
    if not labels_a or len(labels_a) != len(labels_b):
        return None
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / len(labels_a)
    categories = list(dict.fromkeys(rating_scale))
    if len(categories) < 2 or not (set(labels_a) | set(labels_b)).issubset(set(categories)):
        return None
    pooled = Counter(labels_a)
    pooled.update(labels_b)
    probabilities = [pooled[label] / (2 * len(labels_a)) for label in categories]
    expected = sum(p * (1 - p) for p in probabilities) / (len(categories) - 1)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def _exact_agreement(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float | None:
    if not labels_a or len(labels_a) != len(labels_b):
        return None
    return sum(a == b for a, b in zip(labels_a, labels_b)) / len(labels_a)


def _bipolar_weighted_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float | None:
    """Weighted kappa using Hamming similarity of positive/negative components."""
    if not labels_a or len(labels_a) != len(labels_b):
        return None

    def weight(label_a: str, label_b: str) -> float:
        bits_a, bits_b = SENTIMENT_BITS[label_a], SENTIMENT_BITS[label_b]
        distance = sum(value_a != value_b for value_a, value_b in zip(bits_a, bits_b))
        return 1 - distance / 2

    observed = sum(weight(a, b) for a, b in zip(labels_a, labels_b)) / len(labels_a)
    marginal_a = Counter(labels_a)
    marginal_b = Counter(labels_b)
    expected = sum(
        marginal_a[label_a] / len(labels_a)
        * marginal_b[label_b] / len(labels_b)
        * weight(label_a, label_b)
        for label_a in SENTIMENTS
        for label_b in SENTIMENTS
    )
    return (observed - expected) / (1 - expected) if expected < 1 else None


def _annotation(raw: dict[str, Any], source: Path, review_label: str) -> Annotation:
    target = raw.get("target", raw.get("text"))
    start = raw.get("start_char", raw.get("start"))
    end = raw.get("end_char", raw.get("end"))
    if target is None or (isinstance(target, str) and target.upper() == "NULL") or start == -1:
        target, start, end = None, None, None
    else:
        if not isinstance(target, str):
            raise ValueError(f"{source}: target in review {review_label} must be a string or NULL")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise ValueError(f"{source}: invalid span in review {review_label}: ({start}, {end})")
    category = raw.get("category")
    sentiment = raw.get("sentiment")
    if not isinstance(category, str) or not isinstance(sentiment, str):
        raise ValueError(f"{source}: annotation in review {review_label} lacks category/sentiment")
    sentiment = SENTIMENT_ALIASES.get(sentiment, sentiment)
    if category not in CATEGORIES:
        raise ValueError(f"{source}: unknown category {category!r} in review {review_label}")
    if sentiment not in SENTIMENTS:
        raise ValueError(f"{source}: unknown sentiment {sentiment!r} in review {review_label}")
    return Annotation(target, start, end, category, sentiment)


def _raw_export_annotations(raw: dict[str, Any], source: Path, review_label: str) -> list[dict[str, Any]]:
    """Convert Label Studio's parallel explicit/implicit fields to canonical rows."""
    categories = raw.get("categories") or []
    sentiments = raw.get("sentiment") or []
    if isinstance(sentiments, str) and isinstance(categories, list) and len(categories) == 1:
        sentiments = [sentiments]
    if not isinstance(categories, list) or not isinstance(sentiments, list):
        raise ValueError(f"{source}: categories/sentiment for review {review_label} must be lists")
    if len(categories) != len(sentiments):
        raise ValueError(
            f"{source}: review {review_label} has {len(categories)} explicit categories "
            f"but {len(sentiments)} sentiments"
        )

    annotations: list[dict[str, Any]] = []
    for category_span, sentiment in zip(categories, sentiments):
        if not isinstance(category_span, dict):
            raise ValueError(f"{source}: explicit category in review {review_label} must be an object")
        labels = category_span.get("labels")
        if not isinstance(labels, list) or len(labels) != 1 or not isinstance(labels[0], str):
            raise ValueError(f"{source}: explicit category in review {review_label} must have one label")
        annotations.append(
            {
                "target": category_span.get("text"),
                "start_char": category_span.get("start"),
                "end_char": category_span.get("end"),
                "category": labels[0],
                "sentiment": sentiment,
            }
        )

    implicit_groups = raw.get("implicit_aspects") or []
    if not isinstance(implicit_groups, list):
        raise ValueError(f"{source}: implicit_aspects for review {review_label} must be a list")
    for group in implicit_groups:
        if not isinstance(group, dict) or not isinstance(group.get("taxonomy", []), list):
            raise ValueError(f"{source}: invalid implicit_aspects entry in review {review_label}")
        for taxonomy_item in group.get("taxonomy", []):
            if (
                not isinstance(taxonomy_item, list)
                or len(taxonomy_item) != 2
                or not all(isinstance(value, str) for value in taxonomy_item)
            ):
                raise ValueError(f"{source}: invalid implicit taxonomy item in review {review_label}")
            category, sentiment = taxonomy_item
            annotations.append(
                {
                    "target": None,
                    "start_char": None,
                    "end_char": None,
                    "category": category,
                    "sentiment": sentiment,
                }
            )
    return annotations


def _annotation_rows(raw: dict[str, Any], source: Path, review_label: str) -> list[dict[str, Any]]:
    if "annotations" in raw:
        rows = raw["annotations"]
    elif "aspects" in raw:
        rows = raw["aspects"]
    else:
        return _raw_export_annotations(raw, source, review_label)
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        raise ValueError(f"{source}: annotations for review {review_label} must be a list of objects")
    return rows


def load_annotations(path: str | Path) -> dict[ReviewKey, Review]:
    """Load canonical, Label Studio raw-export, or legacy parsed JSON."""
    source = Path(path)
    try:
        with source.open(encoding="utf-8") as handle:
            raw_data = json.load(handle)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{source}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(raw_data, list):
        raise ValueError(f"{source}: top-level JSON value must be a list")

    reviews: dict[ReviewKey, Review] = {}
    for position, raw in enumerate(raw_data):
        if not isinstance(raw, dict):
            raise ValueError(f"{source}: review at index {position} is not an object")
        source_id_value = raw.get("review_id", raw.get("id"))
        source_id = None if source_id_value is None else str(source_id_value)
        url = raw.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"{source}: review at index {position} has no valid url")
        text = raw.get("text", raw.get("comment"))
        if not isinstance(text, str):
            raise ValueError(f"{source}: review at index {position} has no text/comment")
        review_key = (url.strip(), text)
        display_key = f"{url} | {text[:60]!r}"
        if review_key in reviews:
            raise ValueError(f"{source}: duplicate review key {display_key}")
        annotation_rows = _annotation_rows(raw, source, display_key)
        if "is_noise" in raw:
            if not isinstance(raw["is_noise"], bool):
                raise ValueError(f"{source}: is_noise for review {display_key} must be boolean")
            is_noise = raw["is_noise"]
        else:
            review_status = str(raw.get("review_status", "DA")).upper()
            if review_status not in {"DA", "NE", "NOISE"}:
                raise ValueError(f"{source}: unsupported review_status {review_status!r} in review {display_key}")
            is_noise = review_status in {"NE", "NOISE"}
        annotations = tuple(_annotation(item, source, display_key) for item in annotation_rows)
        reviews[review_key] = Review(source_id, url.strip(), text, is_noise, annotations)
    return reviews


def _span_iou(a: Annotation, b: Annotation) -> float:
    if a.span is None or b.span is None:
        return 0.0
    intersection = max(0, min(a.end, b.end) - max(a.start, b.start))  # type: ignore[arg-type]
    union = max(a.end, b.end) - min(a.start, b.start)  # type: ignore[arg-type]
    return intersection / union if union else 0.0


def align_annotations(
    annotations_a: Sequence[Annotation], annotations_b: Sequence[Annotation]
) -> list[tuple[Annotation, Annotation, float]]:
    """Align explicit spans by IoU and implicit aspects as unordered multisets."""
    explicit_a = [item for item in annotations_a if not item.implicit]
    explicit_b = [item for item in annotations_b if not item.implicit]
    aligned: list[tuple[Annotation, Annotation, float]] = []
    if explicit_a and explicit_b:
        similarities = np.array([[_span_iou(a, b) for b in explicit_b] for a in explicit_a])
        rows, columns = linear_sum_assignment(-similarities)
        aligned.extend(
            (explicit_a[row], explicit_b[column], float(similarities[row, column]))
            for row, column in zip(rows, columns)
            if similarities[row, column] > 0
        )
    implicit_a = [item for item in annotations_a if item.implicit]
    implicit_b = [item for item in annotations_b if item.implicit]
    aligned.extend(_align_implicit_annotations(implicit_a, implicit_b))
    return aligned


def _align_implicit_annotations(
    annotations_a: Sequence[Annotation], annotations_b: Sequence[Annotation]
) -> list[tuple[Annotation, Annotation, float]]:
    """Match implicit aspects by category without using sentiment as identity."""
    remaining_a = list(annotations_a)
    remaining_b = list(annotations_b)
    matches: list[tuple[Annotation, Annotation, float]] = []

    # Category is the identity of an implicit aspect; sentiment must not be used
    # to construct the pairs on which sentiment agreement may later be judged.
    for annotation_a in list(remaining_a):
        match_index = next(
            (
                index
                for index, annotation_b in enumerate(remaining_b)
                if annotation_b.category == annotation_a.category
            ),
            None,
        )
        if match_index is not None:
            remaining_a.remove(annotation_a)
            matches.append((annotation_a, remaining_b.pop(match_index), 1.0))

    # Pair residual category disagreements deterministically. Kappa is invariant to
    # their ordering because none of these residual category labels are equal.
    remaining_a.sort(key=lambda item: (item.category, item.sentiment))
    remaining_b.sort(key=lambda item: (item.category, item.sentiment))
    matches.extend((a, b, 1.0) for a, b in zip(remaining_a, remaining_b))
    return matches


def _implicit_category_pairs(
    annotations_a: Sequence[Annotation], annotations_b: Sequence[Annotation]
) -> list[tuple[str, str]]:
    """Align unordered implicit category multisets without dropping extras."""
    counts_a = Counter(item.category for item in annotations_a)
    counts_b = Counter(item.category for item in annotations_b)
    pairs: list[tuple[str, str]] = []
    for category in CATEGORIES:
        shared = min(counts_a[category], counts_b[category])
        pairs.extend((category, category) for _ in range(shared))
        counts_a[category] -= shared
        counts_b[category] -= shared

    remaining_a = [category for category in CATEGORIES for _ in range(counts_a[category])]
    remaining_b = [category for category in CATEGORIES for _ in range(counts_b[category])]
    size = max(len(remaining_a), len(remaining_b))
    remaining_a.extend([MISSING_CATEGORY] * (size - len(remaining_a)))
    remaining_b.extend([MISSING_CATEGORY] * (size - len(remaining_b)))
    pairs.extend(zip(remaining_a, remaining_b))
    return pairs


def _f1(matched: float, count_a: int, count_b: int) -> float:
    denominator = count_a + count_b
    return 1.0 if denominator == 0 else 2 * matched / denominator


def _pair_metrics(data_a: dict[ReviewKey, Review], data_b: dict[ReviewKey, Review]) -> dict[str, float | None]:
    ids_a, ids_b = set(data_a), set(data_b)
    if ids_a != ids_b:
        missing_a = sorted(ids_b - ids_a)[:5]
        missing_b = sorted(ids_a - ids_b)[:5]
        raise ValueError(f"annotator review keys differ (missing from A: {missing_a}; missing from B: {missing_b})")
    review_keys = sorted(ids_a)
    noise_a = [data_a[item].is_noise for item in review_keys]
    noise_b = [data_b[item].is_noise for item in review_keys]

    strict_matches = partial_matches = 0.0
    explicit_count_a = explicit_count_b = 0
    category_a: list[str] = []
    category_b: list[str] = []
    sentiment_a: list[str] = []
    sentiment_b: list[str] = []
    acsa_tuple_matches = acsa_tuple_count_a = acsa_tuple_count_b = 0
    tuple_matches = tuple_count_a = tuple_count_b = 0

    for review_key in review_keys:
        review_a, review_b = data_a[review_key], data_b[review_key]
        if not review_a.is_noise and not review_b.is_noise:
            explicit_a = [item for item in review_a.annotations if not item.implicit]
            explicit_b = [item for item in review_b.annotations if not item.implicit]
            explicit_count_a += len(explicit_a)
            explicit_count_b += len(explicit_b)
            explicit_alignment = align_annotations(explicit_a, explicit_b)
            strict_matches += sum(a.span == b.span for a, b, _ in explicit_alignment)
            partial_matches += sum(iou for _, _, iou in explicit_alignment)

            for annotation_a, annotation_b, _ in explicit_alignment:
                category_a.append(annotation_a.category)
                category_b.append(annotation_b.category)
                if annotation_a.category == annotation_b.category:
                    sentiment_a.append(annotation_a.sentiment)
                    sentiment_b.append(annotation_b.sentiment)

            implicit_a = [item for item in review_a.annotations if item.implicit]
            implicit_b = [item for item in review_b.annotations if item.implicit]
            implicit_categories_a = {item.category for item in implicit_a}
            implicit_categories_b = {item.category for item in implicit_b}
            for category_value_a, category_value_b in _implicit_category_pairs(implicit_a, implicit_b):
                category_a.append(category_value_a)
                category_b.append(category_value_b)

            # A sentiment decision is identifiable only when each annotator has
            # exactly one implicit entry for the mutually selected category.
            for category in implicit_categories_a & implicit_categories_b:
                category_items_a = [item for item in implicit_a if item.category == category]
                category_items_b = [item for item in implicit_b if item.category == category]
                if len(category_items_a) == len(category_items_b) == 1:
                    sentiment_a.append(category_items_a[0].sentiment)
                    sentiment_b.append(category_items_b[0].sentiment)

        acsa_tuples_a = (
            {(item.category, item.sentiment) for item in review_a.annotations}
            if not review_a.is_noise
            else set()
        )
        acsa_tuples_b = (
            {(item.category, item.sentiment) for item in review_b.annotations}
            if not review_b.is_noise
            else set()
        )
        acsa_tuple_count_a += len(acsa_tuples_a)
        acsa_tuple_count_b += len(acsa_tuples_b)
        acsa_tuple_matches += len(acsa_tuples_a & acsa_tuples_b)

        tuples_a = Counter(_tuple_key(item) for item in review_a.annotations) if not review_a.is_noise else Counter()
        tuples_b = Counter(_tuple_key(item) for item in review_b.annotations) if not review_b.is_noise else Counter()
        tuple_count_a += sum(tuples_a.values())
        tuple_count_b += sum(tuples_b.values())
        tuple_matches += sum((tuples_a & tuples_b).values())

    return {
        "noise_cohen_kappa": _cohen(noise_a, noise_b),
        "span_strict_f1": _f1(strict_matches, explicit_count_a, explicit_count_b),
        "span_partial_f1": _f1(partial_matches, explicit_count_a, explicit_count_b),
        "category_cohen_kappa": _cohen(category_a, category_b),
        "category_gwet_ac1": _gwet_ac1(
            category_a,
            category_b,
            rating_scale=[*CATEGORIES, MISSING_CATEGORY],
        ),
        "acsa_tuple_micro_f1": _f1(
            acsa_tuple_matches,
            acsa_tuple_count_a,
            acsa_tuple_count_b,
        ),
        "sentiment_cohen_kappa": _cohen(sentiment_a, sentiment_b, labels=SENTIMENTS),
        "sentiment_gwet_ac1": _gwet_ac1(sentiment_a, sentiment_b, rating_scale=SENTIMENTS),
        "sentiment_exact_agreement": _exact_agreement(sentiment_a, sentiment_b),
        "sentiment_positive_component_kappa": _cohen(
            [SENTIMENT_BITS[label][0] for label in sentiment_a],
            [SENTIMENT_BITS[label][0] for label in sentiment_b],
        ),
        "sentiment_negative_component_kappa": _cohen(
            [SENTIMENT_BITS[label][1] for label in sentiment_a],
            [SENTIMENT_BITS[label][1] for label in sentiment_b],
        ),
        "sentiment_bipolar_weighted_kappa": _bipolar_weighted_kappa(sentiment_a, sentiment_b),
        "full_tuple_micro_f1": _f1(tuple_matches, tuple_count_a, tuple_count_b),
    }


def _tuple_key(annotation: Annotation) -> tuple[Any, ...]:
    target = None if annotation.implicit else annotation.span
    return target, annotation.category, annotation.sentiment


def _fleiss_noise(datasets: Sequence[dict[ReviewKey, Review]]) -> float | None:
    review_keys = sorted(datasets[0])
    table = np.zeros((len(review_keys), 2), dtype=int)
    for row, review_key in enumerate(review_keys):
        for dataset in datasets:
            table[row, int(dataset[review_key].is_noise)] += 1
    if not len(table):
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            value = float(fleiss_kappa(table))
    except (ZeroDivisionError, ValueError):
        return None
    return value if math.isfinite(value) else None


def calculate_iaa(paths: Sequence[str | Path]) -> dict[str, Any]:
    if any(item is None for item in (np, linear_sum_assignment, cohen_kappa_score, fleiss_kappa)):
        raise RuntimeError("IAA calculation requires numpy, scipy, scikit-learn and statsmodels")
    if len(paths) < 2:
        raise ValueError("at least two annotator files are required")
    sources = [Path(path) for path in paths]
    datasets = [load_annotations(path) for path in sources]
    expected_ids = set(datasets[0])
    for source, dataset in zip(sources[1:], datasets[1:]):
        if set(dataset) != expected_ids:
            raise ValueError(f"{source}: (url, text) review keys do not match {sources[0]}")

    pair_results: dict[str, dict[str, float | None]] = {}
    for (index_a, data_a), (index_b, data_b) in combinations(enumerate(datasets, 1), 2):
        pair_results[f"A{index_a}-A{index_b}"] = _pair_metrics(data_a, data_b)
    metric_names = next(iter(pair_results.values()))
    means = {metric: _mean(result[metric] for result in pair_results.values()) for metric in metric_names}
    return {
        "annotators": [{"id": f"A{i}", "file": str(path)} for i, path in enumerate(sources, 1)],
        "review_count": len(expected_ids),
        "pair_count": len(pair_results),
        "pairs": pair_results,
        "group_means": means,
        "noise_fleiss_kappa": _fleiss_noise(datasets),
        "methodology": {
            "review_alignment": "exact composite key (url, review text); source IDs are ignored",
            "span_scope": "reviews both annotators marked non-noise; explicit targets only",
            "explicit_alignment": "Hungarian maximum-total character IoU; overlap must be > 0",
            "category_units": "aligned explicit targets plus unordered implicit category multisets; unmatched implicit entries use MISSING",
            "acsa_tuple_units": "unique (category, sentiment) pairs per review; targets are ignored and duplicates are consolidated",
            "implicit_alignment": "order-independent category multiset; duplicate-category sentiment is excluded as ambiguous",
            "sentiment_scope": "target-aligned entries with matching categories",
            "sentiment_bipolar_mapping": SENTIMENT_BITS,
            "sentiment_bipolar_weight": "1 - HammingDistance(positive_bit, negative_bit) / 2",
            "undefined_scores": "null; excluded from group means",
        },
    }


def generate_dataset_statistics(final_data_json: str | Path) -> dict[str, Any]:
    """Generate statistics for annotation/annotations.json's consolidated schema."""
    source = Path(final_data_json)
    try:
        with source.open(encoding="utf-8") as handle:
            rows = json.load(handle)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{source}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(rows, list):
        raise ValueError(f"{source}: top-level JSON value must be a list")

    review_keys: set[tuple[str, str]] = set()
    valid_reviews = 0
    noise_reviews = 0
    annotations: list[Annotation] = []
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{source}: review at index {position} is not an object")
        phone = row.get("phone")
        comment = row.get("comment")
        status = row.get("review_status")
        aspect_terms = row.get("aspect_terms")
        aspect_categories = row.get("aspect_categories")
        if not isinstance(phone, str) or not phone.strip():
            raise ValueError(f"{source}: review at index {position} has no valid phone")
        if not isinstance(comment, str):
            raise ValueError(f"{source}: review at index {position} has no valid comment")
        if status not in {"DA", "NE"}:
            raise ValueError(f"{source}: review at index {position} has invalid review_status {status!r}")
        if not isinstance(aspect_terms, list) or not all(isinstance(item, dict) for item in aspect_terms):
            raise ValueError(f"{source}: aspect_terms at index {position} must be a list of objects")
        if not isinstance(aspect_categories, list) or not all(
            isinstance(item, dict) for item in aspect_categories
        ):
            raise ValueError(f"{source}: aspect_categories at index {position} must be a list of objects")

        review_key = (phone.strip(), comment)
        if review_key in review_keys:
            raise ValueError(f"{source}: duplicate (phone, comment) key at index {position}")
        review_keys.add(review_key)

        if status == "NE":
            noise_reviews += 1
            continue
        valid_reviews += 1
        for term_index, term in enumerate(aspect_terms):
            category = term.get("category")
            sentiment = term.get("polarity")
            sentiment = SENTIMENT_ALIASES.get(sentiment, sentiment)
            if category not in CATEGORIES:
                raise ValueError(
                    f"{source}: unknown category {category!r} in aspect_terms[{term_index}] "
                    f"of review {position}"
                )
            if sentiment not in SENTIMENTS:
                raise ValueError(
                    f"{source}: unknown polarity {sentiment!r} in aspect_terms[{term_index}] "
                    f"of review {position}"
                )

            start = term.get("fr")
            end = term.get("to")
            target = term.get("trg")
            if start == -1 and end == -1 and target is None:
                annotations.append(Annotation(None, None, None, category, sentiment))
            elif (
                isinstance(start, int)
                and isinstance(end, int)
                and 0 <= start < end
                and isinstance(target, str)
            ):
                annotations.append(Annotation(target, start, end, category, sentiment))
            else:
                raise ValueError(
                    f"{source}: invalid span/target in aspect_terms[{term_index}] "
                    f"of review {position}: ({start}, {end}, {target!r})"
                )

    category_counts = Counter(item.category for item in annotations)
    sentiment_counts = Counter(item.sentiment for item in annotations)
    category_order = CATEGORIES + sorted(set(category_counts) - set(CATEGORIES))
    sentiment_order = SENTIMENTS + sorted(set(sentiment_counts) - set(SENTIMENTS))
    explicit = sum(not item.implicit for item in annotations)
    implicit = len(annotations) - explicit

    def distribution(counts: Counter[str], order: Sequence[str]) -> dict[str, dict[str, float | int]]:
        total = sum(counts.values())
        return {
            label: {"count": counts[label], "percentage": 100 * counts[label] / total if total else 0.0}
            for label in order
        }

    cross_tab = {
        category: {sentiment: 0 for sentiment in sentiment_order} for category in category_order
    }
    for item in annotations:
        cross_tab[item.category][item.sentiment] += 1
    total_reviews = len(rows)
    return {
        "total_reviews": total_reviews,
        "valid_reviews": valid_reviews,
        "noise_reviews": noise_reviews,
        "noise_percentage": 100 * noise_reviews / total_reviews if total_reviews else 0.0,
        "total_annotations": len(annotations),
        "category_distribution": distribution(category_counts, category_order),
        "sentiment_distribution": distribution(sentiment_counts, sentiment_order),
        "category_sentiment_crosstab": cross_tab,
        "explicit": {"count": explicit, "percentage": 100 * explicit / len(annotations) if annotations else 0.0},
        "implicit": {"count": implicit, "percentage": 100 * implicit / len(annotations) if annotations else 0.0},
        "annotation_density": len(annotations) / valid_reviews if valid_reviews else 0.0,
    }


METRIC_ROWS = [
    ("Review Noise Status", "Cohen's Kappa", "noise_cohen_kappa"),
    ("Span Extraction (ATE)", "Strict F1", "span_strict_f1"),
    ("Span Extraction (ATE)", "Partial F1", "span_partial_f1"),
    ("Category (ACSA)", "Cohen's Kappa", "category_cohen_kappa"),
    ("Category (ACSA)", "Gwet's AC1", "category_gwet_ac1"),
    ("ACSA Tuple", "Micro F1", "acsa_tuple_micro_f1"),
    ("Sentiment", "Nominal Cohen's Kappa", "sentiment_cohen_kappa"),
    ("Sentiment", "Gwet's AC1", "sentiment_gwet_ac1"),
    ("Sentiment", "Exact Agreement", "sentiment_exact_agreement"),
    ("Sentiment (supp.)", "Positive Component Kappa", "sentiment_positive_component_kappa"),
    ("Sentiment (supp.)", "Negative Component Kappa", "sentiment_negative_component_kappa"),
    ("Sentiment (supp.)", "Bipolar Weighted Kappa", "sentiment_bipolar_weighted_kappa"),
    ("Full Tuple", "Micro F1", "full_tuple_micro_f1"),
]


def _score(value: float | None, bold: bool = False) -> str:
    rendered = "N/A" if value is None else f"{value:.2f}"
    return f"**{rendered}**" if bold else rendered


def render_markdown(iaa: dict[str, Any], statistics: dict[str, Any] | None = None) -> str:
    pairs = list(iaa["pairs"])
    lines = [
        f"### 1. Inter-Annotator Agreement (Calibration Analysis - {len(iaa['annotators'])} Annotators, {iaa['pair_count']} Pairs)",
        "",
        "| Level of Analysis | Metric | " + " | ".join(pairs) + " | **Group Mean** |",
        "| :-- | :-- | " + " | ".join(":--:" for _ in pairs) + " | :--: |",
    ]
    for level, label, key in METRIC_ROWS:
        values = [_score(iaa["pairs"][pair][key]) for pair in pairs]
        lines.append(f"| {level} | {label} | " + " | ".join(values) + f" | {_score(iaa['group_means'][key], True)} |")
    lines.extend(["", f"- Overall Fleiss' Kappa (Noise Status): {_score(iaa['noise_fleiss_kappa'], True)}"])
    if statistics is None:
        return "\n".join(lines) + "\n"

    total = statistics["total_reviews"]
    lines.extend([
        "",
        "### 2. Final Dataset Descriptive Statistics",
        "",
        f"- **Total Reviews:** {total} (Valid: {statistics['valid_reviews']}, Noise: {statistics['noise_reviews']} / {statistics['noise_percentage']:.2f}%)",
        f"- **Total Annotations:** {statistics['total_annotations']} (Explicit: {statistics['explicit']['percentage']:.2f}%, Implicit/NULL: {statistics['implicit']['percentage']:.2f}%)",
        f"- **Average Aspect Density:** {statistics['annotation_density']:.2f} aspects/review",
        "",
        "#### Category & Sentiment Breakdown Matrix",
        "",
        "| Category | Total | " + " | ".join(SENTIMENTS) + " |",
        "| :-- | :--: | " + " | ".join(":--:" for _ in SENTIMENTS) + " |",
    ])
    for category, cells in statistics["category_sentiment_crosstab"].items():
        total_category = sum(cells.values())
        lines.append(f"| {category} | {total_category} | " + " | ".join(str(cells.get(item, 0)) for item in SENTIMENTS) + " |")
    lines.extend(["", "#### Category Distribution", ""])
    lines.extend(
        f"- **{category}:** {values['count']} ({values['percentage']:.2f}%)"
        for category, values in statistics["category_distribution"].items()
    )
    lines.extend(["", "#### Sentiment Distribution", ""])
    lines.extend(
        f"- **{sentiment}:** {values['count']} ({values['percentage']:.2f}%)"
        for sentiment, values in statistics["sentiment_distribution"].items()
    )
    return "\n".join(lines) + "\n"


def _resolve_inputs(inputs: Sequence[str], excluded: Sequence[Path]) -> list[Path]:
    if len(inputs) == 1 and Path(inputs[0]).is_dir():
        excluded_paths = {path.resolve() for path in excluded}
        paths = sorted(path for path in Path(inputs[0]).glob("*.json") if path.resolve() not in excluded_paths)
    else:
        paths = [Path(item) for item in inputs]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"annotator files not found: {', '.join(missing)}")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="annotator JSON paths, or one directory containing them")
    parser.add_argument("--final", type=Path, help="final consolidated dataset JSON")
    parser.add_argument("--output", type=Path, default=Path("iaa_report.json"), help="summary JSON path")
    args = parser.parse_args(argv)
    try:
        excluded = [args.output] + ([args.final] if args.final else [])
        paths = _resolve_inputs(args.inputs, excluded)
        iaa = calculate_iaa(paths)
        statistics = generate_dataset_statistics(args.final) if args.final else None
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    report = {"iaa": iaa, "dataset_statistics": statistics}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(render_markdown(iaa, statistics))
    print(f"Report saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
