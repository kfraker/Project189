"""Home page flows in a real browser: weight cards, health bar, header stats,
Quick Add (weigh-in + workout), and editing the weight cards."""
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from tests.conftest import seed_setting, seed_weight


def _day(offset):
    return (date.today() - timedelta(days=offset)).isoformat()


TODAY = _day(0)


@pytest.fixture()
def home(signed_in_page, client):
    """Signed-in browser + an API client for seeding, both on test user 1."""
    def open_home():
        signed_in_page.goto("/")
        signed_in_page.wait_for_load_state("networkidle")
        return signed_in_page
    return open_home, client


def _text(page, element_id):
    return page.locator(f"#{element_id}")


# ── What the page shows ──────────────────────────────────────────────────────

def test_new_account_shows_empty_cards_and_zero_stats(home):
    open_home, _ = home
    page = open_home()
    for plate in ("start", "current", "lost", "goal"):
        expect(_text(page, f"{plate}-lbs-num")).to_have_text("—")
    expect(_text(page, "mp-active-streak")).to_have_text("0 days")
    expect(_text(page, "mp-kcal-week")).to_have_text("0")
    expect(_text(page, "mp-trend")).to_have_text("—")


def test_cards_and_health_bar_reflect_saved_weights(home):
    open_home, client = home
    seed_setting(client, "starting_weight", 230.0)
    seed_setting(client, "goal_weight", 189.0)
    seed_weight(client, TODAY, 210.0)
    page = open_home()

    expect(_text(page, "start-lbs-num")).to_have_text("230")
    expect(_text(page, "current-lbs-num")).to_have_text("210")
    expect(_text(page, "goal-lbs-num")).to_have_text("189")
    expect(_text(page, "lost-lbs-num")).to_have_text("20")
    expect(_text(page, "lost-plate-label")).to_have_text("LOST")
    # 20 of 41 lbs lost → 48.8% of the way to goal
    expect(_text(page, "healthbar-fill-track")).to_have_attribute("aria-valuenow", "48.8")
    expect(_text(page, "healthbar-tooltip")).to_have_text("21.0 lbs to goal")


def test_header_shows_streak_kcal_and_trend(home):
    open_home, client = home
    seed_weight(client, _day(1), 198.0)
    seed_weight(client, _day(2), 196.0)          # last-7 avg 197
    seed_weight(client, _day(8), 200.0)
    seed_weight(client, _day(9), 202.0)          # prior-7 avg 201
    client.post("/api/workout", json={"date": TODAY, "type": "Basketball", "duration_min": 30,
                                      "kcal": 260, "note": ""})
    page = open_home()
    expect(_text(page, "mp-active-streak")).to_have_text("3 days")   # today (workout) + 2 weigh-ins
    expect(_text(page, "mp-kcal-week")).to_have_text("260")
    expect(_text(page, "mp-trend")).to_have_text("−4.0")


# ── Quick Add → weigh-in ─────────────────────────────────────────────────────

def test_quick_add_weigh_in_updates_card_and_streak(home):
    """Regression for #17: the header streak refreshes right after logging."""
    open_home, client = home
    page = open_home()
    page.locator("#mp-footer-add-btn").click()
    expect(_text(page, "quick-add-modal")).to_be_visible()
    page.locator("#qa-log-weight").click()

    modal = _text(page, "history-modal")
    expect(modal).to_be_visible()
    expect(_text(page, "history-date")).not_to_have_value("")   # today is pre-selected
    page.locator("#history-weight").fill("205")
    page.locator("#history-save").click()

    expect(modal).to_be_hidden()
    expect(_text(page, "current-lbs-num")).to_have_text("205")
    expect(_text(page, "mp-active-streak")).to_have_text("1 day")
    rows = client.get("/api/weights?range=all").get_json()
    assert [(r["date"], r["weight_lbs"]) for r in rows] == [(TODAY, 205.0)]


# ── Editing the weight cards ─────────────────────────────────────────────────

def test_edit_current_weight_asks_before_overwriting_today(home):
    open_home, client = home
    seed_setting(client, "starting_weight", 230.0)
    seed_weight(client, TODAY, 210.0)
    page = open_home()

    page.locator("#current-plate").click()
    expect(_text(page, "current-input")).to_have_value("210")
    page.locator("#current-input").fill("208")
    page.locator("#current-save").click()

    expect(_text(page, "current-screen-confirm")).to_be_visible()
    expect(_text(page, "current-overwrite-message")).to_contain_text("overwrite")
    page.locator("#current-overwrite-confirm").click()

    expect(_text(page, "current-modal")).to_be_hidden()
    expect(_text(page, "current-lbs-num")).to_have_text("208")
    expect(_text(page, "lost-lbs-num")).to_have_text("22")
    expect(_text(page, "mp-active-streak")).to_have_text("1 day")
    assert client.get("/api/latest-weight").get_json()["weight_lbs"] == 208.0


def test_set_goal_weight_persists(home):
    open_home, client = home
    page = open_home()
    page.locator("#goal-plate").click()
    page.locator("#goal-input").fill("180")
    page.locator("#goal-save").click()
    expect(_text(page, "goal-modal")).to_be_hidden()
    expect(_text(page, "goal-lbs-num")).to_have_text("180")

    page = open_home()   # still there after a reload
    expect(_text(page, "goal-lbs-num")).to_have_text("180")


