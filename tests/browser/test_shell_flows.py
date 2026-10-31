"""Shared-shell flows in a real browser (header/footer, menu and its windows):
menu order and closing, Insights, Profile (Fight Card), Settings, profile
picture → matching cursor, the custom cursor across page changes, log out,
and no hover tooltips."""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.conftest import seed_weight


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


@pytest.fixture()
def shell(signed_in_page, client):
    """Signed-in browser on Home + an API client for seeding, both on test user 1."""
    def open_page(path="/"):
        signed_in_page.goto(path)
        signed_in_page.wait_for_load_state("networkidle")
        return signed_in_page
    return open_page, client


def _open_menu(page):
    page.locator("#profile-btn").click()
    expect(page.locator("#menu-modal")).to_be_visible()


def _menu_item(page, label):
    _open_menu(page)
    page.locator("#menu-modal .menu-modal-btn", has_text=label).click()


def _saved_prefs(client):
    return client.get("/api/preferences").get_json()


# ── Menu ─────────────────────────────────────────────────────────────────────

def test_menu_lists_items_in_order(shell):
    open_page, _ = shell
    page = open_page()
    _open_menu(page)
    expect(page.locator("#menu-modal .menu-modal-btn-label")).to_have_text(
        ["Insights", "Settings", "Profile", "Log Out"])


def test_menu_closes_with_x_and_escape(shell):
    open_page, _ = shell
    page = open_page()
    _open_menu(page)
    page.locator("#menu-modal-close").click()
    expect(page.locator("#menu-modal")).to_be_hidden()
    _open_menu(page)
    page.keyboard.press("Escape")
    expect(page.locator("#menu-modal")).to_be_hidden()


# ── Insights ─────────────────────────────────────────────────────────────────

def test_insights_summarises_weigh_ins_and_returns_to_menu(shell):
    open_page, client = shell
    for i, w in enumerate([200.0, 201.0, 202.0]):
        seed_weight(client, _day(i), w)
    page = open_page()
    _menu_item(page, "Insights")
    expect(page.locator("#insights-modal")).to_be_visible()
    streak = page.locator(".insight-card", has_text="Current Streak")
    expect(streak.locator(".insight-value")).to_have_text("3")

    page.locator("#insights-close").click()
    expect(page.locator("#insights-modal")).to_be_hidden()
    expect(page.locator("#menu-modal")).to_be_visible()        # back where you came from


def test_insights_with_no_data(shell):
    open_page, _ = shell
    page = open_page()
    _menu_item(page, "Insights")
    expect(page.locator("#insights-grid")).to_contain_text("No weight data yet.")


# ── Profile (Fight Card) ─────────────────────────────────────────────────────

def test_fight_card_saves_name_and_goal_mode(shell):
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Profile")
    expect(page.locator("#fight-card-modal")).to_be_visible()
    page.locator("#fight-name").fill("Test Fighter")
    page.locator("#fight-goal-muscle").click()
    with page.expect_response("**/api/preference"):
        page.locator("#fight-card-save").click()

    expect(page.locator("#fight-card-modal")).to_be_hidden()
    expect(page.locator("#healthbar-name")).to_have_text("Test Fighter")
    expect(page.locator("#lost-plate-label")).to_have_text("GAINED")   # Muscle Monster mode

    page = open_page()                                            # saved to the account
    expect(page.locator("#healthbar-name")).to_have_text("Test Fighter")
    expect(page.locator("#lost-plate-label")).to_have_text("GAINED")
    assert _saved_prefs(client)["fight_goal_mode"] == "muscle"


# ── Settings ─────────────────────────────────────────────────────────────────

def test_settings_switch_to_kilograms_applies_and_persists(shell):
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Settings")
    expect(page.locator("#settings-modal")).to_be_visible()
    page.locator("#prof-kg-btn").click()
    with page.expect_response("**/api/preference"):
        page.locator("#settings-save").click()

    expect(page.locator("#settings-modal")).to_be_hidden()
    expect(page.locator(".plate").first).to_have_class("plate kg-primary")
    page = open_page()
    expect(page.locator(".plate").first).to_have_class("plate kg-primary")
    assert _saved_prefs(client)["pref_unit"] == "kg"


