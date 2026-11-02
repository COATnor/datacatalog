# DataStore ingestion — upgrade plan

Status: implemented on branch `feat/datastore-ingest` (base 78b1bcb), verified
on the local test stack. This document describes what changed, how to deploy
it in production, and the known risks.

## Background

Today every tabular file the COAT portal receives (roughly 500+ `.csv` and
`.txt` resources across ~132 datasets, snapshot in `/tmp/opencode/prod_all.json`)
is stored as an opaque file: the portal serves the bytes, but the data cannot
be queried, filtered, charted or exposed through the API.

CKAN 2.12 solves this with the (legacy but still supported) **DataStore**
(`ckanext.datastore`, already shipped inside the portal image since 2.12.1) +
**DataPusher** (`ckanext.datapusher`, same image) or the standalone
`ckan/ckan-base-datapusher:0.0.21` container. This branch enables that stack:
each uploaded CSV/xlsx resource is parsed and imported into a Postgres table
that becomes queryable via `datastore_search`/`datastore_search_sql` and the
resource page table view.

The alternative considered, `ckanext-store` (the 2.12 SQLAlchemy-based
successor), is **not vendored** in the image and was not needed: the legacy
DataStore is maintained by the CKAN project, fully compatible, and required a
strictly smaller diff.

## What changed

| File | Change |
|---|---|
| `custom/coat-entrypoint.sh` | Enables `datastore datapusher` plugins; sets `ckan.datastore.write_url`/`read_url` to the main CKAN Postgres; sets `ckan.datapusher.url` + `ckan.datapusher.callback_url_base`; mints an API token at boot for auto-created `datapusher_bot` sysadmin (or uses `CKAN_DATAPUSHER_API_TOKEN` if provided). |
| `docker-compose.yml` | New `datapusher` service (`ckan/ckan-base-datapusher:0.0.21`, port 8800 inside the network) + env passthrough `CKAN_DATAPUSHER_URL/CALLBACK_URL/API_TOKEN`. |
| `template.env` | Three new (empty-by-default) DataStore/Datapusher vars with comments. |
| `scripts/ingest_existing_resources.py` | Backfill tool (see below). |
| `docs/datastore-ingestion-plan.md` | This document. |

Notes
- DataStore tables live in the same `ckan` Postgres database; no other
  database, user or migration is needed (the `ckan` role owns the database).
- DataPusher receives the API token in the job payload; it holds no secrets
  itself. `ckan.datapusher.api_token` is mandatory since CKAN 2.10 — hence
  the boot-time bot user.
- `ckan.datapusher.formats` keeps the upstream default (`csv xls xlsx tsv ods`
  …). Plain-`.txt` files are **not** auto-pushed (many COAT `.txt` files are
  not tabular, and delimiters vary); tab-separated `.txt` data can be
  ingested by the backfill tool instead (see Risks).
- The background `ckan-worker` service is not involved in DataPusher jobs
  (they are sent over HTTP to the datapusher container).

## Production deployment

Order matters only mildly; the whole sequence is idempotent.

1. Update the repo on the prod host (`docker compose` uses the image built
   from this branch — rebuild: `docker compose --profile prod build`).
2. Add the three `CKAN_DATAPUSHER_*` lines to the real `.env`
   (`template.env` documents them). Recommended for prod: pre-mint a token
   instead of the boot-time bot:
   ```
   docker compose --profile prod run --rm ckan-prod ckan user add datapusher_bot email=datapusher_bot@coat.no
   docker compose --profile prod run --rm ckan-prod ckan sysadmin add datapusher_bot
   docker compose --profile prod run --rm ckan-prod ckan user token add datapusher_bot   # copy printed JWT
   # then set CKAN_DATAPUSHER_API_TOKEN=<jwt> and
   #   CKAN_DATAPUSHER_CALLBACK_URL=https://data.coat.no/ in .env
   ```
   If you skip this, boot auto-creates the bot — acceptable, less auditable.
