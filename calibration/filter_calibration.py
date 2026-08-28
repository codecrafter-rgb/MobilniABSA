import argparse
import json
import re
import sys
import pandas as pd

from pathlib import Path
absPath = Path(__file__).resolve().parent


def check_condition(
	comment: str, 
	patterns: list[str], 
	complexity_score: int, 
	reasons: list[str], 
	reason: str
) -> int:
	for pattern in patterns:
		if re.search(pattern, comment):
			reasons.append(reason)
			return complexity_score
	return 0


def assess_complexity(comment: str) -> tuple[int, list[str]]:
	"""
	Analyse comment and calculate complexity score and tracks reasons.
	"""
	if not isinstance(comment, str):
		return 0, []

	comment_lower = comment.lower()
	words = comment_lower.split()
	word_cnt = len(words)
	
	complexity_score = 0
	reasons = []
	
	# 1. Comment length (longer comments are preferred)
	if word_cnt >= 15:
		complexity_score += 2
		reasons.append("Dužina (>=15 reči)")
		
	# 2. Contrast Conjunction (Indicates mixed sentiment)
	contrast_conjunction = [
		r"\bali\b", 
		r"\bmeđutim\b", 
		r"\bdok\b", 
		r"\biako\b", 
		r"\bal\b", 
		r"\bipak\b"
	]
	complexity_score += check_condition(comment_lower, contrast_conjunction, 3, reasons, "Suprotni veznici")

	# 3. Litotes
	negations = [r"\bnije\b", r"\bnema\b", r"\bne\b", r"\bniti\b", r"\bbez\b"]
	complexity_score += check_condition(comment_lower, negations, 2, reasons, "Negacija")

	# 4. Measurement Units (Could mean neutral sentiment)
	spec_patterns = [r"\b(\d+\s*(mah|hz|gb|mp|w|cm|inča|inca|ram))\b"]
	complexity_score += check_condition(comment_lower, spec_patterns, 2, reasons, "Specifikacija")

	# 5. Slang and other phrases implying aspect
	slang_patterns = [
		r"\bcigla\b", 
		r"\bfotke\b", 
		r"\bšaomi\b", 
		r"\bsecka\b",  
		r"\bkanta\b", 
		r"\bsmeće\b"
	]
	complexity_score += check_condition(comment_lower, slang_patterns, 2, reasons, "Sleng")

	# 6. General & Price oriented comments
	general_price = [
		r"\bzbog\b", 
		r"\buzeo|uzela sam\b", 
		r"\bkupio|kupila sam\b", 
		r"\bplatio|platila sam\b"
	]
	complexity_score += check_condition(comment_lower, general_price, 1, reasons, "Motiv kupovine")

	return complexity_score, reasons


def candidate_select(input_csv: Path, output_csv: Path, candidate_num: int = 150):
	"""
	- Loads csv file, 
	- Ranks comments based on complexity,
	- Stores top 'candidate_num' comments,
	- Returns sorted by complexity score DataFrame
	"""
	if not input_csv.exists():
		print(f"Error: Input comments CSV not found at: {input_csv}")
		sys.exit(1)

	print(f"Loading file: {input_csv}...")
	df = pd.read_csv(input_csv)

	results = df["comment"].apply(assess_complexity)
	
	df["complexity_score"] = [r[0] for r in results]
	df["reasons"] = [", ".join(r[1]) for r in results]
	
	df_sorted = df.sort_values(by="complexity_score", ascending=False)
	
	candidates = df_sorted.head(candidate_num)
	
	candidates.to_csv(output_csv, index=False, encoding="utf-8-sig")
	print(f"Successfully stored {len(candidates)} candidates in file: {output_csv}")

	return df_sorted


def generate_calibration_set(
	input_csv: Path,
	output_candidates_csv: Path,
	output_csv: Path,
	complex_cnt: int = 150,
	total_number: int = 600,
	random_state: int = 390
):
	"""
	Takes 'complex_cnt' of top complex comments and randomly picks rest.
	"""
	if not input_csv.exists():
		print(f"Error: Input comments CSV not found at: {input_csv}")
		sys.exit(1)

	df_sorted = candidate_select(input_csv, output_candidates_csv, complex_cnt)
	df_complex = df_sorted.head(complex_cnt)
	df_rest = df_sorted.iloc[complex_cnt:]
	df_random = df_rest.sample(n=total_number - complex_cnt, random_state=random_state)

	result = pd.concat([df_complex, df_random]) \
			.sample(frac=1, random_state=random_state) \
			.reset_index(drop=True)
	result.to_csv(output_csv, index=False, encoding="utf-8-sig")
	print(f"Successfully stored {len(result)} comments in file: {output_csv}")


