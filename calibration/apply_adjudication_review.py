#!/usr/bin/env python3
"""Apply manually reviewed Label Studio tasks to the adjudicated calibration set."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE = Path("calibration/.adjudication_work/adjudicated_calibration.json")
QUEUE = Path("calibration/.adjudication_work/adjudication_review_queue.json")
REVIEWED = Path("calibration/adjudication_review_finished.json")
OUTPUT = Path("calibration/adjudicated_calibration_final.json")
WORK = Path("calibration/.adjudication_work")
CHANGES = WORK / "adjudication_manual_changes.json"
SUMMARY = WORK / "adjudication_final_summary.json"
METADATA = Path("calibration/calibration_annotations.json")


def aggregate_polarity(values: list[str]) -> str | None:
    if "Konflikt" in values or ("Pozitivan" in values and "Negativan" in values):
        return "Konflikt"
    for value in ("Pozitivan", "Negativan", "Neutralan"):
        if value in values:
            return value
    return None


def canonicalize(row: dict[str, Any], phone: str) -> dict[str, Any]:
    terms = list(row["aspect_terms"])
    terms.extend(
        {"fr": -1, "to": -1, "trg": None, "category": item["category"], "polarity": item["polarity"]}
        for item in row["aspect_categories"]
    )
    grouped: dict[str, list[str]] = defaultdict(list)
    for term in terms:
        grouped[term["category"]].append(term["polarity"])
    categories = [
        {"category": category, "polarity": polarity}
        for category, values in grouped.items()
        if (polarity := aggregate_polarity(values)) is not None
    ]
    return {
        "phone": phone,
        "comment": row["comment"],
        "review_status": row["review_status"],
        "aspect_terms": terms if row["review_status"] == "DA" else [],
        "aspect_categories": categories if row["review_status"] == "DA" else [],
    }


def parse_annotation(task: dict[str, Any]) -> dict[str, Any]:
    annotations = task.get("annotations") or []
    if len(annotations) != 1 or annotations[0].get("was_cancelled"):
        raise ValueError(f"Task {task.get('id')} must contain one submitted annotation")
    results = annotations[0].get("result") or []
    status = None
    regions: dict[str, dict[str, Any]] = defaultdict(dict)
    implicit = []
    for result in results:
        value = result.get("value") or {}
        name = result.get("from_name")
        if name == "review_status":
            choices = value.get("choices") or []
            if len(choices) != 1:
                raise ValueError(f"Task {task.get('id')} has invalid review_status")
            status = choices[0]
        elif name == "categories":
            labels = value.get("labels") or []
            if len(labels) != 1:
                raise ValueError(f"Task {task.get('id')} has invalid category region")
            regions[result["id"]].update(
                fr=value.get("start"), to=value.get("end"), trg=value.get("text"), category=labels[0]
            )
        elif name == "sentiment":
            choices = value.get("choices") or []
            if len(choices) != 1:
                raise ValueError(f"Task {task.get('id')} has invalid sentiment region")
            regions[result["id"]]["polarity"] = choices[0]
        elif name == "implicit_aspects":
            for taxonomy in value.get("taxonomy") or []:
                if not isinstance(taxonomy, list) or len(taxonomy) != 2:
                    raise ValueError(f"Task {task.get('id')} has invalid implicit taxonomy")
                implicit.append({"category": taxonomy[0], "polarity": taxonomy[1]})
    if status not in {"DA", "NE"}:
        raise ValueError(f"Task {task.get('id')} has no valid submitted review_status")
    terms = list(regions.values())
    required = {"fr", "to", "trg", "category", "polarity"}
    if any(set(term) != required for term in terms):
        raise ValueError(f"Task {task.get('id')} has an unpaired category/sentiment region")
    comment = task["data"]["comment"]
    terms.sort(key=lambda item: (item["fr"], item["to"], item["category"]))
    for term in terms:
        if not (0 <= term["fr"] < term["to"] <= len(comment)) or comment[term["fr"]:term["to"]] != term["trg"]:
            raise ValueError(f"Task {task.get('id')} has invalid text offsets")
    if status == "NE":
        terms, implicit = [], []
    return {
        "phone": task["data"].get("phone"),
        "comment": comment,
        "review_status": status,
        "aspect_terms": terms,
        "aspect_categories": implicit,
    }


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    base = json.loads(BASE.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    reviewed = json.loads(REVIEWED.read_text(encoding="utf-8"))
    metadata_rows = json.loads(METADATA.read_text(encoding="utf-8"))
    phone_by_comment = {item["data"]["comment"]: item["data"]["phone"] for item in metadata_rows}
    if len(phone_by_comment) != len(metadata_rows):
        raise ValueError("Calibration metadata contains duplicate comments")
    expected = {item["index"] for item in queue}
    reviewed_by_index = {}
    for task in reviewed:
        index = task.get("data", {}).get("adjudication_index")
        if not isinstance(index, int) or index in reviewed_by_index:
            raise ValueError(f"Missing or duplicate adjudication_index: {index!r}")
        reviewed_by_index[index] = task
    if set(reviewed_by_index) != expected:
        raise ValueError(
            f"Reviewed indices differ from queue; missing={sorted(expected-set(reviewed_by_index))}, "
            f"extra={sorted(set(reviewed_by_index)-expected)}"
        )

    final = [dict(row) for row in base]
    changes = []
    counters = Counter()
    reasons = {item["index"]: item["review_reasons"] for item in queue}
    for index in sorted(reviewed_by_index):
        old = base[index]
        new = parse_annotation(reviewed_by_index[index])
        if old["comment"] != new["comment"]:
            raise ValueError(f"Comment mismatch at adjudication_index {index}")
        final[index] = new
        changed_fields = [field for field in ("review_status", "aspect_terms", "aspect_categories") if old[field] != new[field]]
        if changed_fields:
            counters["changed_reviews"] += 1
            counters["status_changes"] += old["review_status"] != new["review_status"]
            counters["explicit_changes"] += old["aspect_terms"] != new["aspect_terms"]
            counters["implicit_changes"] += old["aspect_categories"] != new["aspect_categories"]
            changes.append(
                {
                    "adjudication_index": index,
                    "review_reasons": reasons[index],
                    "changed_fields": changed_fields,
                    "before": old,
                    "after": new,
                }
            )

    if set(phone_by_comment) != {row["comment"] for row in final}:
        raise ValueError("Calibration metadata comments do not match the adjudicated set")
    canonical_final = [canonicalize(row, phone_by_comment[row["comment"]]) for row in final]
    OUTPUT.write_text(json.dumps(canonical_final, ensure_ascii=False, indent=2), encoding="utf-8")
    CHANGES.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    valid = [row for row in final if row["review_status"] == "DA"]
    summary = {
        "reviews": len(final),
        "manually_reviewed": len(reviewed_by_index),
        "unchanged_after_review": len(reviewed_by_index) - counters["changed_reviews"],
        **dict(counters),
        "valid_reviews": len(valid),
        "noise_reviews": len(final) - len(valid),
        "explicit_aspects": sum(len(row["aspect_terms"]) for row in valid),
        "implicit_aspects": sum(len(row["aspect_categories"]) for row in valid),
        "metadata_phone_corrections": sum(row["phone"] != phone_by_comment[row["comment"]] for row in final),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved final dataset to {OUTPUT}")


if __name__ == "__main__":
    main()
