#!/usr/bin/env python3
"""Create a fixed ABSA split with manual stratification and separate NE data.

DA comments are split by the 44 category/sentiment labels with a manual
rare-label-first iterative algorithm. NE comments are then deterministically
allocated to fill the exact global train/validation/test capacities.

The script intentionally does not group duplicate comments. Splitting is
always performed before two-stage notebooks expand comments into ACSA pairs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


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

SENTIMENTS = [
    "Pozitivan",
    "Negativan",
    "Neutralan",
    "Konflikt",
]

SPLIT_NAMES = ("train", "validation", "test")
DEFAULT_RATIOS = (0.80, 0.10, 0.10)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent

    parser = argparse.ArgumentParser(
        description=(
            "Create a fixed 80/10/10 ABSA split with manual rare-label-first "
            "stratification for DA and separate allocation of NE comments."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "annotation" / "annotations.json",
        help="Source annotations JSON (default: annotation/annotations.json).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir / "output-manual",
        help="Directory for split JSON files and the manifest.",
    )
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_RATIOS[0])
    parser.add_argument("--validation-ratio", type=float, default=DEFAULT_RATIOS[1])
    parser.add_argument("--test-ratio", type=float, default=DEFAULT_RATIOS[2])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow existing output files to be replaced.",
    )
    return parser.parse_args()


def pair_label_names() -> list[str]:
    return [
        f"{category}::{sentiment}"
        for category in CATEGORIES
        for sentiment in SENTIMENTS
    ]


def validate_ratios(ratios: Sequence[float]) -> None:
    if len(ratios) != len(SPLIT_NAMES):
        raise ValueError(f"Expected {len(SPLIT_NAMES)} split ratios.")
    if any(ratio <= 0 for ratio in ratios):
        raise ValueError("Every split ratio must be greater than zero.")
    if not math.isclose(sum(ratios), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"Split ratios must sum to 1.0, got {sum(ratios):.12f}.")


def load_and_validate_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        records = json.load(handle)

    if not isinstance(records, list) or not records:
        raise ValueError("The input JSON must be a non-empty list of comments.")

    valid_categories = set(CATEGORIES)
    valid_sentiments = set(SENTIMENTS)

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} is not a JSON object.")
        if not isinstance(record.get("comment"), str) or not record["comment"].strip():
            raise ValueError(f"Record {index} has an empty or invalid comment.")

        status = record.get("review_status")
        if status not in {"DA", "NE"}:
            raise ValueError(f"Record {index} has invalid review_status={status!r}.")

        aspects = record.get("aspect_categories")
        if not isinstance(aspects, list):
            raise ValueError(f"Record {index} has invalid aspect_categories.")
        if status == "NE" and aspects:
            raise ValueError(f"NE record {index} must not have aspect_categories.")

        seen_categories: set[str] = set()
        for aspect in aspects:
            if not isinstance(aspect, dict):
                raise ValueError(f"Record {index} contains an invalid aspect.")
            category = aspect.get("category")
            sentiment = aspect.get("polarity")
            if category not in valid_categories:
                raise ValueError(
                    f"Record {index} contains unknown category={category!r}."
                )
            if sentiment not in valid_sentiments:
                raise ValueError(
                    f"Record {index} contains unknown polarity={sentiment!r}."
                )
            if category in seen_categories:
                raise ValueError(
                    f"Record {index} has category {category!r} more than once in "
                    "aspect_categories."
                )
            seen_categories.add(category)

    return records


def build_da_sample_labels(
    records: Sequence[dict[str, Any]],
    da_indices: Sequence[int],
    labels: Sequence[str],
) -> list[set[int]]:
    label_to_id = {label: index for index, label in enumerate(labels)}
    samples: list[set[int]] = []

    for record_index in da_indices:
        samples.append(
            {
                label_to_id[f"{aspect['category']}::{aspect['polarity']}"]
                for aspect in records[record_index]["aspect_categories"]
            }
        )

    return samples


def exact_split_sizes(total: int, ratios: Sequence[float]) -> list[int]:
    """Use the largest-remainder rule so split sizes sum exactly to total."""
    exact = [total * ratio for ratio in ratios]
    sizes = [math.floor(value) for value in exact]
    missing = total - sum(sizes)

    remainder_order = sorted(
        range(len(ratios)),
        key=lambda index: (-(exact[index] - sizes[index]), index),
    )
    for index in remainder_order[:missing]:
        sizes[index] += 1

    return sizes


def iterative_multilabel_split(
    samples: Sequence[set[int]],
    split_sizes: Sequence[int],
    seed: int,
    number_of_labels: int,
) -> list[list[int]]:
    """Assign samples by repeatedly distributing the rarest remaining label.

    This is a dependency-free implementation of the central idea behind
    iterative multilabel stratification.  For the currently rarest label, a
    sample is sent to the split that still needs that label most.  Exact split
    capacities are always respected.
    """
    if sum(split_sizes) != len(samples):
        raise ValueError("Split sizes must add up to the number of samples.")

    rng = random.Random(seed)
    split_count = len(split_sizes)
    assignments: list[list[int]] = [[] for _ in range(split_count)]
    remaining_capacity = list(split_sizes)

    label_to_samples: list[set[int]] = [set() for _ in range(number_of_labels)]
    for sample_index, active_labels in enumerate(samples):
        for label_id in active_labels:
            label_to_samples[label_id].add(sample_index)

    total = len(samples)
    desired_label_counts = [
        [
            len(label_to_samples[label_id]) * split_sizes[split_id] / total
            for split_id in range(split_count)
        ]
        for label_id in range(number_of_labels)
    ]

    label_priority = list(range(number_of_labels))
    rng.shuffle(label_priority)
    priority_rank = {label_id: rank for rank, label_id in enumerate(label_priority)}
    unassigned = set(range(total))

    def choose_split(label_id: int) -> int:
        available = [
            split_id
            for split_id, capacity in enumerate(remaining_capacity)
            if capacity > 0
        ]
        greatest_label_need = max(
            desired_label_counts[label_id][split_id] for split_id in available
        )
        candidates = [
            split_id
            for split_id in available
            if math.isclose(
                desired_label_counts[label_id][split_id],
                greatest_label_need,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ]
        greatest_capacity = max(remaining_capacity[split_id] for split_id in candidates)
        candidates = [
            split_id
            for split_id in candidates
            if remaining_capacity[split_id] == greatest_capacity
        ]
        return rng.choice(candidates)

    while True:
        non_empty_labels = [
            label_id
            for label_id, sample_indices in enumerate(label_to_samples)
            if sample_indices
        ]
        if not non_empty_labels:
            break

        rarest_label = min(
            non_empty_labels,
            key=lambda label_id: (
                len(label_to_samples[label_id]),
                priority_rank[label_id],
            ),
        )
        candidates = list(label_to_samples[rarest_label])
        rng.shuffle(candidates)

        for sample_index in candidates:
            if sample_index not in unassigned:
                continue

            split_id = choose_split(rarest_label)
            assignments[split_id].append(sample_index)
            remaining_capacity[split_id] -= 1
            unassigned.remove(sample_index)

            for label_id in samples[sample_index]:
                desired_label_counts[label_id][split_id] -= 1.0
                label_to_samples[label_id].discard(sample_index)

    # DA comments without aspect categories have an empty label set.  They are
    # assigned last according to the exact remaining capacities.
    leftovers = list(unassigned)
    rng.shuffle(leftovers)
    for sample_index in leftovers:
        greatest_capacity = max(remaining_capacity)
        candidates = [
            split_id
            for split_id, capacity in enumerate(remaining_capacity)
            if capacity == greatest_capacity
        ]
        split_id = rng.choice(candidates)
        assignments[split_id].append(sample_index)
        remaining_capacity[split_id] -= 1

    if any(remaining_capacity):
        raise RuntimeError(f"Non-zero capacities after splitting: {remaining_capacity}")

    for indices in assignments:
        indices.sort()
    return assignments


def split_da_records(
    da_indices: Sequence[int],
    samples: Sequence[set[int]],
    ratios: Sequence[float],
    seed: int,
    number_of_labels: int,
) -> tuple[list[list[int]], list[int]]:
    """Mirror the library version's 80/20 then validation/test procedure."""
    held_out_ratio = ratios[1] + ratios[2]
    first_split_sizes = exact_split_sizes(
        len(da_indices),
        (ratios[0], held_out_ratio),
    )
    train_local, held_out_local = iterative_multilabel_split(
        samples=samples,
        split_sizes=first_split_sizes,
        seed=seed,
        number_of_labels=number_of_labels,
    )

    held_out_samples = [samples[local_index] for local_index in held_out_local]
    relative_ratios = (
        ratios[1] / held_out_ratio,
        ratios[2] / held_out_ratio,
    )
    second_split_sizes = exact_split_sizes(len(held_out_local), relative_ratios)
    validation_in_held_out, test_in_held_out = iterative_multilabel_split(
        samples=held_out_samples,
        split_sizes=second_split_sizes,
        seed=seed + 1,
        number_of_labels=number_of_labels,
    )

    assignments = [
        [da_indices[local_index] for local_index in train_local],
        [
            da_indices[held_out_local[local_index]]
            for local_index in validation_in_held_out
        ],
        [
            da_indices[held_out_local[local_index]]
            for local_index in test_in_held_out
        ],
    ]
    return assignments, [len(indices) for indices in assignments]


