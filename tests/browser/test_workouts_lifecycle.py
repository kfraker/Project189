"""Workouts runs on the page lifecycle (migration M3.1): restarting it in place
leaves nothing behind, and leaving it removes all of it.

Every test also passes the page-error guard, so "zero errors" is checked throughout.
"""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.browser.helpers import listener_count, remount

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture()
def workouts_page(signed_in_page, client):
    # Yesterday, not today: with nothing logged today, + opens with today picked.
    client.post("/api/workout", json={"date": YESTERDAY, "type": "Yoga", "duration_min": 20, "kcal": 100, "note": ""})
    signed_in_page.goto("/workouts")
    signed_in_page.wait_for_load_state("networkidle")
    expect(signed_in_page.locator(".wp-row")).to_have_count(1)
    return signed_in_page


def test_workouts_registers_as_a_page(workouts_page):
    assert workouts_page.evaluate("appRouter.current") == "workouts"


def test_twenty_restarts_leave_listeners_and_globals_flat(workouts_page):
    page = workouts_page
    remount(page)
    listeners = listener_count(page)
    names = page.evaluate("Object.keys(window).length")

    remount(page, 20)
    expect(page.locator(".wp-row")).to_have_count(1)                 # table redrawn, not doubled
    assert listener_count(page) == listeners
    assert page.evaluate("Object.keys(window).length") == names


def test_after_restarts_each_click_fires_exactly_once(workouts_page, client):
    page = workouts_page
    remount(page, 20)

    page.locator("#wp-add-btn").click()
    expect(page.locator("#wp-log-modal")).to_be_visible()
    page.locator("#workout-type-input").fill("yoga")
    page.locator("#workout-search-dropdown .wsd-item", has_text="Yoga").first.click()
    page.locator("#workout-dur-up").click()
    expect(page.locator("#workout-dur-val")).to_have_text("35")      # one +5 step, not 21
    page.locator("#wpm-add-activity-btn").click()
    expect(page.locator("#wpm-staged-entries .wpm-staged-row")).to_have_count(1)

    posts = []
    page.on("request", lambda r: r.method == "POST" and r.url.endswith("/api/workout") and posts.append(r))
    page.locator("#wp-modal-save").click()
    expect(page.locator("#wp-log-modal")).to_be_hidden()
    page.wait_for_load_state("networkidle")
    assert len(posts) == 1
    assert len(client.get("/api/workouts").get_json()) == 2


def test_leaving_removes_everything_the_page_set_up(workouts_page):
    page = workouts_page
    page.evaluate("appRouter.leave()")
    assert page.evaluate("'setWorkoutsRange' in window") is False
    page.locator("#wp-add-btn").click()
    expect(page.locator("#wp-log-modal")).to_be_hidden()             # its buttons are disconnected


def test_saving_settings_keeps_the_workouts_table(workouts_page):
    """Regression for #25: saving Settings on Workouts (unit or date format change)
    used to call Workouts' own table function with no data, blanking the table."""
    page = workouts_page
    page.locator("#profile-btn").click()
    page.locator("#menu-modal .menu-modal-btn", has_text="Settings").click()
    page.locator("#prof-kg-btn").click()
    with page.expect_response("**/api/preference"):
        page.locator("#settings-save").click()
    expect(page.locator("#settings-modal")).to_be_hidden()
    expect(page.locator(".wp-row")).to_have_count(1)
