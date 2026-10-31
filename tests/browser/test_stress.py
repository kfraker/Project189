"""Stress test for in-page navigation (migration M6.1): 30+ page changes mixing
nav clicks, Back, Forward and refreshes. Nothing may pile up, and every page
must look the same after an in-page arrival as after a fresh full load.

The page-error guard runs throughout, so any JS error fails the test.
"""
import base64
import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.browser.helpers import listener_count, settle
from tests.conftest import seed_setting, seed_weight

PAGES = {"home": ("Home", "/"), "weights": ("Weigh-ins", "/weights"), "workouts": ("Workouts", "/workouts")}

# Nav clicks by page name, plus "back", "forward" and "reload".
ROUTE = (["weights", "workouts", "home", "back", "back", "forward", "forward", "weights",
          "home", "reload"] * 3
         + ["workouts", "weights", "workouts", "back", "home"])


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


@pytest.fixture()
def seeded(signed_in_page, client):
    seed_setting(client, "starting_weight", 230.0)
    seed_setting(client, "goal_weight", 189.0)
    for i in range(1, 40):
        seed_weight(client, _day(i), 210.0 - i / 3)
    for i in range(1, 6):
        client.post("/api/workout", json={"date": _day(i), "type": "Yoga", "duration_min": 20 + i,
                                          "kcal": 100, "note": ""})
    signed_in_page.set_viewport_size({"width": 1280, "height": 800})
    return signed_in_page


def _expected_after(step, history, position):
    """Which page a step should land on, tracking the browser's history list."""
    if step == "back":
        position -= 1
    elif step == "forward":
        position += 1
    elif step != "reload":
        del history[position + 1:]
        history.append(step)
        position += 1
    return history[position], position


def _take(page, step):
    if step == "back":
        page.go_back()
    elif step == "forward":
        page.go_forward()
    elif step == "reload":
        page.reload()
    else:
        page.get_by_role("navigation", name="Pages").get_by_role("link", name=PAGES[step][0]).click()


def _settled(page):
    """No background ghost left, no fade in progress."""
    expect(page.locator(".bg-ghost")).to_have_count(0, timeout=5000)
    page.wait_for_function("() => !document.documentElement.classList.contains('page-fading')")


def test_thirty_plus_page_changes_leave_nothing_behind(seeded):
    page = seeded
    page.goto("/")
    page.wait_for_load_state("networkidle")
    history, position = ["home"], 0
    home_listeners = []

    for i, step in enumerate(ROUTE):
        expected, position = _expected_after(step, history, position)
        settle(page, lambda: _take(page, step), until=f"() => window.appRouter && appRouter.current === '{expected}'")
        _settled(page)
        label, path = PAGES[expected]
        expect(page).to_have_url(re.compile(re.escape(path) + r"$"))
        expect(page.get_by_role("navigation", name="Pages").locator("a.active")).to_have_accessible_name(label)
        assert page.evaluate("Object.keys(window.Chart?.instances ?? {}).length") <= 2, f"step {i}: {step}"
        assert page.locator('[data-region="bg"] > *').count() == 1
        assert page.locator("style[data-page-style]").count() == 1
        if expected == "home" and step != "reload":
            home_listeners.append(listener_count(page))

    assert len(ROUTE) >= 30
    assert len(set(home_listeners)) == 1, f"listeners on Home drifted: {home_listeners}"


# ── In-page arrival looks the same as a fresh load ───────────────────────────

def _screenshot(page):
    page.mouse.move(0, 0)
    page.wait_for_timeout(1500)                     # charts and bars finish animating
    # Endless animations (the streak's flame glow) are frozen on their first frame,
    # or two screenshots would catch them at different moments.
    return base64.b64encode(page.screenshot(animations="disabled")).decode()


def _differing_share(page, a, b):
    """Share of pixels that differ noticeably between two screenshots, compared in
    the browser (no image library needed)."""
    return page.evaluate("""async ([a, b]) => {
        const load = src => new Promise(done => { const img = new Image(); img.onload = () => done(img); img.src = src; });
        const [ia, ib] = await Promise.all([load('data:image/png;base64,' + a), load('data:image/png;base64,' + b)]);
        const pixels = img => { const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
                                const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
                                return ctx.getImageData(0, 0, c.width, c.height).data; };
        const pa = pixels(ia), pb = pixels(ib);
        let differ = 0;
        for (let i = 0; i < pa.length; i += 4)
            if (Math.abs(pa[i] - pb[i]) + Math.abs(pa[i+1] - pb[i+1]) + Math.abs(pa[i+2] - pb[i+2]) > 48) differ++;
        return differ / (pa.length / 4);
    }""", [a, b])


@pytest.mark.parametrize("name", ["weights", "workouts", "home"])
def test_in_page_arrival_looks_like_a_fresh_load(seeded, name):
    page = seeded
    label, path = PAGES[name]
    page.goto(path)
    page.wait_for_load_state("networkidle")
    fresh = _screenshot(page)

    other = "workouts" if name != "workouts" else "weights"
    page.goto(PAGES[other][1])
    page.wait_for_load_state("networkidle")
    link = page.get_by_role("navigation", name="Pages").get_by_role("link", name=label)
    settle(page, link.click, until=f"() => appRouter.current === '{name}'")
    _settled(page)
    page.evaluate("document.activeElement.blur()")  # focus moved to the content; a fresh load has none
    arrived = _screenshot(page)

    share = _differing_share(page, fresh, arrived)
    assert share < 0.002, f"{name}: {share:.2%} of pixels differ from a fresh load"