def test_health_bar_and_its_settings_are_hidden_for_now(shell):
    open_page, client = shell
    client.post("/api/preference", json={"key": "pref_healthbar", "value": "1"})   # even if it was left on
    page = open_page()
    expect(page.locator("#healthbar-hud")).to_be_hidden()
    _menu_item(page, "Settings")
    expect(page.locator("#prof-healthbar-on")).to_be_hidden()
    expect(page.locator("#prof-fighter-name-on")).to_be_hidden()
    expect(page.locator("#change-pic-btn")).to_be_visible()       # shares that Settings section


def test_settings_health_bar_switch_unlocks_fighter_name(shell):
    """The hidden section still works: Health Bar is one on/off choice, and Fighter
    Name is only locked while it's off."""
    open_page, client = shell
    client.post("/api/preference", json={"key": "pref_healthbar", "value": "0"})
    page = open_page()
    _menu_item(page, "Settings")
    page.evaluate("document.getElementById('healthbar-options').style.display = ''")
    bar_on, bar_off = page.locator("#prof-healthbar-on"), page.locator("#prof-healthbar-off")
    name_on, name_off = page.locator("#prof-fighter-name-on"), page.locator("#prof-fighter-name-off")
    expect(name_on).to_be_disabled()
    expect(name_off).to_be_disabled()

    bar_on.click()
    expect(bar_on).to_have_class("profile-opt-btn active")
    expect(bar_off).to_have_class("profile-opt-btn")
    expect(name_on).to_be_enabled()
    expect(name_off).to_be_enabled()

    bar_off.click()
    expect(bar_off).to_have_class("profile-opt-btn active")
    expect(bar_on).to_have_class("profile-opt-btn")
    expect(name_on).to_be_disabled()

    bar_on.click()
    name_on.click()
    expect(name_on).to_have_class("profile-opt-btn active")
    with page.expect_response(lambda r: "pref_fighter_name" in (r.request.post_data or "")):
        page.locator("#settings-save").click()
    expect(page.locator("#settings-modal")).to_be_hidden()
    prefs = _saved_prefs(client)
    assert prefs["pref_healthbar"] == "1" and prefs["pref_fighter_name"] == "1"


def test_settings_unsaved_changes_save_and_close(shell):
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Settings")
    page.locator("#prof-kg-btn").click()
    page.locator("#settings-cancel").click()
    expect(page.locator("#app-confirm-modal")).to_contain_text("Close without saving your settings?")
    with page.expect_response("**/api/preference"):
        page.get_by_role("button", name="Save & Close").click()
    expect(page.locator("#settings-modal")).to_be_hidden()
    expect(page.locator(".plate").first).to_have_class("plate kg-primary")
    assert _saved_prefs(client)["pref_unit"] == "kg"


def test_settings_unsaved_changes_close_without_saving(shell):
    """Regression for #24: the prompt offers a working "Close" (discard) button."""
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Settings")
    page.locator("#prof-kg-btn").click()
    page.locator("#settings-cancel").click()
    page.get_by_role("button", name="Close", exact=True).click(timeout=3000)
    expect(page.locator("#settings-modal")).to_be_hidden()
    expect(page.locator(".plate").first).not_to_have_class("plate kg-primary")
    assert _saved_prefs(client).get("pref_unit", "lbs") == "lbs"


def test_plain_confirmations_still_say_cancel_after_a_close_prompt(shell):
    """The "Close" label from an unsaved-changes prompt mustn't leak into the next dialog."""
    open_page, client = shell
    client.post("/api/workout", json={"date": _day(0), "type": "Yoga", "duration_min": 20, "kcal": 100, "note": ""})
    page = open_page("/workouts")
    _menu_item(page, "Settings")
    page.locator("#prof-kg-btn").click()
    page.locator("#settings-cancel").click()
    expect(page.locator("#app-confirm-cancel")).to_have_text("Close")
    page.locator("#app-confirm-cancel").click()
    expect(page.locator("#menu-modal")).to_be_visible()           # back to the menu it came from
    page.locator("#menu-modal-close").click()

    page.locator(".wp-row .wp-del-btn").first.click()
    expect(page.locator("#app-confirm-cancel")).to_have_text("Cancel")
    page.locator("#app-confirm-cancel").click()                   # plain cancel: nothing else happens
    expect(page.locator(".wp-row")).to_have_count(1)


