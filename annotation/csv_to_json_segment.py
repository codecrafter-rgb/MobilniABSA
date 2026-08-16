import argparse
import csv
import json
import sys

from pathlib import Path
absPath = Path(__file__).resolve().parent


def convert_csv_segment_to_json(
    input_csv: Path,
    output_json: Path,
    index: int,
    segment_size: int = 50,
):
    """
    Convert one segment of a CSV file to a JSON list.

    The CSV is split into chunks of `segment_size` rows. Each chunk is exported as
    a JSON array where every item contains:
      - "id": row index in the original CSV
      - "data": {"phone": ..., "comment": ...}

    Example:
      index=0, segment_size=50 => rows 0..49
      index=1, segment_size=50 => rows 50..99
    """
    if not input_csv.exists():
        print(f"Error: CSV file '{input_csv}' does not exist.")
        sys.exit(1)

    if index < 0:
        print("Error: index must be >= 0.")
        sys.exit(1)

    if segment_size <= 0:
        print("Error: segment_size must be > 0.")
        sys.exit(1)

    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    start = index * segment_size
    end = start + segment_size

    if start >= len(rows):
        print(
            f"Error: segment index {index} is out of range for a CSV with {len(rows)} rows."
        )
        sys.exit(1)

    selected_rows = rows[start:end]
    output_data = []

    for row_index, row in enumerate(selected_rows, start=start):
        output_data.append(
            {
                "id": row_index,
                "data": {
                    "phone": row.get("phone", ""),
                    "comment": row.get("comment", ""),
                },
            }
        )

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(
        f"Saved {len(output_data)} records from CSV rows {start} to {end - 1} "
        f"to '{output_json}'."
    )
    return output_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert one segment of a CSV file into a JSON array with id/data fields."
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="../mobilnisvet_comments_non_calibration",
        help="Path to the source directory (default: '../mobilnisvet_comments_non_calibration').",
    )
    parser.add_argument(
        "--brand",
        type=str,
        required=True,
        help="CSV file name (e.g. 'Apple', 'Honor', 'Huawei', 'Samsung', 'Xiaomi')."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to the output JSON file. If not provided, a default filename is generated.",
    )
    parser.add_argument(
        "--index",
        type=int,
        required=True,
        help="Segment index to export. Example: index=0 -> first segment, index=1 -> second segment.",
    )
    parser.add_argument(
        "--segment-size",
        type=int,
        default=50,
        help="Number of rows per segment (default: 50).",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    if args.output is None:
        output_json = f"mobilnisvet_segment_{args.brand}/{args.index}.json"

    convert_csv_segment_to_json(
        input_csv=absPath / args.input_dir / f"{args.brand}.csv",
        output_json=absPath / output_json,
        index=args.index,
        segment_size=args.segment_size,
    )
