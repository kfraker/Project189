"""Weigh-ins page flows in a real browser: charts, date ranges, Daily/Weekly switch,
table view, logging (incl. missing days), notes, deleting, the "max data" info
icon (#20) and the 0-day streak colour (#16)."""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.conftest import seed_weight


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


TODAY = _day(0)


@pytest.fixture()
def weights(signed_in_page, client):
    """Signed-in browser + an API client for seeding, both on test user 1."""
    def open_weights():
        signed_in_page.goto("/weights")
        signed_in_page.wait_for_load_state("networkidle")
        return signed_in_page
    return open_weights, client


def _seed_with_note(client, entry_date, weight_lbs, notes):
    client.post("/api/weight", json={"date": entry_date, "weight_lbs": weight_lbs, "notes": notes})


def _wait_for_chart_days(page, canvas_id, days):
    """Wait until the Chart.js chart on `canvas_id` spans exactly `days` days.
    (Range changes re-fetch data, so the chart updates a moment after the click.)"""
    page.wait_for_function(
        "([id, n]) => { const c = window.Chart && Chart.getChart(id); return c && c.data.labels.length === n; }",
        arg=[canvas_id, days])


def _pick_daily_range(page, value):
    page.locator("#mp-filter-btn").click()
    page.locator(f'#mp-daily-ranges .range-btn[data-range="{value}"]').click()


def _delete_selected(page):
    """Click "Delete selected" and wait until the app has finished deleting."""
    with page.expect_response(lambda r: r.request.method == "DELETE"):
        page.locator("#row-delete-ok").click()


def _row_for(page, iso_date):
    return page.locator(f'tr.daily-row:has(td.cell-weight[data-date="{iso_date}"])')


def _open_table(page):
    page.locator("#view-toggle-btn").click()
    expect(page.locator("#data-table-wrap")).to_be_visible()


def _rows(client):
    return {r["date"]: r for r in client.get("/api/weights?range=all").get_json()}


# ── Header stats ─────────────────────────────────────────────────────────────

def test_zero_day_streak_is_blue(weights):
    """Regression for #16: a 0-day streak gets the same blue as on Home/Workouts."""
    open_weights, _ = weights
    page = open_weights()
    expect(page.locator("#wt-streak")).to_have_text("0")
    expect(page.locator("#wt-streak")).to_have_css("color", "rgb(60, 120, 255)")


def test_header_shows_streak_and_seven_day_average(weights):
    open_weights, client = weights
    for i, w in enumerate([200.0, 202.0, 204.0]):
        seed_weight(client, _day(i), w)
    page = open_weights()
    expect(page.locator("#wt-streak")).to_have_text("3")
    expect(page.locator("#wt-7d-avg")).to_have_text("202.0 lbs")


# ── Charts & ranges ──────────────────────────────────────────────────────────

def test_daily_chart_plots_weigh_ins_and_ranges_change_it(weights):
    open_weights, client = weights
    for offset in (0, 1, 2, 20, 40):
        seed_weight(client, _day(offset), 200.0 + offset / 10)
    page = open_weights()

    _pick_daily_range(page, "all")
    _wait_for_chart_days(page, "weight-chart", 41)   # oldest weigh-in (40 days ago) → today

    _pick_daily_range(page, "7d")
    _wait_for_chart_days(page, "weight-chart", 3)    # only the last 3 days have data in that window


def test_switch_between_daily_and_weekly_charts(weights):
    open_weights, client = weights
    for i in range(10):
        seed_weight(client, _day(i), 200.0 - i / 2)
    page = open_weights()
    switch = page.locator("#chart-type-btn")
    expect(switch).to_have_attribute("aria-label", "Switch to weekly chart")

    switch.click()
    expect(switch).to_have_attribute("aria-label", "Switch to daily chart")
    page.wait_for_function("() => { const c = Chart.getChart('weekly-chart'); return c && c.data.labels.length >= 2; }")

    switch.click()
    expect(switch).to_have_attribute("aria-label", "Switch to weekly chart")


def test_new_account_shows_empty_chart_message(weights):
    open_weights, _ = weights
    page = open_weights()
    expect(page.locator("#chart-empty")).to_be_visible()


# ── "Showing max data" info icon (#20) ───────────────────────────────────────

