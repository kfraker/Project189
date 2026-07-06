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

def test_profile_menu_container(html):
    assert 'id="profile-menu"' in html


def test_profile_sub_buttons(html):
    assert 'id="dumbbell-btn"' in html
    assert 'id="protein-btn"' in html
    assert 'id="whistle-btn"' in html
    assert 'id="settings-btn"' in html


# ── Unit toggle ───────────────────────────────────────────────────────────────

def test_unit_toggle_btn_present(html):
    assert 'id="unit-toggle-btn"' in html


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
    for name in ('pointer.png', 'pointer2.png', 'pointer3.png', 'pointer4.png',
                 'editpointer.png', 'editpointer2.png', 'editpointer3.png', 'editpointer4.png'):
        assert name in html, f'{name} not referenced in page'


def test_cursor_sets_cover_all_profiles(html):
    """CURSOR_SETS must define entries for all four profiles."""
    assert "pointer2.png" in html
    assert "pointer3.png" in html
    assert "pointer4.png" in html
    assert "editpointer2.png" in html
    assert "editpointer3.png" in html
    assert "editpointer4.png" in html


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


def test_whistle_btn_not_in_coming_soon(html):
    """whistle-btn must not appear in the coming-soon forEach list."""
    idx = html.find("'dumbbell-btn', 'protein-btn'")
    assert idx != -1, "Coming-soon list not found"
    snippet = html[idx:idx + 80]
    assert 'whistle' not in snippet


def test_predicted_goal_date_is_wide(html):
    """Predicted Goal Date stat must carry wide: true so it spans the full grid row."""
    idx = html.find("'Predicted Goal Date'")
    assert idx != -1, "Predicted Goal Date stat not found"
    snippet = html[idx:idx + 220]
    assert 'wide: true' in snippet


def test_most_common_day_removed_from_insights(html):
    """Most Common Day was removed from the insights stats array."""
    assert "'Most Common Day'" not in html


def test_insights_uses_open_exclusive(html):
    """Insights button must open via openExclusive, not a manual activeModal guard."""
    assert 'openExclusive(openInsights)' in html


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
    """computeGoalDateISO must be defined as a module-level function."""
    assert 'function computeGoalDateISO' in html


def test_chart_fetches_settings_alongside_rows(html):
    """loadChart must fetch /api/settings in parallel with /api/weights."""
    assert "fetch('/api/settings')" in html


def test_goal_line_uses_second_dataset(html):
    """Goal weight line must be a second Chart.js dataset, not a custom plugin."""
    assert 'goalWeightVal' in html
    assert 'goalData' in html


def test_goal_line_uses_border_dash(html):
    """Goal weight dataset must use borderDash for the dashed line style."""
    assert 'borderDash' in html


def test_tooltip_filters_to_weight_dataset(html):
    """External tooltip must filter to datasetIndex 0 to skip the goal line dataset."""
    assert 'datasetIndex === 0' in html


# ── Notes on weigh-ins ────────────────────────────────────────────────────────

def test_note_popover_present(html):
    assert 'id="note-popover"' in html


def test_note_popover_textarea_present(html):
    assert 'id="note-popover-text"' in html


def test_note_popover_date_span_present(html):
    assert 'id="note-popover-date"' in html


def test_note_popover_save_cancel_buttons(html):
    assert 'id="note-popover-save"'   in html
    assert 'id="note-popover-cancel"' in html


def test_note_textarea_wrap_present(html):
    """Textarea must be wrapped in note-textarea-wrap for custom scrollbar overlay."""
    assert 'class="note-textarea-wrap"' in html


def test_note_custom_scrollbar_track_present(html):
    """Custom scrollbar track div must exist inside note-textarea-wrap."""
    assert 'class="note-scrollbar-track"' in html


def test_note_custom_scrollbar_thumb_present(html):
    """Custom scrollbar thumb div must exist inside the track."""
    assert 'class="note-scrollbar-thumb"' in html


def test_open_note_editor_defined(html):
    """window.openNoteEditor must be assigned so table rows can call it."""
    assert 'window.openNoteEditor' in html


