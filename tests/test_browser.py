import os
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

    select2 hides #field-author and Lightpanda can't click below the fold,
    so the widget is driven through the DOM anchored at #field-author.
    """
    page.evaluate(
        "() => { const box = document.getElementById('field-author')"
        ".parentElement.querySelector('.select2-container');"
        " if (!box) throw new Error('author select2 widget not found');"
        " const close = box.querySelector('.select2-search-choice-close');"
        " if (close) close.click();"
        " box.querySelector('input.select2-input').focus(); }"
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
    page.keyboard.type(custom, delay=20)
    page.wait_for_function(
        "(exp) => [...document.querySelectorAll('.select2-highlighted')]"
        ".some((el) => el.textContent.includes(exp))",
        arg=tag,
        polling=500,
        timeout=UI_TIMEOUT_MS,
    )
    page.keyboard.press("Enter")
    with page.expect_response("**/state-variable/edit/**", timeout=UI_TIMEOUT_MS):
        _submit_author_form(page)
    shown = _api("package_show", token, id=sv["id"])
    assert shown.get("author") == custom, (
        f"Custom author was not stored: got {shown.get('author')!r}, expected {custom!r}"
    )
