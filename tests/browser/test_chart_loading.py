"""Chart.js loads on demand (migration M1.3): only Weigh-ins downloads it, only
once, and the charts still draw after waiting for it."""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.conftest import seed_weight

CHART_JS = "chart.umd.min.js"


def _chart_js_requests(page, action):
    """Run `action` and return the Chart.js requests the page made meanwhile."""
    seen = []
    page.on("request", lambda req: CHART_JS in req.url and seen.append(req.url))
    action()
    page.wait_for_load_state("networkidle")
    return seen


@pytest.mark.parametrize("path", ["/", "/workouts"])
def test_other_pages_never_download_chart_js(signed_in_page, path):
    page = signed_in_page
    assert _chart_js_requests(page, lambda: page.goto(path)) == []
    assert page.evaluate("typeof window.Chart") == "undefined"
    assert page.locator(f'script[src*="{CHART_JS}"]').count() == 0


def test_weigh_ins_loads_chart_js_once_and_draws_both_charts(signed_in_page, client):
    for i in range(10):
        seed_weight(client, (date.today() - timedelta(days=i)).isoformat(), 200.0 - i / 2)
    page = signed_in_page
    requests = _chart_js_requests(page, lambda: page.goto("/weights"))
    assert len(requests) == 1
    page.wait_for_function("() => window.Chart && Chart.getChart('weight-chart')?.data.labels.length > 0")

    # The weekly chart is drawn later, on first switch; it reuses the loaded library.
    later = _chart_js_requests(page, lambda: page.locator("#chart-type-btn").click())
    page.wait_for_function("() => Chart.getChart('weekly-chart')?.data.labels.length > 0")
    assert later == []
    assert page.locator(f'script[src*="{CHART_JS}"]').count() == 1
    assert page.evaluate("Chart.registry.plugins.get('chartAxisLabels') !== undefined")


def test_load_script_once_shares_one_download(signed_in_page):
    page = signed_in_page
    page.goto("/")
    result = page.evaluate("""async () => {
        const src = 'data:text/javascript,window.probeRuns=(window.probeRuns||0)+1';
        const a = window.loadScriptOnce(src), b = window.loadScriptOnce(src);
        await a; await window.loadScriptOnce(src);
        return { same: a === b, runs: window.probeRuns,
                 tags: [...document.scripts].filter(s => s.src === src).length };
    }""")
    assert result == {"same": True, "runs": 1, "tags": 1}


@pytest.mark.allow_page_errors          # the missing file is the point of the test
def test_load_script_once_failure_rejects_and_can_retry(signed_in_page):
    page = signed_in_page
    page.goto("/")
    result = page.evaluate("""async () => {
        const src = '/static/js/does-not-exist.js';
        const first = await window.loadScriptOnce(src).then(() => 'loaded', e => e.message);
        const retry = window.loadScriptOnce(src);
        await retry.catch(() => {});
        return { first, tags: document.querySelectorAll('script[src="' + src + '"]').length };
    }""")
    assert result["first"] == "Could not load /static/js/does-not-exist.js"
    assert result["tags"] == 2                 # a failure isn't cached, so the retry really retries