3. `docker compose --profile prod build && docker compose --profile prod up -d`
   (brings up `datapusher` and restart CKAN with the new plugins).
4. Sanity check (as any user):
   ```
   curl -s https://data.coat.no/api/3/action/datastore_search?resource_id=__none__ | head -c 200
   ```
   — should return a JSON error mentioning resource_id (proves datastore is
   live), not a 404.
5. Backfill (below).
6. Re-check the 5 datasets whose bounding boxes needed re-saving after the
   earlier spatial fix (unchanged by this upgrade, listed here to not lose
   track).

## Backfill

`scripts/ingest_existing_resources.py` (stdlib only; `python3` on the host or
anywhere) walks catalog resources and calls `datastore_create` with
`file_url` — this loads data server-side without the DataPusher round-trip
and works for both stored uploads and external links. It skips resources that
already have a table (idempotent, safe to re-run), and never modifies
metadata.

```
# trial run (nothing written):
python3 scripts/ingest_existing_resources.py \
    --url https://data.coat.no --token <TOKEN> --dry-run

# limit to two datasets first:
python3 scripts/ingest_existing_resources.py \
    --url https://data.coat.no --token <TOKEN> --datasets <name1>,<name2>

# full run (log to file; moderate — imports serially):
python3 scripts/ingest_existing_resources.py \
    --url https://data.coat.no --token <TOKEN> 2>&1 | tee backfill.log
```

Verification: pick a few resources and confirm row counts —
`datastore_search?resource_id=<id>&limit=0` returns `total`; compare against
`wc -l` of the source file. Spot-check one private dataset too: anonymous
`datastore_search` on its resources must return 403 (see next section).

Duration estimate: server-side import at ~250 rows/insert chunk; most COAT
files are small-moderate. Expect minutes-per-100-resources, hours worst case
for the full catalog; the script logs per-resource progress and resumes
cleanly.

## Risks & open questions

- **Embargo/private datasets**: verified on the test stack — anonymous
  `datastore_search` on a private dataset's resource returns 403 because
  `datastore_auth` chains through `resource_show`. Because the embargo logic
  is custom to this portal, keep the 403 check in the acceptance criteria of
  any future datastore change (regression test exists on this branch? — the
  verify worker's report records the live evidence; treat this as a manual
  acceptance test until automatable).
- **`.txt`-but-actually-tabular**: the bulk of COAT tabular data lives in
  `.txt` files where comma/tab/space delimiters vary per dataset. The
  backfill treats txt as tabular, but `datastore_create`'s parser may guess
  wrong on files with unusual delimiters → check `total` counts vs file line
  counts on a sample; consider `--include-formats csv` for a conservative
  first pass, extending to txt afterwards.
- **Non-tabular `.txt`**: currently also attempted by the txt pass; failures
  are logged per-resource and harmless (no table is created).
- **Large files**: DataPusher downloads up to 1 MB chunks — fine; very large
  resources (>~100 MB) are unusual in this catalog.
- **datasetversions interplay**: versioning clones resources (files are
  hard-linked, metadata duplicated). Each version's resource has its own
  resource_id → could create duplicate datastore tables per version. The
  backfill will ingest every version's resource — dedupe by skipping
  resources whose name matches `*_v\d+`? Not automated here; decide with the
  data owners whether historical versions should also become queryable
  (probably yes, but they also double table space).
- **Postgres growth**: datastore tables physically duplicate file content.
  With ~500 small files this is negligible, but add this to the prod
  monitoring list.

## Rollback

1. Remove `datastore datapusher` from `ckan.plugins` in the entrypoint
   (or set the ini back) and `docker compose --profile prod up -d` — the
   portal reverts to file-only behavior. No schema changes happened that
   break core CKAN.
2. To free the resulting disk space, purge table per resource:
   `ckan datastore purge <resource_id>` for each ingested resource (do NOT
   drop `_table_metadata` blindly — it is the registry of all datastore
   tables).
3. `docker compose down -v` recreates everything from scratch if in doubt
   (destroys ALL data — production disaster; only on a copy).
