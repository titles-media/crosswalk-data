#!/usr/bin/env python3
import argparse
import csv
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from dump_wikidata_id import get_film_data  # noqa: E402
from generate_missing_ids import process_csv  # noqa: E402
from sort_by_col import sort_csv_by_id  # noqa: E402
from validate_works import validate_csv  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
MOVIES_CSV = REPO_ROOT / "data/works/movies.csv"
CORE_SCHEMA = REPO_ROOT / "schema/works.yaml"
TYPED_SCHEMA = REPO_ROOT / "schema/works/movies.yaml"
HASH_FIELDS = ["title", "year"]
DIGEST_BYTES = 5


def load_fieldnames():
    with open(CORE_SCHEMA) as f:
        core = yaml.safe_load(f)["fields"]
    with open(TYPED_SCHEMA) as f:
        typed = yaml.safe_load(f)["fields"]
    return list(core.keys()) + [s["id_field"] for s in typed]


def find_existing(csv_path, film):
    """Return the existing row dict if a match is found, else None."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("wikidata_id") == film.wikidata_id:
                return row
            if film.imdb_id and row.get("imdb_id") == film.imdb_id:
                return row
    return None


def remove_row(csv_path, row_to_remove):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if r["id"] != row_to_remove["id"]]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_row(csv_path, film, existing_id=""):
    schema_fieldnames = load_fieldnames()
    with open(csv_path, newline="", encoding="utf-8") as f:
        fieldnames = csv.DictReader(f).fieldnames or schema_fieldnames
    write_header = csv_path.stat().st_size == 0

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow({**film.__dict__, "id": existing_id})


def main():
    parser = argparse.ArgumentParser(
        description="Add one or more films to movies.csv from Wikidata."
    )
    parser.add_argument(
        "provided_ids", nargs="*", help="Wikidata (Q…) or IMDb (tt…) ID(s)"
    )
    parser.add_argument(
        "--from-file",
        metavar="FILE",
        help="File of IDs to add, one per line (combined with any positional IDs)",
    )
    parser.add_argument(
        "--ignore-existing",
        action="store_true",
        help="Silently skip entries that already exist",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing entries with freshly fetched data, preserving their IDs",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between Wikidata requests (default: 1.0)",
    )
    args = parser.parse_args()

    ids_from_file = []
    if args.from_file:
        with open(args.from_file) as f:
            ids_from_file = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]

    all_ids = (args.provided_ids or []) + ids_from_file
    if not all_ids:
        parser.error("provide at least one ID as an argument or via --from-file")

    added, skipped, failed = [], [], []
    total = len(all_ids)

    for i, provided_id in enumerate(all_ids):
        print(f"[{i + 1}/{total}] Fetching {provided_id}...")
        film = get_film_data(provided_id)

        if not film:
            print("  Error: could not fetch data", file=sys.stderr)
            failed.append(provided_id)
        else:
            print(f"  Found: {film.title} ({film.year})")
            existing = find_existing(MOVIES_CSV, film)
            if existing:
                if args.force:
                    print(f"  Replacing existing entry (id={existing['id']})")
                    remove_row(MOVIES_CSV, existing)
                    append_row(MOVIES_CSV, film, existing_id=existing["id"])
                    added.append(provided_id)
                elif args.ignore_existing:
                    print(f"  Skipping: already exists (id={existing['id']})")
                    skipped.append(provided_id)
                else:
                    print(
                        f"  Error: already exists (id={existing['id']})",
                        file=sys.stderr,
                    )
                    failed.append(provided_id)
            else:
                append_row(MOVIES_CSV, film)
                added.append(provided_id)

        if i < total - 1 and args.delay > 0:
            time.sleep(args.delay)

    print(f"\nDone: {len(added)} added, {len(skipped)} skipped, {len(failed)} failed.")

    if failed and not added:
        sys.exit(1)

    if added:
        process_csv(
            str(MOVIES_CSV),
            id_field="id",
            hash_fields=HASH_FIELDS,
            digest_bytes=DIGEST_BYTES,
        )
        sort_csv_by_id(str(MOVIES_CSV), field="id")
        validate_csv(str(MOVIES_CSV), str(CORE_SCHEMA), str(TYPED_SCHEMA))


if __name__ == "__main__":
    main()
