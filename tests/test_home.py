"""GET / — home page renders correctly."""
import pytest


@pytest.fixture()
def html(client):
    return client.get("/").data.decode()


def test_home_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_home_returns_html(client):
    response = client.get("/")
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_home_contains_app_elements(client):
    """Key landmarks exist in the served HTML."""
    html = client.get("/").data.decode()
    assert "chart-tooltip" in html or "chart-wrap" in html


# ── Modal presence ────────────────────────────────────────────────────────────

def test_settings_modal_present(html):
    assert 'id="settings-modal"' in html


def test_profile_modal_id_removed(html):
    """Old id was renamed to settings-modal in v1.2.0; verify no stale reference."""
    assert 'id="profile-modal"' not in html


def test_fight_card_modal_present(html):
    assert 'id="fight-card-modal"' in html


# ── Fight Card fields ─────────────────────────────────────────────────────────

def test_fight_card_name_input(html):
    assert 'id="fight-name"' in html


def test_fight_card_sex_buttons(html):
    assert 'id="fight-sex-male"' in html
    assert 'id="fight-sex-female"' in html


def test_fight_card_dob_input(html):
    assert 'id="fight-dob"' in html


def test_fight_card_age_display(html):
    assert 'id="fight-age-num"' in html


def test_fight_card_height_fields(html):
    assert 'id="fight-height-ft"' in html
    assert 'id="fight-height-in"' in html
    assert 'id="fight-height-cm"' in html


# ── Custom date picker (history modal) ───────────────────────────────────────

def test_history_date_picker_wrap(html):
    assert 'id="history-date-wrap"' in html


def test_history_calendar_dropdown(html):
    assert 'id="history-calendar"' in html


def test_history_calendar_nav_buttons(html):
    assert 'id="dp-prev"' in html
    assert 'id="dp-next"' in html


def test_history_calendar_grid(html):
    assert 'id="dp-grid"' in html


def test_history_calendar_month_label(html):
    assert 'id="dp-month-label"' in html


# ── Custom date picker (fight card DOB) ──────────────────────────────────────

def test_fight_dob_calendar_dropdown(html):
    assert 'id="fight-dob-calendar"' in html


def test_fight_dob_calendar_nav_buttons(html):
    assert 'id="fight-dp-prev"' in html
    assert 'id="fight-dp-next"' in html


def test_fight_dob_calendar_grid(html):
    assert 'id="fight-dp-grid"' in html


# ── Profile menu ──────────────────────────────────────────────────────────────
# Hover-based profile-menu was replaced by a tap-friendly "Menu" modal (base.html
# migration, v2.8.0). Sub-buttons live in the footer nav / menu modal now.

def test_profile_menu_container(html):
    """Old hover profile-menu was replaced by the tap-to-open menu-modal."""
    assert 'id="menu-modal"' in html


def test_profile_sub_buttons(html):
    assert 'id="protein-btn"' in html
    assert 'id="menu-settings-btn"' in html


def test_menu_modal_profile_and_close_buttons(html):
    """menu-modal must also have the Insights, Profile (Fight Card) and close buttons."""
    assert 'id="menu-insights-btn"' in html
    assert 'id="menu-profile-btn"' in html
    assert 'id="menu-modal-close"' in html


def test_menu_modal_insights_appears_first(html):
    """Insights must be the first option in the menu modal, before Profile and Settings."""
    insights_pos = html.index('id="menu-insights-btn"')
    profile_pos  = html.index('id="menu-profile-btn"')
    settings_pos = html.index('id="menu-settings-btn"')
    assert insights_pos < profile_pos < settings_pos


# ── Unit toggle ───────────────────────────────────────────────────────────────

def test_unit_toggle_btn_present(html):
    """Standalone unit-toggle-btn was folded into the Settings modal's LBS/KGS toggle pair."""
    assert 'id="prof-lbs-btn"' in html
    assert 'id="prof-kg-btn"' in html


# ── Profile pic picker ────────────────────────────────────────────────────────

def test_change_pic_btn_present(html):
    assert 'id="change-pic-btn"' in html


def test_profile_pic_picker_present(html):
    assert 'id="profile-pic-picker"' in html


def test_profile_pic_backdrop_present(html):
    assert 'id="profile-pic-backdrop"' in html


