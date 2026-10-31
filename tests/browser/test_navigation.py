"""In-page navigation (migration M4.1): a header nav click swaps in the next
page's regions, style and script without a full page load, and keeps the shell
(cursor, menus) as it is. Anything unexpected falls back to a normal page load.
M4.2: the address bar, tab title and highlighted nav button follow along.
M4.3: Back and Forward swap pages the same way.
M4.4: the latest click wins, and clicking the page you're on does nothing.
M4.5: focus moves to the new page's content and its name is announced.
M5.1: the page's parts fade out while the next page downloads, then fade in.
M5.2: backgrounds cross-fade once the new background image has loaded.

Every test also passes the page-error guard, so "zero errors" is checked throughout.
"""
import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.browser.helpers import listener_count, settle
from tests.conftest import seed_setting, seed_weight


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


def _mark_document(page):
    """Tag the current document and the cursor element; a full page load loses both.
    (Not a window variable: leaving a page deletes those it created.)"""
    page.evaluate("document.documentElement.dataset.sameDocument = '1';"
                  "document.getElementById('site-cursor').dataset.kept = '1'")


def _still_same_document(page):
    return page.evaluate("document.documentElement.dataset.sameDocument === '1' &&"
                         "document.getElementById('site-cursor').dataset.kept === '1'")


def _go(page, label, name):
    """Click a header nav link and wait until that page has started."""
    link = page.get_by_role("navigation", name="Pages").get_by_role("link", name=label)
    settle(page, link.click, until=f"() => appRouter.current === '{name}'")


@pytest.fixture()
def started_on_home(signed_in_page, client):
    seed_setting(client, "starting_weight", 230.0)
    seed_setting(client, "goal_weight", 189.0)
    for i in range(1, 11):
        seed_weight(client, _day(i), 210.0 - i / 2)
    client.post("/api/workout", json={"date": _day(1), "type": "Yoga", "duration_min": 20, "kcal": 100, "note": ""})
    signed_in_page.goto("/")
    signed_in_page.wait_for_load_state("networkidle")
    _mark_document(signed_in_page)
    return signed_in_page


def test_nav_click_swaps_the_page_without_a_full_load(started_on_home):
    page = started_on_home
    _go(page, "Workouts", "workouts")
    assert _still_same_document(page)                       # shell and cursor never rebuilt

    expect(page.locator('[data-region="header_title"] h1')).to_have_text("Workouts")
    expect(page.locator('[data-region="header_stats"] #wp-count')).to_have_text("1")
    expect(page.locator('[data-region="bg"] .wp-bg')).to_have_count(1)
    expect(page.locator('[data-region="footer_left"] #wp-range-menu')).to_have_count(1)
    expect(page.locator('[data-region="footer_add"] #wp-add-btn')).to_have_count(1)
    assert page.evaluate("document.querySelector('[data-region=\"healthbar\"]').children.length") == 0
    expect(page.locator(".wp-row")).to_have_count(1)

    styles = page.locator("style[data-page-style]")
    expect(styles).to_have_count(1)                          # Home's style swapped out
    assert ".wp-bg" in styles.inner_text() and ".mp-bg" not in styles.inner_text()
    assert page.evaluate("'refreshPlatesData' in window") is False          # Home was left


def test_every_page_works_after_arriving_in_page(started_on_home):
    page = started_on_home
    _go(page, "Weigh-ins", "weights")
    page.wait_for_function("() => window.Chart && Chart.getChart('weight-chart')?.data.labels.length > 0")
    expect(page.locator("#wt-logged-week")).not_to_have_text("—")

    _go(page, "Workouts", "workouts")
    assert page.evaluate("Object.keys(Chart.instances).length") == 0        # Weigh-ins' charts gone
    expect(page.locator("body > #chart-tooltip")).to_have_count(0)
    expect(page.locator(".wp-row")).to_have_count(1)

    _go(page, "Home", "home")
    expect(page.locator("#current-lbs-num")).to_have_text("209.5")
    expect(page.locator("#lost-lbs-num")).to_have_text("20.5")
    expect(page.locator("#healthbar-fill-track")).to_have_attribute("aria-valuenow", re.compile(r"^[1-9]"))

    page.locator("#mp-footer-add-btn").click()                              # its buttons work
    expect(page.locator("#quick-add-modal")).to_be_visible()
    assert _still_same_document(page)


