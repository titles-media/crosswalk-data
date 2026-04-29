#!/usr/bin/env python3
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"


def collect_ids(data_dir: Path) -> dict[str, list[str]]:
    """Return mapping of id → [file, ...] for all CSVs under data_dir."""
    seen = defaultdict(list)
    for csv_path in sorted(data_dir.rglob("*.csv")):
        rel = csv_path.relative_to(REPO_ROOT)
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "id" not in (reader.fieldnames or []):
                continue
            for row in reader:
                id_val = row.get("id", "").strip()
                if id_val:
                    seen[id_val].append(str(rel))
    return seen


def validate(data_dir: Path) -> bool:
    seen = collect_ids(data_dir)
    duplicates = {id_val: files for id_val, files in seen.items() if len(files) > 1}

    if duplicates:
        print(
            f"\nGlobal ID uniqueness check failed — {len(duplicates)} duplicate(s):\n"
        )
        for id_val, files in sorted(duplicates.items()):
            print(f"  {id_val}: {', '.join(files)}")
        return False

    print(
        f"Global ID uniqueness check passed ✅  ({len(seen)} unique IDs across {data_dir})"
    )
    return True


if __name__ == "__main__":
    if not validate(DATA_DIR):
        sys.exit(1)