def test_profile_pic_options_present(html):
    assert 'data-pic="1"' in html
    assert 'data-pic="2"' in html
    assert 'data-pic="3"' in html


def test_profile_pic_picker_actions(html):
    assert 'id="pic-save-btn"' in html
    assert 'id="pic-cancel-btn"' in html


def test_profile_pic_all_images_referenced(html):
    assert 'profilebutton.png' in html
    assert 'profile2button.png' in html
    assert 'profile3button.png' in html
    assert 'profile4button.png' in html


# ── Cursor sets ───────────────────────────────────────────────────────────────

def test_all_cursor_images_referenced(html):
    for name in ('pointer.png', 'pointer2.png', 'pointer3.png', 'pointer4.png'):
        assert name in html, f'{name} not referenced in page'


def test_cursor_sets_cover_all_profiles(html):
    """CURSOR_SETS must define entries for all four profiles."""
    assert "pointer2.png" in html
    assert "pointer3.png" in html
    assert "pointer4.png" in html


def test_change_pic_btn_inside_settings_modal(html):
    """change-pic-btn must appear before the settings modal's closing tag."""
    settings_start = html.find('id="settings-modal"')
    change_pic_pos = html.find('id="change-pic-btn"')
    picker_pos     = html.find('id="profile-pic-picker"')
    assert settings_start < change_pic_pos
    assert change_pic_pos < picker_pos


# ── Insights modal ────────────────────────────────────────────────────────────

def test_insights_modal_present(html):
    assert 'id="insights-modal"' in html


def test_insights_grid_present(html):
    assert 'id="insights-grid"' in html


def test_insights_close_btn_present(html):
    assert 'id="insights-close"' in html


def test_insights_modal_before_settings_modal(html):
    """Insights modal must appear before settings modal in document order."""
    assert html.index('id="insights-modal"') < html.index('id="settings-modal"')


def test_dumbbell_btn_not_in_coming_soon(html):
    """dumbbell-btn must not be in the coming-soon list — it opens the workout modal."""
    protein_idx = html.find("'protein-btn'")
    cs_snippet  = html[max(0, protein_idx - 20):protein_idx + 20]
    assert 'dumbbell' not in cs_snippet


def test_dumbbell_links_to_workouts_page(html):
    """Dumbbell button must now be an <a> linking to /workouts."""
    assert 'href="/workouts"' in html


def test_workout_modal_not_on_home(html):
    """Workout modal moved to /workouts page — should not be in index.html."""
    assert 'id="workout-modal"' not in html


def test_predicted_goal_date_is_wide(html):
    """Predicted Goal Date stat must carry wide:true so it spans the full grid row."""
    idx = html.find("'Predicted Goal Date'")
    assert idx != -1, "Predicted Goal Date stat not found"
    snippet = html[idx:idx + 220]
    assert 'wide:true' in snippet


def test_most_common_day_removed_from_insights(html):
    """Most Common Day was removed from the insights stats array."""
    assert "'Most Common Day'" not in html


def test_insights_uses_open_exclusive(html):
    """Insights button must open via openExclusive, not a manual activeModal guard."""
    assert 'openExclusive(window.openInsights)' in html


def test_insight_card_wide_class_in_render(html):
    """render() must apply insight-card-wide class for wide stat cards."""
    assert 'insight-card-wide' in html


def test_fight_card_activity_buttons(html):
    """Fight Card must contain all four activity level buttons."""
    assert 'id="fight-act-sedentary"' in html
    assert 'id="fight-act-light"'     in html
    assert 'id="fight-act-moderate"'  in html
    assert 'id="fight-act-active"'    in html


# ── Goal date vertical line ────────────────────────────────────────────────────

def test_compute_goal_date_iso_defined(html):
    """Goal-date prediction (Mifflin-St. Jeor estimate, inlined into the Insights
    render in the base.html migration) must still compute a predicted date string."""
    assert 'goalDateStr' in html
    assert 'Mifflin-St. Jeor' in html


def test_chart_fetches_settings_alongside_rows(html):
    """loadChart must fetch /api/settings in parallel with /api/weights."""
    assert "fetch('/api/settings')" in html


# ── Notes on weigh-ins ────────────────────────────────────────────────────────

def test_goal_label_unit_aware(html):
    """Goal label must switch between lbs and kgs based on active unit."""
    assert "'kgs'" in html or '"kgs"' in html


