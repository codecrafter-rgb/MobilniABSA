import argparse
import sys
import pandas as pd

from pathlib import Path

absPath = Path(__file__).resolve().parent

def prepare_dataset(
	dataset_csv: Path,
	calibration_set_csv: Path,
	output_csv: Path
):
	"""
	Prepare the dataset by filtering out the calibration set from the main dataset.
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

	# 4. Save the remaining dataset to the output CSV file
	df_remaining.to_csv(output_csv, index=False, encoding="utf-8-sig")
	print(f"Successfully removed calibration set ({len(calibration_set_df)}) from the main dataset ({len(dataset_df)}).")
	print(f"Remaining dataset saved to '{output_csv}' with {len(df_remaining)} entries.")

	return df_remaining


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Prepare the dataset by filtering out the calibration set from the main dataset."
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
		"--output_csv",
		type=str,
		default="mobilnisvet_comments_non_calibration.csv",
		help="Path to the output CSV file (default: 'mobilnisvet_comments_non_calibration.csv')."
	)
	return parser


if __name__ == "__main__":
	parser = build_parser()
	args = parser.parse_args()

	prepare_dataset(
		dataset_csv=absPath / args.dataset_csv,
		calibration_set_csv=absPath / args.calibration_set_csv,
		output_csv=absPath / args.output_csv
	)
