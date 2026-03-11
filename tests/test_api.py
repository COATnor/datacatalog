"""
API-level integration tests for COAT CKAN extensions.

Runs against a live CKAN instance (COAT_URL env var or http://localhost:5000).
Requires:
  - ckan.auth.create_user_via_api = true
  - ckan.auth.user_create_organizations = true
  - coat / coatcustom / datasetversions plugins enabled
"""

import os
import uuid
from datetime import datetime, timedelta

import pytest
import requests
from tenacity import retry, stop_after_delay, wait_fixed

BASE = os.environ.get("COAT_URL", "http://localhost:5000")
_RUN_ID = uuid.uuid4().hex[:8]

TEST_USER_NAME = f"test_apiuser_{_RUN_ID}"
TEST_USER_EMAIL = f"apiuser_{_RUN_ID}@test.coat.no"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_USER_FULLNAME = "Test API User"

# Required COAT schema fields for every dataset
PKG_DEFAULTS = {
    "notes": "Test dataset for automated API tests.",
    "topic_category": "Biota",
    "license_id": "CC-BY_4.0",
    "publisher": "NINA",
    "state": "active",
}

# Required COAT schema fields for every state variable
SV_DEFAULTS = {
    "type": "state-variable",
    "notes": "Test state variable.",
    "state": "active",
    "license_id": "CC-BY_4.0",
    "temporal_start": "2020-01-01",
    "temporal_end": "2024-12-31",
}


def uid():
    return uuid.uuid4().hex[:8]


def extras(pkg):
    return {e["key"]: e["value"] for e in pkg.get("extras", [])}


def make_user(fullname=None):
    """Create a fresh CKAN user (requires create_user_via_api = true)."""
    tag = uid()
    kwargs = dict(
        name=f"test_user_{tag}",
        email=f"user_{tag}@test.coat.no",
        password=TEST_USER_PASSWORD,
    )
    if fullname:
        kwargs["fullname"] = fullname
    return CKANClient(BASE).action("user_create", **kwargs)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CKANAPIError(Exception):
    def __init__(self, action, error, status_code):
        self.action = action
        self.error = error
        self.status_code = status_code
        super().__init__(f"{action} failed ({status_code}): {error}")