def test_note_btn_class_used_in_render_table(html):
    """note-btn class must be applied inside renderTable."""
    assert "'note-btn'" in html or '"note-btn"' in html


def test_note_patch_endpoint_called(html):
    """Frontend must PATCH /api/weight/.../note to save notes."""
    assert "/api/weight/' + activeDate + '/note" in html


def test_chart_tooltip_shows_notes(html):
    """Chart tooltip must render the ctt-note div when a note exists."""
    assert 'ctt-note' in html


def test_goal_line_is_teal(html):
    """Goal weight dataset must use a teal border color, not amber."""
    assert 'rgba(0, 200, 175' in html


def test_goal_label_plugin_registered(html):
    """A Chart.js afterDraw plugin must be registered to draw y-axis labels."""
    assert "id: 'chartAxisLabels'" in html
    assert 'afterDraw' in html


def test_goal_label_reads_window_goal_weight_val(html):
    """Plugin must read window.goalWeightVal to get the goal value."""
    assert 'window.goalWeightVal' in html


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


def test_goal_line_gated_on_pref_in_load_chart(html):
    """loadChart must read pref_goal_line from localStorage before drawing the line."""
    assert "pref_goal_line" in html
    assert "goalLineOn" in html


# ── Moving average line ───────────────────────────────────────────────────────

def test_ma_toggle_buttons_present(html):
    """Settings modal must have On/Off buttons for the moving average preference."""
    assert 'id="prof-ma-line-on"' in html
    assert 'id="prof-ma-line-off"' in html


def test_ma_pref_key_saved(html):
    """doSave must write pref_ma_line to preferences."""
    assert 'pref_ma_line' in html


def test_ma_data_computed_in_load_chart(html):
    """loadChart must compute maData and set window.maCurrentVal."""
    assert 'maData' in html
    assert 'window.maCurrentVal' in html


def test_ma_is_third_dataset(html):
    """MA must be the third Chart.js dataset (index 2)."""
    assert 'datasets[2].data' in html


def test_ma_label_plugin_draws_7d_avg(html):
    """afterDraw plugin must draw the 7D AVG label."""
    assert '7D AVG' in html


def test_ma_color_is_amber(html):
    """MA dataset must use an amber border color."""
    assert 'rgba(255, 200, 50' in html


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

def test_weekly_chart_canvas_present(html):
    assert 'id="weekly-chart"' in html


def test_weekly_chart_empty_msg_present(html):
    assert 'id="weekly-chart-empty"' in html


def test_weekly_info_icon_present(html):
    assert 'id="weekly-info-icon"' in html


def test_weekly_add_btn_present(html):
    """Shared add-entry button must be present; it's accessible from both daily and weekly views."""
    assert 'id="chart-add-btn"' in html


def test_weekly_range_btns_present(html):
    """All five weekly range buttons must exist."""
    for weeks in ('4', '12', '30', 'all', 'custom'):
        assert f'data-weeks="{weeks}"' in html, f'missing data-weeks="{weeks}"'


def test_custom_weeks_input_present(html):
    assert 'id="custom-weeks"' in html


def test_custom_weeks_minimum_4(html):
    """Custom weeks input must enforce a minimum of 4."""
    assert 'min="4"' in html


def test_custom_weeks_maximum_156(html):
    """Custom weeks input must cap at 156 weeks (3 years)."""
    assert 'max="156"' in html


# ── Chart slider structure ────────────────────────────────────────────────────

def test_chart_slide_viewport_present(html):
    assert 'id="chart-slide-viewport"' in html


def test_chart_slide_inner_present(html):
    assert 'id="chart-slide-inner"' in html


def test_chart_page_nav_buttons_present(html):
    """Left and right slide nav buttons must both be present."""
    assert 'id="chart-page-btn-left"' in html
    assert 'id="chart-page-btn-right"' in html


def test_chart_page_left_btn_starts_invisible(html):
    """Left nav button must start invisible (only shows when on weekly page)."""
    assert 'id="chart-page-btn-left"' in html
    idx = html.find('id="chart-page-btn-left"')
    snippet = html[max(0, idx - 80):idx + 20]
    assert 'invisible' in snippet


