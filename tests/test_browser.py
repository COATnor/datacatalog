import os
import time
import uuid
from pathlib import Path

import pytest
import requests
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_delay, wait_fixed

BASE = os.environ.get("COAT_URL", "http://localhost:5000")
CDP_ENDPOINT = os.environ.get("CDP_ENDPOINT", "ws://lightpanda:9222")
CDP_CONNECT_TIMEOUT = float(os.environ.get("CDP_CONNECT_TIMEOUT", "30"))
LOGIN_TIMEOUT_MS = 60_000
UI_TIMEOUT_MS = 15_000


@retry(stop=stop_after_delay(CDP_CONNECT_TIMEOUT), wait=wait_fixed(1), reraise=True)
def _connect_browser(playwright):
    return playwright.chromium.connect_over_cdp(CDP_ENDPOINT)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = _connect_browser(p)

        yield b
        b.close()


@pytest.fixture(scope="session")
def page(browser):
    p = browser.new_page()
    yield p
    p.close()


@pytest.mark.xdist_group("browser")
def test_search_map_renders(page):
    page.goto(f"{BASE}/dataset/")
    page.wait_for_selector(".leaflet-container", timeout=5000)
    assert page.query_selector(".leaflet-container") is not None


def _feide_login(page):
    """Log in through Feide; the deployment offers no local login form."""
    page.context.clear_cookies()
    page.goto(f"{BASE}/user/login", wait_until="domcontentloaded")
    # goto instead of click: Lightpanda can't click outside the viewport
    feide_link = page.locator("a[href*='authselection=feide|realm|testusers.feide.no']")
    page.goto(feide_link.get_attribute("href"), wait_until="domcontentloaded")
    page.wait_for_selector("#username", timeout=LOGIN_TIMEOUT_MS)
    page.fill("#username", "emma123elev")
    page.fill("#password", "098asd")
    page.press("#password", "Enter")
    page.wait_for_function(
        "() => !document.querySelector('#username')"
        " || !!document.querySelector('.account .username')",
        polling=500,
        timeout=LOGIN_TIMEOUT_MS,
    )
    if page.query_selector(".account .username") is None:
        page.locator("input[type='submit'], button[type='submit']").first.click()
        page.wait_for_selector(".account .username", timeout=LOGIN_TIMEOUT_MS)


@pytest.mark.xdist_group("browser")
def test_feide_login(page):
    _feide_login(page)
    assert page.query_selector(".account .username") is not None