def test_info_icon_explains_short_history_on_hover(weights):
    open_weights, client = weights
    for i in range(3):
        seed_weight(client, _day(i), 200.0)
    page = open_weights()
    _pick_daily_range(page, "90d")

    icon = page.locator("#chart-info-icon")
    expect(icon).to_be_visible()
    expect(icon).to_have_attribute("aria-label", "Showing max data — 3 entries logged")
    icon.hover()
    page.wait_for_function("""() => {
        const after = getComputedStyle(document.getElementById('chart-info-icon'), '::after');
        return after.opacity === '1' && after.content.includes('Showing max data');
    }""")


def test_info_icon_hidden_when_history_covers_range(weights):
    open_weights, client = weights
    for i in range(8):
        seed_weight(client, _day(i), 200.0)
    page = open_weights()
    _pick_daily_range(page, "7d")
    _wait_for_chart_days(page, "weight-chart", 7)
    expect(page.locator("#chart-info-icon")).to_be_hidden()


# ── Logging ──────────────────────────────────────────────────────────────────

def test_log_weigh_in_adds_point_and_table_row(weights):
    open_weights, client = weights
    seed_weight(client, _day(1), 201.0)
    page = open_weights()
    page.locator("#chart-add-btn").click()
    expect(page.locator("#history-modal")).to_be_visible()
    page.locator("#history-weight").fill("199.5")
    page.locator("#history-save").click()
    expect(page.locator("#history-modal")).to_be_hidden()
    assert _rows(client)[TODAY]["weight_lbs"] == 199.5

    _open_table(page)
    expect(_row_for(page, TODAY).locator("td.cell-weight")).to_contain_text("199.5 lbs")


def test_missing_day_can_be_filled_from_the_table(weights):
    open_weights, client = weights
    seed_weight(client, TODAY, 200.0)
    seed_weight(client, _day(2), 202.0)
    page = open_weights()
    _open_table(page)

    gap = _row_for(page, _day(1))
    expect(gap).to_have_class("daily-row row-missing")
    gap.locator(".missing-excl-btn").click()
    expect(page.locator("#history-modal")).to_be_visible()
    page.locator("#history-weight").fill("201")
    page.locator("#history-save").click()

    expect(gap.locator("td.cell-weight")).to_contain_text("201 lbs")
    assert _rows(client)[_day(1)]["weight_lbs"] == 201.0


# ── Notes ────────────────────────────────────────────────────────────────────

def test_add_and_edit_a_note_from_the_table(weights):
    open_weights, client = weights
    seed_weight(client, TODAY, 200.0)
    page = open_weights()
    _open_table(page)
    row = _row_for(page, TODAY)

    row.get_by_role("button", name="Add note").click()
    expect(page.locator("#note-popover")).to_be_visible()
    page.locator("#note-popover-text").fill("felt great")
    page.locator("#note-popover-save").click()
    expect(page.locator("#note-popover")).to_be_hidden()
    expect(row.get_by_role("button", name="Edit note")).to_be_visible()
    assert _rows(client)[TODAY]["notes"] == "felt great"

    row.get_by_role("button", name="Edit note").click()
    expect(page.locator("#note-popover-text")).to_have_value("felt great")
    page.locator("#note-popover-text").fill("felt amazing")
    page.locator("#note-popover-save").click()
    expect(page.locator("#note-popover")).to_be_hidden()
    assert _rows(client)[TODAY]["notes"] == "felt amazing"


# ── Deleting ─────────────────────────────────────────────────────────────────

def test_delete_weight_but_keep_note(weights):
    open_weights, client = weights
    _seed_with_note(client, TODAY, 200.0, "rest day")
    page = open_weights()
    _open_table(page)

    _row_for(page, TODAY).get_by_role("button", name="Delete this entry").click()
    expect(page.locator("#row-delete-modal")).to_be_visible()
    page.locator('#row-delete-checks [data-key="note"]').uncheck()
    _delete_selected(page)
    expect(page.locator("#row-delete-modal")).to_be_hidden()

    row = _rows(client)[TODAY]
    assert row["weight_lbs"] is None
    assert row["notes"] == "rest day"


def test_delete_whole_entry(weights):
    open_weights, client = weights
    _seed_with_note(client, TODAY, 200.0, "rest day")
    seed_weight(client, _day(1), 201.0)
    page = open_weights()
    _open_table(page)

    _row_for(page, TODAY).get_by_role("button", name="Delete this entry").click()
    expect(page.locator('#row-delete-checks [data-key="note"]')).to_be_checked()
    _delete_selected(page)                          # weight + note both ticked by default
    assert TODAY not in _rows(client)
    assert _day(1) in _rows(client)