def test_starting_weight_stepper_and_kg_preview(home):
    open_home, _ = home
    page = open_home()
    page.locator("#start-plate").click()
    page.locator("#start-input").fill("230")
    page.locator("#start-step-up").click()
    expect(_text(page, "start-input")).to_have_value("231")
    expect(_text(page, "start-kg-preview")).to_have_text("104.8 kgs")
    page.locator("#start-save").click()
    expect(_text(page, "start-lbs-num")).to_have_text("231")
    expect(_text(page, "start-kg-num")).to_have_text("104.8")


def test_cancel_does_not_save(home):
    open_home, client = home
    page = open_home()
    page.locator("#goal-plate").click()
    page.locator("#goal-input").fill("180")
    page.locator("#goal-cancel").click()
    expect(_text(page, "goal-modal")).to_be_hidden()
    expect(_text(page, "goal-lbs-num")).to_have_text("—")
    assert "goal_weight" not in client.get("/api/settings").get_json()


# ── Quick Add → workout ──────────────────────────────────────────────────────

def test_quick_add_workout_updates_kcal_and_streak(home):
    open_home, client = home
    page = open_home()
    page.locator("#mp-footer-add-btn").click()
    page.locator("#qa-log-workout").click()

    modal = _text(page, "wp-log-modal")
    expect(modal).to_be_visible()
    page.locator("#workout-type-input").fill("Basket")
    page.locator("#workout-search-dropdown .wsd-item", has_text="Basketball").click()
    expect(_text(page, "workout-selected-label")).to_have_text("Basketball")
    # 6.5 MET × 80 kg default (no weigh-ins yet) × 0.5 h = 260 kcal
    expect(_text(page, "workout-kcal-num")).to_have_text("260")
    page.locator("#wpm-add-activity-btn").click()
    expect(page.locator("#wpm-staged-entries .wpm-staged-row")).to_have_count(1)
    page.locator("#wp-modal-save").click()

    expect(modal).to_be_hidden()
    expect(_text(page, "mp-kcal-week")).to_have_text("260")
    expect(_text(page, "mp-active-streak")).to_have_text("1 day")
    workouts = client.get("/api/workouts").get_json()
    assert [(w["date"], w["type"], w["kcal"]) for w in workouts] == [(TODAY, "Basketball", 260)]


def test_remove_workouts_deletes_only_ticked_ones(home):
    """Regression for #23 on Home: in the delete-confirm checklist, only the
    ticked workouts are deleted."""
    open_home, client = home
    for workout_type in ("Basketball", "Yoga"):
        client.post("/api/workout", json={"date": TODAY, "type": workout_type, "duration_min": 30,
                                          "kcal": 200, "note": ""})
    page = open_home()
    page.locator("#mp-footer-add-btn").click()
    page.locator("#qa-log-workout").click()
    # Today already has workouts, so the modal opens with no date: pick today.
    page.locator("#wp-date-input").click()
    page.locator("#wpm-dp-grid .dp-today").click()

    day_rows = page.locator("#wpm-day-entries .wpm-day-row")
    expect(day_rows).to_have_count(2)
    day_rows.first.get_by_role("button", name="Delete").click()
    day_rows.first.get_by_role("button", name="Delete").click()
    page.locator("#wp-modal-save").click()

    expect(page.locator("#idx-del-check-modal")).to_be_visible()
    page.locator("#idx-del-checks label", has_text="Yoga").locator("input").uncheck()
    page.locator("#idx-del-check-ok").click()
    expect(page.locator("#wp-log-modal")).to_be_hidden()
    assert [w["type"] for w in client.get("/api/workouts").get_json()] == ["Yoga"]


# ── Pop-ups sit above the header, footer and health bar (bug #22) ───────────

def _covering_element(page, selector):
    """The id/class of whatever is actually on top at the centre of `selector`."""
    return page.evaluate("""sel => {
        const r = document.querySelector(sel).getBoundingClientRect();
        const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
        return top.closest('#wp-log-modal') ? 'modal' : (top.id || top.className || top.tagName);
    }""", selector)


@pytest.mark.parametrize("path,open_button", [
    ("/", None),                       # Home: + → Quick Add → Log Workout
    ("/workouts", "#wp-add-btn"),      # Workouts page: its own + button
])
def test_log_workout_modal_fully_usable_on_laptop_screen(signed_in_page, path, open_button):
    """Regression for #22: at 1366×768 the modal used to sit under the header,
    footer and health bar, so Save couldn't be clicked."""
    page = signed_in_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(path)
    page.wait_for_load_state("networkidle")
    if open_button:
        page.locator(open_button).click()
    else:
        page.locator("#mp-footer-add-btn").click()
        page.locator("#qa-log-workout").click()
    expect(page.locator("#wp-log-modal")).to_be_visible()

    assert _covering_element(page, "#wp-log-modal-title") == "modal"
    assert _covering_element(page, "#wp-modal-save") == "modal"
    page.locator("#wp-modal-save").click(trial=True, timeout=3000)
