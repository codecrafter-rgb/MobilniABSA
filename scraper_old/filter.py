import csv
import sys

if len(sys.argv) != 4:
    print(f"Usage: python {sys.argv[0]} input.csv output.csv max_length")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]
max_length = int(sys.argv[3])

with open(input_file, newline="", encoding="utf-8-sig") as infile, \
     open(output_file, "w", newline="", encoding="utf-8-sig") as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    # Copy header
    header = next(reader)
    writer.writerow(header)

    kept = 0
    removed = 0

    for row in reader:
        if len(row[4].strip()) <= max_length and "?" not in row[4].strip():   # comment column
            writer.writerow(row)
            kept += 1
        else:
            removed += 1

print(f"Kept {kept} rows")
print(f"Removed {removed} rows")