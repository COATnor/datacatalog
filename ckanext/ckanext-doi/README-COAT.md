# ckanext-doi (vendored)

Vendored from
[NaturalHistoryMuseum/ckanext-doi](https://github.com/NaturalHistoryMuseum/ckanext-doi)
at tag `v4.0.4`, verbatim except for the COAT patches listed below.
Upstream is frozen (no commits since v4.0.4) and not compatible with
SQLAlchemy 2 / CKAN 2.12, hence vendoring instead of bumping a pin.
If upstream revives, prefer switching back to a git pin and dropping
this directory.

## COAT patches (all marked `COAT:` in the source)

1. `ckanext/doi/model/doi.py`: `relation` → `relationship`
   (`sqlalchemy.orm.relation` was removed in SQLAlchemy 2.0; the names
   are aliases with identical semantics).
2. `ckanext/doi/model/doi.py`: classical `meta.mapper(...)` →
   `meta.registry.map_imperatively(...)` (same pattern as `ckan/model`
   in CKAN 2.12; the former raises `InvalidRequestError` on SQLAlchemy 2).
3. `ckanext/doi/model/crud.py`: `Session.commit()` → `Session.flush()`
   at all 5 write sites. These helpers run inside CKAN action
   transactions (e.g. `after_dataset_update`); committing there closes
   the caller's transaction, which SQLAlchemy 2 refuses to re-commit
   (`ResourceClosedError: This transaction is closed` on every
   `package_update`). Flushed writes are persisted by the outer action
   commit; CLI callers (`ckan doi ...`) commit themselves, so no
   standalone behavior is lost.

## Housekeeping deviations from upstream (tooling only, no behavior)

- Removed upstream `[tool.ruff*]` sections from `pyproject.toml` so the
  repo-root ruff config (which excludes this tree) applies uniformly.
- `pragma: allowlist secret` on the stock Alembic `sqlalchemy.url`
  placeholder (`migration/doi/alembic.ini`) and on the migration
  `revision` hex id (`migration/doi/versions/86a245a136db_*.py`):
  both are detect-secrets false positives.
