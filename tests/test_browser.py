import os

import pytest
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_delay, wait_fixed

BASE = os.environ.get("COAT_URL", "http://localhost:5000")
CDP_ENDPOINT = os.environ.get("CDP_ENDPOINT", "ws://lightpanda:9222")
CDP_CONNECT_TIMEOUT = float(os.environ.get("CDP_CONNECT_TIMEOUT", "30"))


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


@pytest.mark.xdist_group("browser")
def test_feide_login(page):
    page.context.clear_cookies()
    page.goto(f"{BASE}/user/login", wait_until="domcontentloaded")

    # goto instead of click — Lightpanda can't click elements outside the viewport
    feide_link = page.locator("a[href*='authselection=feide|realm|testusers.feide.no']")
    page.goto(feide_link.get_attribute("href"), wait_until="domcontentloaded")

    page.wait_for_selector("#username")
    page.fill("#username", "emma123elev")
    page.fill("#password", "098asd")
    page.click("button[type='submit']")

    # Lightpanda doesn't update the page after form POST redirect chains
    # https://github.com/lightpanda-io/browser/issues/1890
    page.wait_for_timeout(5000)

    # Click through the SAML bridge page if present
    submit = page.locator("input[type='submit'], button[type='submit']").first
    if "://traefik/" not in page.url and submit.is_visible():
        submit.click()
        page.wait_for_timeout(2000)

    page.wait_for_selector(".account .username")