def _wait_for(page, expression, timeout_ms=UI_TIMEOUT_MS):
    """Poll a JS expression until truthy.

    Lightpanda never notifies wait_for_function/wait_for_selector about
    DOM mutations, so poll with evaluate, which always sees the live DOM.
    Values are inlined into the expression: Lightpanda unreliably forwards
    evaluate's arg parameter.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        if page.evaluate(expression):
            return
        if time.monotonic() > deadline:
            raise TimeoutError(f"condition not met within {timeout_ms}ms: {expression[:80]}")
        time.sleep(0.5)


def _api(action, token, **kwargs):
    resp = requests.post(
        f"{BASE}/api/3/action/{action}",
        json=kwargs,
        headers={"Authorization": token},
        timeout=30,
    )
    body = resp.json()
    assert body.get("success"), f"{action} failed: {body}"
    return body["result"]


def _author_search(page):
    """Clear the Contact Persons widget and focus its search box.

    select2 (4.x on CKAN 2.12) hides #field-author and Lightpanda can't
    click below the fold, so the widget is driven through the DOM anchored
    at #field-author. Waits for select2 enhancement first: the input is
    rendered before the widget container is inserted.
    """
    _wait_for(
        page,
        "() => { const hid = document.getElementById('field-author');"
        " return !!hid.parentElement.querySelector('.select2-container'); }",
    )
    page.evaluate(
        "() => { const box = document.getElementById('field-author')"
        ".parentElement.querySelector('.select2-container');"
        " if (!box) throw new Error('author select2 widget not found');"
        " const close = box.querySelector('.select2-selection__choice__remove');"
        " if (close) close.click();"
        " box.querySelector('.select2-search__field').focus(); }"
    )


def _submit_author_form(page):
    """Submit the edit form with the save button's name included.

    Lightpanda implements neither requestSubmit nor button activation, and
    CKAN's edit handler requires `save` in the POST body.
    """
    page.evaluate(
        "() => { const f = document.getElementById('field-author').form;"
        " const save = document.createElement('input');"
        " save.type = 'hidden'; save.name = 'save'; save.value = '';"
        " f.appendChild(save); f.submit(); }"
    )


def _create_sv(token, tag):
    org = _api(
        "organization_create",
        token,
        name=f"browser-org-{tag}",
        title="Browser Org",
        description="Organization for automated browser tests.",
        datamanager="coat_test_admin",
        image_url="",
    )
    pkg = _api(
        "package_create",
        token,
        type="dataset",
        title=f"Browser Pkg {tag}",
        notes="Browser test dataset.",
        topic_category="Biota",
        license_id="CC-BY_4.0",
        state="active",
        owner_org=org["id"],
        private=True,
        author="browser@example.com",
    )
    sv = _api(
        "package_create",
        token,
        type="state-variable",
        title=f"Browser SV {tag}",
        notes="Browser test state variable.",
        topic_category="Biota",
        license_id="CC-BY_4.0",
        state="active",
        owner_org=org["id"],
        private=True,
        temporal_start="2020-01-01",
        temporal_end="2024-12-31",
        datasets=pkg["name"],
        author="browser@example.com",
    )
    return org, sv


def _find_feide_user(token):
    users = _api("user_list", token, all_fields=True)
    for u in users:
        if "emma" in f"{u.get('name')} {u.get('fullname')} {u.get('email')}".lower():
            return u["name"]
    raise AssertionError(
        f"Feide-mapped user not found among: {[(u.get('name'), u.get('fullname')) for u in users]}"
    )


@pytest.mark.xdist_group("browser")
def test_sv_author_accepts_custom_value(page):
    """State-variable Contact Persons accepts free-text values, not just suggestions."""
    token = Path("/tokens/api_token").read_text().strip()
    tag = uuid.uuid4().hex[:8]
    org, sv = _create_sv(token, tag)
    custom = f"Custom Person <custom-{tag}@example.com>"

    _feide_login(page)
    _api(
        "member_create",
        token,
        id=org["id"],
        object=_find_feide_user(token),
        object_type="user",
        capacity="editor",
    )

    page.goto(f"{BASE}/state-variable/edit/{sv['id']}", wait_until="domcontentloaded")
    page.wait_for_selector("#field-author", state="attached", timeout=UI_TIMEOUT_MS)
    _author_search(page)
    _wait_for(
        page,
        "() => { const hid = document.getElementById('field-author');"
        " const box = hid.parentElement.querySelector('.select2-container');"
        " return !!box && box.classList.contains('select2-container--open'); }",
    )
    page.keyboard.type(custom, delay=20)
    _wait_for(
        page,
        "() => [...document.querySelectorAll('.select2-results__option--highlighted')]"
        f".some((el) => (el.getAttribute('data-value') || '').includes('{tag}'))",
    )
    # ArrowDown highlights the offered free-text choice before committing it
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    _wait_for(
        page,
        f"() => document.getElementById('field-author').value === {custom!r}",
    )
    with page.expect_response("**/state-variable/edit/**", timeout=UI_TIMEOUT_MS):
        _submit_author_form(page)
    shown = _api("package_show", token, id=sv["id"])
    assert shown.get("author") == custom, (
        f"Custom author was not stored: got {shown.get('author')!r}, expected {custom!r}"
    )


def _commit_author_choice(page, typed, highlight, expected):
    """Type into Contact Persons, pick the highlighted suggestion, submit."""
    page.keyboard.type(typed, delay=20)
    _wait_for(
        page,
        "() => [...document.querySelectorAll('.select2-results__option--highlighted')]"
        f".some((el) => (el.getAttribute('data-value') || '').includes({highlight!r}))",
    )
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    _wait_for(
        page,
        f"() => document.getElementById('field-author').value === {expected!r}",
    )
    with page.expect_response("**/state-variable/edit/**", timeout=UI_TIMEOUT_MS):
        _submit_author_form(page)


def _create_public_dataset(token, tag, embargo=None):
    """Public dataset with one link resource, for download-button tests."""
    org = _api(
        "organization_create",
        token,
        name=f"dl-org-{tag}",
        title="Download Org",
        description="Organization for download button tests.",
        datamanager="coat_test_admin",
        image_url="",
    )
    extras = {"embargo": embargo} if embargo else {}
    pkg = _api(
        "package_create",
        token,
        type="dataset",
        title=f"Download Pkg {tag}",
        notes="Download test dataset.",
        topic_category="Biota",
        license_id="CC-BY_4.0",
        state="active",
        owner_org=org["id"],
        private=True,
        author=f"browser-{tag}@uit.no",
        **extras,
    )
    _api(
        "resource_create",
        token,
        package_id=pkg["id"],
        name="data.csv",
        url="http://example.com/data.csv",
    )
    shown = _api("package_show", token, id=pkg["id"])
    shown["private"] = False
    _api("package_update", token, **shown)
    return org, _api("package_show", token, id=pkg["id"])


def _ready(page):
    page.wait_for_function(
        "() => document.readyState === 'complete'",
        polling=500,
        timeout=UI_TIMEOUT_MS,
    )


def _download_links(page):
    """Hrefs of bulk-download entry points only (not single-file links)."""
    return page.evaluate(
        "() => [...document.querySelectorAll('a[href]')]"
        ".map((el) => el.getAttribute('href'))"
        ".filter((h) => h.includes('download_all') || /\\/zip$/.test(h))"
    )


@pytest.mark.xdist_group("browser")
def test_download_buttons_shown_when_anonymous(page):
    """Public datasets are downloadable by anyone, logged in or not."""
    token = Path("/tokens/api_token").read_text().strip()
    _, pkg = _create_public_dataset(token, uuid.uuid4().hex[:8])
    page.context.clear_cookies()
    page.goto(f"{BASE}/dataset/{pkg['name']}", wait_until="domcontentloaded")
    _wait_for(
        page,
        "() => !!document.querySelector('h1')",
    )
    _ready(page)
    links = _download_links(page)
    assert any("download_all" in href for href in links), links
    assert any(href.endswith("/zip") for href in links), links


@pytest.mark.xdist_group("browser")
def test_download_buttons_shown_to_members(page):
    """Logged-in members keep both bulk-download entry points."""
    token = Path("/tokens/api_token").read_text().strip()
    org, pkg = _create_public_dataset(token, uuid.uuid4().hex[:8])

    _feide_login(page)
    _api(
        "member_create",
        token,
        id=org["id"],
        object=_find_feide_user(token),
        object_type="user",
        capacity="editor",
    )
    page.goto(f"{BASE}/dataset/{pkg['name']}", wait_until="domcontentloaded")
    _wait_for(
        page,
        "() => !!document.querySelector('h1')",
    )
    _ready(page)
    links = _download_links(page)
    assert any("download_all" in href for href in links), links
    assert any(href.endswith("/zip") for href in links), links


@pytest.mark.xdist_group("browser")
def test_download_buttons_hidden_under_embargo(page):
    """Embargoed datasets show no bulk-download entry points, only a warning."""
    token = Path("/tokens/api_token").read_text().strip()
    _, pkg = _create_public_dataset(token, uuid.uuid4().hex[:8], embargo="2030-01-01")
    page.context.clear_cookies()
    page.goto(f"{BASE}/dataset/{pkg['name']}", wait_until="domcontentloaded")
    _wait_for(
        page,
        "() => !!document.querySelector('h1')",
    )
    _ready(page)
    # Hidden *because* embargoed: the warning badge must be what replaced them.
    assert _download_links(page) == [], _download_links(page)
    assert "Dataset under embargo" in page.inner_text("body")


@pytest.mark.xdist_group("browser")
def test_dataset_new_renders(page):
    """New dataset form renders instead of 500ing (regression)."""
    token = Path("/tokens/api_token").read_text().strip()
    tag = uuid.uuid4().hex[:8]
    org = _api(
        "organization_create",
        token,
        name=f"newform-org-{tag}",
        title="Newform Org",
        description="Org for new-form tests.",
        datamanager="coat_test_admin",
        image_url="",
    )
    _feide_login(page)
    _api(
        "member_create",
        token,
        id=org["id"],
        object=_find_feide_user(token),
        object_type="user",
        capacity="editor",
    )
    page.goto(f"{BASE}/dataset/new", wait_until="domcontentloaded")
    _wait_for(
        page,
        "() => !!document.querySelector('#field-title, .dataset-form, .primary form')",
    )
    info = page.evaluate(
        "() => ({ primary: (document.querySelector('.primary') || {}).textContent || '',"
        " secondary: (document.querySelector('.secondary') || {}).textContent || '' })"
    )
    # The dataset-type description is sidebar copy on the creation form.
    assert "typical COAT dataset" in info["secondary"]
    assert "typical COAT dataset" not in info["primary"]


@pytest.mark.xdist_group("browser")
def test_state_variable_new_renders(page):
    """State-variable creation form renders with its sidebar (regression)."""
    token = Path("/tokens/api_token").read_text().strip()
    tag = uuid.uuid4().hex[:8]
    org = _api(
        "organization_create",
        token,
        name=f"svnew-org-{tag}",
        title="SV Newform Org",
        description="Org for state-variable form tests.",
        datamanager="coat_test_admin",
        image_url="",
    )
    _feide_login(page)
    _api(
        "member_create",
        token,
        id=org["id"],
        object=_find_feide_user(token),
        object_type="user",
        capacity="editor",
    )
    page.goto(f"{BASE}/state-variable/new", wait_until="domcontentloaded")
    _wait_for(page, "() => !!document.querySelector('#field-title, .dataset-form, .primary form')")
    _ready(page)
    secondary = page.evaluate(
        "() => (document.querySelector('.secondary') || {}).textContent || ''"
    )
    assert "describes directly a feature related to" in secondary


@pytest.mark.xdist_group("browser")
def test_sv_author_accepts_suggested_user(page):
    """State-variable Contact Persons stores an autocomplete suggestion on first save."""
    token = Path("/tokens/api_token").read_text().strip()
    tag = uuid.uuid4().hex[:8]
    org, sv = _create_sv(token, tag)

    _feide_login(page)
    feide_user = _find_feide_user(token)
    _api(
        "member_create",
        token,
        id=org["id"],
        object=feide_user,
        object_type="user",
        capacity="editor",
    )

    page.goto(f"{BASE}/state-variable/edit/{sv['id']}", wait_until="domcontentloaded")
    page.wait_for_selector("#field-author", state="attached", timeout=UI_TIMEOUT_MS)
    _author_search(page)
    _wait_for(
        page,
        "() => { const hid = document.getElementById('field-author');"
        " const box = hid.parentElement.querySelector('.select2-container');"
        " return !!box && box.classList.contains('select2-container--open'); }",
    )
    # Type the full Feide username so the autocomplete suggests exactly it
    _commit_author_choice(page, feide_user, feide_user, feide_user)
    shown = _api("package_show", token, id=sv["id"])
    assert shown.get("author") == feide_user, (
        f"Suggested author was not stored: got {shown.get('author')!r}, expected {feide_user!r}"
    )


def _create_legacy_sv(token, tag, shape):
    """State variable with a legacy-shaped author: bare name or empty."""
    org = _api(
        "organization_create",
        token,
        name=f"legacy-org-{tag}-{shape}",
        title="Legacy Org",
        description="Organization for legacy author tests.",
        datamanager="coat_test_admin",
        image_url="",
    )
    if shape == "empty":
        datasets = ""
        author = ""
    else:
        base = _api(
            "package_create",
            token,
            type="dataset",
            title=f"Legacy Base {tag}",
            notes="Base dataset.",
            topic_category="Biota",
            license_id="CC-BY_4.0",
            state="active",
            owner_org=org["id"],
            private=True,
            author="a@b.c",
        )
        datasets = base["name"]
        author = "COAT Climate Module"
    sv = _api(
        "package_create",
        token,
        type="state-variable",
        title=f"Legacy SV {tag} {shape}",
        notes="Legacy author shape.",
        topic_category="Biota",
        license_id="CC-BY_4.0",
        state="active",
        owner_org=org["id"],
        private=True,
        temporal_start="2020-01-01",
        temporal_end="2024-12-31",
        datasets=datasets,
        author=author,
    )
    return org, sv


@pytest.mark.xdist_group("browser")
@pytest.mark.parametrize("shape", ["bare", "empty"])
def test_sv_author_edit_legacy_shape_sticks_first_save(page, shape):
    """Editing an SV with a legacy author stores the new contact on first save."""
    token = Path("/tokens/api_token").read_text().strip()
    tag = uuid.uuid4().hex[:8]
    org, sv = _create_legacy_sv(token, tag, shape)
    new_contact = f"Legacy Fix <legacy-{tag}@example.com>"

    _feide_login(page)
    _api(
        "member_create",
        token,
        id=org["id"],
        object=_find_feide_user(token),
        object_type="user",
        capacity="editor",
    )

    page.goto(f"{BASE}/state-variable/edit/{sv['id']}", wait_until="domcontentloaded")
    page.wait_for_selector("#field-author", state="attached", timeout=UI_TIMEOUT_MS)
    _author_search(page)
    # No --open wait: Lightpanda does not reflect the open class for an
    # empty multi-select, but typing opens the dropdown regardless.
    _commit_author_choice(page, new_contact, tag, new_contact)
    shown = _api("package_show", token, id=sv["id"])
    assert shown.get("author") == new_contact, (
        f"[{shape}] author was not stored on first save: got {shown.get('author')!r}, "
        f"expected {new_contact!r}"
    )