def test_fight_card_unsaved_changes_close_without_saving(shell):
    """#24 also affected Profile: "Close" discards the edits."""
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Profile")
    page.locator("#fight-name").fill("Not Saved")
    page.locator("#fight-card-cancel").click()
    expect(page.locator("#app-confirm-modal")).to_contain_text("Close without saving?")
    page.get_by_role("button", name="Close", exact=True).click()
    expect(page.locator("#fight-card-modal")).to_be_hidden()
    expect(page.locator("#healthbar-name")).to_have_text("")
    assert "fight_name" not in _saved_prefs(client)


# ── Profile picture → matching cursor ────────────────────────────────────────

def test_profile_picture_changes_avatar_and_cursor(shell):
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Settings")
    page.locator("#change-pic-btn").click()
    expect(page.locator("#profile-pic-picker")).to_be_visible()
    page.locator('.pic-option[data-pic="3"]').click()
    with page.expect_response("**/api/preference"):
        page.locator("#pic-save-btn").click()

    expect(page.locator("#profile-btn-img")).to_have_attribute("src", "/static/profile3button.png")
    assert "cursor-pointer3.png" in page.locator("#site-cursor").evaluate("el => el.style.backgroundImage")

    page = open_page("/workouts")                                 # kept on other pages
    expect(page.locator("#profile-btn-img")).to_have_attribute("src", "/static/profile3button.png")
    assert "cursor-pointer3.png" in page.locator("#site-cursor").evaluate("el => el.style.backgroundImage")
    assert _saved_prefs(client)["pref_profile_pic"] == "3"


def test_profile_picture_unsaved_choice_close_without_saving(shell):
    """#24 also affected the picture picker: "Close" keeps the old picture."""
    open_page, client = shell
    page = open_page()
    _menu_item(page, "Settings")
    page.locator("#change-pic-btn").click()
    page.locator('.pic-option[data-pic="2"]').click()
    page.locator("#pic-cancel-btn").click()
    expect(page.locator("#app-confirm-modal")).to_contain_text("Close without saving your profile pic?")
    page.get_by_role("button", name="Close", exact=True).click()
    expect(page.locator("#profile-pic-picker")).to_be_hidden()
    expect(page.locator("#profile-btn-img")).to_have_attribute("src", "/static/profilebutton.png")
    assert "pref_profile_pic" not in _saved_prefs(client)


# ── Custom cursor ────────────────────────────────────────────────────────────

def test_custom_cursor_follows_mouse_and_survives_page_change(shell):
    """Regression for #15: after a nav click the custom cursor is already shown
    where the mouse was, instead of vanishing until the mouse moves."""
    open_page, _ = shell
    page = open_page()
    cursor = page.locator("#site-cursor")
    page.mouse.move(400, 300)
    expect(cursor).to_be_visible()
    assert "translate3d" in cursor.evaluate("el => el.style.transform")

    nav = page.get_by_role("navigation", name="Pages").get_by_role("link", name="Workouts")
    box = nav.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down(); page.mouse.up()
    page.wait_for_url("**/workouts")
    page.wait_for_load_state("networkidle")
    expect(page.locator("#site-cursor")).to_be_visible()          # no mouse move needed


def _cursor_image(page):
    return page.locator("#site-cursor").evaluate("el => el.style.backgroundImage")


def test_cursor_becomes_the_open_hand_over_editable_things(shell):
    open_page, _ = shell
    page = open_page()
    page.mouse.move(5, 300)
    assert "cursor-pointer.png" in _cursor_image(page)

    box = page.locator("#goal-plate").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_function("document.getElementById('site-cursor').style.backgroundImage.includes('cursor-edit.png')")
    cursor = page.locator("#site-cursor").bounding_box()
    assert (cursor["width"], cursor["height"]) == (117, 64)

    page.mouse.move(5, 300)
    page.wait_for_function("document.getElementById('site-cursor').style.backgroundImage.includes('cursor-pointer.png')")
    cursor = page.locator("#site-cursor").bounding_box()
    assert (cursor["width"], cursor["height"]) == (88, 48)


def test_open_hand_cursor_matches_the_profile_picture(shell):
    open_page, client = shell
    client.post("/api/preference", json={"key": "pref_profile_pic", "value": "3"})
    page = open_page()
    box = page.locator("#goal-plate").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_function("document.getElementById('site-cursor').style.backgroundImage.includes('cursor-edit3.png')")


