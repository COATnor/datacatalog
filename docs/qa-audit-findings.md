# QA audit findings: ckanext-coat and ckanext-coatcustom

Static review of the two project-owned extensions (`ckanext/ckanext-coat`,
`ckanext/ckanext-coatcustom`). `ckanext-oauth2`, `ckanext-scheming`,
`ckanext-spatial` and `ckanext-doi` are out of scope.

Lint: `ruff check` (repo config, `--no-fix`) and `ruff format --check` pass.
prek hooks pass on every commit. Note: the ruff config sets `fix = true`, so a
plain `ruff check` rewrites files. Use `--no-fix` when reviewing.

Severity: **blocker** (fix before next release), **major** (real risk, fix
soon), **minor** (correctness or hygiene, low impact), **noise** (cosmetic or
dead code).

Items marked *(verify)* were found by reading code only and have not been
reproduced against a running instance.

Already fixed on this branch: see the commit log (`git log master..chore/qa-audit`).

---

## Blocker

### B1. Anonymous enumeration of all user email addresses

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/views.py:19-41`
  (`autocomplete`), `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:115-130`
  (`scheming_author_autocomplete_tags`).
- **What is wrong:** `/scheming/api/util/author/autocomplete` has no auth check.
  `scheming_author_autocomplete_tags` yields `"Full Name <email>"` for every
  user. The filter is `value.lower() in tag.lower()`, so an empty
  `incomplete` matches every user.
- **Why it matters:** `GET /scheming/api/util/author/autocomplete` with no
  parameters dumps the email address of every account to any anonymous
  visitor. This is personal data, and it applies to a public catalogue.
- **Suggested fix:** require login on the endpoint, and do not return emails
  to the autocomplete (match on name and username; store the email server
  side when the author is picked). Decision needed on the author-field
  storage format. Add a test that anonymous GET returns no emails.

---

## Major

### M1. Embargoed resource URLs can leak through `package_search` *(verify)*

- **Where:** `ckanext/ckanext-coat/ckanext/coat/logic/action/get.py:11-14`
  (`package_search`), compared with `get.py:17-26` (`package_show`).
- **What is wrong:** `package_show` replaces resource URLs with
  `#resource-under-embargo` when the viewer cannot access the dataset.
  `package_search` returns the indexed `validated_data_dict`, which contains
  the real resource URLs, and applies no equivalent masking.
- **Why it matters:** For a public dataset with an active embargo, anonymous
  search results expose the download URLs that the embargo is supposed to hide.
- **Suggested fix:** apply the same URL masking to each result in
  `package_search`, or strip `url` from `resources` in the indexed/returned
  dict when `embargo_access` fails. Add a test in `TestEmbargo`
  (`tests/test_api.py`) that searches anonymously and asserts no real URL.

### M2. Bulk-download embargo gate fails open

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/embargo.py:25-33`.
- **What is wrong:** `blocked_dataset` wraps everything in
  `except Exception` and logs at `debug` level, then returns `None`. Any
  error (DB failure, bad extras, unexpected type) lets the request through.
- **Why it matters:** The gate exists to stop embargoed data leaving the
  portal. Its failure mode is the opposite of the fail-closed behaviour
  described in `ckanext/ckanext-coat/ckanext/coat/helpers.py:125-145`.
- **Suggested fix:** catch narrower exceptions, log at `warning`, and return
  the dataset name (block) when the gate cannot decide. Accept that a DB outage
  then also blocks bulk downloads.

### M3. Merge from linked datasets reads private and embargoed datasets with `ignore_auth` *(verify)*

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/validators.py:52-61`
  (`_associated_datasets`), used by `merge_from_datasets` (line 65) and
  `merge_tags_from_datasets` (line 91).
- **What is wrong:** A state variable's `datasets` field is resolved with
  `ckan_package_show` and `{"ignore_auth": True}`. Any authenticated user can
  name a private or embargoed dataset in that field. Its `author`, scientific
  names and tags are then copied into the state variable, which is public.