def test_coming_back_reuses_page_scripts_and_chart_library(started_on_home):
    page = started_on_home
    downloads = []
    page.on("request", lambda r: re.search(r"/static/js/pages/|chart\.umd", r.url) and downloads.append(r.url))
    for _ in range(2):
        _go(page, "Weigh-ins", "weights")
        page.wait_for_function("() => window.Chart && Chart.getChart('weight-chart')?.data.labels.length > 0")
        _go(page, "Workouts", "workouts")
        _go(page, "Home", "home")
    names = sorted(re.search(r"(weights|workouts|home)\.js|chart\.umd", u).group(0) for u in downloads)
    assert names == ["chart.umd", "weights.js", "workouts.js"]              # each fetched once; Home's already ran


def test_round_trips_leave_listeners_flat(started_on_home):
    page = started_on_home
    _go(page, "Weigh-ins", "weights")
    _go(page, "Workouts", "workouts")
    _go(page, "Home", "home")
    listeners = listener_count(page)
    for _ in range(3):
        _go(page, "Weigh-ins", "weights")
        _go(page, "Workouts", "workouts")
        _go(page, "Home", "home")
    assert listener_count(page) == listeners
    assert page.locator("script[data-page-script]").count() == 3            # one tag per page, ever


def test_shell_menu_still_works_after_navigating(started_on_home):
    page = started_on_home
    _go(page, "Workouts", "workouts")
    page.locator("#profile-btn").click()
    page.locator("#menu-modal .menu-modal-btn", has_text="Settings").click()
    page.locator("#prof-kg-btn").click()
    with page.expect_response("**/api/preference"):
        page.locator("#settings-save").click()
    expect(page.locator("#settings-modal")).to_be_hidden()
    expect(page.locator(".wp-row")).to_have_count(1)
    page.locator("#menu-modal-close").click()                               # Settings returns to the menu
    _go(page, "Home", "home")
    expect(page.locator(".plate").first).to_have_class("plate kg-primary")  # new unit applies on arrival


# ── Address bar, tab title, highlighted nav button (M4.2) ───────────────────

PAGES = [("Weigh-ins", "weights", "/weights", "Weigh-ins — Sweat Equity"),
         ("Workouts", "workouts", "/workouts", "Workouts — Sweat Equity"),
         ("Home", "home", "/", "Sweat Equity")]


def test_address_bar_title_and_nav_button_follow_each_click(started_on_home):
    page = started_on_home
    nav = page.get_by_role("navigation", name="Pages")
    for label, name, path, title in PAGES:
        _go(page, label, name)
        expect(page).to_have_url(re.compile(re.escape(path) + r"$"))
        expect(page).to_have_title(title)
        expect(nav.locator("a.active")).to_have_count(1)
        expect(nav.get_by_role("link", name=label)).to_have_class(re.compile(r"\bactive\b"))
    assert _still_same_document(page)
    assert page.evaluate("history.length") >= 4                             # one entry per click


def test_refresh_after_navigating_reloads_the_page_you_are_on(started_on_home):
    page = started_on_home
    _go(page, "Workouts", "workouts")
    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.evaluate("appRouter.current") == "workouts"
    assert not _still_same_document(page)                                   # a real reload
    expect(page.locator(".wp-row")).to_have_count(1)


# ── Back / Forward (M4.3) ───────────────────────────────────────────────────

def _history(page, step, name):
    """Press Back (step=-1) or Forward (step=1) and wait until that page has started."""
    move = page.go_back if step < 0 else page.go_forward
    settle(page, move, until=f"() => appRouter.current === '{name}'")


