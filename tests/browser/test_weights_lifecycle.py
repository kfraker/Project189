"""Weigh-ins runs on the page lifecycle (migrations M3.3 and M3.4).

M3.3: the page registers, leaving it removes its listeners, shared names, the
chart tooltip it adds to <body>, and the note editor's body class, and it no
longer carries its own copies of shell code.
M3.4: its charts are destroyed and its resize watchers stopped on leave, so
restarting it in place leaves nothing behind and never more than 2 charts exist.

Every test also passes the page-error guard, so "zero errors" is checked throughout.
"""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.browser.helpers import listener_count, remount
from tests.conftest import seed_weight

TODAY = date.today().isoformat()

# Names Weigh-ins shares on window for the shell and its own parts to call.
WEIGHTS_SHARED = ["refreshChart", "refreshWeeklyChart", "renderTable", "setView", "setTablePage",
                  "setWeeklyRange", "applyChartNav", "getChartRange", "getWeeklyChartRange",
                  "openWeightModal", "openNoteEditor", "refreshHeaderStats", "currentChartPage"]


@pytest.fixture()
def weights_page(signed_in_page, client):
    for i in range(10):
        seed_weight(client, (date.today() - timedelta(days=i)).isoformat(), 200.0 - i / 2)
    signed_in_page.goto("/weights")
    signed_in_page.wait_for_load_state("networkidle")
    signed_in_page.wait_for_function("() => window.Chart && Chart.getChart('weight-chart')?.data.labels.length > 0")
    return signed_in_page


def test_weigh_ins_registers_as_a_page_and_shares_its_functions(weights_page):
    assert weights_page.evaluate("appRouter.current") == "weights"
    assert weights_page.evaluate("names => names.filter(n => !(n in window))", WEIGHTS_SHARED) == []


def test_uses_the_shells_save_pref_and_date_format(weights_page):
    """Weigh-ins used to carry its own copies of savePref and fmtDateShort, which
    silently replaced the shell's; now the shell's are the only ones."""
    page = weights_page
    with open("static/js/pages/weights.js", encoding="utf-8") as f:
        source = f.read()
    for duplicate in ("window.savePref =", "function fmtDateShort", "classList.remove('preload')",
                      "history.scrollRestoration"):
        assert duplicate not in source
    with page.expect_response("**/api/preference"):
        page.evaluate("savePref('pref_probe', 'x')")
    assert page.evaluate("localStorage.getItem('pref_probe')") == "x"


def test_leaving_removes_everything_the_page_set_up(weights_page):
    page = weights_page
    expect(page.locator("body > #chart-tooltip")).to_have_count(1)
    page.evaluate("appRouter.leave()")
    assert page.evaluate("names => names.filter(n => n in window)", WEIGHTS_SHARED) == []
    expect(page.locator("#chart-tooltip")).to_have_count(0)               # removed from <body>
    page.locator("#view-toggle-btn").click()
    expect(page.locator("#data-table-wrap")).to_be_hidden()              # its buttons are disconnected
    page.locator("#chart-add-btn").click()
    expect(page.locator("#history-modal")).to_be_hidden()


def test_leaving_mid_note_edit_clears_the_body_class(weights_page):
    page = weights_page
    page.locator("#view-toggle-btn").click()
    page.locator(f'tr.daily-row:has(td.cell-weight[data-date="{TODAY}"])').get_by_role("button", name="Add note").click()
    expect(page.locator("#note-popover")).to_be_visible()
    assert page.evaluate("document.body.classList.contains('note-open')")
    page.evaluate("appRouter.leave()")
    assert not page.evaluate("document.body.classList.contains('note-open')")


# ── Charts (M3.4) ───────────────────────────────────────────────────────────

def _chart_count(page):
    return page.evaluate("Object.keys(Chart.instances).length")


def _show_weekly(page):
    page.locator("#chart-type-btn").click()
    page.wait_for_function("() => Chart.getChart('weekly-chart')?.data.labels.length > 0")


def test_twenty_restarts_leave_listeners_globals_and_charts_flat(weights_page):
    page = weights_page
    _show_weekly(page)                                          # both charts exist
    remount(page)
    _show_weekly(page)
    listeners = listener_count(page)
    names = page.evaluate("Object.keys(window).length")
    assert _chart_count(page) == 2

    for _ in range(4):                                          # 20 restarts, both charts each time
        remount(page, 5)
        _show_weekly(page)
        assert _chart_count(page) <= 2
    assert _chart_count(page) == 2
    assert listener_count(page) == listeners
    assert page.evaluate("Object.keys(window).length") == names
    expect(page.locator("body > #chart-tooltip")).to_have_count(1)     # one tooltip, not 21


def test_after_restarts_a_range_click_fetches_once(weights_page):
    page = weights_page
    remount(page, 20)

    fetches = []
    page.on("request", lambda r: "/api/weights?range=" in r.url and fetches.append(r.url))
    page.locator("#mp-filter-btn").click()
    page.locator('#mp-daily-ranges .range-btn[data-range="7d"]').click()
    page.wait_for_function("() => Chart.getChart('weight-chart')?.data.labels.length === 7")
    assert len(fetches) == 1



def test_leaving_destroys_both_charts(weights_page):
    page = weights_page
    _show_weekly(page)
    page.evaluate("appRouter.leave()")
    assert _chart_count(page) == 0


def test_leaving_while_charts_load_draws_nothing_afterwards(weights_page):
    """Restart then leave at once: the restarted page's chart data arrives after
    it was left, and must not draw a chart on a page that's gone."""
    page = weights_page
    finished = []
    page.on("requestfinished", lambda r: "/api/weights?range=" in r.url and finished.append(r))
    page.evaluate("appRouter.remount(); appRouter.leave()")
    for _ in range(200):                                        # until the chart data has come back
        if finished:
            break
        page.wait_for_timeout(50)
    assert finished
    page.wait_for_timeout(300)                                  # time for a (wrong) redraw
    assert _chart_count(page) == 0


def test_saving_settings_on_weigh_ins_redraws_the_charts(weights_page):
    """The shell's Settings save calls back into Weigh-ins (refreshChart,
    renderTable, ...): switching to kg redraws the chart in kg."""
    page = weights_page
    page.locator("#profile-btn").click()
    page.locator("#menu-modal .menu-modal-btn", has_text="Settings").click()
    page.locator("#prof-kg-btn").click()
    with page.expect_response("**/api/preference"):
        page.locator("#settings-save").click()
    expect(page.locator("#settings-modal")).to_be_hidden()
    page.wait_for_function(
        "() => { const d = Chart.getChart('weight-chart')?.data.datasets[0].data.filter(v => v != null);"
        " return d && d.length && Math.max(...d) < 100; }")           # ~200 lbs → ~91 kg
    assert _chart_count(page) == 1
