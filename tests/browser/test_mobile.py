"""The app at phone and tablet sizes, with touch on: every page fits the screen,
nav and footer buttons can be tapped, windows fit and close, logging works, and
the desktop custom cursor stays out of the way."""

from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.conftest import seed_setting, seed_weight

SMALL_PHONE = {
    "viewport": {"width": 360, "height": 640},
    "has_touch": True,
    "is_mobile": True,
    "device_scale_factor": 2,
}
PHONE = {"viewport": {"width": 390, "height": 844}, "has_touch": True, "is_mobile": True, "device_scale_factor": 3}
TABLET = {"viewport": {"width": 820, "height": 1180}, "has_touch": True, "is_mobile": True, "device_scale_factor": 2}

PAGES = ["/", "/weights", "/workouts"]

# Each page fitting the screen is part of reading that page's main view.
PAGES_FIT = [
    pytest.param("/", marks=pytest.mark.flow("see-progress-on-home"), id="/"),
    pytest.param("/weights", marks=pytest.mark.flow("read-weight-charts"), id="/weights"),
    pytest.param("/workouts", marks=pytest.mark.flow("review-workouts"), id="/workouts"),
]

# Each page has its own footer "+" button.
ADD_BUTTON = {"/": "#mp-footer-add-btn", "/weights": "#chart-add-btn", "/workouts": "#wp-add-btn"}


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


@pytest.fixture()
def mobile(signed_in_page, client):
    """Signed-in touch browser on an account with some history."""
    seed_setting(client, "starting_weight", 230.0)
    seed_setting(client, "goal_weight", 189.0)
    for i in range(1, 15):
        seed_weight(client, _day(i), 210.0 + i / 2)
    client.post(
        "/api/workout", json={"date": _day(1), "type": "Basketball", "duration_min": 30, "kcal": 260, "note": ""}
    )

    def open_page(path="/"):
        signed_in_page.goto(path)
        signed_in_page.wait_for_load_state("networkidle")
        return signed_in_page

    return open_page, client


def _sideways_overflow(page):
    """How many px the page can be scrolled sideways (0 is what we want)."""
    return page.evaluate("""() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)
                                  - document.documentElement.clientWidth""")


def _assert_on_screen_and_tappable(page, selector):
    """The control's centre is on screen, and a tap there would land on it."""
    problem = page.locator(selector).evaluate("""el => {
        const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
        if (r.width === 0 || x < 0 || y < 0 || x > innerWidth || y > innerHeight) {
            return `off screen: ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}x${Math.round(r.height)}`;
        }
        const hit = document.elementFromPoint(x, y);
        if (!hit || !(el === hit || el.contains(hit) || hit.contains(el))) {
            return `covered by <${hit && hit.tagName.toLowerCase()} id="${hit && hit.id}" class="${hit && hit.className}">`;
        }
        return null;
    }""")
    assert problem is None, f"{selector}: {problem}"


def _tap(page, selector):
    """Scroll `selector` into view, check a finger would land on it, then tap it."""
    page.locator(selector).scroll_into_view_if_needed()
    _assert_on_screen_and_tappable(page, selector)
    page.locator(selector).tap()


def _open_menu_item(page, button_id):
    _tap(page, "#profile-btn")
    expect(page.locator("#menu-modal")).to_be_visible()
    _tap(page, f"#{button_id}")


def _open_table_row(page, day):
    """The Weigh-ins table, with `day`'s row in view; returns that row's selector."""
    _tap(page, "#view-toggle-btn")
    expect(page.locator("#data-table-wrap")).to_be_visible()
    return f'tr.daily-row:has(td.cell-weight[data-date="{day}"])'


def _weights(client):
    return {r["date"]: r for r in client.get("/api/weights?range=all").get_json()}


def _prefs(client):
    return client.get("/api/preferences").get_json()


