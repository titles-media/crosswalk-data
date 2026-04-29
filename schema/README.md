# Schema Overview

This document describes the structure and validation rules for the crosswalk CSV files.

## Works Schema

Works use a two-layer schema:

- **Core schema** (`works.yaml`) — fields common to all work types: internal ID, title, and year.
- **Type schema** (`works/<type>.yaml`) — external ID fields specific to a work type (e.g. `movies.yaml`).

Validation is performed by loading both layers. See `scripts/validate_works.py`.

### Core Fields (`works.yaml`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Internal stable identifier. Globally unique across all data files. |
| `title` | string | yes | Name of the work. |
| `year` | integer | yes | Year the work was released or created. |

### Movies (`works/movies.yaml`)

| Field | Source | Required | Pattern |
|-------|--------|----------|---------|
| `imdb_id` | [IMDb](https://www.imdb.com) | yes | `tt` followed by 7–9 digits |
| `letterboxd_id` | [Letterboxd](https://letterboxd.com) | yes | alphanumeric slug |
| `tmdb_id` | [The Movie Database](https://www.themoviedb.org) | yes | 1–8 digits |
| `wikidata_id` | [Wikidata](https://www.wikidata.org) | yes | `Q` followed by 1–10 digits |

All four fields are required. A film must have all four IDs to be included.

---

## Persons Schema

Persons use a single combined schema file (`persons.yaml`) containing both core fields and external source definitions under a `sources` key.

Validation is performed by loading this single file. See `scripts/validate_persons.py`.

### Core Fields (`persons.yaml`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Internal stable identifier. Globally unique across all data files. |
| `name_last` | string | yes | Family name as credited, or full name for mononyms. |
| `name_first` | string | no | Given name as credited (well-known or credited form, not necessarily legal name). Empty for mononyms. |
| `name_middle` | string | no | Middle name, included only when part of the person's credited identity (e.g. Paul Thomas Anderson, Michael B. Jordan). |
| `birth_year` | integer | yes | Four-digit birth year. |
| `birth_month` | integer | no | Birth month (1–12). |
| `birth_day` | integer | no | Birth day (1–31). |

### External Sources (`persons.yaml` — `sources` key)

| Field | Source | Required | Pattern |
|-------|--------|----------|---------|
| `imdb_id` | [IMDb](https://www.imdb.com) | no | `nm` followed by 7–10 digits |
| `wikidata_id` | [Wikidata](https://www.wikidata.org) | no | `Q` followed by 1–10 digits |
| `tmdb_id` | [The Movie Database](https://www.themoviedb.org) | no | 1–8 digits |

All external ID fields are optional. A person may be included without all sources resolved.

---

## Data Rules

- `id` must be globally unique across all rows in all data files (enforced by `scripts/validate_unique_ids.py`).
- External IDs must be unique within their column.
- Rows must be sorted by `id`.
- Missing values must be empty — do not use `NULL` or placeholder strings.
- No leading or trailing whitespace in any field.
- Files must be UTF-8 encoded with UNIX line endings (`\n`).

## Notes

- Internal IDs are deterministic but should be treated as opaque. Do not reconstruct them from field values.
- Once assigned, an `id` will not change. Stability takes priority over any deterministic scheme.
- The schema is intentionally stable. Column structure changes will only be made when strictly necessary to avoid disrupting downstream consumers.
- Column order is not guaranteed to be stable when new sources are added.
- Row order is guaranteed to be sorted by `id`. Row numbers must not be treated as stable references.
