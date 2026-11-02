#!/usr/bin/env python3
"""Backfill tabular CKAN resources into the DataStore.

Iterates over catalog datasets and calls ``datastore_create`` with
``file_url`` for every tabular resource (csv/txt/tsv) that does not have a
DataStore table yet. This loads the file contents directly server-side and
does not need the DataPusher round-trip. Re-runs are idempotent: resources
that already have a DataStore table are skipped.

Read-only outside of DataStore ingestion: nothing except DataStore table
creation is written, and resource/package metadata is never modified.

Usage::

    python ingest_existing_resources.py --url https://data.coat.no \
        --token <API_TOKEN> [--dry-run] [--force] \
        [--datasets name1,name2] [--include-formats csv,txt,tsv]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def api(
    base_url: str, token: str, action: str, payload: dict | None = None, method: str | None = None
) -> tuple[bool, object]:
    """Call a CKAN API action. Returns (success, parsed result or error text)."""
    if method is None:
        method = "POST" if payload is not None else "GET"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    url = f"{base_url.rstrip('/')}/api/3/action/{action}"
    # nosemgrep: scheme from operator-supplied --url (http/https enforced by usage)
    request = urllib.request.Request(url, data=body, method=method)  # noqa: S310
    request.add_header("Authorization", token)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            return True, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", {"__type__": "HTTP"})
        except Exception:  # noqa: BLE001 - best-effort error reporting
            detail = str(exc)
        return False, detail
    except Exception as exc:  # noqa: BLE001 - best-effort error reporting
        return False, str(exc)


def datastore_table_exists(base_url: str, token: str, resource_id: str) -> bool | None:
    """True if the resource already has a DataStore table."""
    ok, result = api(
        base_url, token, "datastore_search", payload={"resource_id": resource_id, "limit": 0}
    )
    if ok:
        return True
    if isinstance(result, dict):
        if "__type__" in result and "NotFound" in str(result.get("__type__", "")):
            return False
        if "resource_id" in str(result):
            return False
    return None


def absolute(base_url: str, url: str) -> str:
    """Prefix resource URLs that CKAN stored as site-relative paths."""
    if not url:
        return ""
    if url.lower().startswith(("http://", "https://")):
        return url
    return base_url.rstrip("/") + "/" + url.lstrip("/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill tabular resources into the CKAN DataStore"
    )
    parser.add_argument("--url", required=True, help="CKAN base URL")
    parser.add_argument("--token", required=True, help="CKAN API token")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would be ingested")
    parser.add_argument(
        "--force", action="store_true", help="Ingest even if a DataStore table exists"
    )
    parser.add_argument(
        "--datasets", default=None, help="Comma-separated package names to restrict to"
    )
    parser.add_argument(
        "--include-formats",
        default="csv,txt,tsv",
        help="Comma-separated resource formats (default csv,txt,tsv)",
    )
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args(argv)

    wanted = {f.strip().lower() for f in args.include_formats.split(",")}
    only = {d.strip() for d in args.datasets.split(",")} if args.datasets else None

    ok, result = api(
        args.url,
        args.token,
        "package_search",
        payload={
            "rows": args.page_size,
            "start": 0,
            "q": "" if only is None else " OR ".join(f"name:{d}" for d in only),
        },
    )
    if not ok:
        print(f"package_search failed: {result}", file=sys.stderr)
        return 1
    packages = result["results"]
    print(f"scanned {len(packages)} datasets", flush=True)

    ingested = skipped = failed = 0
    for package in packages:
        for resource in package.get("resources", []):
            fmt = (resource.get("format") or "").lower()
            if fmt not in wanted:
                continue
            rid = resource["id"]
            label = f"{package['name']}/{resource.get('name', rid)}"
            exists = datastore_table_exists(args.url, args.token, rid)
            if exists and not args.force:
                skipped += 1
                continue
            payload = {"resource_id": rid, "file_url": absolute(args.url, resource.get("url", ""))}
            if not payload["file_url"]:
                print(f"SKIP  {label}: no url", flush=True)
                continue
            if args.dry_run:
                print(f"DRY   {label}: would ingest {payload['file_url']}", flush=True)
                continue
            ok, result = api(args.url, args.token, "datastore_create", payload=payload)
            if ok:
                ingested += 1
                print(f"OK    {label}", flush=True)
            else:
                failed += 1
                print(f"FAIL  {label}: {json.dumps(result)[:300]}", flush=True)

    print(f"done: ingested={ingested} skipped={skipped} failed={failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