def _shows(page, path, title, label):
    expect(page).to_have_url(re.compile(re.escape(path) + r"$"))
    expect(page).to_have_title(title)
    nav = page.get_by_role("navigation", name="Pages")
    expect(nav.locator("a.active")).to_have_accessible_name(label)


def test_back_and_forward_swap_pages_in_place(started_on_home):
    page = started_on_home
    _go(page, "Weigh-ins", "weights")
    _go(page, "Workouts", "workouts")
    entries = page.evaluate("history.length")

    _history(page, -1, "weights")
    _shows(page, "/weights", "Weigh-ins — Sweat Equity", "Weigh-ins")
    page.wait_for_function("() => Chart.getChart('weight-chart')?.data.labels.length > 0")

    _history(page, -1, "home")
    _shows(page, "/", "Sweat Equity", "Home")
    expect(page.locator("#current-lbs-num")).to_have_text("209.5")

    _history(page, 1, "weights")
    _history(page, 1, "workouts")
    _shows(page, "/workouts", "Workouts — Sweat Equity", "Workouts")
    expect(page.locator(".wp-row")).to_have_count(1)

    assert page.evaluate("history.length") == entries                       # Back/Forward add no entries
    assert _still_same_document(page)


def test_back_from_a_fragment_link_stays_on_the_page(started_on_home):
    """The "Skip to main content" link adds a #main-content history entry; going
    Back from it must not reload or restart the page."""
    page = started_on_home
    _go(page, "Workouts", "workouts")
    page.evaluate("location.hash = '#main-content'")
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    page.go_back()
    page.wait_for_timeout(300)
    expect(page).to_have_url(re.compile(r"/workouts$"))
    assert page.evaluate("appRouter.current") == "workouts"
    assert requests == []
    assert _still_same_document(page)


def test_back_falls_back_to_a_full_load_without_an_extra_entry(started_on_home):
    page = started_on_home
    _go(page, "Weigh-ins", "weights")
    _go(page, "Workouts", "workouts")
    entries = page.evaluate("history.length")
    page.route("**/weights", lambda route: route.fulfill(status=200, content_type="text/html",
                                                         body="<html><body>not an app page</body></html>"),
               times=1)
    page.go_back()
    page.wait_for_function("() => window.appRouter && appRouter.current === 'weights'")
    assert not _still_same_document(page)                                   # it was a full load
    assert page.evaluate("history.length") == entries
    page.go_forward()                                                       # Forward still leads to Workouts
    expect(page).to_have_url(re.compile(r"/workouts$"))


# ── Rapid and repeat clicks (M4.4) ──────────────────────────────────────────

def _click(page, label):
    page.get_by_role("navigation", name="Pages").get_by_role("link", name=label).click()


def _hold(page, pattern):
    """Hold back the answers to requests matching `pattern` until released."""
    held = []
    page.route(pattern, lambda route: held.append(route))

    def release():
        for route in held:
            route.continue_()
        page.unroute(pattern)
    return held, release


def test_clicking_the_page_you_are_on_does_nothing(started_on_home):
    page = started_on_home
    requests = []
    page.on("request", lambda r: r.resource_type in ("document", "fetch", "xhr", "script") and requests.append(r.url))
    _click(page, "Home")
    page.wait_for_timeout(300)
    assert requests == []
    assert page.evaluate("appRouter.current") == "home"
    assert _still_same_document(page)


def test_a_slow_earlier_click_cannot_replace_a_later_one(started_on_home):
    page = started_on_home
    held, release = _hold(page, "**/weights")
    _click(page, "Weigh-ins")
    _go(page, "Workouts", "workouts")                                       # the later click lands first
    assert len(held) == 1
    settle(page, release)                                                   # now the earlier page arrives
    page.wait_for_timeout(300)
    assert page.evaluate("appRouter.current") == "workouts"
    expect(page).to_have_url(re.compile(r"/workouts$"))
    expect(page).to_have_title("Workouts — Sweat Equity")
    expect(page.locator(".wp-row")).to_have_count(1)


