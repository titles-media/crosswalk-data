#!/usr/bin/env python3
import argparse
import sys
import time
from csv import DictWriter
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests

USER_AGENT = "PajaroLabs Bot/0.1 (nick@pajarolabs.com)"


@dataclass
class Film:
    id: Optional[str]
    title: str
    year: int
    date: datetime
    imdb_id: str
    letterboxd_id: str
    tmdb_id: str
    wikidata_id: str


def parse_date(dt_str: str) -> datetime:
    if dt_str.startswith("+"):
        dt_str = dt_str[1:]
    # workaround Z suffix for python < 3.11
    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")
    # workaround for lower precision dates
    # TODO do we want to do this?
    if "-00" in dt_str:
        dt_str = dt_str.replace("-00-", "-01-").replace("-00T", "-01T")
    return datetime.fromisoformat(dt_str)


def iter_claims(entity, property_id, skip_deprecated: bool) -> iter:
    claims = entity["claims"]
    if not claims:
        return
    if property_id not in claims:
        return
    for claim in claims[property_id]:
        if skip_deprecated and claim["rank"] == "deprecated":
            continue
        yield claim["mainsnak"]["datavalue"]


def parse_str_claim(entity, property_id, skip_deprecated: bool = True) -> Optional[str]:
    for claim in iter_claims(entity, property_id, skip_deprecated):
        return claim["value"]


def parse_dt_claim(
    entity, property_id, skip_deprecated: bool = True, min_precision: int = 11
) -> Optional[datetime]:
    for claim in iter_claims(entity, property_id, skip_deprecated):
        if claim["value"]["precision"] < min_precision:
            continue
        time = claim["value"]["time"]
        if time:
            return parse_date(time)


def parse_labels(entity, languages: list[str] = None) -> Optional[str]:
    if not languages:
        languages = ["en", "mul"]
    if not entity or "labels" not in entity:
        return
    labels = entity["labels"]
    for lang in languages:
        if lang in labels:
            return labels[lang]["value"]


def query_sparql_id(property: str, provided_id: str) -> Optional[str]:
    url = "https://query.wikidata.org/sparql"

    query = f"""
        SELECT distinct ?item ?itemLabel ?description WHERE {{
        ?item wdt:{property} "{provided_id}".
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
        }}
    """
    params = {"query": query, "format": "json"}
    headers = {"User-Agent": "PajaroLabs Bot/0.1 (nick@pajarolabs.com)"}

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    results = response.json()
    bindings = results["results"]["bindings"]
    if not bindings:
        print(f"No results for {property} -> {provided_id}")
        return None
    if len(bindings) != 1:
        print(f"Multiple results ({len(bindings)}) for {property} -> {provided_id}")
        return None

    for result in bindings:
        return result["item"]["value"].split("/")[-1]


def get_wikidata_id(provided_id: str) -> Optional[str]:
    if provided_id.startswith("tt"):
        # imdb
        return query_sparql_id("P345", provided_id)

    if provided_id.startswith("Q"):
        return provided_id
    return "Q" + provided_id


def get_film_data(provided_id) -> Film:
    """
    Retrieves structured data for a film from Wikidata.

    Args:
        provided_id (str): The provided_id of the film, imdb or wikidata (e.g., "Q158312", for "The Matrix").

    Returns:
        dict: A dictionary containing the film's title, year, IMDb ID, and TMDb ID,
              or None if the data could not be retrieved.
    """

    wikidata_id = get_wikidata_id(provided_id)
    if not wikidata_id:
        return

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"

    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()

        entity = data["entities"][wikidata_id]

        title = parse_labels(
            entity,
        )
        date = parse_dt_claim(entity, "P577", min_precision=9)  # minimum year precision

        film_data = Film(
            id=None,
            date=date,
            imdb_id=parse_str_claim(entity, "P345"),
            letterboxd_id=parse_str_claim(entity, "P6127"),
            tmdb_id=parse_str_claim(entity, "P4947"),
            wikidata_id=wikidata_id,
            year=date.year if date else "",
            title=title,
        )

        return film_data

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Wikidata: {e}")
        return None
    except (KeyError, TypeError) as e:
        print(f"Error parsing Wikidata response: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve film data from Wikidata.")
    parser.add_argument(
        "provided_ids", nargs="+", help="One or more Wikidata/imdb IDs of films."
    )
    parser.add_argument(
        "--write-header",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Write the header",
    )
    parser.add_argument(
        "-s",
        "--sleep",
        type=float,
        default=1.0,
        help="Time to sleep in seconds (default: 1.0)",
    )
    headers = "id,title,year,imdb_id,letterboxd_id,tmdb_id,wikidata_id".split(",")

    args = parser.parse_args()
    writer = DictWriter(sys.stdout, headers, extrasaction="ignore")
    if args.write_header:
        writer.writeheader()
    total = len(args.provided_ids)
    for i, provided_id in enumerate(args.provided_ids):
        film_data = get_film_data(provided_id)
        if film_data:
            # fields = [str(f) for f in [film_data.id or '', film_data.title, film_data.year, film_data.imdb_id or "", film_data.letterboxd_id or "",film_data.tmdb_id or "",film_data.wikidata_id or ""]]
            # print(";".join(fields))
            writer.writerow(film_data.__dict__)
        else:
            writer.writerow({"provided_id": provided_id})
        if i < total - 1 and args.sleep > 0:
            time.sleep(args.sleep)