def test_chart_page_nav_outside_viewport(html):
    """Nav buttons must be siblings of the slide viewport, not inside .chart-header."""
    left_pos     = html.find('id="chart-page-btn-left"')
    right_pos    = html.find('id="chart-page-btn-right"')
    viewport_pos = html.find('id="chart-slide-viewport"')
    assert left_pos < viewport_pos, 'left nav button must precede the viewport'
    assert right_pos > viewport_pos, 'right nav button must follow the viewport'


def test_chart_with_nav_wrapper_present(html):
    assert 'class="chart-with-nav"' in html


def test_at_weekly_css_class_defined(html):
    """JS must use 'at-weekly' class to trigger the slide transition."""
    assert 'at-weekly' in html


def test_table_view_title_present(html):
    """Shared table must have a title element that updates per active chart."""
    assert 'id="table-view-title"' in html


# ── Weekly chart JS ───────────────────────────────────────────────────────────

def test_load_weekly_chart_once_defined(html):
    """window.loadWeeklyChartOnce must be assigned so slide nav can trigger lazy load."""
    assert 'window.loadWeeklyChartOnce' in html


def test_refresh_weekly_chart_defined(html):
    """window.refreshWeeklyChart must be assigned for unit-toggle and settings save."""
    assert 'window.refreshWeeklyChart' in html


def test_get_weekly_chart_range_defined(html):
    assert 'window.getWeeklyChartRange' in html


def test_current_chart_page_defined(html):
    """window.currentChartPage must be set so view-toggle and unit-toggle can branch."""
    assert 'window.currentChartPage' in html


def test_weekly_chart_groups_by_iso_week(html):
    """Weekly chart must use ISO-week Monday-start grouping."""
    assert 'isoWeekMonday' in html or 'groupByWeek' in html


def test_weekly_chart_reads_api_as_bare_array(html):
    """loadWeeklyChart must treat /api/weights response as a direct array, not data.weights."""
    assert 'filteredRows' in html
    assert 'data.weights' not in html or html.count('data.weights') == 0


def test_weekly_chart_tooltip_uses_shared_element(html):
    """Weekly tooltip must reuse the existing chartTtEl div (referenced more than once — daily + weekly)."""
    assert html.count('chartTtEl') >= 2


def test_weekly_chart_sets_axis_label_globals(html):
    """Weekly chart must set window.goalWeightVal and window.trendCurrentVal for the label plugin."""
    assert 'window.goalWeightVal' in html
    assert 'window.trendCurrentVal' in html


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
    """CURSOR_SETS must include pointer4.png and editpointer4.png."""
    assert 'pointer4.png' in html
    assert 'editpointer4.png' in html


# ── Weekly chart fixes (v2.2.1) ───────────────────────────────────────────────

def test_weekly_chart_slices_to_max_weeks(html):
    """Weekly chart must trim grouped calendar weeks to exactly the requested count."""
    assert 'maxWeeks' in html
    assert 'weeks.slice' in html


def test_set_weekly_range_defined(html):
    """window.setWeeklyRange must be assigned so settings-save can update the chart."""
    assert 'window.setWeeklyRange' in html


def test_get_weekly_chart_range_null_when_empty(html):
    """getWeeklyChartRange must return null (not 4) when the custom-weeks input is empty."""
    idx = html.find('getWeeklyChartRange')
    assert idx != -1
    snippet = html[idx:idx + 200]
    assert '|| null' in snippet


def test_weekly_range_active_button_initialized(html):
    """Weekly chart IIFE must dynamically set the active button from the saved preference."""
    assert 'activeWeeksRange' in html
    assert 'initWeeklyBtn' in html


def test_missing_row_has_height_spacer(html):
    """Missing table rows must render dash content and action buttons so they match the height of data rows."""
    assert 'row-missing' in html
    assert 'missing-dash' in html


def test_custom_days_default_is_30(html):
    """When no custom-days preference is saved, the daily chart must default to 30 days."""
    assert 'parseInt(savedCustomDaysStr) || 30' in html
