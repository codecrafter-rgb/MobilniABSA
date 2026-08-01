import re
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
	Analyse comment and calculate complexity score and tracks reasongs.
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
		
	# 2. Contrast Conjuction (Indicates mixed sentiment)
	contrast_conjuction = [
		r"\bali\b", 
		r"\bmeđutim\b", 
		r"\bdok\b", 
		r"\biako\b", 
		r"\bal\b", 
		r"\bipak\b"
	]
	complexity_score += check_condition(comment_lower, contrast_conjuction, 3, reasons, "Suprotni veznici")

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


def candidate_select(input_csv: str, output_csv: str, candidate_num: int = 150):
	"""
		- Loads csv file, 
		- Rangs comments based on complexity,
		- Stores top 'candidate_num' comments,
		- Returns sorted by complexity score DataFrame
	"""
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
	input_csv: str, 
	output_candidates_csv: str, 
	output_csv: str, 
	complex_cnt: int = 150, 
	total_number: int = 600
):
	"""
	Takes 'complex_cnt' of top complex comments and randomly picks rest.
	"""
	df_sorted = candidate_select(input_csv, output_candidates_csv, complex_cnt)
	df_complex = df_sorted.head(complex_cnt)
	df_rest = df_sorted.iloc[complex_cnt:]
	df_random = df_rest.sample(n=total_number - complex_cnt, random_state=390)

	result = pd.concat([df_complex, df_random]) \
			.sample(frac=1, random_state=390) \
			.reset_index(drop=True)
	result.to_csv(output_csv, index=False, encoding="utf-8-sig")
	print(f"Successfully stored {len(result)} comments in file: {output_csv}")


if __name__ == "__main__":
	INPUT_FILE = str(absPath / "../mobilnisvet_comments_clean.csv")
	OUTPUT_CANDIDATES_FILE = str(absPath / "calibration_candidates.csv")
	OUTPUT_FILE = str(absPath / "calibration_set.csv")
	
	generate_calibration_set(
		input_csv=INPUT_FILE,
		output_candidates_csv=OUTPUT_CANDIDATES_FILE,
		output_csv=OUTPUT_FILE,
		complex_cnt=250,
		total_number=800
	)