def _log_yoga(page, path, scroll=False):
    """Open Log Workout from `path`, pick Yoga and add it. Add Activity must be in view
    straight away unless `scroll` is set, for screens too short to show the whole window."""
    page.locator(ADD_BUTTON[path]).tap()
    if path == "/":
        page.locator("#qa-log-workout").tap()
    expect(page.locator("#wp-log-modal")).to_be_visible()
    page.locator("#workout-type-input").fill("Yoga")
    page.locator("#workout-search-dropdown .wsd-item").first.tap()
    add = page.locator("#wpm-add-activity-btn")
    if scroll:
        add.scroll_into_view_if_needed()
    _assert_on_screen_and_tappable(page, "#wpm-add-activity-btn")
    add.tap()
    expect(page.locator("#wpm-staged-entries .wpm-staged-row")).to_have_count(1)
    _assert_on_screen_and_tappable(page, "#wp-modal-save")


def _assert_fits_screen(page, selector):
    box = page.locator(selector).evaluate("""el => {
        const r = el.getBoundingClientRect();
        return { left: r.left, right: r.right, width: r.width, vw: document.documentElement.clientWidth };
    }""")
    assert box["left"] >= -1 and box["right"] <= box["vw"] + 1, f"{selector} doesn't fit: {box}"


class _MobileFlows:
    @pytest.mark.parametrize("path", PAGES_FIT)
    def test_page_does_not_scroll_sideways(self, mobile, path):
        open_page, _ = mobile
        assert _sideways_overflow(open_page(path)) <= 1

    @pytest.mark.flow("read-weight-table")
    def test_weigh_ins_table_view_does_not_scroll_the_page_sideways(self, mobile):
        open_page, _ = mobile
        page = open_page("/weights")
        page.locator("#view-toggle-btn").tap()
        expect(page.locator("#data-table-wrap")).to_be_visible()
        assert _sideways_overflow(page) <= 1

    @pytest.mark.flow("sign-in")
    def test_login_page_fits(self, signed_out_page):
        """Regression: the card's padding was added on top of its 90% width, so on phones
        it filled the screen edge to edge, and its pop-in bounce briefly overflowed it.
        Measure once the bounce has finished, so the result doesn't depend on timing."""
        page = signed_out_page
        page.goto("/login")
        expect(page.get_by_role("link", name="Sign in with Google")).to_be_visible()
        page.wait_for_function("document.getAnimations().every(a => a.playState === 'finished')")
        assert _sideways_overflow(page) <= 1
        _assert_fits_screen(page, ".login-card")
        card = page.locator(".login-card").bounding_box()
        width = page.viewport_size["width"]
        assert card["x"] >= 8 and card["x"] + card["width"] <= width - 8, f"no side margin: {card}"
        _assert_on_screen_and_tappable(page, ".google-btn")

    @pytest.mark.parametrize("path", PAGES)
    def test_footer_buttons_can_be_tapped(self, mobile, path):
        open_page, _ = mobile
        page = open_page(path)
        _assert_on_screen_and_tappable(page, "#profile-btn")
        _assert_on_screen_and_tappable(page, ADD_BUTTON[path])

    @pytest.mark.flow("move-between-pages")
    def test_nav_links_can_be_tapped_and_change_page(self, mobile):
        open_page, _ = mobile
        page = open_page()
        nav = page.get_by_role("navigation", name="Pages")
        for name, url in (("Weigh-ins", "**/weights"), ("Workouts", "**/workouts"), ("Home", "**/")):
            link = nav.get_by_role("link", name=name)
            link.tap()
            page.wait_for_url(url)
            page.wait_for_load_state("networkidle")

    @pytest.mark.flow("use-the-menu")
    def test_menu_fits_and_closes(self, mobile):
        open_page, _ = mobile
        page = open_page()
        page.locator("#profile-btn").tap()
        expect(page.locator("#menu-modal")).to_be_visible()
        for button in ("#menu-settings-btn", "#menu-logout-btn", "#menu-modal-close"):
            _assert_on_screen_and_tappable(page, button)
        page.locator("#menu-modal-close").tap()
        expect(page.locator("#menu-modal")).to_be_hidden()

    def test_settings_window_fits_and_closes(self, mobile):
        open_page, _ = mobile
        page = open_page()
        page.locator("#profile-btn").tap()
        page.locator("#menu-settings-btn").tap()
        title = page.locator("#menu-modal-title")
        expect(title).to_be_hidden()
        assert _sideways_overflow(page) <= 1
        page.keyboard.press("Escape")

    @pytest.mark.flow("log-weigh-in")
    def test_log_a_weigh_in_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page()
        page.locator("#mp-footer-add-btn").tap()
        expect(page.locator("#quick-add-modal")).to_be_visible()
        page.locator("#qa-log-weight").tap()
        expect(page.locator("#history-modal")).to_be_visible()
        _assert_on_screen_and_tappable(page, "#history-weight")
        page.locator("#history-weight").fill("205")
        _assert_on_screen_and_tappable(page, "#history-save")
        page.locator("#history-save").tap()
        expect(page.locator("#history-modal")).to_be_hidden()
        assert any(w["date"] == _day(0) and w["weight_lbs"] == 205 for w in client.get("/api/weights").get_json())

    @pytest.mark.flow("log-workout")
    @pytest.mark.parametrize("path", ["/", "/workouts"])
    def test_log_a_workout_by_touch(self, mobile, path):
        open_page, client = mobile
        page = open_page(path)
        _log_yoga(page, path)
        page.locator("#wp-modal-save").tap()
        expect(page.locator("#wp-log-modal")).to_be_hidden()
        assert any(w["date"] == _day(0) and w["type"] == "Yoga" for w in client.get("/api/workouts").get_json())

    def test_custom_cursor_stays_hidden_after_a_tap(self, mobile):
        open_page, _ = mobile
        page = open_page()
        page.locator("#mp-footer-add-btn").tap()
        expect(page.locator("#quick-add-modal")).to_be_visible()
        expect(page.locator("#site-cursor")).to_be_hidden()

    # ── Flows that were only tested on desktop (story 4.6) ──

    @pytest.mark.flow("sign-out")
    def test_log_out_by_touch(self, mobile):
        open_page, _ = mobile
        page = open_page()
        _open_menu_item(page, "menu-logout-btn")
        page.wait_for_url("**/login")
        expect(page.get_by_role("link", name="Sign in with Google")).to_be_visible()

    @pytest.mark.flow("set-starting-and-goal-weight")
    def test_set_goal_weight_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page()
        _tap(page, "#goal-plate")
        expect(page.locator("#goal-modal")).to_be_visible()
        _assert_fits_screen(page, "#goal-modal .modal-card")
        page.locator("#goal-input").fill("180")
        _tap(page, "#goal-save")
        _tap(page, "#goal-overwrite-confirm")  # a goal of 189 is already saved
        expect(page.locator("#goal-modal")).to_be_hidden()
        expect(page.locator("#goal-lbs-num")).to_have_text("180")
        assert client.get("/api/settings").get_json()["goal_weight"]["value_lbs"] == 180

    @pytest.mark.flow("edit-weigh-in")
    def test_edit_a_weigh_in_from_the_table_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page("/weights")
        row = _open_table_row(page, _day(1))
        _tap(page, f"{row} td.cell-weight")
        expect(page.locator("#history-modal")).to_be_visible()
        page.locator("#history-weight").fill("199.5")
        _tap(page, "#history-save")
        _tap(page, "#history-overwrite-confirm")
        expect(page.locator(f"{row} td.cell-weight")).to_contain_text("199.5 lbs")
        assert _weights(client)[_day(1)]["weight_lbs"] == 199.5

    @pytest.mark.flow("delete-weigh-in")
    def test_delete_a_weigh_in_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page("/weights")
        row = _open_table_row(page, _day(1))
        _tap(page, f'{row} button[aria-label="Delete this entry"]')
        expect(page.locator("#row-delete-modal")).to_be_visible()
        with page.expect_response(lambda r: r.request.method == "DELETE"):
            _tap(page, "#row-delete-ok")
        expect(page.locator("#row-delete-modal")).to_be_hidden()
        assert _day(1) not in _weights(client)

    @pytest.mark.flow("add-weigh-in-note")
    def test_add_a_note_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page("/weights")
        row = _open_table_row(page, _day(1))
        _tap(page, f'{row} button[aria-label="Add note"]')
        expect(page.locator("#note-popover")).to_be_visible()
        _assert_fits_screen(page, "#note-popover")
        page.locator("#note-popover-text").fill("felt great")
        _tap(page, "#note-popover-save")
        expect(page.locator("#note-popover")).to_be_hidden()
        assert _weights(client)[_day(1)]["notes"] == "felt great"

    @pytest.mark.flow("delete-workout")
    def test_delete_a_workout_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page("/workouts")
        _tap(page, ".wp-row .wp-del-btn")
        expect(page.locator("#app-confirm-modal")).to_be_visible()
        with page.expect_response(lambda r: r.request.method == "DELETE"):
            _tap(page, "#app-confirm-ok")
        expect(page.locator("#wp-empty")).to_be_visible()
        assert client.get("/api/workouts").get_json() == []

    @pytest.mark.flow("change-settings")
    def test_switch_to_kilograms_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page()
        _open_menu_item(page, "menu-settings-btn")
        expect(page.locator("#settings-modal")).to_be_visible()
        assert _sideways_overflow(page) <= 1
        _tap(page, "#prof-kg-btn")
        with page.expect_response("**/api/preference"):
            _tap(page, "#settings-save")
        expect(page.locator("#settings-modal")).to_be_hidden()
        expect(page.locator(".plate").first).to_have_class("plate kg-primary")
        assert _prefs(client)["pref_unit"] == "kg"

    @pytest.mark.flow("change-profile-picture")
    def test_choose_a_profile_picture_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page()
        _open_menu_item(page, "menu-settings-btn")
        _tap(page, "#change-pic-btn")
        expect(page.locator("#profile-pic-picker")).to_be_visible()
        _assert_fits_screen(page, "#profile-pic-picker")  # it was ~644px wide, so Save hung off a phone
        _tap(page, '.pic-option[data-pic="3"]')
        with page.expect_response("**/api/preference"):
            _tap(page, "#pic-save-btn")
        expect(page.locator("#profile-btn-img")).to_have_attribute("src", "/static/profile3button.png")
        assert _prefs(client)["pref_profile_pic"] == "3"

    @pytest.mark.flow("edit-fight-card")
    def test_fill_in_the_fight_card_by_touch(self, mobile):
        open_page, client = mobile
        page = open_page()
        _open_menu_item(page, "menu-profile-btn")
        expect(page.locator("#fight-card-modal")).to_be_visible()
        assert _sideways_overflow(page) <= 1
        page.locator("#fight-name").fill("Test Fighter")
        _tap(page, "#fight-goal-muscle")
        with page.expect_response("**/api/preference"):
            _tap(page, "#fight-card-save")
        expect(page.locator("#fight-card-modal")).to_be_hidden()
        expect(page.locator("#lost-plate-label")).to_have_text("GAINED")
        assert _prefs(client)["fight_goal_mode"] == "muscle"

    @pytest.mark.flow("read-insights")
    def test_read_insights_by_touch(self, mobile):
        open_page, _ = mobile
        page = open_page()
        _open_menu_item(page, "menu-insights-btn")
        expect(page.locator("#insights-modal")).to_be_visible()
        assert _sideways_overflow(page) <= 1
        expect(page.locator(".insight-card", has_text="Longest Streak").locator(".insight-value")).to_have_text("14")
        _tap(page, "#insights-close")
        expect(page.locator("#insights-modal")).to_be_hidden()


@pytest.mark.browser_context_args(**SMALL_PHONE)
class TestSmallPhone(_MobileFlows):
    pass


@pytest.mark.browser_context_args(**PHONE)
class TestPhone(_MobileFlows):
    pass


@pytest.mark.browser_context_args(**TABLET)
class TestTablet(_MobileFlows):
    pass


@pytest.mark.flow("log-workout")
@pytest.mark.browser_context_args(viewport={"width": 640, "height": 360}, has_touch=True, is_mobile=True)
@pytest.mark.parametrize("path", ["/", "/workouts"])
def test_log_workout_window_scrolls_on_a_very_short_screen(mobile, path):
    """A phone turned sideways: the window can't fit, so scrolling it must reach Add Activity
    and leave Save tappable."""
    open_page, _ = mobile
    page = open_page(path)
    _log_yoga(page, path, scroll=True)
