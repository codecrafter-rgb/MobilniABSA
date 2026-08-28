#!/usr/bin/env python3
"""Describe disagreement sources in the five calibration annotation sets."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

ANNOTATORS = {
    "A1": Path("calibration/at/raw.json"),
    "A2": Path("calibration/jb/raw.json"),
    "A3": Path("calibration/lr/raw.json"),
    "A4": Path("calibration/nb/raw.json"),
    "A5": Path("calibration/zg/raw.json"),
}
MISSING_CATEGORY = "__MISSING__"


@dataclass(frozen=True)
class Annotation:
    start: int | None
    end: int | None
    category: str
    sentiment: str

    @property
    def implicit(self) -> bool:
        return self.start is None

    @property
    def span(self) -> tuple[int, int] | None:
        return None if self.implicit else (self.start, self.end)  # type: ignore[return-value]


@dataclass(frozen=True)
class Review:
    is_noise: bool
    annotations: tuple[Annotation, ...]


def load_annotations(path: Path) -> dict[tuple[str, str], Review]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for row in rows:
        annotations = []
        categories = row.get("categories") or []
        sentiments = row.get("sentiment") or []
        if isinstance(sentiments, str) and len(categories) == 1:
            sentiments = [sentiments]
        if len(categories) != len(sentiments):
            raise ValueError(f"Unpaired categories/sentiments in {path}: {row.get('id')}")
        for span, sentiment in zip(categories, sentiments):
            annotations.append(Annotation(span["start"], span["end"], span["labels"][0], sentiment))
        for group in row.get("implicit_aspects") or []:
            for category, sentiment in group.get("taxonomy", []):
                annotations.append(Annotation(None, None, category, sentiment))
        key = (row["url"].strip(), row["comment"])
        result[key] = Review(str(row.get("review_status", "DA")).upper() in {"NE", "NOISE"}, tuple(annotations))
    return result


def span_iou(a: Annotation, b: Annotation) -> float:
    intersection = max(0, min(a.end, b.end) - max(a.start, b.start))  # type: ignore[arg-type]
    union = max(a.end, b.end) - min(a.start, b.start)  # type: ignore[arg-type]
    return intersection / union if union else 0.0


def maximum_assignment(weights: list[list[float]]) -> list[tuple[int, int]]:
    """Maximum-weight square assignment using the Hungarian algorithm."""
    size = max(len(weights), len(weights[0]) if weights else 0)
    if not size:
        return []
    costs = [[0.0] * size for _ in range(size)]
    for i, row in enumerate(weights):
        for j, weight in enumerate(row):
            costs[i][j] = -weight
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i
        minv = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        j0 = 0
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, size + 1):
                if not used[j]:
                    cur = costs[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    return [(p[j] - 1, j - 1) for j in range(1, size + 1) if p[j] and p[j] <= len(weights) and j <= len(weights[p[j] - 1])]


def align_annotations(a: list[Annotation], b: list[Annotation]) -> list[tuple[Annotation, Annotation, float]]:
    weights = [[span_iou(left, right) for right in b] for left in a]
    return [(a[i], b[j], weights[i][j]) for i, j in maximum_assignment(weights) if weights[i][j] > 0]


def implicit_category_pairs(a: list[Annotation], b: list[Annotation]) -> list[tuple[str, str]]:
    counts_a = Counter(item.category for item in a)
    counts_b = Counter(item.category for item in b)
    pairs = []
    for category in sorted(set(counts_a) | set(counts_b)):
        shared = min(counts_a[category], counts_b[category])
        pairs.extend([(category, category)] * shared)
        counts_a[category] -= shared
        counts_b[category] -= shared
    left = [category for category, count in sorted(counts_a.items()) for _ in range(count)]
    right = [category for category, count in sorted(counts_b.items()) for _ in range(count)]
    size = max(len(left), len(right))
    left.extend([MISSING_CATEGORY] * (size - len(left)))
    right.extend([MISSING_CATEGORY] * (size - len(right)))
    pairs.extend(zip(left, right))
    return pairs


def percent(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 2) if whole else None


def main() -> None:
    datasets = {name: load_annotations(path) for name, path in ANNOTATORS.items()}
    totals = Counter()
    annotator_totals = {name: Counter() for name in datasets}
    explicit_category_confusions: Counter[tuple[str, str]] = Counter()
    implicit_category_confusions: Counter[tuple[str, str]] = Counter()
    sentiment_confusions: Counter[tuple[str, str]] = Counter()
    pair_summaries = {}

    for (name_a, data_a), (name_b, data_b) in combinations(datasets.items(), 2):
        pair = Counter()
        for key in sorted(data_a):
            review_a, review_b = data_a[key], data_b[key]
            pair["reviews"] += 1
            if review_a.is_noise != review_b.is_noise:
                pair["noise_status_disagreements"] += 1
            if review_a.is_noise or review_b.is_noise:
                continue

            pair["joint_non_noise_reviews"] += 1
            explicit_a = [item for item in review_a.annotations if not item.implicit]
            explicit_b = [item for item in review_b.annotations if not item.implicit]
            alignment = align_annotations(explicit_a, explicit_b)
            pair["explicit_a"] += len(explicit_a)
            pair["explicit_b"] += len(explicit_b)
            pair["overlapping_span_pairs"] += len(alignment)
            pair["unmatched_explicit_mentions"] += len(explicit_a) + len(explicit_b) - 2 * len(alignment)

            for annotation_a, annotation_b, _ in alignment:
                if annotation_a.span == annotation_b.span:
                    pair["exact_boundary_pairs"] += 1
                else:
                    pair["overlap_boundary_disagreements"] += 1
                if annotation_a.category == annotation_b.category:
                    pair["category_agreements_on_overlap"] += 1
                    if annotation_a.sentiment == annotation_b.sentiment:
                        pair["sentiment_agreements"] += 1
                    else:
                        pair["sentiment_disagreements"] += 1
                        sentiment_confusions[tuple(sorted((annotation_a.sentiment, annotation_b.sentiment)))] += 1
                else:
                    pair["category_disagreements_on_overlap"] += 1
                    explicit_category_confusions[tuple(sorted((annotation_a.category, annotation_b.category)))] += 1

            implicit_a = [item for item in review_a.annotations if item.implicit]
            implicit_b = [item for item in review_b.annotations if item.implicit]
            for category_a, category_b in implicit_category_pairs(implicit_a, implicit_b):
                pair["implicit_category_units"] += 1
                if category_a == category_b:
                    pair["implicit_category_agreements"] += 1
                else:
                    pair["implicit_category_disagreements"] += 1
                    implicit_category_confusions[tuple(sorted((category_a, category_b)))] += 1

        totals.update(pair)
        pair_summaries[f"{name_a}-{name_b}"] = dict(pair)

    for name, dataset in datasets.items():
        summary = annotator_totals[name]
        for review in dataset.values():
            summary["noise_reviews"] += int(review.is_noise)
            if not review.is_noise:
                summary["non_noise_reviews"] += 1
                summary["explicit_mentions"] += sum(not item.implicit for item in review.annotations)
                summary["implicit_aspects"] += sum(item.implicit for item in review.annotations)

    aligned = totals["overlapping_span_pairs"]
    category_units = aligned + totals["implicit_category_units"]
    category_disagreements = (
        totals["category_disagreements_on_overlap"] + totals["implicit_category_disagreements"]
    )
    sentiment_units = totals["sentiment_agreements"] + totals["sentiment_disagreements"]
    output = {
        "methodology": {
            "scope": "Ten pairwise comparisons of five independent annotations of the same 800 reviews",
            "explicit_alignment": "Hungarian maximum-total character IoU; spans must overlap",
            "counting_note": "Counts are pairwise comparison units, not unique reviews or unique aspect mentions",
            "annotators": {name: str(path) for name, path in ANNOTATORS.items()},
            "missing_category_label": MISSING_CATEGORY,
        },
        "totals": dict(totals),
        "annotator_totals": {name: dict(values) for name, values in annotator_totals.items()},
        "rates": {
            "noise_status_disagreement_pct": percent(totals["noise_status_disagreements"], totals["reviews"]),
            "exact_boundaries_among_overlaps_pct": percent(totals["exact_boundary_pairs"], aligned),
            "boundary_disagreement_among_overlaps_pct": percent(totals["overlap_boundary_disagreements"], aligned),
            "category_disagreement_pct": percent(category_disagreements, category_units),
            "category_disagreement_on_explicit_overlap_pct": percent(totals["category_disagreements_on_overlap"], aligned),
            "sentiment_disagreement_after_category_match_pct": percent(totals["sentiment_disagreements"], sentiment_units),
        },
        "top_explicit_category_confusions": [
            {"categories": list(labels), "count": count}
            for labels, count in explicit_category_confusions.most_common(15)
        ],
        "top_implicit_category_confusions": [
            {"categories": list(labels), "count": count}
            for labels, count in implicit_category_confusions.most_common(15)
        ],
        "top_sentiment_confusions": [
            {"sentiments": list(labels), "count": count}
            for labels, count in sentiment_confusions.most_common()
        ],
        "pairs": pair_summaries,
    }
    destination = Path("analytics/disagreement_analysis.json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Saved to {destination}")


if __name__ == "__main__":
    main()
