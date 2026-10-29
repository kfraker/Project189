"""Page lifecycle (migration M2.1): registerPage() starts a page with a context whose
signal and onLeave() undo everything the page set up when it is left, and
appRouter.remount() restarts the current page in place.

These tests register small probe pages, after first leaving the real page
(Home) so the probes start from a page with nothing running.
"""
import pytest

# A probe page: counts clicks on the document and records its cleanups in window.log.
PROBE = """
window.log = [];
window.clicks = 0;
window.contexts = [];
registerPage('probe', page => {
    window.contexts.push(page);
    document.addEventListener('click', () => window.clicks++, { signal: page.signal });
    const n = window.contexts.length;
    page.onLeave(() => log.push('first cleanup ' + n));
    page.onLeave(() => log.push('second cleanup ' + n));
});
"""


@pytest.fixture()
def home(signed_in_page):
    """Home with its own page left, so nothing is running."""
    signed_in_page.goto("/")
    signed_in_page.wait_for_load_state("networkidle")
    signed_in_page.evaluate("appRouter.leave()")
    return signed_in_page


def _click_count_after_one_click(page):
    return page.evaluate("() => { window.clicks = 0; document.body.click(); return window.clicks; }")


@pytest.mark.parametrize("path,name", [("/", "home"), ("/weights", "weights"), ("/workouts", "workouts")])
def test_each_page_registers_itself_on_load(signed_in_page, path, name):
    signed_in_page.goto(path)
    signed_in_page.wait_for_load_state("networkidle")
    assert signed_in_page.evaluate("appRouter.current") == name


def test_with_no_page_running_there_is_nothing_to_restart(home):
    assert home.evaluate("appRouter.current") is None
    assert home.evaluate("appRouter.remount()") is False


def test_register_page_starts_it_with_a_context(home):
    home.evaluate(PROBE)
    assert home.evaluate("appRouter.current") == "probe"
    ctx = home.evaluate("({ name: contexts[0].name, aborted: contexts[0].signal.aborted })")
    assert ctx == {"name": "probe", "aborted": False}
    assert _click_count_after_one_click(home) == 1


def test_leaving_removes_listeners_and_runs_cleanups_newest_first(home):
    home.evaluate(PROBE)
    home.evaluate("appRouter.leave()")
    assert home.evaluate("appRouter.current") is None
    assert home.evaluate("contexts[0].signal.aborted") is True
    assert home.evaluate("log") == ["second cleanup 1", "first cleanup 1"]
    assert _click_count_after_one_click(home) == 0


def test_remount_restarts_the_page_with_a_fresh_context(home):
    home.evaluate(PROBE)
    assert home.evaluate("appRouter.remount()") is True
    assert home.evaluate("appRouter.current") == "probe"
    assert home.evaluate("[contexts.length, contexts[0].signal.aborted, contexts[1].signal.aborted]") == [2, True, False]
    assert home.evaluate("log") == ["second cleanup 1", "first cleanup 1"]   # old cleanups ran, once
    assert _click_count_after_one_click(home) == 1


def test_twenty_remounts_leave_exactly_one_listener(home):
    home.evaluate(PROBE)
    home.evaluate("for (let i = 0; i < 20; i++) appRouter.remount()")
    assert _click_count_after_one_click(home) == 1
    assert home.evaluate("log.length") == 40                               # 2 cleanups × 20 leaves


def test_registering_another_page_leaves_the_current_one(home):
    home.evaluate(PROBE)
    home.evaluate("registerPage('other', page => page.onLeave(() => log.push('other left')))")
    assert home.evaluate("appRouter.current") == "other"
    assert home.evaluate("log") == ["second cleanup 1", "first cleanup 1"]
    assert _click_count_after_one_click(home) == 0


@pytest.mark.allow_page_errors          # the failing cleanup is the point of the test
def test_a_failing_cleanup_does_not_stop_the_others(home):
    errors = []
    home.on("console", lambda msg: msg.type == "error" and errors.append(msg.text))
    home.evaluate("""window.log = [];
        registerPage('fragile', page => {
            page.onLeave(() => log.push('still cleaned'));
            page.onLeave(() => { throw new Error('boom'); });
        })""")
    home.evaluate("appRouter.leave()")
    assert home.evaluate("log") == ["still cleaned"]
    assert any('Page "fragile" cleanup failed' in e for e in errors)


# ── Page-shared names on window are cleared on leave (M2.2) ─────────────────

