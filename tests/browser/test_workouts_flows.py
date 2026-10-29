"""Workouts page flows in a real browser: the day-grouped table, header stats,
range filter, logging (with a day note), deleting (single row, and several via
the delete-confirm checkboxes), and the "discard unsaved changes?" guard."""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


TODAY = _day(0)


@pytest.fixture()
def workouts(signed_in_page, client):
    """Signed-in browser + an API client for seeding, both on test user 1."""
    def open_workouts():
        signed_in_page.goto("/workouts")
        signed_in_page.wait_for_load_state("networkidle")
        return signed_in_page
    return open_workouts, client


def _seed_workout(client, entry_date, workout_type, duration_min, kcal):
    client.post("/api/workout", json={"date": entry_date, "type": workout_type,
                                      "duration_min": duration_min, "kcal": kcal, "note": ""})


def _saved(client):
    return sorted((w["date"], w["type"], w["duration_min"]) for w in client.get("/api/workouts").get_json())


def _groups(page):
    return page.locator("#wp-table-inner .wp-date-group")


def _pick_range(page, value):
    page.locator("#wp-filter-btn").click()
    page.locator(f'#wp-range-menu .wp-range-btn[data-range="{value}"]').click()


# ── What the page shows ──────────────────────────────────────────────────────

def test_new_account_shows_empty_state(workouts):
    open_workouts, _ = workouts
    page = open_workouts()
    expect(page.locator("#wp-empty")).to_be_visible()
    expect(page.locator("#wp-count")).to_have_text("0")
    expect(page.locator("#wp-kcal")).to_have_text("0")
    expect(page.locator("#wp-streak")).to_have_text("0")
    expect(page.locator("#wp-streak")).to_have_css("color", "rgb(60, 120, 255)")


def test_table_groups_workouts_by_day_with_totals_and_note(workouts):
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Basketball", 30, 260)
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    _seed_workout(client, _day(3), "Running (6 mph)", 40, 400)
    client.post("/api/workout-day-note", json={"date": TODAY, "note": "double session"})
    page = open_workouts()

    expect(_groups(page)).to_have_count(2)
    today = _groups(page).first                                  # newest day first
    expect(today.locator(".wp-date-count")).to_contain_text("2 workouts")
    expect(today.locator(".wp-header-dur")).to_have_text("50 min")
    expect(today.locator(".wp-header-kcal")).to_contain_text("360")
    expect(today.locator(".wp-day-note")).to_have_text("double session")
    expect(today.locator(".wp-row")).to_have_count(2)

    expect(page.locator("#wp-count")).to_have_text("3")          # all three are within 7 days
    expect(page.locator("#wp-kcal")).to_have_text("760")
    expect(page.locator("#wp-streak")).to_have_text("1")


def test_day_group_collapses_and_expands(workouts):
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    page = open_workouts()
    group = _groups(page).first
    group.locator(".wp-date-header-row").click()
    expect(group).to_have_class("wp-date-group collapsed")
    group.locator(".wp-date-header-row").click()
    expect(group).to_have_class("wp-date-group")


def test_range_filter_shows_older_days_and_is_remembered(workouts):
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    _seed_workout(client, _day(20), "Boxing", 30, 300)
    page = open_workouts()
    expect(_groups(page)).to_have_count(1)                       # default: last 7 days

    with page.expect_response("**/api/preference"):
        _pick_range(page, "30d")
    expect(_groups(page)).to_have_count(2)

    page = open_workouts()                                       # reload keeps the choice
    expect(_groups(page)).to_have_count(2)


# ── Logging ──────────────────────────────────────────────────────────────────

def test_log_workout_with_day_note(workouts):
    open_workouts, client = workouts
    page = open_workouts()
    page.locator("#wp-add-btn").click()
    expect(page.locator("#wp-log-modal")).to_be_visible()
    expect(page.locator("#wp-date-input")).not_to_have_value("")   # today pre-selected

    page.locator("#workout-type-input").fill("yoga")
    page.locator("#workout-search-dropdown .wsd-item", has_text="Yoga").first.click()
    page.locator("#workout-dur-up").click()
    page.locator("#workout-dur-up").click()
    expect(page.locator("#workout-dur-val")).to_have_text("40")
    page.locator("#wpm-add-activity-btn").click()
    page.locator("#workout-note-input").fill("easy day")
    page.locator("#wp-modal-save").click()

    expect(page.locator("#wp-log-modal")).to_be_hidden()
    today = _groups(page).first
    expect(today.locator(".wp-row")).to_have_count(1)
    expect(today.locator(".wp-row-dur")).to_have_text("40 min")
    expect(today.locator(".wp-day-note")).to_have_text("easy day")
    expect(page.locator("#wp-count")).to_have_text("1")
    assert [(d, d_min) for d, _, d_min in _saved(client)] == [(TODAY, 40)]
    assert client.get(f"/api/workout-day-note?date={TODAY}").get_json()["note"] == "easy day"


