import argparse
import json

from pathlib import Path
absPath = Path(__file__).resolve().parent

FILE_LIST = [
	"huawei.json", "honor.json", "apple.json", "xiaomi.json", "samsung.json"
]


def merge_json_files(folder_path: Path):
	merged_json = []

	for file in FILE_LIST:
		file_path = folder_path / file

		if not file_path.exists():
			print(f"Error! File doesn't exist on location: {file_path}")
			continue

		with file_path.open("r", encoding="utf-8") as file:
			merged_json.extend(json.load(file))

	if not merged_json:
		print(f"Nothing to merge for {folder_path.name}")
		return

	output_path = folder_path / "raw.json"
	with output_path.open("w", encoding="utf-8") as file:
		json.dump(merged_json, file, indent=4, ensure_ascii=False)

	print(f"Successfully merged json files from {folder_path.name} folder! Number of elements: {len(merged_json)}")


def load_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Merge ['apple', 'honor', 'huawei', 'samsung', 'xiaomi'] json files from specified folder."
	)
	parser.add_argument(
		"--folder",
		type=str,
		required=True,
		help="Folder name where json files are located."
	)
	return parser	


if __name__ == "__main__":
	parser = load_parser()
	args = parser.parse_args()

	merge_json_files(absPath / args.folder)
