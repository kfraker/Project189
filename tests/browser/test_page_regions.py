"""The parts of the page that change from page to page are labelled with
data-region, so in-page navigation can swap exactly those parts (migration M1.1).

Each page must have every region exactly once, each holding that page's own
content, and the labels must not change the layout.
"""
import pytest
from playwright.sync_api import expect

REGIONS = ["bg", "header_title", "header_stats", "healthbar", "content", "footer_left", "footer_add"]

# What each page puts in each region (None = that page leaves the region empty).
EXPECTED = {
    "/": {
        "bg": ".mp-bg",
        "header_title": "h1.site-title:text-is('Sweat Equity')",
        "header_stats": "#mp-trend",
        "healthbar": "#healthbar-hud",
        "content": ".mp-plates-section",
        "footer_left": None,
        "footer_add": "#mp-footer-add-btn",
    },
    "/weights": {
        "bg": ".wt-bg",
        "header_title": "h1.site-title:text-is('Weigh-ins')",
        "header_stats": "#wt-logged-week",
        "healthbar": None,
        "content": ".chart-with-nav",
        "footer_left": "#mp-filter-btn",
        "footer_add": "#chart-add-btn",
    },
    "/workouts": {
        "bg": ".wp-bg",
        "header_title": "h1.site-title:text-is('Workouts')",
        "header_stats": "#wp-count",
        "healthbar": None,
        "content": ".wp-table-wrap",
        "footer_left": "#wp-range-menu",
        "footer_add": "#wp-add-btn",
    },
}


@pytest.mark.parametrize("path", EXPECTED)
def test_each_region_appears_once_with_its_pages_content(signed_in_page, path):
    page = signed_in_page
    page.goto(path)
    page.wait_for_load_state("networkidle")
    for name in REGIONS:
        region = page.locator(f'[data-region="{name}"]')
        expect(region, f"region {name}").to_have_count(1)
        inside = EXPECTED[path][name]
        if inside:
            expect(region.locator(inside), f"{inside} in region {name}").to_have_count(1)
        else:
            assert region.evaluate("el => el.children.length") == 0, f"region {name} should be empty on {path}"


@pytest.mark.parametrize("path", EXPECTED)
def test_region_wrappers_take_no_part_in_layout(signed_in_page, path):
    """Regions without a container of their own get a wrapper that is display:
    contents, so the page title stays a direct flex item of the header, etc."""
    page = signed_in_page
    page.goto(path)
    wrappers = page.locator(".page-region")
    expect(wrappers).to_have_count(3)                     # bg, header_title, healthbar
    for display in wrappers.evaluate_all("els => els.map(el => getComputedStyle(el).display)"):
        assert display == "contents"


def test_shell_parts_are_outside_every_region(signed_in_page):
    """The header nav, menu button and shared windows belong to the shell, which
    in-page navigation keeps, so none of them may sit inside a swappable region."""
    page = signed_in_page
    page.goto("/")
    for shell_part in ["#site-cursor", ".site-nav[aria-label='Pages']", "#profile-btn",
                       "#menu-modal", "#settings-modal", "#app-confirm-modal"]:
        assert page.locator(shell_part).evaluate("el => !el.closest('[data-region]')"), shell_part