class CKANClient:
    """Minimal CKAN API client."""

    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api = f"{base_url}/api/3/action"
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = api_key

    def action(self, action_name, **kwargs):
        resp = self.session.post(f"{self.api}/{action_name}", json=kwargs)
        body = resp.json()
        if not body.get("success"):
            raise CKANAPIError(action_name, body.get("error", {}), resp.status_code)
        return body["result"]

    def post(self, action_name, **kwargs):
        """Return the raw response without raising on failure."""
        return self.session.post(f"{self.api}/{action_name}", json=kwargs)

    def create_package(self, org_id, *, author, **overrides):
        title = overrides.pop("title", f"Test Package {uid()}")
        return self.action("package_create", **{
            **PKG_DEFAULTS, "title": title,
            "owner_org": org_id, "private": True, "author": author,
            **overrides,
        })

    def create_sv(self, org_id, *dataset_names, **overrides):
        """Create a state variable and return the package_show result.

        dataset_names are joined as the 'datasets' field. Extra keyword
        arguments are passed through to package_create.
        """
        sv = self.action("package_create", **{
            **SV_DEFAULTS,
            "title": overrides.pop("title", f"Test SV {uid()}"),
            "owner_org": org_id,
            "private": True,
            "datasets": ",".join(dataset_names),
            **overrides,
        })
        # after_show computes resource_citations; package_create does not trigger it
        return self.action("package_show", id=sv["id"])

    def update_package(self, pkg_id, **overrides):
        """Fetch current state, apply overrides, and update (CKAN does a full replace)."""
        pkg = self.action("package_show", id=pkg_id)
        pkg.update(overrides)
        return self.action("package_update", **pkg)

    def publish(self, pkg_id):
        return self.update_package(pkg_id, private=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@retry(stop=stop_after_delay(60), wait=wait_fixed(2), reraise=True)
def _wait_for_ckan():
    requests.get(f"{BASE}/api/3/action/status_show", timeout=5).raise_for_status()


@pytest.fixture(scope="session")
def client():
    """Authenticated CKAN client, created once for the entire test session."""
    _wait_for_ckan()
    anon = CKANClient(BASE)
    api_key = None
    try:
        user = anon.action(
            "user_create",
            name=TEST_USER_NAME,
            email=TEST_USER_EMAIL,
            password=TEST_USER_PASSWORD,
            fullname=TEST_USER_FULLNAME,
        )
        api_key = user.get("apikey")
    except CKANAPIError as exc:
        print(f"user_create failed: {exc}")

    api_key = api_key or os.environ.get("CKAN_API_KEY")
    if not api_key:
        pytest.fail(
            "Cannot obtain an API key. "
            "Set ckan.auth.create_user_via_api = true, or provide CKAN_API_KEY."
        )
    return CKANClient(BASE, api_key)


@pytest.fixture(scope="session")
def org(client):
    """One shared test organisation for the whole session."""
    return client.action(
        "organization_create",
        name=f"test-org-{uid()}",
        title="Test Org",
        description="Organization for automated API tests.",
        datamanager=TEST_USER_NAME,
        image_url="",
    )


@pytest.fixture
def anon():
    """Unauthenticated client."""
    return CKANClient(BASE)


@pytest.fixture
def pkg(client, org):
    """Fresh private package for each test."""
    return client.create_package(org["id"], author=TEST_USER_NAME)


@pytest.fixture
def pub(client, pkg):
    """Published (public) package for each test."""
    return client.publish(pkg["id"])


# ---------------------------------------------------------------------------
# Package lifecycle
# ---------------------------------------------------------------------------

class TestPackageLifecycle:
    def test_create_is_private(self, pkg):
        assert pkg["private"] is True
        assert pkg["state"] == "active"

    def test_create_public_rejected(self, client, org):
        resp = client.post("package_create", **{
            **PKG_DEFAULTS,
            "title": f"Should Fail {uid()}",
            "owner_org": org["id"],
            "private": False,
            "author": TEST_USER_NAME,
        })
        assert not resp.json()["success"]

    def test_create_sets_version_and_base_name(self, client, org):
        tag = uid()
        title = f"Version Base Name Test {tag}"
        pkg = client.create_package(org["id"], author=TEST_USER_NAME, title=title)
        assert pkg["version"] == "1"
        assert pkg["name"].endswith("_v1")
        pkg_extras = extras(pkg)
        assert "base_name" in pkg_extras
        assert pkg_extras["base_name"] == f"version-base-name-test-{tag}"

    def test_make_public(self, client, pkg):
        assert client.publish(pkg["id"])["private"] is False

    def test_public_protected_from_edits(self, client, pub):
        current = client.action("package_show", id=pub["id"])
        current["title"] = "Modified Title"
        resp = client.post("package_update", **current)
        assert not resp.json().get("success")
        assert resp.status_code == 403

    def test_public_can_be_made_private(self, client, pub):
        assert client.update_package(pub["id"], private=True)["private"] is True

    def test_delete_private(self, client, pkg):
        client.action("package_delete", id=pkg["id"])
        assert client.action("package_show", id=pkg["id"])["state"] == "deleted"

    def test_delete_public_blocked(self, client, pub):
        resp = client.post("package_delete", id=pub["id"])
        assert not resp.json()["success"]
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Draft
# ---------------------------------------------------------------------------

class TestDraftBehavior:
    def test_draft_forced_private(self, client, org):
        pkg = client.create_package(org["id"], author=TEST_USER_NAME, state="draft")
        assert client.update_package(pkg["id"], private=False, state="draft")["private"] is True


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

class TestResourceManagement:
    def test_create_resource(self, client, pkg):
        res = client.action("resource_create", package_id=pkg["id"],
                            name="data.csv", url="http://example.com/data.csv")
        assert res["name"] == "data.csv"
        assert res["package_id"] == pkg["id"]

    def test_resource_extension_lowercased(self, client, pkg):
        res = client.action("resource_create", package_id=pkg["id"],
                            name="DATA.CSV", url="http://example.com/data.csv")
        assert res["name"] == "DATA.csv"

    def test_multiple_resources(self, client, pkg):
        for i in range(2):
            client.action("resource_create", package_id=pkg["id"],
                          name=f"data{i}.csv", url=f"http://example.com/data{i}.csv")
        assert len(client.action("package_show", id=pkg["id"])["resources"]) == 2


# ---------------------------------------------------------------------------
# Embargo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("days,use_anon,expected_url", [
    ( 30, True,  "#resource-under-embargo"),       # future embargo: hidden for anon
    ( 30, False, "http://example.com/res.csv"),    # future embargo: visible for auth
    ( -1, True,  "http://example.com/res.csv"),    # past embargo: visible for anon
])
def test_embargo(days, use_anon, expected_url, client, org, anon):
    embargo_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    pkg = client.create_package(org["id"], author=TEST_USER_NAME, embargo=embargo_date)
    client.action("resource_create", package_id=pkg["id"],
                  name="res.csv", url="http://example.com/res.csv")
    client.publish(pkg["id"])

    viewer = anon if use_anon else client
    shown = viewer.action("package_show", id=pkg["id"])
    assert shown["resources"][0]["url"] == expected_url


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

