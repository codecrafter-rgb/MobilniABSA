#!/usr/bin/env python3
"""Create the recommended fixed ABSA split with iterative-stratification.

Strategy:
1. Split DA comments by their 44 category/sentiment labels with
   MultilabelStratifiedShuffleSplit (80/20, then the held-out 20 into 10/10).
2. Deterministically shuffle NE comments and use them to fill the exact global
   train/validation/test capacities.
3. Save complete JSON subsets and an auditable manifest.

The dependency-free implementation in create_stratified_split.py remains
available as a separate alternative.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

from create_stratified_split import (
    CATEGORIES,
    SENTIMENTS,
    SPLIT_NAMES,
    count_statuses,
    exact_split_sizes,
    load_and_validate_records,
    sha256,
    validate_assignments,
    validate_ratios,
    write_json,
)


DEFAULT_RATIOS = (0.80, 0.10, 0.10)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent

    parser = argparse.ArgumentParser(
        description=(
            "Create a fixed 80/10/10 ABSA split with the "
            "iterative-stratification library."
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
        default=script_dir / "output-iterstrat",
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


def build_pair_matrix(
    records: Sequence[dict[str, Any]],
    record_indices: Sequence[int],
    labels: Sequence[str],
) -> np.ndarray:
    label_to_id = {label: index for index, label in enumerate(labels)}
    matrix = np.zeros((len(record_indices), len(labels)), dtype=np.uint8)

    for row_index, record_index in enumerate(record_indices):
        for aspect in records[record_index]["aspect_categories"]:
            label = f"{aspect['category']}::{aspect['polarity']}"
            matrix[row_index, label_to_id[label]] = 1

    return matrix


def one_library_split(
    matrix: np.ndarray,
    test_ratio: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    splitter = MultilabelStratifiedShuffleSplit(
        n_splits=1,
        test_size=test_ratio,
        random_state=seed,
    )
    # The splitter only needs the number of X rows; all stratification
    # information is contained in the multilabel matrix.
    dummy_features = np.zeros((len(matrix), 1), dtype=np.uint8)
    train_indices, test_indices = next(splitter.split(dummy_features, matrix))
    return train_indices, test_indices


def split_da_records(
    da_indices: Sequence[int],
    matrix: np.ndarray,
    ratios: Sequence[float],
    seed: int,
) -> list[list[int]]:
    held_out_ratio = ratios[1] + ratios[2]
    train_local, held_out_local = one_library_split(
        matrix=matrix,
        test_ratio=held_out_ratio,
        seed=seed,
    )

    relative_test_ratio = ratios[2] / held_out_ratio
    validation_in_held_out, test_in_held_out = one_library_split(
        matrix=matrix[held_out_local],
        test_ratio=relative_test_ratio,
        seed=seed + 1,
    )

    da_array = np.asarray(da_indices, dtype=np.int64)
    held_out_global = da_array[held_out_local]
    return [
        da_array[train_local].tolist(),
        held_out_global[validation_in_held_out].tolist(),
        held_out_global[test_in_held_out].tolist(),
    ]


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


def get_output_paths(output_dir: Path) -> dict[str, Path]:
    paths = {name: output_dir / f"{name}.json" for name in SPLIT_NAMES}
    paths["manifest"] = output_dir / "split_manifest.json"
    return paths


def ensure_outputs_are_writable(paths: dict[str, Path], overwrite: bool) -> None:
    existing = [path for path in paths.values() if path.exists()]
    if existing and not overwrite:
        joined = "\n  ".join(str(path) for path in existing)
        raise FileExistsError(
            "Output files already exist. Use --overwrite to replace them:\n  " + joined
        )


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
        index for index, record in enumerate(records) if record["review_status"] == "DA"
    ]
    ne_indices = [
        index for index, record in enumerate(records) if record["review_status"] == "NE"
    ]

    pair_matrix = build_pair_matrix(records, da_indices, labels)
    da_assignments = split_da_records(da_indices, pair_matrix, ratios, args.seed)
    target_sizes = exact_split_sizes(len(records), ratios)
    assignments, ne_split_counts = fill_with_ne_records(
        da_assignments=da_assignments,
        ne_indices=ne_indices,
        target_sizes=target_sizes,
        seed=args.seed,
    )
    validate_assignments(assignments, len(records))

    output_dir = args.output_dir.resolve()
    paths = get_output_paths(output_dir)
    ensure_outputs_are_writable(paths, args.overwrite)
    output_dir.mkdir(parents=True, exist_ok=True)

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
    package_version = importlib.metadata.version("iterative-stratification")
    manifest = {
        "schema_version": 1,
        "method": "iterative-stratification library; DA and NE split separately",
        "library": {
            "distribution": "iterative-stratification",
            "version": package_version,
            "class": "iterstrat.ml_stratifiers.MultilabelStratifiedShuffleSplit",
        },
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
                "Library split into train and held-out subsets, followed by a "
                "library split of held-out into validation and test."
            ),
            "NE": (
                "Deterministic shuffle followed by allocation into the exact "
                "remaining global split capacities."
            ),
            "second_split_seed": args.seed + 1,
            "NE_shuffle_seed": args.seed + 2,
            "NE_split_counts": dict(zip(SPLIT_NAMES, ne_split_counts)),
        },
        "global_status_counts": count_statuses(all_indices, records),
        "global_label_counts": count_pair_labels(all_indices, records, labels),
        "splits": split_metadata,
        "notes": [
            "Duplicate comments are not grouped.",
            "Split comments before creating two-stage ACSA comment/category pairs.",
            "A label with fewer examples than splits cannot occur in every split.",
        ],
    }
    write_json(paths["manifest"], manifest)

    print(f"Source: {source_path}")
    print(
        "Method: MultilabelStratifiedShuffleSplit for DA; "
        "deterministic proportional allocation for NE"
    )
    print(f"iterative-stratification: {package_version}")
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
        for label, count in manifest["global_label_counts"].items()
        if 0 < count < len(SPLIT_NAMES)
    ]
    if rare_labels:
        print("\nLabels too rare to appear in every split:")
        for label, count in rare_labels:
            print(f"  {label}: {count}")

    print(f"\nSaved split files and manifest to: {output_dir}")


if __name__ == "__main__":
    main()
