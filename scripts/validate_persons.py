#!/usr/bin/env python3
import csv
import sys
from collections import defaultdict

from validate_works import check_duplicate_ids, load_yaml, validate_field


def validate_csv(csv_path, schema_path, fail_fast=False):
    errors = []

    schema = load_yaml(schema_path)
    core_schema = schema["fields"]
    sources = schema.get("sources", [])

    seen_ids = defaultdict(set)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        prev_id = None
        for i, row in enumerate(reader, start=2):
            name_last = row.get("name_last", "")
            row_label = f"Row {i} ({name_last})" if name_last else f"Row {i}"

            if prev_id and row.get("id") < prev_id:
                errors.append(
                    f"{row_label}: Not sorted, ID '{row.get('id')}' comes after '{prev_id}'"
                )
                if fail_fast and errors:
                    print("\n".join(errors))
                    sys.exit(1)

            for field, rules in core_schema.items():
                value = row.get(field, "")
                errors.extend(validate_field(value, rules, field, row_label))
                if rules.get("unique", False):
                    errors.extend(
                        check_duplicate_ids(field, value, seen_ids[field], row_label)
                    )
                if fail_fast and errors:
                    print("\n".join(errors))
                    sys.exit(1)

            for s in sources:
                field = s["id_field"]
                value = row.get(field, "")
                errors.extend(validate_field(value, s, field, row_label))
                if s.get("unique", True):
                    errors.extend(
                        check_duplicate_ids(field, value, seen_ids[field], row_label)
                    )
                if fail_fast and errors:
                    print("\n".join(errors))
                    sys.exit(1)

            prev_id = row["id"]

    if errors:
        print(f"\nValidation failed with {len(errors)} errors:\n")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("Validation successful ✅")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate persons CSV against schema")
    parser.add_argument("csv", default="data/persons.csv")
    parser.add_argument("--schema", default="schema/persons.yaml")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first error")
    args = parser.parse_args()

    validate_csv(args.csv, args.schema, fail_fast=args.fail_fast)
