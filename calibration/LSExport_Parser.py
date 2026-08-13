import json
import os
import sys

if (len(sys.argv) < 2):
    print("Input file not specified")
    sys.exit()

if not os.path.exists(sys.argv[1]):
    print("Can't find input file!")
    sys.exit()

filename = ""

with open(sys.argv[1], 'r', encoding='utf-8') as file:
    data = json.load(file)
    filename = os.path.splitext(sys.argv[1])[0]

parsed_data = []

for data_row in data:

    parsed_dara_row = {
        "url": data_row["url"],
        "brand": data_row["brand"],
        "phone": data_row["phone"],
        "author": data_row["author"],
        "date": data_row["date"],
        "comment": data_row["comment"],
        "complexity_score": data_row["complexity_score"],
        "reasons": data_row["reasons"],
        "id": data_row["id"],
        "review_status": data_row["review_status"]
    }

    if (data_row["review_status"] == "NE"):
        continue


    aspects = []

    if ("categories" in data_row and "sentiment" in data_row):

        #Indeksi za aspekte u listi "categories" i sentimente u listi "sentiment" se poklapaju,
        #pa te liste mogu da se pridruze na sledeci nacin

        aspectCategoriyList = data_row["categories"]
        sentimentList = data_row["sentiment"]

        for i in range(len(aspectCategoriyList)):
            aspect = {
                        "start": aspectCategoriyList[i]["start"],
                        "end": aspectCategoriyList[i]["end"],
                        "text": aspectCategoriyList[i]["text"],
                        "category": aspectCategoriyList[i]["labels"][0],
                        "sentiment": sentimentList[i]
                    }

            aspects.append(aspect)

    if ("implicit_aspects" in data_row and "taxonomy" in data_row["implicit_aspects"][0]):
        list_of_implicit_aspects = data_row["implicit_aspects"][0]["taxonomy"]

        for implicit_aspect in list_of_implicit_aspects:
            aspect = {
                "start": -1,
                "end": -1,
                "text": None,
                "category": implicit_aspect[0],
                "sentiment": implicit_aspect[1]
            }

            aspects.append(aspect)
    

    parsed_dara_row["aspects"] = aspects

    parsed_data.append(parsed_dara_row)

print("Konacan broj recenzija: " + str(len(parsed_data)))

with open(filename + "_parsed.json", "w", encoding="utf-8") as f:
    json.dump(parsed_data, f, indent=4, ensure_ascii=False)

