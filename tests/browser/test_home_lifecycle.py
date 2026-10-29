"""Home runs on the page lifecycle (migration M3.2): restarting it in place
leaves nothing behind, and leaving it removes all of it.

Every test also passes the page-error guard, so "zero errors" is checked throughout.
"""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.browser.helpers import listener_count, remount
from tests.conftest import seed_setting, seed_weight

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

# Names Home shares on window for the shell and its own parts to call.
HOME_SHARED = ["updateLostWeight", "updateHealthBar", "updateHealthBarName", "applyHealthbarPref",
               "applyPlateUnit", "refreshPlatesData", "openWeightModal", "openWorkoutModal",
               "refreshHeaderStats", "oldestEntryDate"]


@pytest.fixture()
def home_page(signed_in_page, client):
    # Yesterday, not today: with nothing logged today, Quick Add opens with today picked.
    seed_setting(client, "starting_weight", 230.0)
    seed_setting(client, "goal_weight", 189.0)
    seed_weight(client, YESTERDAY, 210.0)
    signed_in_page.goto("/")
    signed_in_page.wait_for_load_state("networkidle")
    expect(signed_in_page.locator("#lost-lbs-num")).to_have_text("20")
    return signed_in_page


def test_home_registers_as_a_page_and_shares_its_functions(home_page):
    assert home_page.evaluate("appRouter.current") == "home"
    assert home_page.evaluate("names => names.filter(n => !(n in window))", HOME_SHARED) == []


def test_twenty_restarts_leave_listeners_and_globals_flat(home_page):
    page = home_page
    remount(page)
    listeners = listener_count(page)
    names = page.evaluate("Object.keys(window).length")
    healthbar = page.locator("#healthbar-img").get_attribute("src")

    remount(page, 20)
    expect(page.locator("#lost-lbs-num")).to_have_text("20")             # cards refilled
    expect(page.locator("#healthbar-fill-track")).to_have_attribute("aria-valuenow", "48.8")
    assert listener_count(page) == listeners
    assert page.evaluate("Object.keys(window).length") == names
    assert page.locator("#healthbar-img").get_attribute("src") == healthbar   # image processed once


def test_after_restarts_quick_add_weigh_in_saves_once(home_page, client):
    page = home_page
    remount(page, 20)
    page.locator("#mp-footer-add-btn").click()
    expect(page.locator("#quick-add-modal")).to_be_visible()
    page.locator("#qa-log-weight").click()
    expect(page.locator("#history-modal")).to_be_visible()
    page.locator("#history-weight").fill("205")

    posts = []
    page.on("request", lambda r: r.method == "POST" and r.url.endswith("/api/weight") and posts.append(r))
    page.locator("#history-save").click()
    expect(page.locator("#history-modal")).to_be_hidden()
    expect(page.locator("#current-lbs-num")).to_have_text("205")
    page.wait_for_load_state("networkidle")
    assert len(posts) == 1
    assert len(client.get("/api/weights?range=all").get_json()) == 2


def test_after_restarts_quick_add_workout_steps_once(home_page):
    page = home_page
    remount(page, 20)
    page.locator("#mp-footer-add-btn").click()
    page.locator("#qa-log-workout").click()
    expect(page.locator("#wp-log-modal")).to_be_visible()
    page.locator("#workout-type-input").fill("yoga")
    page.locator("#workout-search-dropdown .wsd-item", has_text="Yoga").first.click()
    page.locator("#workout-dur-up").click()
    expect(page.locator("#workout-dur-val")).to_have_text("35")          # one +5 step, not 21


def test_leaving_removes_everything_the_page_set_up(home_page):
    page = home_page
    page.evaluate("appRouter.leave()")
    assert page.evaluate("names => names.filter(n => n in window)", HOME_SHARED) == []
    page.locator("#mp-footer-add-btn").click()
    expect(page.locator("#quick-add-modal")).to_be_hidden()             # its buttons are disconnected
    page.locator("#current-plate").click()
    expect(page.locator("#current-modal")).to_be_hidden()