# ── Deleting ─────────────────────────────────────────────────────────────────

def test_delete_single_workout_from_table_after_confirming(workouts):
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    page = open_workouts()

    page.locator(".wp-row .wp-del-btn").first.click()
    expect(page.locator("#app-confirm-modal")).to_be_visible()
    expect(page.locator("#app-confirm-modal")).to_contain_text('Delete "Yoga" (20 min)?')
    with page.expect_response(lambda r: r.request.method == "DELETE"):
        page.locator("#app-confirm-ok").click()

    expect(page.locator("#wp-empty")).to_be_visible()
    expect(page.locator("#wp-count")).to_have_text("0")
    assert _saved(client) == []


def test_cancel_delete_keeps_workout(workouts):
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    page = open_workouts()
    page.locator(".wp-row .wp-del-btn").first.click()
    page.locator("#app-confirm-cancel").click()
    expect(page.locator("#app-confirm-modal")).to_be_hidden()
    expect(page.locator(".wp-row")).to_have_count(1)
    assert len(_saved(client)) == 1


def _mark_both_for_removal(page):
    page.locator(".wp-row").first.click()                         # opens that day for editing
    expect(page.locator("#wp-log-modal")).to_be_visible()
    day_rows = page.locator("#wpm-day-entries .wpm-day-row")
    expect(day_rows).to_have_count(2)
    day_rows.first.get_by_role("button", name="Delete").click()
    day_rows.first.get_by_role("button", name="Delete").click()
    expect(day_rows).to_have_count(0)
    page.locator("#wp-modal-save").click()
    expect(page.locator("#wp-del-check-modal")).to_be_visible()
    expect(page.locator("#wp-del-checks input[type=checkbox]")).to_have_count(2)


def test_remove_several_and_confirm_all(workouts):
    """Regression for #23: with every box ticked (the default), all are deleted."""
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Basketball", 30, 260)
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    page = open_workouts()
    _mark_both_for_removal(page)
    page.locator("#wp-del-check-ok").click()                      # both ticked (default)
    expect(page.locator("#wp-log-modal")).to_be_hidden()
    expect(page.locator("#wp-empty")).to_be_visible()
    assert _saved(client) == []


def test_remove_several_then_confirm_only_some(workouts):
    """Regression for #23: mark two workouts for removal, untick one in the
    delete-confirm checklist — only the ticked one is deleted."""
    open_workouts, client = workouts
    _seed_workout(client, TODAY, "Basketball", 30, 260)
    _seed_workout(client, TODAY, "Yoga", 20, 100)
    page = open_workouts()
    _mark_both_for_removal(page)
    page.locator("#wp-del-checks label", has_text="Yoga").locator("input").uncheck()
    page.locator("#wp-del-check-ok").click()

    expect(page.locator("#wp-log-modal")).to_be_hidden()
    expect(page.locator(".wp-row")).to_have_count(1)
    assert [t for _, t, _ in _saved(client)] == ["Yoga"]


# ── Discard-changes guard ────────────────────────────────────────────────────

def test_cancel_with_unsaved_changes_asks_before_discarding(workouts):
    open_workouts, client = workouts
    page = open_workouts()
    page.locator("#wp-add-btn").click()
    page.locator("#workout-type-input").fill("yoga")
    page.locator("#workout-search-dropdown .wsd-item", has_text="Yoga").first.click()
    page.locator("#wpm-add-activity-btn").click()

    page.locator("#wp-modal-cancel").click()
    expect(page.locator("#app-confirm-modal")).to_be_visible()
    expect(page.locator("#app-confirm-modal")).to_contain_text("unsaved changes")
    page.locator("#app-confirm-cancel").click()                   # keep editing
    expect(page.locator("#wp-log-modal")).to_be_visible()
    expect(page.locator("#wpm-staged-entries .wpm-staged-row")).to_have_count(1)

    page.locator("#wp-modal-cancel").click()
    page.locator("#app-confirm-ok").click()                       # discard
    expect(page.locator("#wp-log-modal")).to_be_hidden()
    assert _saved(client) == []


def test_cancel_without_changes_closes_immediately(workouts):
    open_workouts, _ = workouts
    page = open_workouts()
    page.locator("#wp-add-btn").click()
    page.locator("#wp-modal-cancel").click()
    expect(page.locator("#wp-log-modal")).to_be_hidden()
    expect(page.locator("#app-confirm-modal")).to_be_hidden()
