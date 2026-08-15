import argparse
import re
import sys
import pandas as pd

from pathlib import Path
absPath = Path(__file__).resolve().parent


def sanitize_brand_name(brand):
	"""Convert a brand value into a safe filename fragment."""
	if pd.isna(brand):
		return "unknown"

	brand_name = str(brand).strip()
	if not brand_name:
		return "unknown"

	brand_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", brand_name)
	brand_name = brand_name.strip("._ ") or "unknown"
	return brand_name


def prepare_dataset(
	dataset_csv: Path,
	calibration_set_csv: Path,
	output_dir: Path
):
	"""
	Prepare the dataset by filtering out the calibration set from the main dataset,
	then split the remaining rows by brand into separate CSV files.
	"""

	# 1. Check if the input CSV files exist
	if not dataset_csv.exists():
		print(f"Error: Dataset CSV file '{dataset_csv}' does not exist.")
		sys.exit(1)
	if not calibration_set_csv.exists():
		print(f"Error: Calibration set CSV file '{calibration_set_csv}' does not exist.")
		sys.exit(1)

	# 2. Read the CSV files into DataFrames
	dataset_df = pd.read_csv(dataset_csv)
	calibration_set_df = pd.read_csv(calibration_set_csv)

	# 3. Filter out the calibration set from the main dataset
	calibration_comments = set(calibration_set_df["comment"].dropna())
	df_remaining = dataset_df[~dataset_df["comment"].isin(calibration_comments)].copy()

	print(f"Successfully removed calibration set ({len(calibration_set_df)}) from the main dataset ({len(dataset_df)}).")
	print(f"Remaining dataset with {len(df_remaining)} entries.")

	# 4. Split by brand and save each subset to a separate CSV file.
	if "brand" not in df_remaining.columns:
		print("Error: The dataset does not contain a 'brand' column, so it cannot be split by brand.")
		sys.exit(1)

	output_dir.mkdir(parents=True, exist_ok=True)
	brand_files = []
	for brand, group in df_remaining.groupby("brand", dropna=False):
		brand_name = sanitize_brand_name(brand)
		brand_path = output_dir / f"{brand_name}.csv"
		group.to_csv(brand_path, index=False, encoding="utf-8-sig")
		brand_files.append(brand_path)
		print(f"Saved {brand_name} specific file with {len(group)} rows in file: {brand_path}")

	print(f"Saved {len(brand_files)} brand-specific CSV files under '{output_dir}'.")

	return df_remaining


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Prepare the dataset by filtering out the calibration set from the main dataset and splitting by brand."
	)
	parser.add_argument(
		"--dataset_csv",
		type=str,
		default="mobilnisvet_comments_clean.csv",
		help="Path to the main dataset CSV file (default: 'mobilnisvet_comments_clean.csv')."
	)
	parser.add_argument(
		"--calibration_set_csv",
		type=str,
		default="calibration/calibration_set_1200.csv",
		help="Path to the calibration set CSV file (default: 'calibration/calibration_set_1200.csv')."
	)
	parser.add_argument(
		"--output_dir",
		type=str,
		default="mobilnisvet_comments_non_calibration",
		help="Directory where each brand-specific CSV will be saved (default: 'mobilnisvet_comments_non_calibration')."
	)
	return parser


if __name__ == "__main__":
	parser = build_parser()
	args = parser.parse_args()

	prepare_dataset(
		dataset_csv=absPath / args.dataset_csv,
		calibration_set_csv=absPath / args.calibration_set_csv,
		output_dir=absPath / args.output_dir
	)