def expand_calibration_set(
	input_csv: Path,
	existing_set_csv: Path,
	output_csv: Path,
	target_total: int,
	additional_complex_cnt: int = 150,
	random_state: int = 390
):
	"""
	Expands an existing calibration set CSV to target_total rows without altering
	or re-ordering existing rows.
	"""
	# 1. Check if existing set and input CSV files exist
	if not existing_set_csv.exists():
			print(f"Error: Existing calibration set CSV not found at: {existing_set_csv}")
			sys.exit(1)
	
	if not input_csv.exists():
		print(f"Error: Input comments CSV not found at: {input_csv}")
		sys.exit(1)

	# 2. Load existing calibration dataset
	existing_df = pd.read_csv(existing_set_csv)
	current_cnt = len(existing_df)
	needed_cnt = target_total - current_cnt

	if needed_cnt <= 0:
		print(f"Existing set already has {current_cnt} rows (target: {target_total}). Nothing to do.")
		return existing_df

	print(f"Found {current_cnt} existing rows. Preparing to add {needed_cnt} new rows...")

	# 3. Score the full dataset
	df_full = pd.read_csv(input_csv)
	results = df_full["comment"].apply(assess_complexity)
	df_full["complexity_score"] = [r[0] for r in results]
	df_full["reasons"] = [", ".join(r[1]) for r in results]

	df_sorted = df_full.sort_values(by="complexity_score", ascending=False)

	# 4. Exclude existing comments to prevent duplicates
	existing_comments = set(existing_df["comment"].dropna())
	df_remaining = df_sorted[~df_sorted["comment"].isin(existing_comments)].copy()
	if len(df_remaining) < needed_cnt:
		raise ValueError(
			f"Cannot expand to {target_total} rows: only {len(df_remaining)} new comments are available"
		)

	# 5. Pick additional complex and random rows from the remaining pool
	if additional_complex_cnt > 0:
		complex_needed = min(additional_complex_cnt, needed_cnt)
		df_add_complex = df_remaining.head(complex_needed)
		df_rest = df_remaining.iloc[complex_needed:]
		
		random_needed = needed_cnt - len(df_add_complex)
		df_add_random = df_rest.sample(n=random_needed, random_state=random_state)
		
		new_rows = pd.concat([df_add_complex, df_add_random])
	else:
		new_rows = df_remaining.sample(n=needed_cnt, random_state=random_state)

	# 6. Append new rows to existing ones (preserves old rows intact)
	expanded_df = pd.concat([existing_df, new_rows], ignore_index=True)
	expanded_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

	print(f"Successfully expanded calibration set from {current_cnt} to {len(expanded_df)} rows: {output_csv}")
	return expanded_df