- **Why it matters:** Metadata of datasets the user cannot read is disclosed
  through a public record. Embargoed metadata is included.
- **Suggested fix:** resolve linked datasets with the editing user's context
  (no `ignore_auth`), or drop non-readable datasets from the merge and report
  a validation error. Add a test where a non-member links a private dataset.

### M4. Plausible analytics sends private dataset and resource names to a third party *(verify config)*

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/analytics.py:43-66`
  (`package_names`, `resource_names`, `payload`), `analytics.py:85-111`
  (`track`), `analytics.py:105-106` (client IP from `X-Forwarded-For`).
- **What is wrong:** `track` runs on every 200 response. For a download it
  posts the dataset name, base name and resource name to
  `ckanext.coat.plausible_host` (default `plausible.io`). The lookups use
  `ignore_auth`, so private datasets are included. The client IP is forwarded
  from a client-supplied header.
- **Why it matters:** The feature is off by default
  (`ckanext.coat.plausible_download_events`). If it is enabled in production,
  names of private, unreleased datasets leave the portal. Viewers' IPs are sent
  too. Spoofed `X-Forwarded-For` values pollute the analytics.
- **Suggested fix:** decision needed. Send only public dataset identifiers,
  never private or embargoed ones. Take the client IP only from trusted proxy
  configuration. Document the data sent in the README.

---

## Minor

### m1. Resource clone rewrites external link URLs to the resource name *(verify intent)*

- **Where:** `ckanext/ckanext-coat/ckanext/coat/blueprint.py:99-101`
  (`_clone_resources`).
- **What is wrong:** For non-upload resources, `resource["url"]` is replaced
  with `resource["name"]`. A link resource in the new version therefore points
  at the resource name, not the original URL. If the original URL was masked
  by the embargo logic, the masked placeholder is cloned too.
- **Why it matters:** Links break in every new version. Unless this is an
  intentional convention, it is data loss.
- **Suggested fix:** keep the original `url` for link resources. Add a test for
  `new_version` with a link resource. `new_version` has no test at all today.

### m2. Unreachable `raise` in `is_protected`

- **Where:** `ckanext/ckanext-coat/ckanext/coat/helpers.py:62-66`.
- **What is wrong:** `return` precedes the `raise`, so the
  "Cannot modify a resource" error can never fire. The early return is an
  intentional bulk-upload workaround. Resource edits on public datasets are
  still blocked because CKAN's `resource_update` calls `package_update`, which
  runs the public-dataset check.
- **Why it matters:** The code reads as if resource-level protection is
  enforced when it is not. Future readers may rely on the wrong guard.
- **Suggested fix:** delete the unreachable `raise`, and replace the comment
  with an explanation that the guard lives in `package_update`.

### m3. `package_search` mutates the caller's `fq_list`

- **Where:** `ckanext/ckanext-coat/ckanext/coat/logic/action/get.py:12-13`.
- **What is wrong:** `data_dict["fq_list"].append(...)` mutates the list the
  caller passed in. Retried or reused dicts pick up the collapse filter twice.
- **Suggested fix:** copy the list first (`list(data_dict.get("fq_list", []))`).

### m4. Typo in a dataset field name

- **Where:** `ckanext/ckanext-coat/ckanext/coat/blueprint.py:68`
  (`"medatata_modified"`).
- **What is wrong:** `metadata_modified` is misspelled. The value is set on the
  new package but ignored by CKAN.
- **Suggested fix:** delete the key. CKAN sets `metadata_modified` itself. Do not
  rename it blindly, because that changes stored data.

### m5. KeyError and AttributeError paths in `package_create`

- **Where:** `ckanext/ckanext-coat/ckanext/coat/logic/action/create.py:29`
  (`data_dict.get("title", "").lower()` fails when `title` is `None`), and
  `:62-64` (`data_dict["owner_org"]` and `data_dict["type"]` raise KeyError
  when absent).
- **Suggested fix:** use `(data_dict.get("title") or "")` and `.get()` for
  `owner_org` and `type`. Validate `owner_org` and return a `ValidationError`.

### m6. `get_package` leaves `data_dict` unbound

- **Where:** `ckanext/ckanext-coat/ckanext/coat/helpers.py:45-55`.
- **What is wrong:** If the object has neither `id` nor `name_or_id`, the loop
  falls through and `data_dict` is unbound (`UnboundLocalError`).
- **Suggested fix:** raise a clear `ValidationError` in the `else` path.

### m7. Resource name validators: wildcard and state issues

- **Where:** `ckanext/ckanext-coat/ckanext/coat/logic/validators.py:25`
  (`ilike(name)`), `:24` (`extras["base_name"]` KeyError), `:26-27` (no check
  on the resource's package `state`), `:36` (`resource["name"]` may be `None`),
  `:10-11` (`lowercase_extension(None)` raises TypeError).
- **What is wrong:** `ilike` treats `%` and `_` in the user's name as wildcards,
  so `100%` matches any name starting with `100`. Deleted resources still count
  as conflicts. Missing or `None` values raise uncaught exceptions.
- **Suggested fix:** escape LIKE wildcards or compare `lower()` in Python, filter
  on `Resource.state == "active"`, and guard `None` values.

### m8. `private_on_creation` and `resource_name_conflict` assume `context["package"]` *(verify)*

- **Where:** `ckanext/ckanext-coat/ckanext/coat/logic/validators.py:42`
  (`context["package"].id`).
- **What is wrong:** During `package_create` the context may not have a
  `package` key yet, so this is an AttributeError or NotFound. The existing
  tests seem to create resources only after the dataset exists.
- **Suggested fix:** confirm with a test that creating a dataset with resources
  inline works, and guard the lookup.

### m9. Broad exception handling hides failures

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/analytics.py:81-82`
  and `:112-114`; `embargo.py:32-33` (see M2).
