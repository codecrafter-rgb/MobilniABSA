import csv
import glob
import os
import re
import sys

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <base_name>")
    print("Example: python merge.py comments")
    sys.exit(1)

base = sys.argv[1]

files = sorted(
    glob.glob(f"{base}_*.csv"),
    key=lambda f: int(re.search(r"_(\d+)\.csv$", f).group(1))
)

if not files:
    print("No matching files found.")
    sys.exit(1)

with open(f"{base}.csv", "w", newline="", encoding="utf-8-sig") as outfile:
    writer = csv.writer(outfile)

    first = True

    for file in files:
        print(f"Merging {file}")

        with open(file, newline="", encoding="utf-8-sig") as infile:
            reader = csv.reader(infile)

            if first:
                writer.writerows(reader)
                first = False
            else:
                next(reader, None)  # Skip header
                writer.writerows(reader)

print(f"Created {base}.csv")