def test_a_slow_page_script_cannot_take_over_a_later_page(started_on_home):
    """Weigh-ins' page arrives and is swapped in, but its script is still
    downloading when Workouts is clicked. When the script arrives it must
    register without starting (it would run against Workouts' page)."""
    page = started_on_home
    held, release = _hold(page, "**/static/js/pages/weights.js*")
    _click(page, "Weigh-ins")
    expect(page).to_have_url(re.compile(r"/weights$"))                      # swapped, script pending
    _go(page, "Workouts", "workouts")
    settle(page, release)
    page.wait_for_timeout(300)
    assert page.evaluate("appRouter.current") == "workouts"
    expect(page.locator(".wp-row")).to_have_count(1)

    _go(page, "Weigh-ins", "weights")                                       # registered: starts without a download
    page.wait_for_function("() => window.Chart && Chart.getChart('weight-chart')?.data.labels.length > 0")


def test_clicking_the_current_page_cancels_a_pending_click(started_on_home):
    page = started_on_home
    held, release = _hold(page, "**/weights")
    _click(page, "Weigh-ins")
    _click(page, "Home")                                                    # changed my mind
    settle(page, release)
    page.wait_for_timeout(300)
    assert page.evaluate("appRouter.current") == "home"
    expect(page).to_have_url(re.compile(r"/$"))
    assert _still_same_document(page)


def test_many_quick_clicks_end_on_the_last_one(started_on_home):
    page = started_on_home
    for label in ["Weigh-ins", "Workouts", "Home", "Weigh-ins", "Workouts", "Weigh-ins", "Workouts"]:
        _click(page, label)
    settle(page, lambda: None, until="() => appRouter.current === 'workouts'")
    page.wait_for_timeout(500)
    assert page.evaluate("appRouter.current") == "workouts"
    expect(page).to_have_url(re.compile(r"/workouts$"))
    expect(page.locator(".wp-row")).to_have_count(1)
    assert page.evaluate("Object.keys(window.Chart?.instances ?? {}).length") == 0


# ── Screen readers and keyboard (M4.5) ──────────────────────────────────────

def _announced(page):
    return page.locator("#status-announce")


def test_focus_moves_to_the_content_and_the_page_is_announced(started_on_home):
    page = started_on_home
    for label, name, *_ in PAGES:
        _go(page, label, name)
        assert page.evaluate("document.activeElement.id") == "main-content"
        expect(_announced(page)).to_have_text(f"{label} page")


def test_keyboard_user_lands_in_the_new_pages_content(started_on_home):
    page = started_on_home
    page.get_by_role("navigation", name="Pages").get_by_role("link", name="Workouts").focus()
    settle(page, lambda: page.keyboard.press("Enter"), until="() => appRouter.current === 'workouts'")
    assert page.evaluate("document.activeElement.id") == "main-content"
    page.keyboard.press("Tab")                                              # next stop is inside the page
    assert page.evaluate("document.getElementById('main-content').contains(document.activeElement)")


def test_each_page_has_one_main_landmark(started_on_home):
    page = started_on_home
    for label, name, *_ in PAGES:
        _go(page, label, name)
        expect(page.locator("main")).to_have_count(1)
        expect(page.locator("#main-content")).to_have_count(1)


def test_weigh_ins_table_mode_stays_inside_the_page(started_on_home):
    """Regression for #26: table mode's class went on the shell's <main> (the
    first of two #main-content elements), so its styles never applied, and with
    in-page navigation it would have stayed on the shell after leaving."""
    page = started_on_home
    _go(page, "Weigh-ins", "weights")
    page.locator("#view-toggle-btn").click()
    expect(page.locator(".wt-main")).to_have_class(re.compile(r"(^| )wt-table-mode( |$)"))
    expect(page.locator("#main-content")).not_to_have_class(re.compile("wt-table-mode"))
    _go(page, "Workouts", "workouts")
    expect(page.locator("#main-content")).not_to_have_class(re.compile("wt-table-mode"))


