#!/usr/bin/env python3
import argparse
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from dump_wikidata_id import (  # noqa: E402
    USER_AGENT,
    iter_claims,
    parse_date,
    parse_labels,
    query_sparql_id,
)
from generate_missing_ids import process_csv  # noqa: E402
from sort_by_col import sort_csv_by_id  # noqa: E402
from validate_persons import validate_csv  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
PERSONS_CSV = REPO_ROOT / "data/persons.csv"
SCHEMA = REPO_ROOT / "schema/persons.yaml"
HASH_FIELDS = [
    "name_last",
    "name_first",
    "name_middle",
    "birth_year",
    "birth_month",
    "birth_day",
]
DIGEST_BYTES = 5


@dataclass
class Person:
    id: Optional[str]
    name_last: str
    name_first: str
    name_middle: str
    birth_year: str
    birth_month: str
    birth_day: str
    imdb_id: str
    wikidata_id: str
    tmdb_id: str


def load_fieldnames():
    with open(SCHEMA) as f:
        schema = yaml.safe_load(f)
    core_fields = list(schema["fields"].keys())
    source_fields = [s["id_field"] for s in schema.get("sources", [])]
    return core_fields + source_fields


def get_wikidata_id(provided_id: str) -> Optional[str]:
    if provided_id.startswith("nm"):
        return query_sparql_id("P345", provided_id)
    if provided_id.startswith("Q"):
        return provided_id
    return "Q" + provided_id


def parse_item_claim_qids(entity: dict, property_id: str) -> list[str]:
    """Return QIDs for wikibase-item claims, preferred rank first."""
    preferred, normal = [], []
    for claim in entity.get("claims", {}).get(property_id, []):
        if claim.get("rank") == "deprecated":
            continue
        try:
            value = claim["mainsnak"]["datavalue"]["value"]
            if isinstance(value, dict) and "id" in value:
                bucket = preferred if claim.get("rank") == "preferred" else normal
                bucket.append(value["id"])
        except (KeyError, TypeError):
            continue
    return preferred + normal


def fetch_entity_labels(qids: list[str]) -> dict[str, str]:
    if not qids:
        return {}
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": "|".join(qids),
        "props": "labels",
        "languages": "en",
        "format": "json",
    }
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    result = {}
    for qid, ent in response.json().get("entities", {}).items():
        label = ent.get("labels", {}).get("en", {}).get("value")
        if label:
            result[qid] = label
    return result


def parse_given_names_from_label(
    label: str, family_names: list[str]
) -> tuple[str, str]:
    """Strip family name tokens from the entity label to get well-known given/middle names."""
    family_tokens = {t for name in family_names for t in name.split()}
    given_tokens = [t for t in label.split() if t not in family_tokens]
    name_first = given_tokens[0] if given_tokens else ""
    name_middle = " ".join(given_tokens[1:]) if len(given_tokens) > 1 else ""
    return name_first, name_middle


def parse_birth_date(entity: dict) -> tuple:
    for claim in entity.get("claims", {}).get("P569", []):
        if claim.get("rank") == "deprecated":
            continue
        try:
            value = claim["mainsnak"]["datavalue"]["value"]
            precision = value["precision"]
            if precision < 9:
                continue
            dt = parse_date(value["time"])
            return (
                dt.year,
                dt.month if precision >= 10 else "",
                dt.day if precision >= 11 else "",
            )
        except (KeyError, TypeError):
            continue
    return "", "", ""


def get_person_data(provided_id: str) -> Optional[Person]:
    wikidata_id = get_wikidata_id(provided_id)
    if not wikidata_id:
        return None

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        entity = response.json()["entities"][wikidata_id]
    except (requests.exceptions.RequestException, KeyError, TypeError) as e:
        print(f"Error fetching {wikidata_id}: {e}")
        return None

    try:
        family_qids = parse_item_claim_qids(entity, "P734")
        given_qids = parse_item_claim_qids(entity, "P735")
        labels = fetch_entity_labels(family_qids + given_qids)

        def dedup(lst):
            seen = set()
            return [x for x in lst if not (x in seen or seen.add(x))]

        family_names = dedup([labels[q] for q in family_qids if q in labels])
        given_names = dedup([labels[q] for q in given_qids if q in labels])

        name_last = " ".join(family_names)
        label = parse_labels(entity)
        if label and family_names:
            name_first, name_middle = parse_given_names_from_label(label, family_names)
        else:
            name_first = given_names[0] if given_names else ""
            name_middle = " ".join(given_names[1:]) if len(given_names) > 1 else ""

        birth_year, birth_month, birth_day = parse_birth_date(entity)

        imdb_id = ""
        for claim in iter_claims(entity, "P345", skip_deprecated=True):
            val = claim.get("value", "")
            if isinstance(val, str) and val.startswith("nm"):
                imdb_id = val
                break

        tmdb_id = ""
        for claim in iter_claims(entity, "P4985", skip_deprecated=True):
            tmdb_id = claim.get("value", "")
            break

        return Person(
            id=None,
            name_last=name_last,
            name_first=name_first,
            name_middle=name_middle,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            imdb_id=imdb_id,
            wikidata_id=wikidata_id,
            tmdb_id=tmdb_id,
        )
    except Exception as e:
        print(f"Error parsing entity {wikidata_id}: {e}")
        return None


def find_existing(csv_path: Path, person: Person) -> Optional[dict]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("wikidata_id") == person.wikidata_id:
                return row
            if person.imdb_id and row.get("imdb_id") == person.imdb_id:
                return row
    return None


def remove_row(csv_path: Path, row_to_remove: dict):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if r["id"] != row_to_remove["id"]]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_row(csv_path: Path, person: Person, existing_id: str = ""):
    fieldnames = load_fieldnames()
    with open(csv_path, newline="", encoding="utf-8") as f:
        fieldnames = csv.DictReader(f).fieldnames or fieldnames
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writerow({**person.__dict__, "id": existing_id})


def main():
    parser = argparse.ArgumentParser(
        description="Add one or more persons to persons.csv from Wikidata."
    )
    parser.add_argument(
        "provided_ids", nargs="*", help="Wikidata (Q…) or IMDb (nm…) ID(s)"
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
        person = get_person_data(provided_id)

        if not person:
            print("  Error: could not fetch data", file=sys.stderr)
            failed.append(provided_id)
        else:
            print(
                f"  Found: {person.name_first} {person.name_last} ({person.birth_year})"
            )
            existing = find_existing(PERSONS_CSV, person)
            if existing:
                if args.force:
                    print(f"  Replacing existing entry (id={existing['id']})")
                    remove_row(PERSONS_CSV, existing)
                    append_row(PERSONS_CSV, person, existing_id=existing["id"])
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
                append_row(PERSONS_CSV, person)
                added.append(provided_id)

        if i < total - 1 and args.delay > 0:
            time.sleep(args.delay)

    print(f"\nDone: {len(added)} added, {len(skipped)} skipped, {len(failed)} failed.")

    if failed and not added:
        sys.exit(1)

    if added:
        process_csv(
            str(PERSONS_CSV),
            id_field="id",
            hash_fields=HASH_FIELDS,
            digest_bytes=DIGEST_BYTES,
            prefix="person",
        )
        sort_csv_by_id(str(PERSONS_CSV), field="id")
        validate_csv(str(PERSONS_CSV), str(SCHEMA))


if __name__ == "__main__":
    main()
