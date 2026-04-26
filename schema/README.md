# Schema Overview

This document describes the structure and validation rules for the crosswalk CSV files.

The schema is split into two layers:

- **Core schema** (`works.yaml`) — fields common to all work types: internal ID, title, and year.
- **Type schema** (`works/<type>.yaml`) — external ID fields specific to a work type (e.g. `movies.yaml`).

Validation is performed by loading both layers and checking data against the combined rules. See `scripts/validate_works.py`.

## Core Schema (`works.yaml`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Internal stable identifier. Globally unique across all work types. |
| `title` | string | yes | Name of the work. |
| `year` | integer | yes | Year the work was released or created. |

## Type Schemas (`works/<type>.yaml`)

Each work type defines its own set of external ID fields. Each field entry supports:

| Property | Description |
|----------|-------------|
| `id_field` | Column name in the CSV |
| `name` | Human-readable source name |
| `required` | Whether the field must be present for an entry to be valid |
| `active` | Whether the field is currently validated |
| `stable` | Whether the ID is considered stable by the upstream source |
| `pattern` | Regex pattern the value must match |

### Movies (`works/movies.yaml`)

| Field | Source | Pattern |
|-------|--------|---------|
| `imdb_id` | [IMDb](https://www.imdb.com) | `tt` followed by 7–9 digits |
| `letterboxd_id` | [Letterboxd](https://letterboxd.com) | alphanumeric slug |
| `tmdb_id` | [The Movie Database](https://www.themoviedb.org) | 1–8 digits |
| `wikidata_id` | [Wikidata](https://www.wikidata.org) | `Q` followed by 1–10 digits |

All four fields are required. A film must have all four IDs to be included.

## Data Rules

- `id` must be globally unique across all rows and all work types.
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