def merge_annotations(exported_json: Path, input_csv: Path, output_json: Path):
	"""
	Merges completed annotations from an exported Label Studio JSON file with 
	a target CSV dataset to create an updated JSON file ready for Label Studio import.
	"""
	print(f"\n[1/4] Checking file paths...")
	
	if not exported_json.exists():
		print(f"Error: Exported JSON file not found at: {exported_json}")
		sys.exit(1)

	if not input_csv.exists():
		print(f"Error: CSV dataset file not found at: {input_csv}")
		sys.exit(1)

	print(f"Exported JSON: {exported_json}")
	print(f"Dataset CSV:   {input_csv}")
	print(f"Output Target: {output_json}")

	# Load and parse JSON
	print(f"\n[2/4] Parsing exported annotations...")
	try:
		with open(exported_json, "r", encoding="utf-8") as f:
			old_data = json.load(f)
	except Exception as e:
		print(f"Error reading/parsing JSON file '{exported_json}': {e}")
		sys.exit(1)

	if not isinstance(old_data, list):
		print("Error: Expected JSON file to contain a top-level list of tasks.")
		sys.exit(1)

	# Build annotations lookup map
	annotations_map = {}
	for task in old_data:
		if isinstance(task, dict) and task.get("annotations"):
			comment_text = task.get("data", {}).get("comment")
			if comment_text:
				clean_annotations = [
					{
						"result": ann.get("result", []),
						"was_cancelled": ann.get("was_cancelled", False),
						"ground_truth": ann.get("ground_truth", False),
						"created_at": ann.get("created_at"),
						"updated_at": ann.get("updated_at")
					}
					for ann in task["annotations"]
				]
				annotations_map[comment_text] = clean_annotations

	print(f"Extracted annotations for {len(annotations_map)} unique comments.")

	# Read dataset CSV
	print(f"\n[3/4] Reading target CSV dataset...")
	try:
		df_dataset = pd.read_csv(input_csv)
	except Exception as e:
		print(f"Error reading CSV file '{input_csv}': {e}")
		sys.exit(1)

	if "comment" not in df_dataset.columns:
		print("Error: Missing required column 'comment' in CSV file.")
		sys.exit(1)

	# Merge annotations
	import_tasks = []
	matched_count = 0

	for _, row in df_dataset.iterrows():
		data_dict = {
			col: (val if pd.notna(val) else "")
			for col, val in row.items()
		}

		comment_text = str(data_dict.get("comment", ""))

		task_payload = {
			"data": data_dict
		}

		# Attach existing annotations if comment was previously annotated
		if comment_text in annotations_map:
			task_payload["annotations"] = annotations_map[comment_text]
			matched_count += 1

		import_tasks.append(task_payload)

	# Save output JSON
	print(f"\n[4/4] Saving output JSON...")
	try:
		with open(output_json, "w", encoding="utf-8") as f:
			json.dump(import_tasks, f, ensure_ascii=False, indent=2)
	except Exception as e:
		print(f"Error writing output JSON file to '{output_json}': {e}")
		sys.exit(1)

	print("\n" + "=" * 50)
	print("SUCCESS SUMMARY")
	print("=" * 50)
	print(f" - Matched & preserved annotations: {matched_count}")
	print(f" - Unannotated new tasks added:     {len(import_tasks) - matched_count}")
	print(f" - Total tasks in output JSON:      {len(import_tasks)}")
	print(f" - Saved to: {output_json}")
	print("=" * 50 + "\n")


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Generate, expand, or merge calibration datasets for Label Studio")
	subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

	# Command: generate
	parser_generate = subparsers.add_parser("generate", help="Generate a new calibration set CSV")
	parser_generate.add_argument(
		"--input",
		type=str,
		default="../mobilnisvet_comments_clean.csv",
		help="Relative path to input comments CSV (default: '../mobilnisvet_comments_clean.csv')"
	)
	parser_generate.add_argument(
		"--candidates-output",
		type=str,
		default=".calibration_candidates.csv",
		help="Relative path for intermediate candidates CSV (default: '.calibration_candidates.csv')"
	)
	parser_generate.add_argument(
		"--output",
		type=str,
		default="calibration_set.csv",
		help="Relative path for output CSV (default: 'calibration_set.csv')"
	)

	# Command: expand
	parser_expand = subparsers.add_parser("expand", help="Expand an existing calibration set CSV to an explicit target size")
	parser_expand.add_argument(
		"--input",
		type=str,
		default="../mobilnisvet_comments_clean.csv",
		help="Relative path to input comments CSV (default: '../mobilnisvet_comments_clean.csv')"
	)
	parser_expand.add_argument(
		"--existing-set",
		type=str,
		default="calibration_set.csv",
		help="Relative path to existing calibration set CSV (default: 'calibration_set.csv')"
	)
	parser_expand.add_argument(
		"--output",
		type=str,
		default="calibration_set_expanded.csv",
		help="Relative path for optional expanded output CSV (default: 'calibration_set_expanded.csv')"
	)
	parser_expand.add_argument(
		"--target-total",
		type=int,
		required=True,
		help="Required target number of comments in the expanded calibration set"
	)

	# Command: merge
	parser_merge = subparsers.add_parser("merge", help="Merge exported JSON annotations into a dataset JSON for Label Studio import")
	parser_merge.add_argument(
		"exported_json",
		type=str,
		help="Relative path to old exported JSON file"
	)
	parser_merge.add_argument(
		"output_json",
		type=str,
		help="Relative path for output import JSON file"
	)
	parser_merge.add_argument(
		"--csv",
		type=str,
		default="calibration_set.csv",
		help="Relative path to the final 800-comment CSV dataset (default: 'calibration_set.csv')"
	)

	return parser


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)

	if args.command == "generate":
		generate_calibration_set(
			input_csv=absPath / args.input,
			output_candidates_csv=absPath / args.candidates_output,
			output_csv=absPath / args.output,
			complex_cnt=250,
			total_number=800,
			random_state=390
		)
		return 0
	if args.command == "expand":
		expand_calibration_set(
			input_csv=absPath / args.input,
			existing_set_csv=absPath / args.existing_set,
			output_csv=absPath / args.output,
			target_total=args.target_total,
			additional_complex_cnt=150,
			random_state=390
		)
		return 0
	if args.command == "merge":
		merge_annotations(
			exported_json=absPath / args.exported_json,
			input_csv=absPath / args.csv,
			output_json=absPath / args.output_json
		)
		return 0

	parser.error(f"Unknown command: {args.command}")
	return 2


if __name__ == "__main__":
	raise SystemExit(main())
