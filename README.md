# crosswalk-data

Crosswalk data for media works maintained by [titles.media](https://titles.media). Maps stable internal IDs to external identifiers across IMDb, TMDB, Letterboxd, and Wikidata.

For richer formats (JSON, Parquet, additional metadata) and tooling, see [titles-media/crosswalk](https://github.com/titles-media/crosswalk), which is built from this data.

## Overview

This repo is the authoritative source of stable internal IDs for media works. It is intentionally minimal — plain CSV files containing identifiers only, with no derived data or enrichment beyond what is needed to uniquely identify a work across external databases.

### Philosophy

- **Source of truth**: Strict, flat CSV files — one file per work type.
- **Identifiers only**: Internal IDs and external IDs only. No ratings, genres, cast, or other dynamic metadata.
- **Stable IDs**: Once assigned, an internal ID will never change. Stability takes priority over any deterministic scheme.
- **Full coverage required**: A work is only included when all required external IDs can be resolved. Partial entries are not committed.
- **Strict validation**: Schema-enforced patterns, uniqueness, and sort order are validated on every change.

### Why This Exists

Film and media data is scattered across incompatible systems — IMDb, TMDB, Letterboxd, and Wikidata each use their own IDs with no standard crosswalk between them. This repo provides a clean, open, stable bridge across those sources.

### Who This Is For

- **Data engineers** building film data pipelines that span multiple sources.
- **Developers** building apps that need consistent, stable identifiers for films.
- **Researchers** working with film data across multiple databases.

### Who This Isn't For

- If you need this data in a more flexible format (JSON, Parquet, etc.) or with richer metadata, use [titles-media/crosswalk](https://github.com/titles-media/crosswalk) — it is built from this data and is the better starting point for most use cases.
- If you need exhaustive historical coverage, be aware that backfill is ongoing and incomplete.

## Data

| File | Description |
|------|-------------|
| `data/works/movies.csv` | Feature films |

Each row contains an internal `id`, `title`, `year`, and external IDs. See [schema/README.md](schema/README.md) for full schema documentation and validation rules.


| Field | Source |
|-------|--------|
| `imdb_id` | [IMDb](https://www.imdb.com) |
| `tmdb_id` | [The Movie Database](https://www.themoviedb.org) |
| `letterboxd_id` | [Letterboxd](https://letterboxd.com) |
| `wikidata_id` | [Wikidata](https://www.wikidata.org) |

### Internal IDs

Internal IDs use a modified Base32 alphabet (`0123456789bcdefghjklmnpqrstvwxyz`). They are opaque and stable — treat them as permanent identifiers and do not attempt to reconstruct them from field values.

### Coverage Priority

Data is added in roughly this order:

1. **Current theatrical releases** — films in wide release
2. **Recent years by box office** — top-grossing films from the last few years
3. **Awards** — Oscar nominees and winners, working backwards
4. **IMDb most popular** — broad cultural relevance
5. **Historical backfill** — year by year from recent to earliest

## Usage

If you want to consume this data, we strongly recommend [titles-media/crosswalk](https://github.com/titles-media/crosswalk) instead — it contains the same core data but is available in JSON, Parquet, and other formats that are much easier to work with in most contexts.

If you specifically need the raw CSV source, data files can be used directly. Pin to a specific commit for stability.

## Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

**Add a film** (by Wikidata or IMDb ID):
```bash
python scripts/add_movie.py Q12345
python scripts/add_movie.py tt12345678
# Multiple at once:
python scripts/add_movie.py Q1 Q2 Q3 --ignore-existing
```

**Validate data:**
```bash
python scripts/validate_works.py data/works/movies.csv
```

## Contributing

Pull requests are welcome.

**Likely to be accepted:**
- New films where all required external IDs can be resolved.
- Corrections to existing ID mappings.
- Tooling improvements or bug fixes to the scripts.

**Will be considered:**
- Additional ID sources where appropriate. Please open a discussion before doing any significant work — inclusion criteria is currently subjective.

**Likely to be rejected:**
- Schema changes — the schema is intentionally stable to protect downstream consumers.
- Partial entries missing required IDs.
- Metadata additions — this repo is intentionally minimal by design.

When in doubt, open an issue before submitting a PR.

## Attribution

This dataset references identifiers from the following third-party sources:

- **IMDb** — identifier data sourced from [IMDb](https://www.imdb.com).
- **The Movie Database (TMDB)** — identifier data sourced from [TMDB](https://www.themoviedb.org).
- **Letterboxd** — identifier data sourced from [Letterboxd](https://letterboxd.com).
- **Wikidata** — identifier data sourced from [Wikidata](https://www.wikidata.org), made available under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

## Trademark Notice

All product names, logos, and brands referenced in this repository are the property of their respective owners. Use of these names is purely for identification and attribution purposes and does not imply endorsement by or affiliation with any trademark holder.

## License

Scripts and tooling are licensed under the [MIT License](LICENSE).

Data in `data/` is licensed under the [Open Data Commons Attribution License (ODC-BY) 1.0](LICENSE-DATA).