# ── Fade between pages (M5.1) ───────────────────────────────────────────────

def _style(page, selector, prop):
    return page.evaluate("([sel, prop]) => getComputedStyle(document.querySelector(sel))[prop]", [selector, prop])


def test_page_fades_out_then_in(started_on_home):
    page = started_on_home
    page.evaluate("""document.fadeLog = [];       // not on window: leaving Home would clear it
        new MutationObserver(() => document.fadeLog.push(document.documentElement.className))
            .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });""")
    _go(page, "Workouts", "workouts")
    page.wait_for_function("() => !document.documentElement.classList.contains('page-fading')")
    log = page.evaluate("document.fadeLog")
    assert any("page-leaving" in c for c in log)                            # faded out...
    assert "page-leaving" not in log[-1] and "page-fading" not in log[-1]   # ...and all the way back in
    assert _style(page, "#wp-add-btn", "opacity") == "1"


def test_while_fading_out_the_old_page_is_hidden_and_unclickable(started_on_home):
    page = started_on_home
    held, release = _hold(page, "**/weights")
    _click(page, "Weigh-ins")
    page.wait_for_function("() => getComputedStyle(document.querySelector('#mp-footer-add-btn')).opacity === '0'")
    assert _style(page, "#mp-footer-add-btn", "pointerEvents") == "none"
    assert _style(page, ".site-header", "opacity") == "1"                   # the shell never fades
    assert _style(page, ".mp-bg", "opacity") == "1"                         # nor the background (M5.2)
    assert _style(page, "#mp-footer-add-btn", "transitionDuration") == "0.125s"
    settle(page, release, until="() => appRouter.current === 'weights'")
    page.wait_for_function("() => getComputedStyle(document.querySelector('#chart-add-btn')).opacity === '1'")


def test_cancelling_a_pending_click_fades_the_page_back_in(started_on_home):
    page = started_on_home
    held, release = _hold(page, "**/weights")
    _click(page, "Weigh-ins")
    page.wait_for_function("() => document.documentElement.classList.contains('page-leaving')")
    _click(page, "Home")
    page.wait_for_function("() => getComputedStyle(document.querySelector('#mp-footer-add-btn')).opacity === '1'")
    settle(page, release)
    assert page.evaluate("appRouter.current") == "home"
    assert _style(page, "#mp-footer-add-btn", "pointerEvents") != "none"


def test_reduced_motion_switches_pages_without_a_fade(started_on_home):
    page = started_on_home
    page.emulate_media(reduced_motion="reduce")
    held, release = _hold(page, "**/weights")
    _click(page, "Weigh-ins")
    page.wait_for_function("() => document.documentElement.classList.contains('page-fading')")
    assert _style(page, "#mp-footer-add-btn", "transitionDuration") == "0s"
    settle(page, release, until="() => appRouter.current === 'weights'")
    assert _style(page, "#chart-add-btn", "opacity") == "1"                 # shown at once, no fade-in


# ── Background cross-fade (M5.2) ────────────────────────────────────────────

GHOST = ".bg-ghost"
WORKOUTS_BG = "**/static/workoutbackground9.png"


def test_old_background_lies_over_the_new_one_then_fades_away(started_on_home):
    page = started_on_home
    held, release = _hold(page, WORKOUTS_BG)
    _click(page, "Workouts")
    page.wait_for_function("() => appRouter.current === 'workouts'")
    ghost = page.locator(GHOST)
    expect(ghost).to_have_count(1)
    assert "homebackground.png" in _style(page, GHOST, "backgroundImage")   # Home's background, frozen
    assert _style(page, GHOST + " > div", "backgroundColor") == "rgba(8, 0, 18, 0.72)"   # with its tint
    assert _style(page, GHOST, "pointerEvents") == "none"
    assert page.evaluate("!document.querySelector('.bg-ghost').closest('[data-region]')")   # part of the shell
    expect(page.locator('[data-region="bg"] .wp-bg')).to_have_count(1)     # the new one, underneath

    page.wait_for_timeout(500)
    assert _style(page, GHOST, "opacity") == "1"                            # waits for the new image
    release()
    expect(ghost).to_have_count(0)                                          # faded out and removed


