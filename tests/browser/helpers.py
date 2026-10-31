"""Helpers shared by the browser tests."""


def listener_count(page):
    """Every event listener currently attached anywhere on the page: on window,
    document, and every element (read through Chrome's DevTools protocol)."""
    cdp = page.context.new_cdp_session(page)
    try:
        total = 0
        for target in ("window", "document"):
            obj = cdp.send("Runtime.evaluate", {"expression": target})["result"]["objectId"]
            total += len(cdp.send("DOMDebugger.getEventListeners",
                                  {"objectId": obj, "depth": -1, "pierce": True})["listeners"])
        return total
    finally:
        cdp.detach()


def settle(page, action, until=None, quiet_ms=200, timeout_ms=30_000):
    """Run `action()`, wait for the JS condition `until` (if given), then wait
    until every request sent meanwhile has finished and none has started for
    `quiet_ms` (so chained requests, e.g. a page script and then its data, count).

    (wait_for_load_state("networkidle") can't be used for this: once a page has
    been idle it returns at once, even with dozens of requests still queued.)"""
    pending = set()

    def started(request):
        pending.add(request)

    def done(request):
        pending.discard(request)

    page.on("request", started)
    page.on("requestfinished", done)
    page.on("requestfailed", done)
    try:
        action()
        if until:
            page.wait_for_function(until)
        waited = quiet = 0
        while quiet < quiet_ms:
            assert waited < timeout_ms, f"{len(pending)} requests still pending"
            page.wait_for_timeout(50)          # lets Playwright deliver the request events
            waited += 50
            quiet = 0 if pending else quiet + 50
    finally:
        page.remove_listener("request", started)
        page.remove_listener("requestfinished", done)
        page.remove_listener("requestfailed", done)


def remount(page, times=1):
    """Leave and restart the current page in place `times` times, then wait for
    every request those restarts sent to finish."""
    settle(page, lambda: page.evaluate("n => { for (let i = 0; i < n; i++) appRouter.remount(); }", times))