class TestVersioning:
    def test_name_suffix_and_version(self, pkg):
        assert "_v1" in pkg["name"]
        assert pkg["version"] == "1"

    def test_version_stable_across_updates(self, client, pkg):
        assert client.update_package(pkg["id"], title="Updated Title")["version"] == "1"

    def test_base_name_stable_across_updates(self, client, pkg):
        before = extras(pkg).get("base_name")
        after = client.update_package(pkg["id"], title="Different Title")
        assert extras(after).get("base_name") == before


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_returns_results(self, client, org):
        tag = uid()
        client.publish(client.create_package(org["id"], author=TEST_USER_NAME,
                                             title=f"Searchable {tag}")["id"])
        assert client.action("package_search", q=tag)["count"] >= 1


# ---------------------------------------------------------------------------
# Anonymous access
# ---------------------------------------------------------------------------

class TestAnonymousAccess:
    def test_can_view_public(self, anon, pub):
        assert anon.action("package_show", id=pub["id"])["id"] == pub["id"]

    def test_cannot_view_private(self, anon, pkg):
        assert not anon.post("package_show", id=pkg["id"]).json()["success"]

    def test_cannot_create(self, anon, org):
        resp = anon.post("package_create", **{
            **PKG_DEFAULTS,
            "title": "Anon Fail",
            "owner_org": org["id"],
            "private": True,
            "author": TEST_USER_NAME,
        })
        assert not resp.json()["success"]


# ---------------------------------------------------------------------------
# State variable — citations
# ---------------------------------------------------------------------------