def test_open_hand_cursor_does_not_stick_after_a_page_change(shell):
    open_page, _ = shell
    page = open_page()
    box = page.locator("#goal-plate").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_function("document.getElementById('site-cursor').style.backgroundImage.includes('cursor-edit.png')")
    page.evaluate("appRouter.navigate('/workouts')")
    page.wait_for_url("**/workouts")
    page.wait_for_function("document.getElementById('site-cursor').style.backgroundImage.includes('cursor-pointer.png')")


def test_cursor_stays_the_pointer_over_table_rows(shell):
    open_page, client = shell
    seed_weight(client, _day(1), 200.0)
    page = open_page("/weights")
    page.locator("#view-toggle-btn").click()
    cell = page.locator(".cell-weight:not(.cell-missing)").first
    expect(cell).to_be_visible()
    cell.hover()
    assert "cursor-pointer.png" in _cursor_image(page)


@pytest.mark.browser_context_args(has_touch=True, is_mobile=True, viewport={"width": 390, "height": 844})
def test_custom_cursor_stays_hidden_on_touch(shell):
    """A tap also fires browser-made mouse events, which must not bring up the cursor."""
    open_page, _ = shell
    page = open_page()
    page.locator("#mp-footer-add-btn").tap()
    expect(page.locator("#quick-add-modal")).to_be_visible()
    page.wait_for_timeout(400)
    expect(page.locator("#site-cursor")).to_be_hidden()


@pytest.mark.browser_context_args(has_touch=True)
def test_custom_cursor_returns_when_a_touchscreen_laptop_uses_its_mouse(shell):
    open_page, _ = shell
    page = open_page()
    page.locator("#mp-footer-add-btn").tap()
    expect(page.locator("#site-cursor")).to_be_hidden()
    page.wait_for_timeout(1100)
    page.mouse.move(300, 300)
    expect(page.locator("#site-cursor")).to_be_visible()


def test_custom_cursor_keeps_its_place_across_a_refresh(shell):
    """Nav clicks no longer reload the page, but a refresh still does: the cursor
    is shown where the mouse was straight away, without waiting for a mouse move."""
    open_page, _ = shell
    page = open_page()
    page.mouse.move(400, 300)
    cursor = page.locator("#site-cursor")
    expect(cursor).to_be_visible()
    before = cursor.evaluate("el => el.style.transform")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#site-cursor")).to_be_visible()                # no mouse move needed
    assert page.locator("#site-cursor").evaluate("el => el.style.transform") == before


# ── Nutrition "Coming Soon" tip ──────────────────────────────────────────────

def test_coming_soon_tip_sits_to_the_right_of_the_nav_buttons(shell):
    """The tip used to open to the left of the Nutrition button, on top of the
    other nav buttons; it now opens to its right."""
    open_page, _ = shell
    page = open_page()
    page.locator("#protein-btn").click()
    tip = page.locator(".coming-soon-tip")
    expect(tip).to_have_class("coming-soon-tip visible")
    tip_box, nutrition = tip.bounding_box(), page.locator("#protein-btn").bounding_box()
    assert tip_box["x"] >= nutrition["x"] + nutrition["width"]               # right of every nav button
    assert abs((tip_box["y"] + tip_box["height"] / 2) - (nutrition["y"] + nutrition["height"] / 2)) < 2   # level with it
    expect(tip).not_to_have_class("coming-soon-tip visible", timeout=3000)   # and goes away


# ── Log out ──────────────────────────────────────────────────────────────────

def test_log_out_returns_to_sign_in(shell):
    open_page, _ = shell
    page = open_page()
    _menu_item(page, "Log Out")
    page.wait_for_url("**/login")
    expect(page.get_by_text("Sign in with Google")).to_be_visible()
    page.goto("/")
    expect(page.get_by_text("Sign in with Google")).to_be_visible()


# ── No hover tooltips (removed by design, 2026-10-28) ────────────────────────

@pytest.mark.parametrize("path", ["/", "/weights", "/workouts"])
def test_no_hover_tooltips(shell, path):
    open_page, _ = shell
    page = open_page(path)
    page.get_by_role("navigation", name="Pages").get_by_role("link", name="Home").hover()
    page.wait_for_timeout(300)
    assert page.locator("#site-tooltip").count() == 0
    assert page.locator("[data-tip]").count() == 0