def fill_with_ne_records(
    da_assignments: Sequence[Sequence[int]],
    ne_indices: Sequence[int],
    target_sizes: Sequence[int],
    seed: int,
) -> tuple[list[list[int]], list[int]]:
    required_ne_counts = [
        target_size - len(da_indices)
        for target_size, da_indices in zip(target_sizes, da_assignments)
    ]
    if any(count < 0 for count in required_ne_counts):
        raise RuntimeError(
            "The DA split is larger than at least one global target size: "
            f"required NE counts={required_ne_counts}."
        )
    if sum(required_ne_counts) != len(ne_indices):
        raise RuntimeError(
            "NE capacities do not match the number of NE comments: "
            f"capacities={required_ne_counts}, NE={len(ne_indices)}."
        )

    shuffled_ne = list(ne_indices)
    random.Random(seed + 2).shuffle(shuffled_ne)

    assignments: list[list[int]] = []
    start = 0
    for split_id, count in enumerate(required_ne_counts):
        stop = start + count
        combined = list(da_assignments[split_id]) + shuffled_ne[start:stop]
        combined.sort()
        assignments.append(combined)
        start = stop

    return assignments, required_ne_counts


def count_pair_labels(
    indices: Sequence[int],
    records: Sequence[dict[str, Any]],
    labels: Sequence[str],
) -> dict[str, int]:
    counts = Counter(
        f"{aspect['category']}::{aspect['polarity']}"
        for record_index in indices
        for aspect in records[record_index]["aspect_categories"]
    )
    return {label: counts[label] for label in labels}


