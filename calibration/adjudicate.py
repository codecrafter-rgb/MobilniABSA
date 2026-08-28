#!/usr/bin/env python3
"""Create a reproducible, automatically adjudicated calibration dataset.

The five original Label Studio exports remain unchanged. Decisions are based on
majority support among annotators that marked a review as relevant. Every tie is
flagged for manual adjudication; no annotator has privileged voting weight.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ANNOTATORS = {
    "A1": Path("calibration/at/raw.json"),
    "A2": Path("calibration/jb/raw.json"),
    "A3": Path("calibration/lr/raw.json"),
    "A4": Path("calibration/nb/raw.json"),
    "A5": Path("calibration/zg/raw.json"),
}
CATEGORY_ORDER = [
    "Baterija", "Kamera", "Ekran", "Memorija", "Zvučnici", "Izgled",
    "Hardver", "Softver", "Performanse", "Cena", "Opšta ocena",
]
SENTIMENT_ORDER = ["Pozitivan", "Negativan", "Neutralan", "Konflikt"]
SENTIMENT_ALIASES = {"P": "Pozitivan", "N": "Negativan", "K": "Konflikt", "Konfliktan": "Konflikt"}


@dataclass(frozen=True)
class Explicit:
    annotator: str
    start: int
    end: int
    text: str
    category: str
    sentiment: str

    @property
    def span(self) -> tuple[int, int]:
        return self.start, self.end


def overlap(a: Explicit, b: Explicit) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start))


def iou(a: Explicit, b: Explicit) -> float:
    common = overlap(a, b)
    union = max(a.end, b.end) - min(a.start, b.start)
    return common / union if union else 0.0


def majority_threshold(voter_count: int) -> int:
    return voter_count // 2 + 1


def choose_label(
    votes: list[tuple[str, str]], order: list[str]
) -> tuple[str, dict[str, Any]]:
    counts = Counter(label for _, label in votes)
    highest = max(counts.values())
    tied = [label for label, count in counts.items() if count == highest]
    if len(tied) == 1:
        chosen = tied[0]
    else:
        # This value is only a deterministic UI proposal. The tie is always
        # placed in the manual-review queue and the human decision is final.
        chosen = min(tied, key=order.index)
    return chosen, {
        "votes": dict(counts),
        "tie": len(tied) > 1,
        "manual_review_required": len(tied) > 1,
    }


def best_group(anchor: Explicit, remaining: list[Explicit]) -> list[Explicit]:
    group = [anchor]
    for annotator in ANNOTATORS:
        if annotator == anchor.annotator:
            continue
        candidates = [item for item in remaining if item.annotator == annotator and overlap(anchor, item) > 0]
        if candidates:
            group.append(max(candidates, key=lambda item: (iou(anchor, item), item.span == anchor.span, -len(item.text))))
    return group


def select_group(remaining: list[Explicit]) -> list[Explicit]:
    candidates = [best_group(anchor, remaining) for anchor in remaining]
    return max(
        candidates,
        key=lambda group: (
            len(group),
            sum(item.span == group[0].span for item in group),
            sum(iou(group[0], item) for item in group),
            -min(item.start for item in group),
        ),
    )


def choose_boundary(group: list[Explicit]) -> tuple[tuple[int, int], dict[str, Any]]:
    counts = Counter(item.span for item in group)
    highest = max(counts.values())
    tied = [span for span, count in counts.items() if count == highest]
    if len(tied) == 1:
        chosen = tied[0]
    else:
        shortest = min(end - start for start, end in tied)
        tied = [span for span in tied if span[1] - span[0] == shortest]
        # As above, the deterministic span is only a proposal for Label Studio.
        chosen = min(tied)
    return chosen, {
        "votes": {f"{start}:{end}": count for (start, end), count in counts.items()},
        "tie": len([span for span, count in counts.items() if count == highest]) > 1,
        "manual_review_required": len([span for span, count in counts.items() if count == highest]) > 1,
    }


def explicit_annotations(row: dict[str, Any], annotator: str) -> list[Explicit]:
    categories = row.get("categories") or []
    sentiments = row.get("sentiment") or []
    if isinstance(sentiments, str) and len(categories) == 1:
        sentiments = [sentiments]
    if len(categories) != len(sentiments):
        raise ValueError(f"{annotator}/{row.get('id')}: categories and sentiments are not paired")
    result = []
    for span, raw_sentiment in zip(categories, sentiments):
        sentiment = SENTIMENT_ALIASES.get(raw_sentiment, raw_sentiment)
        start, end = span.get("start"), span.get("end")
        labels = span.get("labels") or []
        if not isinstance(start, int) or not isinstance(end, int) or end <= start or len(labels) != 1:
            raise ValueError(f"{annotator}/{row.get('id')}: invalid explicit annotation")
        result.append(Explicit(annotator, start, end, span.get("text", ""), labels[0], sentiment))
    return result


def implicit_annotations(row: dict[str, Any]) -> list[tuple[str, str]]:
    result = []
    for group in row.get("implicit_aspects") or []:
        for item in group.get("taxonomy", []):
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError(f"Invalid implicit annotation in review {row.get('id')}")
            category, sentiment = item
            result.append((category, SENTIMENT_ALIASES.get(sentiment, sentiment)))
    return result


def read_inputs() -> dict[str, list[dict[str, Any]]]:
    datasets = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in ANNOTATORS.items()}
    first = datasets["A1"]
    expected = [(row["url"].strip(), row["comment"]) for row in first]
    if len(expected) != len(set(expected)):
        raise ValueError("A1 contains duplicate (url, comment) keys")
    for name, rows in datasets.items():
        keys = [(row["url"].strip(), row["comment"]) for row in rows]
        if set(keys) != set(expected) or len(keys) != len(expected):
            raise ValueError(f"{name} does not contain the same calibration reviews")
        datasets[name] = [dict(zip(keys, rows))[key] for key in expected]
    return datasets


def local_sentiment_vote(values: list[str]) -> tuple[str, bool]:
    counts = Counter(values)
    highest = max(counts.values())
    tied = [value for value, count in counts.items() if count == highest]
    return min(tied, key=SENTIMENT_ORDER.index), len(tied) > 1


def adjudicate_review(index: int, rows: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = rows["A1"]
    da_voters = [name for name, row in rows.items() if str(row.get("review_status", "DA")).upper() == "DA"]
    final_status = "DA" if len(da_voters) >= 3 else "NE"
    base = {
        "phone": source.get("phone"),
        "comment": source["comment"],
        "review_status": final_status,
        "aspect_terms": [],
        "aspect_categories": [],
    }
    audit: dict[str, Any] = {
        "index": index,
        "url": source["url"],
        "source_id": source.get("id"),
        "review_status_votes": {"DA": len(da_voters), "NE": 5 - len(da_voters)},
        "final_review_status": final_status,
        "eligible_annotators": da_voters,
        "explicit_decisions": [],
        "implicit_decisions": [],
        "flags": [],
    }
    if final_status == "NE":
        if len(da_voters) == 2:
            audit["flags"].append("review_status_close_vote")
        return base, audit

    threshold = majority_threshold(len(da_voters))
    remaining = [item for name in da_voters for item in explicit_annotations(rows[name], name)]
    rejected = []
    while remaining:
        group = select_group(remaining)
        for item in group:
            remaining.remove(item)
        if len(group) < threshold:
            rejected.extend(group)
            continue
        boundary, boundary_audit = choose_boundary(group)
        category, category_audit = choose_label([(item.annotator, item.category) for item in group], CATEGORY_ORDER)
        sentiment, sentiment_audit = choose_label([(item.annotator, item.sentiment) for item in group], SENTIMENT_ORDER)
        start, end = boundary
        term = {
            "fr": start,
            "to": end,
            "trg": source["comment"][start:end],
            "category": category,
            "polarity": sentiment,
        }
        base["aspect_terms"].append(term)
        decision = {
            "result": term,
            "support": len(group),
            "required_support": threshold,
            "supporting_annotators": [item.annotator for item in group],
            "source_annotations": [
                {"annotator": item.annotator, "start": item.start, "end": item.end, "text": item.text,
                 "category": item.category, "sentiment": item.sentiment}
                for item in group
            ],
            "boundary_decision": boundary_audit,
            "category_decision": category_audit,
            "sentiment_decision": sentiment_audit,
            "flags": [],
        }
        if len(group) == threshold:
            decision["flags"].append("minimum_majority_support")
        if boundary_audit["tie"]:
            decision["flags"].append("boundary_tie")
        if category_audit["tie"]:
            decision["flags"].append("category_tie")
        if sentiment_audit["tie"]:
            decision["flags"].append("sentiment_tie")
        audit["explicit_decisions"].append(decision)

    base["aspect_terms"].sort(key=lambda item: (item["fr"], item["to"], CATEGORY_ORDER.index(item["category"])))
    audit["rejected_explicit_annotations"] = [
        {"annotator": item.annotator, "start": item.start, "end": item.end, "text": item.text,
         "category": item.category, "sentiment": item.sentiment}
        for item in rejected
    ]
    if rejected:
        audit["flags"].append("rejected_minority_explicit_annotations")

    per_annotator_implicit: dict[str, dict[str, list[str]]] = {}
    for name in da_voters:
        grouped: dict[str, list[str]] = {}
        for category, sentiment in implicit_annotations(rows[name]):
            grouped.setdefault(category, []).append(sentiment)
        per_annotator_implicit[name] = grouped
    for category in CATEGORY_ORDER:
        supporters = [name for name in da_voters if category in per_annotator_implicit[name]]
        if len(supporters) < threshold:
            continue
        votes = []
        local_ties = []
        for name in supporters:
            vote, tied = local_sentiment_vote(per_annotator_implicit[name][category])
            votes.append((name, vote))
            if tied:
                local_ties.append(name)
        sentiment, sentiment_audit = choose_label(votes, SENTIMENT_ORDER)
        result = {"category": category, "polarity": sentiment}
        base["aspect_categories"].append(result)
        decision = {
            "result": result,
            "support": len(supporters),
            "required_support": threshold,
            "supporting_annotators": supporters,
            "sentiment_decision": sentiment_audit,
            "flags": [],
        }
        if len(supporters) == threshold:
            decision["flags"].append("minimum_majority_support")
        if sentiment_audit["tie"]:
            decision["flags"].append("sentiment_tie")
        if local_ties:
            decision["flags"].append("duplicate_local_implicit_sentiment_conflict")
            decision["local_tie_annotators"] = local_ties
        audit["implicit_decisions"].append(decision)
    return base, audit


def source_match_rates(audits: Iterable[dict[str, Any]]) -> dict[str, dict[str, int | float | None]]:
    totals = {name: Counter() for name in ANNOTATORS}
    for review in audits:
        for decision in review["explicit_decisions"]:
            result = decision["result"]
            for source in decision["source_annotations"]:
                counter = totals[source["annotator"]]
                counter["supported_decisions"] += 1
                if (source["start"], source["end"]) == (result["fr"], result["to"]):
                    counter["boundary_matches"] += 1
                if source["category"] == result["category"]:
                    counter["category_matches"] += 1
                if source["sentiment"] == result["polarity"]:
                    counter["sentiment_matches"] += 1
                if (
                    (source["start"], source["end"]) == (result["fr"], result["to"])
                    and source["category"] == result["category"]
                    and source["sentiment"] == result["polarity"]
                ):
                    counter["full_matches"] += 1
    output = {}
    for name, counter in totals.items():
        denominator = counter["supported_decisions"]
        values: dict[str, int | float | None] = dict(counter)
        values["full_match_percentage"] = round(100 * counter["full_matches"] / denominator, 2) if denominator else None
        output[name] = values
    return output


def main() -> None:
    datasets = read_inputs()
    adjudicated, audits = [], []
    for index in range(len(datasets["A1"])):
        rows = {name: dataset[index] for name, dataset in datasets.items()}
        result, audit = adjudicate_review(index, rows)
        adjudicated.append(result)
        audits.append(audit)

    work = Path("calibration/.adjudication_work")
    work.mkdir(parents=True, exist_ok=True)
    output = work / "adjudicated_calibration.json"
    audit_output = work / "adjudication_audit.json"
    queue_output = work / "adjudication_review_queue.json"
    output.write_text(json.dumps(adjudicated, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_output.write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding="utf-8")
    high_risk_flags = {
        "review_status_close_vote", "boundary_tie", "category_tie", "sentiment_tie",
        "duplicate_local_implicit_sentiment_conflict",
    }
    review_queue = []
    for item in audits:
        reasons = sorted(
            high_risk_flags
            & (
                set(item["flags"])
                | {flag for decision in item["explicit_decisions"] + item["implicit_decisions"] for flag in decision["flags"]}
            )
        )
        if reasons:
            queued = dict(item)
            queued["review_reasons"] = reasons
            review_queue.append(queued)
    queue_output.write_text(json.dumps(review_queue, ensure_ascii=False, indent=2), encoding="utf-8")

    valid = [row for row in adjudicated if row["review_status"] == "DA"]
    summary = {
        "methodology": {
            "review_status": "DA when at least three of five annotators voted DA; otherwise NE",
            "aspect_presence": "strict majority among annotators that voted DA",
            "boundary": "most frequent span; every frequency tie is sent to manual adjudication",
            "category_and_sentiment": "majority vote; every tie is sent to manual adjudication",
            "manual_queue": "close DA/NE vote or a boundary/category/sentiment tie",
        },
        "reviews": len(adjudicated),
        "valid_reviews": len(valid),
        "noise_reviews": len(adjudicated) - len(valid),
        "explicit_aspects": sum(len(row["aspect_terms"]) for row in valid),
        "implicit_aspects": sum(len(row["aspect_categories"]) for row in valid),
        "reviews_in_manual_queue": len(review_queue),
        "manual_queue_reasons": dict(Counter(reason for item in review_queue for reason in item["review_reasons"])),
        "source_match_rates_for_supported_explicit_decisions": source_match_rates(audits),
    }
    (work / "adjudication_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved {output}, {audit_output}, {queue_output}")


if __name__ == "__main__":
    main()