def test_names_a_page_puts_on_window_are_removed_when_it_is_left(home):
    home.evaluate("""() => new Promise(done => registerPage('probe', page => {
        window.refreshProbe = () => {};                         // set while starting
        setTimeout(() => { window.probeLoadedLater = 1; done(); }, 50);   // set later on
    }))""")
    assert home.evaluate("[typeof refreshProbe, typeof probeLoadedLater]") == ["function", "number"]
    home.evaluate("appRouter.leave()")
    assert home.evaluate("['refreshProbe', 'probeLoadedLater'].filter(k => k in window)") == []


def test_names_that_existed_before_the_page_are_kept(home):
    home.evaluate("window.setBeforeProbe = 'mine'")
    home.evaluate("registerPage('probe', page => { window.setBeforeProbe = 'changed by page'; })")
    home.evaluate("appRouter.leave()")
    assert home.evaluate("window.setBeforeProbe") == "changed by page"


def test_app_wide_names_created_during_a_page_are_kept(home):
    """A library loaded by a page (Chart.js on Weigh-ins) stays loaded for next time,
    and shell state set while the page is open survives leaving it."""
    assert home.evaluate("'Chart' in window") is False              # Home doesn't load it
    home.evaluate("""registerPage('probe', page => {
        window.Chart = { stand_in: true };
        window.activeModal = { tryClose() {} };
    })""")
    home.evaluate("appRouter.leave()")
    assert home.evaluate("[window.Chart?.stand_in, typeof window.activeModal?.tryClose]") == [True, "function"]
    assert home.evaluate("typeof savePref") == "function"


def test_remounts_do_not_pile_up_names_on_window(home):
    home.evaluate("registerPage('probe', page => { window.probeA = 1; window.probeB = () => {}; })")
    count = home.evaluate("Object.keys(window).length")
    home.evaluate("for (let i = 0; i < 20; i++) appRouter.remount()")
    assert home.evaluate("Object.keys(window).length") == count


@pytest.mark.allow_page_errors          # the undeletable name is the point of the test
def test_undeletable_page_name_is_reported(home):
    """A top-level `var` can't be deleted. Pages must use window.x = … inside init
    instead; if one slips through, leaving the page says so."""
    errors = []
    home.on("console", lambda msg: msg.type == "error" and errors.append(msg.text))
    home.evaluate("registerPage('probe', page => {})")
    home.add_script_tag(content="var leakyProbe = 1;")
    home.evaluate("appRouter.leave()")
    assert any('left window.leakyProbe behind' in e for e in errors)


# ── page.fetch: answers that arrive after the page was left are dropped (M4.1) ─

def test_page_fetch_works_normally_while_the_page_runs(home):
    result = home.evaluate("""() => new Promise(done => registerPage('probe', page => {
        page.fetch('/api/settings').then(r => r.json()).then(data => done(typeof data));
    }))""")
    assert result == "object"


def test_page_fetch_answer_after_leaving_is_dropped(home):
    """The follow-up code of a request still out when the page is left never runs,
    so it can't write into the next page; the request itself still completes."""
    with home.expect_response("**/api/settings"):
        home.evaluate("""window.followUps = [];
            registerPage('probe', page => {
                page.fetch('/api/settings').then(r => { followUps.push('answer'); return r.json(); })
                                           .then(() => followUps.push('body'));
            });
            appRouter.leave();""")
    home.wait_for_timeout(300)
    assert home.evaluate("followUps") == []


def test_page_fetch_body_read_after_leaving_is_dropped(home):
    home.evaluate("""() => new Promise(done => {
        window.followUps = [];
        registerPage('probe', page => {
            page.fetch('/api/settings').then(r => {
                followUps.push('answer');
                appRouter.leave();                  // left between the answer and its body
                r.json().then(() => followUps.push('body'));
                done();
            });
        });
    })""")
    home.wait_for_timeout(300)
    assert home.evaluate("followUps") == ["answer"]


@pytest.mark.allow_page_errors          # the failed request itself is expected
def test_page_fetch_failure_after_leaving_is_silent(home):
    """A request that fails after the page was left raises nothing: no unhandled
    rejection, even where the page code has no error handler."""
    js_errors = []
    home.on("pageerror", lambda exc: js_errors.append(str(exc)))
    home.context.route("**/api/settings", lambda route: route.abort())
    home.evaluate("""window.followUps = [];
        registerPage('probe', page => {
            page.fetch('/api/settings').then(() => followUps.push('answer'), () => followUps.push('error'));
            page.fetch('/api/settings').then(r => r.json());     // no error handler at all
        });
        appRouter.leave();""")
    home.wait_for_timeout(500)
    assert home.evaluate("followUps") == []
    assert js_errors == []