# ── Goal line visibility toggle ───────────────────────────────────────────────

def test_goal_line_toggle_buttons_present(html):
    """Settings modal must have On/Off buttons for the goal line preference."""
    assert 'id="prof-goal-line-on"' in html
    assert 'id="prof-goal-line-off"' in html


def test_goal_line_pref_key_saved(html):
    """doSave must write pref_goal_line to preferences."""
    assert 'pref_goal_line' in html


# ── Moving average line ───────────────────────────────────────────────────────

def test_ma_toggle_buttons_present(html):
    """Settings modal must have On/Off buttons for the moving average preference."""
    assert 'id="prof-ma-line-on"' in html
    assert 'id="prof-ma-line-off"' in html


def test_ma_pref_key_saved(html):
    """doSave must write pref_ma_line to preferences."""
    assert 'pref_ma_line' in html


# ── Settings section labels ───────────────────────────────────────────────────

def test_settings_sections_present(html):
    """Settings modal must have expected section labels."""
    assert 'Default Formats' in html
    assert 'Chart Landing' in html
    assert 'Daily Summary' in html
    assert 'Weekly Summary' in html
    assert 'HUD' in html


def test_settings_collapsible_bodies_present(html):
    """Each section must have a collapsible body wrapper."""
    for key in ('measurements', 'landing', 'overtime', 'weekly', 'hud'):
        assert f'id="ssb-{key}"' in html


def test_settings_section_data_attrs_present(html):
    """Each section label must carry a data-section attribute."""
    for key in ('measurements', 'landing', 'overtime', 'weekly', 'hud'):
        assert f'data-section="{key}"' in html


def test_settings_section_label_class(html):
    """Section dividers must use the settings-section-label class."""
    assert 'settings-section-label' in html


# ── Health bar HUD ────────────────────────────────────────────────────────────

def test_healthbar_hud_present(html):
    assert 'id="healthbar-hud"' in html


def test_healthbar_wrap_present(html):
    assert 'id="healthbar-wrap"' in html


def test_healthbar_fill_track_present(html):
    assert 'id="healthbar-fill-track"' in html


def test_healthbar_fill_present(html):
    assert 'id="healthbar-fill"' in html


def test_healthbar_img_present(html):
    assert 'id="healthbar-img"' in html
    assert 'healthbar.png' in html


def test_healthbar_tooltip_present(html):
    assert 'id="healthbar-tooltip"' in html


def test_healthbar_name_present(html):
    assert 'id="healthbar-name"' in html


def test_update_health_bar_defined(html):
    """window.updateHealthBar must be assigned so progress can be reflected."""
    assert 'window.updateHealthBar' in html


def test_update_health_bar_name_defined(html):
    """window.updateHealthBarName must be assigned to refresh name from localStorage."""
    assert 'window.updateHealthBarName' in html


def test_health_bar_reads_fight_name(html):
    """updateHealthBarName must read fight_name from localStorage."""
    assert "fight_name" in html
    assert "healthbar-name" in html


def test_health_bar_canvas_strip_present(html):
    """Canvas white-removal IIFE must be present to make fill zone transparent."""
    assert 'naturalWidth' in html
    assert 'toDataURL' in html


def test_health_bar_tooltip_shows_to_goal(html):
    """Tooltip text must include 'to goal' string."""
    assert 'to goal' in html


def test_fight_name_maxlength(html):
    """Fighter name input must cap at 20 characters."""
    assert 'maxlength="20"' in html


# ── Weekly Summary chart ──────────────────────────────────────────────────────

def test_weekly_range_btns_present(html):
    """All five weekly range buttons must exist."""
    for weeks in ('4', '12', '30', 'all', 'custom'):
        assert f'data-weeks="{weeks}"' in html, f'missing data-weeks="{weeks}"'


def test_custom_weeks_minimum_4(html):
    """Custom weeks input must enforce a minimum of 4."""
    assert 'min="4"' in html


def test_custom_weeks_maximum_156(html):
    """Custom weeks input must cap at 156 weeks (3 years)."""
    assert 'max="156"' in html


# ── Chart slider structure ────────────────────────────────────────────────────

# ── Weekly chart JS ───────────────────────────────────────────────────────────

def test_refresh_weekly_chart_defined(html):
    """window.refreshWeeklyChart must be assigned for unit-toggle and settings save."""
    assert 'window.refreshWeeklyChart' in html


