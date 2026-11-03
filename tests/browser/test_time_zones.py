"""Dates in every time zone: the Weigh-ins charts and table put each weigh-in on its
own day, wherever the visitor is.

CI runs in UTC, where a local date and a UTC date are the same, so date bugs hide
there. These tests run the page in four time zones, two either side of UTC, on a
fixed "today" with history that spans both clock changes (Europe 2026-10-25, the
US 2026-11-01).
"""

from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.conftest import seed_weight

TODAY = date(2026, 11, 4)  # a Wednesday
FIRST = date(2026, 10, 24)  # a Saturday, before both clock changes
DAYS = [(FIRST + timedelta(days=i)).isoformat() for i in range((TODAY - FIRST).days + 1)]
WEIGHT = {day: 200.0 + i for i, day in enumerate(DAYS)}  # a different weight every day


@pytest.fixture()
def weights(signed_in_page, client, request):
    """The Weigh-ins page at 9pm local time on TODAY, with a weigh-in every day since FIRST."""
    for day in DAYS:
        seed_weight(client, day, WEIGHT[day])
    signed_in_page.clock.set_fixed_time(f"{TODAY.isoformat()}T21:00:00{request.cls.OFFSET}")

    def open_weights(weekly_mode="rolling"):
        signed_in_page.add_init_script(f"localStorage.setItem('pref_weekly_mode', '{weekly_mode}')")
        signed_in_page.goto("/weights")
        signed_in_page.wait_for_load_state("networkidle")
        return signed_in_page

    return open_weights


def _chart(page, canvas_id, expression):
    return page.evaluate(f"() => {{ const c = Chart.getChart('{canvas_id}'); return {expression}; }}")


def _show_weekly(page):
    page.locator("#chart-type-btn").click()
    page.wait_for_function("() => { const c = Chart.getChart('weekly-chart'); return c && c.data.labels.length; }")


class _TimeZoneFlows:
    OFFSET = "+00:00"

    def test_daily_chart_puts_each_weight_on_its_day(self, weights):
        page = weights()
        last_week = DAYS[-7:]
        assert _chart(page, "weight-chart", "c.data.labels.slice(-1)[0]") == "Nov 4"
        assert _chart(page, "weight-chart", "c.data.datasets[0].data.slice(-7)") == [WEIGHT[d] for d in last_week]

    def test_seven_day_average_uses_the_last_seven_days(self, weights):
        page = weights()
        expected = sum(WEIGHT[d] for d in DAYS[-7:]) / 7
        assert _chart(page, "weight-chart", "c.data.datasets[2].data.slice(-1)[0]") == expected

    def test_rolling_weeks_end_today(self, weights):
        page = weights("rolling")
        _show_weekly(page)
        assert _chart(page, "weekly-chart", "c.data.labels") == ["10/22–10/28", "10/29–11/04"]

    def test_calendar_weeks_run_monday_to_sunday(self, weights):
        page = weights("iso")
        _show_weekly(page)
        assert _chart(page, "weekly-chart", "c.data.labels") == ["10/19–10/25", "10/26–11/01", "11/02–11/08"]

    def test_table_lists_each_day_once_newest_first(self, weights):
        page = weights()
        page.locator("#view-toggle-btn").click()
        expect(page.locator("#data-table-wrap")).to_be_visible()
        expect(page.locator("tr.daily-row")).to_have_count(7)  # the default 7-day range
        listed = page.locator("tr.daily-row td.cell-weight").evaluate_all("cells => cells.map(c => c.dataset.date)")
        assert listed == DAYS[-7:][::-1]


@pytest.mark.browser_context_args(timezone_id="Pacific/Honolulu")
class TestHonolulu(_TimeZoneFlows):
    OFFSET = "-10:00"


@pytest.mark.browser_context_args(timezone_id="America/New_York")
class TestNewYork(_TimeZoneFlows):
    OFFSET = "-05:00"


@pytest.mark.browser_context_args(timezone_id="Europe/Berlin")
class TestBerlin(_TimeZoneFlows):
    OFFSET = "+01:00"


@pytest.mark.browser_context_args(timezone_id="Asia/Tokyo")
class TestTokyo(_TimeZoneFlows):
    OFFSET = "+09:00"


# ── Clock changes: a day can be 23 or 25 hours, so counting days as 24 hours slips ──


def _open(page, path):
    page.goto(path)
    page.wait_for_load_state("networkidle")
    return page


def _insight(page, label):
    page.locator("#profile-btn").click()
    page.locator("#menu-modal .menu-modal-btn", has_text="Insights").click()
    return page.locator(".insight-card", has_text=label).locator(".insight-value")


@pytest.mark.browser_context_args(timezone_id="America/New_York")
def test_largest_weekly_loss_counts_a_week_with_a_25_hour_day(signed_in_page, client):
    seed_weight(client, "2026-10-26", 205.0)
    seed_weight(client, "2026-11-02", 200.0)  # 7 days later, across the clocks going back
    signed_in_page.clock.set_fixed_time("2026-11-02T12:00:00-05:00")
    expect(_insight(_open(signed_in_page, "/"), "Largest Weekly Loss")).not_to_have_text("—")


@pytest.mark.browser_context_args(timezone_id="America/New_York")
def test_daily_fluctuation_counts_a_23_hour_day(signed_in_page, client):
    seed_weight(client, "2026-03-08", 200.0)  # the clocks go forward, so this day has 23 hours
    seed_weight(client, "2026-03-09", 199.0)
    signed_in_page.clock.set_fixed_time("2026-03-09T12:00:00-04:00")
    expect(_insight(_open(signed_in_page, "/"), "Avg Daily Fluctuation")).not_to_have_text("—")


@pytest.mark.browser_context_args(timezone_id="America/New_York")
def test_workouts_this_week_includes_seven_days_late_in_the_evening(signed_in_page, client):
    client.post("/api/workout", json={"date": "2026-10-31", "type": "Yoga", "duration_min": 30, "kcal": 100})
    # 11:30pm on Friday 11-06: this week is 10-31 to 11-06, across the clocks going back
    signed_in_page.clock.set_fixed_time("2026-11-06T23:30:00-05:00")
    expect(_open(signed_in_page, "/workouts").locator("#wp-count")).to_have_text("1")