class TestStateVariableCitation:
    def test_citation_populated(self, client, org, pkg):
        """resource_citations resolves the author's fullname and contains the SV name."""
        sv = client.create_sv(org["id"], pkg["name"])
        citation = sv.get("resource_citations", "")
        assert citation, "resource_citations is empty"
        assert sv["name"] in citation
        assert TEST_USER_FULLNAME in citation, (
            f"Expected {TEST_USER_FULLNAME!r} in citation, got: {citation!r}"
        )

    def test_citation_no_fullname_fallback(self, client, org):
        """Author without a fullname falls back to username — no raw email in citation."""
        user = make_user()
        pkg = client.create_package(org["id"], author=user["name"])
        sv = client.create_sv(org["id"], pkg["name"])
        citation = sv.get("resource_citations", "")
        assert citation, "resource_citations is empty"
        assert "@" not in citation, f"Citation leaks raw email: {citation!r}"
        assert user["name"] in citation

    def test_citation_multiple_authors_et_al(self, client, org):
        """Two datasets with different authors produce 'First Author et al.'"""
        user2 = make_user(fullname=f"Second Author {uid()}")
        pkg1 = client.create_package(org["id"], author=TEST_USER_NAME)
        pkg2 = client.create_package(org["id"], author=user2["name"])
        sv = client.create_sv(org["id"], pkg1["name"], pkg2["name"])
        citation = sv.get("resource_citations", "")
        assert "et al." in citation, f"Expected 'et al.' in citation, got: {citation!r}"
        first_author = citation.split(" et al.")[0]
        assert first_author in {TEST_USER_FULLNAME, user2["fullname"]}


# ---------------------------------------------------------------------------
# State variable — external datasets
# ---------------------------------------------------------------------------

class TestStateVariableExternalDatasets:
    def test_external_datasets_stored_and_returned(self, client, org, pkg):
        """external_datasets entries are stored and returned on package_show."""
        url = "https://example.com/external-dataset"
        sv = client.create_sv(org["id"], pkg["name"], external_datasets=[{"url": url}])
        ext = sv.get("external_datasets")
        assert isinstance(ext, list) and len(ext) == 1 and ext[0]["url"] == url, (
            f"Expected [{{url: {url!r}}}], got: {ext!r}"
        )

    def test_external_datasets_optional(self, client, org, pkg):
        """State variable can be created without external_datasets."""
        assert not client.create_sv(org["id"], pkg["name"]).get("external_datasets")


# ---------------------------------------------------------------------------
# State variable — create-only merge and manual overrides
# ---------------------------------------------------------------------------

class TestStateVariableMergeFields:
    def test_fields_merged_on_create(self, client, org, pkg):
        """author and publisher are auto-merged from linked datasets on creation."""
        sv = client.create_sv(org["id"], pkg["name"])
        assert TEST_USER_NAME in sv.get("author", ""), (
            f"Expected author to contain {TEST_USER_NAME!r}, got: {sv.get('author')!r}"
        )
        assert "NINA" in sv.get("publisher", ""), (
            f"Expected publisher to contain 'NINA', got: {sv.get('publisher')!r}"
        )

    def test_manual_override_preserved_on_update(self, client, org, pkg):
        """Manually set author/publisher on update are not overwritten by merge."""
        sv = client.create_sv(org["id"], pkg["name"])
        updated = client.update_package(sv["id"],
                                        author="custom_author",
                                        publisher="Custom Publisher")
        shown = client.action("package_show", id=updated["id"])
        assert shown.get("author") == "custom_author"
        assert shown.get("publisher") == "Custom Publisher"


# ---------------------------------------------------------------------------
# State variable — scientific_name manual editing
# ---------------------------------------------------------------------------

class TestStateVariableScientificName:
    def test_scientific_name_merged_on_create(self, client, org):
        """scientific_name is auto-merged from the linked dataset on SV creation."""
        species = "Lemmus lemmus"
        pkg = client.create_package(org["id"], author=TEST_USER_NAME, scientific_name=species)
        sv = client.create_sv(org["id"], pkg["name"])
        assert species in sv.get("scientific_name", ""), (
            f"Expected {species!r} in scientific_name, got: {sv.get('scientific_name')!r}"
        )

    def test_scientific_name_manual_override_preserved(self, client, org):
        """Manually set scientific_name on update is not overwritten by merge."""
        pkg = client.create_package(org["id"], author=TEST_USER_NAME,
                                    scientific_name="Rangifer tarandus")
        sv = client.create_sv(org["id"], pkg["name"])
        updated = client.update_package(sv["id"], scientific_name="Lemmus lemmus")
        assert client.action("package_show", id=updated["id"])["scientific_name"] == "Lemmus lemmus"
