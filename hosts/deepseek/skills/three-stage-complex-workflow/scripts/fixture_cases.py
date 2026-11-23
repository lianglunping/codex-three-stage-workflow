"""Read synthetic workflow test definitions or a caller-provided TSV."""
import csv
import json


def load_cases(path):
    with path.open(encoding="utf-8", newline="") as source:
        if path.suffix != ".json":
            reader = csv.DictReader(source, delimiter="\t")
            return reader.fieldnames, list(reader)
        rows = json.load(source)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise ValueError("expected a nonempty list of test case objects")
    columns = list(rows[0])
    if any(not isinstance(row, dict) or set(row) != set(columns) for row in rows):
        raise ValueError("inconsistent test case fields")
    return columns, rows