def test_get_weekly_chart_range_defined(html):
    assert 'window.getWeeklyChartRange' in html


# ── Default landing setting ────────────────────────────────────────────────────

def test_default_landing_buttons_present(html):
    assert 'id="prof-landing-daily"' in html
    assert 'id="prof-landing-weekly"' in html
    assert 'id="prof-landing-table-daily"' in html
    assert 'id="prof-landing-table-weekly"' in html


def test_pref_default_landing_saved(html):
    """doSave must persist pref_default_landing to preferences."""
    assert 'pref_default_landing' in html


# ── Weekly Summary section ────────────────────────────────────────────────────

def test_settings_weekly_section_present(html):
    assert 'Weekly Summary' in html


def test_weekly_minmax_buttons_present(html):
    assert 'id="prof-weekly-minmax-on"' in html
    assert 'id="prof-weekly-minmax-off"' in html


def test_pref_weekly_minmax_saved(html):
    assert 'pref_weekly_minmax' in html


def test_weekly_goal_buttons_present(html):
    assert 'id="prof-weekly-goal-on"' in html
    assert 'id="prof-weekly-goal-off"' in html


def test_weekly_trend_buttons_present(html):
    assert 'id="prof-weekly-trend-on"' in html
    assert 'id="prof-weekly-trend-off"' in html


def test_pref_weekly_goal_line_saved(html):
    assert 'pref_weekly_goal_line' in html


def test_pref_weekly_trend_line_saved(html):
    assert 'pref_weekly_trend_line' in html


def test_date_format_buttons_present(html):
    assert 'id="prof-date-mdy"' in html
    assert 'id="prof-date-dmy"' in html


def test_date_format_button_tips(html):
    assert 'data-tip="MM-DD-YYYY"' in html
    assert 'data-tip="DD-MM-YYYY"' in html


def test_pref_date_format_saved(html):
    assert 'pref_date_format' in html


def test_fighter_name_buttons_present(html):
    assert 'id="prof-fighter-name-on"' in html
    assert 'id="prof-fighter-name-off"' in html


def test_pref_fighter_name_saved(html):
    assert 'pref_fighter_name' in html


def test_chart_data_only_button_present(html):
    assert 'id="prof-chart-dots"' in html


def test_chart_no_data_button_present(html):
    assert 'id="prof-chart-none"' in html


# ── Profile 4 ─────────────────────────────────────────────────────────────────

def test_profile_pic_option_4_present(html):
    """Profile 4 must have a selectable button in the pic picker."""
    assert 'data-pic="4"' in html


def test_profile_4_cursor_images_in_cursor_sets(html):
    """CURSOR_SETS must include pointer4.png."""
    assert 'pointer4.png' in html


# ── Weekly chart fixes (v2.2.1) ───────────────────────────────────────────────

def test_set_weekly_range_defined(html):
    """window.setWeeklyRange must be assigned so settings-save can update the chart."""
    assert 'window.setWeeklyRange' in html


def test_fight_goal_lean_button_present(html):
    """Fight card must have a Lean Machine goal button."""
    assert 'id="fight-goal-lean"' in html


def test_fight_goal_muscle_button_present(html):
    """Fight card must have a Muscle Monster goal button."""
    assert 'id="fight-goal-muscle"' in html


def test_fight_goal_row_present(html):
    """Fight card must have a goal toggle row."""
    assert 'fight-goal-row' in html


def test_lost_plate_label_has_id(html):
    """Lost plate textPath must have an id so goal mode can update its label."""
    assert 'id="lost-plate-label"' in html


def test_goal_mode_updates_lost_label(html):
    """updateLostWeight must swap label between LOST and GAINED based on goal mode."""
    assert 'fight_goal_mode' in html
    assert "'GAINED'" in html or '"GAINED"' in html


def test_goal_weight_apiSave_validates_lean(html):
    """apiSave for goal weight must reject equal/higher weights in lean mode."""
    assert 'Must be below starting weight' in html


def test_goal_weight_apiSave_validates_muscle(html):
    """apiSave for goal weight must reject equal/lower weights in muscle mode."""
    assert 'Must exceed starting weight' in html


# ── Workout UI moved to /workouts ─────────────────────────────────────────────
# Tests for autocomplete, compendium, chip, etc. are in test_workouts_page.py
