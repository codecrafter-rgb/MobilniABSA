import re
import pandas as pd

from pathlib import Path
absPath = Path(__file__).resolve().parent

def drop_duplicates(input_csv: str, output_csv: str):
	df = pd.read_csv(input_csv)
	
	df_clean = df.drop_duplicates(subset=["comment"], keep="first")

	df_clean.to_csv(output_csv, index=False, encoding='utf-8-sig')
	print(f"Successfully stored {len(df_clean)} reviews in file {output_csv}")


if __name__ == "__main__":
	INPUT_FILE = str(absPath / "mobilnisvet_comments.csv")
	OUTPUT_FILE = str(absPath / "mobilnisvet_comments_clean.csv")

	drop_duplicates(INPUT_FILE, OUTPUT_FILE)
