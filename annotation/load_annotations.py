from collections import defaultdict
import json
import sys
from typing import Any

from pathlib import Path
absPath = Path(__file__).resolve().parent
sys.path.insert(0, str(absPath.parent))

from common.enums import Category, Polarity

FILE_PATHS = [
	"at/raw.json",
	"jb/raw.json",
	"lr/raw.json",
	"nb/raw.json",
	"zg/raw.json"
]
CALIBRATION_PATH = absPath / "../calibration/adjudicated_calibration_final.json"


def aggregate_polarity(polarities: list[str]) -> Polarity | None:
	if Polarity.CONFLICT in polarities or \
	   Polarity.POSITIVE in polarities and Polarity.NEGATIVE in polarities:
		return Polarity.CONFLICT
	if Polarity.POSITIVE in polarities:
		return Polarity.POSITIVE
	if Polarity.NEGATIVE in polarities:
		return Polarity.NEGATIVE
	if Polarity.NEUTRAL in polarities:
		return Polarity.NEUTRAL
	return None


def get_aspect_categories(aspect_terms: list[dict]):
	annotation_map_to_category = {category: [] for category in Category}
	for aspect_term in aspect_terms:
		annotation_map_to_category[aspect_term["category"]].append(aspect_term["polarity"])
	aspect_categories = []
	for category, polarities in annotation_map_to_category.items():
		polarity = aggregate_polarity(polarities)
		if not polarity:
			continue
		label = {
			"category": category,
			"polarity": polarity
		}
		aspect_categories.append(label)
	return aspect_categories


def parse_records(records: list[Any], folder_path: Path, file_name: str) -> tuple[int, list[Any]]:
	reviews_cnt = 0
	all_records = []
	for record in records:
		annotations = record.get("annotations", [])
		if len(annotations) < 1:
			continue
		annotation = annotations[0]
		results = annotation.get("result", [])
		annotation_map_to_id: dict[str, dict] = defaultdict(dict)
		review_status = None

		for result in results:
			from_name = result.get("from_name")
			value = result.get("value", {})
			res_id = result.get("id")
			
			if from_name == "review_status":
				review_status = value.get("choices", [None])[0]
			elif from_name == "categories":
				label = {
					"fr": value.get("start"),
					"to": value.get("end"),
					"trg": value.get("text"),
					"category": value.get("labels", [None])[0]
				}
				annotation_map_to_id[res_id].update(label)
			elif from_name == "sentiment":
				label = {
					"fr": value.get("start"),
					"to": value.get("end"),
					"trg": value.get("text"),
					"polarity": value.get("choices", [None])[0]
				}
				annotation_map_to_id[res_id].update(label)
			elif from_name == "implicit_aspects":
				taxonomy = value.get("taxonomy", [])
				for index, tax in enumerate(taxonomy):
					label = {
						"fr": -1,
						"to": -1,
						"trg": None,
						"category": tax[0],
						"polarity": tax[1]
					}
					tax_id = f"{res_id}_{index}"
					annotation_map_to_id[tax_id].update(label)
		if review_status == "DA":
			reviews_cnt += 1
		aspect_terms = list(annotation_map_to_id.values()) if review_status == "DA" else []
		aspect_categories = get_aspect_categories(aspect_terms) if review_status == "DA" else []
		flat_record = {
			"phone": record.get("data", {}).get("phone"),
			"comment": record.get("data", {}).get("comment"),
			"review_status": review_status,
			"aspect_terms": aspect_terms,
			"aspect_categories": aspect_categories
		}
		all_records.append(flat_record)

	print(f"Number of reviews: {reviews_cnt}/{len(all_records)}")

	output_path = folder_path / f"parsed_{file_name}"
	with output_path.open("w", encoding="utf-8-sig") as file:
		json.dump(all_records, file, indent=4, ensure_ascii=False)
	print(f"Successfully saved {folder_path.name}/{output_path.name}!")

	return reviews_cnt, all_records


def load_annotation_file(file_path: Path) -> tuple[int, list[Any]]:
	if not file_path.exists():
		print(f"Error! File doesn't exist on location: {file_path}")
		return 0, []

	reviews_cnt, parsed_records = 0, []
	with file_path.open("r", encoding="utf-8-sig") as file:
		try:
			records = json.load(file)
			if not isinstance(records, list):
				records = [records]
			
			print(f"Successfully loaded! Number of elements: {len(records)}")
			reviews_cnt, parsed_records = parse_records(records, file_path.parent, file_path.name)
			
		except json.JSONDecodeError:
			print("Error! File is empty or has invalid format.")
	
	return reviews_cnt, parsed_records


def main():
	total_reviews_cnt, all_records = 0, []

	for file_path in FILE_PATHS:
		print(f"{file_path}: ", end="")
		reviews_cnt, records = load_annotation_file(absPath / file_path)
		total_reviews_cnt += reviews_cnt
		all_records.extend(records)

	with CALIBRATION_PATH.open("r", encoding="utf-8-sig") as file:
		calibration_records = json.load(file)
	if not isinstance(calibration_records, list) or len(calibration_records) != 800:
		raise ValueError("Adjudicated calibration set must contain exactly 800 records")
	for index, record in enumerate(calibration_records):
		if record.get("review_status") not in {"DA", "NE"}:
			raise ValueError(f"Invalid calibration review_status at index {index}")
		if not isinstance(record.get("phone"), str) or not isinstance(record.get("comment"), str):
			raise ValueError(f"Invalid calibration metadata at index {index}")
		if not isinstance(record.get("aspect_terms"), list) or not isinstance(record.get("aspect_categories"), list):
			raise ValueError(f"Invalid calibration annotations at index {index}")
	print(f"{CALIBRATION_PATH.name}: Number of reviews: {sum(r['review_status'] == 'DA' for r in calibration_records)}/{len(calibration_records)}")
	total_reviews_cnt += sum(record["review_status"] == "DA" for record in calibration_records)
	all_records.extend(calibration_records)

	output_path = absPath / "annotations.json"
	with output_path.open("w", encoding="utf-8-sig") as file:
		json.dump(all_records, file, indent=4, ensure_ascii=False)
	print(f"Total number of reviews: {total_reviews_cnt}/{len(all_records)}")
	print(f"Successfully saved annotations to {output_path.name}!")


if __name__ == "__main__":
	main()