def test_background_fade_takes_a_quarter_second(started_on_home):
    page = started_on_home
    held, release = _hold(page, WORKOUTS_BG)
    _click(page, "Workouts")
    expect(page.locator(GHOST)).to_have_count(1)
    assert _style(page, GHOST, "transitionDuration") == "0.25s"
    release()
    expect(page.locator(GHOST)).to_have_count(0)


def test_a_slow_background_cannot_hold_the_fade_forever(started_on_home):
    page = started_on_home
    _hold(page, WORKOUTS_BG)                                                # never released
    _click(page, "Workouts")
    expect(page.locator(GHOST)).to_have_count(1)
    expect(page.locator(GHOST)).to_have_count(0, timeout=4000)              # gives up waiting after 2s
    expect(page.locator(".wp-row")).to_have_count(1)                        # content never waited


@pytest.mark.allow_page_errors          # the broken image is the point of the test
def test_a_broken_background_still_clears_the_old_one(started_on_home):
    page = started_on_home
    page.route(WORKOUTS_BG, lambda route: route.abort())
    _go(page, "Workouts", "workouts")
    expect(page.locator(GHOST)).to_have_count(0, timeout=1000)


def test_reduced_motion_swaps_backgrounds_without_a_fade(started_on_home):
    page = started_on_home
    page.emulate_media(reduced_motion="reduce")
    held, release = _hold(page, WORKOUTS_BG)
    _click(page, "Workouts")
    expect(page.locator(GHOST)).to_have_count(1)
    assert _style(page, GHOST, "transitionDuration") == "0s"
    release()
    expect(page.locator(GHOST)).to_have_count(0, timeout=500)


def test_quick_clicks_leave_no_background_ghosts(started_on_home):
    page = started_on_home
    for label in ["Weigh-ins", "Workouts", "Home", "Weigh-ins", "Workouts"]:
        _click(page, label)
    settle(page, lambda: None, until="() => appRouter.current === 'workouts'")
    expect(page.locator(GHOST)).to_have_count(0, timeout=4000)
    expect(page.locator('[data-region="bg"] > *')).to_have_count(1)


# ── Falling back to a normal page load ───────────────────────────────────────

def test_unexpected_response_falls_back_to_a_full_load(started_on_home):
    page = started_on_home
    page.route("**/workouts", lambda route: route.fulfill(status=200, content_type="text/html",
                                                          body="<html><body>not an app page</body></html>"),
               times=1)
    page.get_by_role("navigation", name="Pages").get_by_role("link", name="Workouts").click()
    page.wait_for_function("() => window.appRouter && appRouter.current === 'workouts'")
    assert not _still_same_document(page)                                   # it was a full load
    expect(page.locator(".wp-row")).to_have_count(1)


def test_signed_out_mid_session_lands_on_sign_in(started_on_home):
    page = started_on_home
    page.context.clear_cookies()
    page.get_by_role("navigation", name="Pages").get_by_role("link", name="Weigh-ins").click()
    expect(page.get_by_text("Sign in with Google")).to_be_visible()


def test_modified_clicks_are_left_to_the_browser(started_on_home):
    """Ctrl/Cmd-click (open in new tab) isn't intercepted."""
    page = started_on_home
    with page.context.expect_page() as new_tab:
        page.get_by_role("navigation", name="Pages").get_by_role("link", name="Workouts").click(modifiers=["ControlOrMeta"])
    new_tab.value.close()
    assert page.evaluate("appRouter.current") == "home"
    assert _still_same_document(page)
