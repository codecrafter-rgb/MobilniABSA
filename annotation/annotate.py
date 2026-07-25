import csv
import json
import time
from openai import OpenAI
import sys

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",#"https://openrouter.ai/api/v1"
    api_key=""
)

MODEL = "gemini-3.1-flash-lite"#"openrouter/free"


SYSTEM_PROMPT = """
You are an expert annotator for Aspect-Based Sentiment Analysis (ABSA).

Determine whether the text is a genuine mobile phone review.

If it is NOT a review (question, advice request, discussion, spam, advertisement, or does not express an opinion), return:

{
  "is_review": false
}

Otherwise, return:

{
  "is_review": true,
  "annotations": [
    {
      "aspect_category": "...",
      "aspect_text": "...",
      "opinion": "...",
      "sentiment": "positive|negative|neutral"
    }
  ]
}

Use ONLY these aspect categories:

- Baterija
- Kamera
- Ekran
- Memorija
- Zvučnici
- Izgled
- Softver
- Cena
- Opšta

Opšta = overall opinion about the phone that does not clearly belong to another category.

Rules:
- Extract every mentioned aspect.
- aspect_category must be one of the categories above.
- aspect_text is the exact aspect phrase from the review.
- opinion is the exact opinion phrase from the review.
- sentiment must be positive, negative, or neutral.
- Return ONLY valid JSON.
"""

INPUT = "comments.csv"
OUTPUT = "absa_annotations.jsonl"


start_from_block = 0
block_size = 50

if len(sys.argv) > 1:
    print(f"First argument: {sys.argv[1]}")
    start_from_block = int(sys.argv[1])
    
    
block_data = []


with open(INPUT, newline="", encoding="utf-8-sig") as infile:

    reader = csv.DictReader(infile)

    fieldnames = [
        #"phone_name",
        #"url",
        #"author",
        #"date",
        #"comment",
        #"is_review",
        #"aspect",
        #"opinion",
        #"sentiment",
        "i",
        "json"
    ]



    for i, row in enumerate(reader, start=0):
    
    
        if(i < (start_from_block-1)*block_size):
            continue
            
        time.sleep(6)# avoid rate limits
        
        print(f"Processing row {i}")

        try:

            response = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": row["comment"],
                    },
                ],
            )

            text = response.choices[0].message.content.strip()
            
            print(text)

            # Remove Markdown fences if present
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1])

            result = json.loads(text)

        except Exception as e:
            print("Error:", e)
            continue
            
        json_output = json.dumps(result, ensure_ascii=False, separators=(',',':'))

        #annotations = result.get("annotations", [])
        block_data.append({"i":i, "json":json_output})


        if((i+1) % block_size == 0):
            block_number = (i+1) // block_size
            file = open(f"annotated_{block_number}.jsonl", "w", newline="", encoding="utf-8")
            
            print("Writing block number "+str(block_number)+" to file")
            
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
    
            for row in block_data:
            
                writer.writerow({
                        "i":row["i"],
                        "json":row["json"]
        
                })
            
            
            file.flush()
            file.close()
            
            block_data = []
        
