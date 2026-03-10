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

# Required COAT schema fields for every dataset
PKG_DEFAULTS = {
    "notes": "Test dataset for automated API tests.",
    "topic_category": "Biota",
    "license_id": "CC-BY_4.0",
    "publisher": "NINA",
    "state": "active",
}


def uid():
    return uuid.uuid4().hex[:8]


def extras(pkg):
    return {e["key"]: e["value"] for e in pkg.get("extras", [])}


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

    def update_package(self, pkg_id, **overrides):
        """Fetch current state, merge overrides, and update (CKAN does a full replace)."""
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
    """Fresh public package for each test (pkg published)."""
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
        updated = client.update_package(pkg["id"], private=False, state="draft")
        assert updated["private"] is True


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
        pkg = client.create_package(org["id"], author=TEST_USER_NAME, title=f"Searchable {tag}")
        client.publish(pkg["id"])
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
