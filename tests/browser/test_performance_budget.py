"""Performance budget: each page's download size, request count and load speed must
stay under agreed limits, so a heavy image or a slow change fails CI instead of
reaching visitors.

Sizes are what the browser actually received for a first visit with an empty cache.
The local test server doesn't compress text like Vercel does, so these are an upper
bound on what visitors download. Load speed is measured with the network slowed to a
typical mobile connection, which makes it depend on page weight and round trips
rather than on how fast the test machine happens to be.
"""

import pytest

# Limits leave about 20% headroom over the measured size on 2026-11-02, so normal
# changes pass but a regression like an unoptimized image fails. Raise a limit only
# as a deliberate decision, noted in the changelog.
BUDGETS = {
    "/login": {"kb": 150, "requests": 6},  # measured 124 KB, 4 requests
    "/": {"kb": 980, "requests": 25},  # 811 KB, 21
    "/weights": {"kb": 1080, "requests": 26},  # 895 KB, 22
    "/workouts": {"kb": 880, "requests": 24},  # 733 KB, 20
}

# Google's "good" Largest Contentful Paint is under 2.5 s on a mobile connection.
LCP_LIMIT_MS = 2500

# Roughly a good 4G connection: 10 Mbps down, 3 Mbps up, 40 ms round trip.
NETWORK = {
    "offline": False,
    "latency": 40,
    "downloadThroughput": 10_000_000 / 8,
    "uploadThroughput": 3_000_000 / 8,
}

LCP_PROBE = """
window.__lcp = 0;
new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) window.__lcp = entry.startTime;
}).observe({ type: 'largest-contentful-paint', buffered: true });
"""


def _measure(page, path, network):
    """Load `path` on a slowed network with an empty cache; return (kb, requests, lcp_ms).

    The page is loaded once first, unmeasured, so the test server's one-off startup work
    (its first database connection, first template render) isn't counted as load speed.
    """
    page.goto(path)
    page.wait_for_load_state("networkidle")

    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    cdp.send("Network.emulateNetworkConditions", network)
    page.add_init_script(LCP_PROBE)

    received = []
    page.on("requestfinished", lambda request: received.append(request))
    page.goto(path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)

    total = 0
    for request in received:
        sizes = request.sizes()
        total += sizes["responseBodySize"] + sizes["responseHeadersSize"]
    lcp = page.evaluate("window.__lcp")
    return total / 1024, len(received), lcp


def _check(page, path, network=NETWORK):
    kb, requests, lcp = _measure(page, path, network)
    budget = BUDGETS[path]
    print(f"\n{path}: {kb:.0f} KB in {requests} requests, LCP {lcp:.0f} ms")
    assert kb <= budget["kb"], f"{path} downloads {kb:.0f} KB, over its {budget['kb']} KB budget"
    assert requests <= budget["requests"], f"{path} makes {requests} requests, over its {budget['requests']} budget"
    assert 0 < lcp <= LCP_LIMIT_MS, f"{path} Largest Contentful Paint {lcp:.0f} ms, over {LCP_LIMIT_MS} ms"


def test_login_page_stays_within_budget(signed_out_page):
    _check(signed_out_page, "/login")


@pytest.mark.parametrize("path", ["/", "/weights", "/workouts"])
def test_signed_in_pages_stay_within_budget(signed_in_page, path):
    _check(signed_in_page, path)


# The budget must actually catch regressions, not just pass.


def test_an_oversized_image_breaks_the_budget(signed_in_page):
    page = signed_in_page
    bloated = b"0" * 400 * 1024
    page.route("**/static/homebackground.webp", lambda route: route.fulfill(body=bloated, content_type="image/webp"))
    with pytest.raises(AssertionError, match="over its 980 KB budget"):
        _check(page, "/")


def test_a_slow_load_breaks_the_budget(signed_in_page):
    slow = {**NETWORK, "latency": 400, "downloadThroughput": 1_000_000 / 8}
    with pytest.raises(AssertionError, match="Largest Contentful Paint"):
        _check(signed_in_page, "/", slow)