def count_statuses(
    indices: Sequence[int], records: Sequence[dict[str, Any]]
) -> dict[str, int]:
    counts = Counter(records[index]["review_status"] for index in indices)
    return {status: counts[status] for status in ("DA", "NE")}


def validate_assignments(assignments: Sequence[Sequence[int]], total: int) -> None:
    flattened = [index for indices in assignments for index in indices]
    if len(flattened) != total:
        raise RuntimeError("The split does not contain every source record exactly once.")
    if len(set(flattened)) != total:
        raise RuntimeError("The generated splits overlap.")
    if set(flattened) != set(range(total)):
        raise RuntimeError("The generated splits do not cover all source indices.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def output_paths(output_dir: Path) -> dict[str, Path]:
    paths = {name: output_dir / f"{name}.json" for name in SPLIT_NAMES}
    paths["manifest"] = output_dir / "split_manifest.json"
    return paths


def main() -> None:
    args = parse_args()
    ratios = (args.train_ratio, args.validation_ratio, args.test_ratio)
    validate_ratios(ratios)

    source_path = args.input.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source_path}")

    records = load_and_validate_records(source_path)
    labels = pair_label_names()
    da_indices = [
        index
        for index, record in enumerate(records)
        if record["review_status"] == "DA"
    ]
    ne_indices = [
        index
        for index, record in enumerate(records)
        if record["review_status"] == "NE"
    ]
    da_samples = build_da_sample_labels(records, da_indices, labels)

    da_assignments, da_target_sizes = split_da_records(
        da_indices=da_indices,
        samples=da_samples,
        ratios=ratios,
        seed=args.seed,
        number_of_labels=len(labels),
    )
    target_sizes = exact_split_sizes(len(records), ratios)
    assignments, ne_split_counts = fill_with_ne_records(
        da_assignments=da_assignments,
        ne_indices=ne_indices,
        target_sizes=target_sizes,
        seed=args.seed,
    )
    validate_assignments(assignments, len(records))

    paths = output_paths(args.output_dir.resolve())
    existing = [path for path in paths.values() if path.exists()]
    if existing and not args.overwrite:
        joined = "\n  ".join(str(path) for path in existing)
        raise FileExistsError(
            "Output files already exist. Use --overwrite to replace them:\n  " + joined
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    split_metadata: dict[str, Any] = {}
    for split_id, name in enumerate(SPLIT_NAMES):
        indices = assignments[split_id]
        write_json(paths[name], [records[index] for index in indices])
        split_metadata[name] = {
            "file": paths[name].name,
            "size": len(indices),
            "source_indices": indices,
            "status_counts": count_statuses(indices, records),
            "label_counts": count_pair_labels(indices, records, labels),
        }

    all_indices = list(range(len(records)))
    global_label_counts = count_pair_labels(all_indices, records, labels)
    manifest = {
        "schema_version": 1,
        "method": "manual rare-label-first; DA and NE split separately",
        "seed": args.seed,
        "source_file": str(source_path),
        "source_sha256": sha256(source_path),
        "total_records": len(records),
        "ratios": dict(zip(SPLIT_NAMES, ratios)),
        "target_sizes": dict(zip(SPLIT_NAMES, target_sizes)),
        "label_definition": {
            "source": "aspect_categories",
            "number_of_category_sentiment_labels": len(labels),
            "labels": labels,
        },
        "strategy": {
            "DA": (
                "Manual split into train and held-out subsets, followed by a "
                "manual split of held-out into validation and test."
            ),
            "NE": (
                "Deterministic shuffle followed by allocation into the exact "
                "remaining global split capacities."
            ),
            "DA_target_sizes": dict(zip(SPLIT_NAMES, da_target_sizes)),
            "second_split_seed": args.seed + 1,
            "NE_shuffle_seed": args.seed + 2,
            "NE_split_counts": dict(zip(SPLIT_NAMES, ne_split_counts)),
        },
        "global_status_counts": count_statuses(all_indices, records),
        "global_label_counts": global_label_counts,
        "splits": split_metadata,
        "notes": [
            "Duplicate comments are not grouped.",
            "Split comments before creating two-stage ACSA comment/category pairs.",
            "A label with fewer examples than splits cannot occur in every split.",
            "This variant exists for a fair algorithm comparison with the library version.",
        ],
    }
    write_json(paths["manifest"], manifest)

    print(f"Source: {source_path}")
    print("Method: manual rare-label-first for DA; deterministic allocation for NE")
    print(f"Seed: {args.seed}")
    print()
    for split_id, name in enumerate(SPLIT_NAMES):
        indices = assignments[split_id]
        statuses = count_statuses(indices, records)
        print(
            f"{name:10s}: {len(indices):5d} "
            f"({len(indices) / len(records):.2%}) | "
            f"DA={statuses['DA']:5d} NE={statuses['NE']:5d}"
        )

    rare_labels = [
        (label, count)
        for label, count in global_label_counts.items()
        if 0 < count < len(SPLIT_NAMES)
    ]
    if rare_labels:
        print("\nLabels too rare to appear in every split:")
        for label, count in rare_labels:
            print(f"  {label}: {count}")

    print(f"\nSaved split files and manifest to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
