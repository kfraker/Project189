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


def remount(page, times=1, timeout_ms=30_000):
    """Leave and restart the current page in place `times` times, then wait for
    every request those restarts sent to finish.

    (wait_for_load_state("networkidle") can't be used here: once a page has
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
        page.evaluate("n => { for (let i = 0; i < n; i++) appRouter.remount(); }", times)
        waited = 0
        while pending:
            assert waited < timeout_ms, f"{len(pending)} requests still pending after restarts"
            page.wait_for_timeout(50)          # lets Playwright deliver the finished events
            waited += 50
    finally:
        page.remove_listener("request", started)
        page.remove_listener("requestfinished", done)
        page.remove_listener("requestfailed", done)
