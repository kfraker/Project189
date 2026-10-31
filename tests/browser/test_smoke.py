"""Smoke tests: every page opens cleanly in a real browser.

Each test also passes through the page-error guard in conftest.py, so any JS
error, failed request, or 4xx/5xx from the app fails the test.
"""
import re

import pytest
from playwright.sync_api import expect

PAGES = [
    ("/", "Home", "Sweat Equity"),
    ("/weights", "Weigh-ins", "Weigh-ins — Sweat Equity"),
    ("/workouts", "Workouts", "Workouts — Sweat Equity"),
]


# ── Safety ────────────────────────────────────────────────────────────────────

@pytest.mark.allow_page_errors
def test_live_server_refuses_requests_outside_test_schema(page):
    """Safety guard: without the test schema active, the server answers nothing."""
    response = page.goto("/")
    assert response.status == 503
    expect(page.get_by_text("test schema not active")).to_be_visible()


# ── Signed in: each page loads cleanly ───────────────────────────────────────

@pytest.mark.parametrize("path,nav_label,title", PAGES)
def test_page_loads_cleanly_signed_in(signed_in_page, path, nav_label, title):
    page = signed_in_page
    page.goto(path)
    page.wait_for_load_state("networkidle")   # let the page's data requests finish
    expect(page).to_have_title(title)
    expect(page.locator(".site-header")).to_be_visible()
    expect(page.get_by_text("Sign in with Google")).to_have_count(0)
    expect(page.get_by_role("link", name=nav_label)).to_have_class(re.compile(r"\bactive\b"))


# ── Signed in: header nav reaches every page ─────────────────────────────────

def test_header_nav_links_reach_each_page(signed_in_page):
    page = signed_in_page
    page.goto("/")
    for path, nav_label, title in PAGES[1:] + PAGES[:1]:
        page.get_by_role("navigation", name="Pages").get_by_role("link", name=nav_label).click()
        expect(page).to_have_url(re.compile(re.escape(path) + r"$"))
        expect(page).to_have_title(title)
        page.wait_for_load_state("networkidle")


# ── Signed out ───────────────────────────────────────────────────────────────

def test_signed_out_home_shows_login(signed_out_page):
    page = signed_out_page
    page.goto("/")
    expect(page.get_by_text("Sign in with Google")).to_be_visible()


@pytest.mark.parametrize("path", ["/weights", "/workouts"])
def test_signed_out_pages_redirect_to_login(signed_out_page, path):
    page = signed_out_page
    page.goto(path)
    expect(page).to_have_url(re.compile(r"/login\?next=" + re.escape(path) + r"$"))
    expect(page.get_by_text("Sign in with Google")).to_be_visible()
