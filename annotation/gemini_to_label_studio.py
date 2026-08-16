import argparse
import json
import random
import string
import sys

from pathlib import Path
absPath = Path(__file__).resolve().parent


def generate_random_id(length=10):
	"""Generates radnom ID of given length (default 10) that Label Studio uses."""
	chars = string.ascii_letters + string.digits + "-_"
	return ''.join(random.choice(chars) for _ in range(length))


def convert_gemini_to_labelstudio(gemini_json: Path, dataset_json: Path, output_json: Path):
	"""
	Converts Gemini model output to Label Studio format.
	
	:param gemini_json: Path to List/JSON output from Gemini model (contains 'id' and 'aspects')
	:param dataset_json: Path to List/JSON of the original dataset (contains 'id' and 'data' with 'comment')
	:param output_json: Path to save the converted Label Studio JSON
	:return: List of tasks formatted for Label Studio import
	"""
	# Check if the input files exist
	if not gemini_json.exists():
		print(f"Error: Gemini output file '{gemini_json}' does not exist.")
		sys.exit(1)
	if not dataset_json.exists():
		print(f"Error: Dataset file '{dataset_json}' does not exist.")
		sys.exit(1)

	# Load the Gemini output and the original dataset
	with gemini_json.open("r", encoding="utf-8") as f:
		gemini_output = json.load(f)
	with dataset_json.open("r", encoding="utf-8") as f:
		raw_dataset = json.load(f)

	# Create a mapping from raw dataset IDs to their corresponding data for quick lookup
	raw_data_map = {item["id"]: item.get("data", item) for item in raw_dataset}
	
	labelstudio_tasks = []

	gemini_output = gemini_output.get("response", [])
	for g_item in gemini_output:
		task_id = g_item["id"]
		original_data = raw_data_map.get(task_id, {})
		comment_text = original_data.get("comment", "")
		
		results = []
		taxonomy = []
		search_pointer = 0
		has_valid_aspects = False
		
		aspects = g_item.get("aspects", [])
		
		for aspect in aspects:
			target = aspect.get("aspect_target")
			category = aspect.get("category")
			sentiment = aspect.get("sentiment")
			
			# 1. Handle implicit aspects (NULL targets) by adding it to taxonomy list
			if not target or target == "NULL":
				has_valid_aspects = True
				taxonomy.append([category, sentiment])
				continue
			
			# 2. Handle explicit aspects (non-NULL targets)
			start = comment_text.find(target, search_pointer)
				
			if start != -1:
				has_valid_aspects = True
				end = start + len(target)
				search_pointer = end
				original_span = comment_text[start:end]
				
				# Generate a unique ID for the pair of category and sentiment annotations
				pair_id = generate_random_id()
				
				# Add the category annotation
				results.append({
					"value": {
						"start": start,
						"end": end,
						"text": original_span,
						"labels": [category]
					},
					"id": pair_id,
					"from_name": "categories",
					"to_name": "comment",
					"type": "labels",
					"origin": "manual"
				})
				
				# Add the sentiment annotation (linked to the same ID)
				results.append({
					"value": {
						"start": start,
						"end": end,
						"text": original_span,
						"choices": [sentiment]
					},
					"id": pair_id,
					"from_name": "sentiment",
					"to_name": "comment",
					"type": "choices",
					"origin": "manual"
				})

		# 3. Add 'review_status' annotation based on the presence of valid aspects ("DA"/"NE")
		review_status = "DA" if has_valid_aspects else "NE"
		status_result = {
			"value": {
				"choices": [review_status]
			},
			"id": generate_random_id(),
			"from_name": "review_status",
			"to_name": "comment",
			"type": "choices",
			"origin": "manual"
		}

		# 4. Add taxonomy list to results
		results.append({
			"value": {
				"taxonomy": taxonomy
			},
			"id": generate_random_id(),
			"from_name": "implicit_aspects",
			"to_name": "comment",
			"type": "taxonomy",
			"origin": "manual"
		})
		
		# Put the review_status annotation at the beginning of the results list
		results.insert(0, status_result)
		
		# 5. Construct the final task structure for Label Studio
		task_structure = {
			"id": task_id,
			"annotations": [
				{
					"result": results,
					"was_cancelled": False,
					"ground_truth": False
				}
			],
			"data": original_data,
			"inner_id": task_id
		}
		
		labelstudio_tasks.append(task_structure)

	# Save the converted data to a JSON file
	with output_json.open("w", encoding="utf-8") as f:
		json.dump(labelstudio_tasks, f, ensure_ascii=False, indent=2)

	print(f"Successfully converted Gemini output to Label Studio format and saved to '{output_json}'.")

	return labelstudio_tasks


def load_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Convert Gemini model output to Label Studio format."
	)
	parser.add_argument(
		"--brand",
		type=str,
		required=True,
		help="Brand name (used for directory location)."
	)
	parser.add_argument(
		"--index",
		type=int,
		required=True,
		help="Index of the segment to process (used in file naming)."
	)
	return parser	


if __name__ == "__main__":
	parser = load_parser()
	args = parser.parse_args()

	dir = f"mobilnisvet_segment_{args.brand}"

	convert_gemini_to_labelstudio(
		gemini_json=absPath / dir / f"g_{args.index}.json",
		dataset_json=absPath / dir / f"{args.index}.json",
		output_json=absPath / dir / f"ls_{args.index}.json"
	)