- **What is wrong:** Bare `except Exception` logs at `debug`, so real errors are
  invisible in production logs.
- **Suggested fix:** log at `warning` with `exc_info`, and narrow the exception
  types where possible.

### m10. Search helpers run with an empty context

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:69-91`
  (`scheming_dataset_choices`), `:158-178` (`scheming_protocol_choice`).
- **What is wrong:** `ckan_package_search({}, ...)` runs without the user's
  context, so `include_private: True` has no effect. Editors cannot link to
  their own private datasets or protocols. `rows` is set to the total count,
  which CKAN silently caps at `ckan.search.rows_max` (1000 by default).
- **Suggested fix:** pass the request user's context, and paginate or raise the
  cap instead of relying on `rows = count`.

### m11. Author choice lists include deleted and pending users

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:93-106`
  and `:115-130` (`User.all()` without a state filter).
- **Suggested fix:** filter on `state == "active"`. Consider exposing usernames
  and full names only.

### m12. `parse_authors` reloads every user on each call

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:103-117`
  and `:248-278`.
- **What is wrong:** `authors_fullnames()` runs `User.all()` each time
  `parse_authors` is called. It runs for every dataset view and DOI build.
  Cost grows with the number of users.
- **Suggested fix:** build the name map once per request, or query only the
  authors being resolved.

### m13. Solr query construction in autocomplete

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/views.py:9-15`
  (`escape`), `:33-34` (`dataset_type` is not escaped).
- **What is wrong:** `escape` does not escape backslash or whitespace, and
  `dataset_type` is appended unescaped. Queries run under the user's permissions,
  so the impact is limited to query shape, not data disclosure.
- **Suggested fix:** escape backslash, and escape or allowlist `dataset_type`.

### m14. Template helper registration exposes modules and data

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/plugin.py:136-137`
  and `:107-108`.
- **What is wrong:** `{name: getattr(helpers, name) for name in dir(helpers)}`
  registers every module-level name, including imported modules (`model`,
  `logic`, `yaml`, `json`) and raw data (`tags`, `names`, `locations`,
  `publishers`). The same applies to validators. Templates can reach
  `h.model`.
- **Suggested fix:** register an explicit list of helpers.

### m15. DOI metadata builder assumes keys exist

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/plugin.py:156`
  (`pkg_dict["version"]`), `:164-171` (`json.loads` and fixed indexing into
  the `spatial` polygon).
- **What is wrong:** A missing version or malformed spatial value raises during
  DOI minting.
- **Suggested fix:** use `.get` and validate the polygon before indexing.

### m16. `data_dict_with_spatial` compares location as list or string

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:31`.
- **What is wrong:** `value not in (data_dict.get("location") or [])` does a
  substring check when `location` is a string.
- **Suggested fix:** normalise `location` to a list first.

### m17. `after_dataset_show` derived fields may be written back *(verify)*

- **Where:** `ckanext/ckanext-coatcustom/ckanext/coatcustom/plugin.py:61-62`.
- **What is wrong:** `resource_citations`, `publisher` and `author_email` are
  added to the `package_show` result. If a caller such as `package_patch` sends
  that dict back to `package_update`, the derived keys could be stored.
- **Suggested fix:** confirm with `package_patch`, and strip derived keys in
  `package_update` if needed.

---

## Noise

- **N1.** Dead code removed in this branch: `_get_or_bust`,
  `scheming_protocol_choices`, `publishers_from_authors`, the
  `commalist_to_json` validator and its `json` import. Still unused and
  candidates for removal: `scheming_locations_choices`,
  `scheming_protocol_choice_required`, `scheming_publisher_choices_required`.
  These need a check against the presets and schema JSON before removal.
- **N2.** `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:18` has a
  commented-out line, and `t = "dataset"` is hard-coded (line 20) even though
  state variables and protocols also call this helper.
- **N3.** `ckanext/ckanext-coat/ckanext/coat/plugin.py:157`: `show_package_schema`
  is a no-op override.
- **N4.** `ckanext/ckanext-coat/ckanext/coat/logic/action/get.py:20`
  mutates `context["package"]` as a side effect of `package_show`.
- **N5.** `ckanext/ckanext-coatcustom/ckanext/coatcustom/helpers.py:158-190`
  duplicates the logic of `scheming_dataset_choices`.
- **N6.** `tests/` mirror plugins: `ckanext/*/tests/test_plugin.py` contain only
  `pass`. Remove them or add real tests.

---

## Test coverage gaps (tests/test_api.py and tests/test_browser.py)

| Area | Gap |
|---|---|
| Auth on mutations | No test that package create/update/delete are rejected via GET. **Added in this branch** (`TestPackageLifecycle::test_mutations_not_callable_via_get`). |
| Author autocomplete | No test that anonymous access returns no emails (B1). |
| Search and embargo | No test that search results mask embargoed resource URLs (M1). |
| Version creation | `new_version` (`blueprint.py`) has no test. This includes link-resource URLs (m1), the `_clone_resources` hardlink path, and non-dataset types. |
| Linked-dataset merge | No test that linking a private dataset does not disclose its metadata (M3). |
| Embargo gate | Only the happy path for bulk download is tested. There is no test for gate errors (M2). |
| Analytics | `analytics.track` is untested, including the `enabled()` default-off behaviour (M4). |
| Legacy header auth | The `X-CKAN-API-KEY` path added in `ckanext-coat/plugin.py` has no test. |
| Browser suite | No browser test for the author autocomplete endpoint or the new-version flow. |

---

## Verification

- `ruff check --no-fix` and `ruff format --check` on both extensions: pass.
- prek hooks: pass on each commit.
- Docker test suite: **not run**. `docker compose --profile test run` failed
  because host port 127.0.0.1:5000 is already bound by an unrelated process
  (rootlesskit, pid 3859). That stack was not touched. This project's stack was
  torn down with `docker compose --profile test down -v`. The regression test
  for the GET fix should be run on a host with port 5000 free.
