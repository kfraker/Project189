"""GET /weights — weights page renders correctly.

Chart, weekly-summary, moving-average, goal-line, and notes-on-weigh-ins
functionality moved here from index.html during the base.html migration
(v2.8.0) — the homepage is now a lightweight dashboard (health bar + weight
plates + quick-add modals), and the full historical/table/chart experience
lives on this dedicated page, mirroring the /workouts split.
"""
import pytest


@pytest.fixture()
def html(client):
    return client.get("/weights").data.decode()


def test_weights_page_returns_200(client):
    assert client.get("/weights").status_code == 200


# ── Daily/Weekly + chart/table toggle (replaces the old slide-nav arrow buttons) ──

def test_chart_type_toggle_btn_present(html):
    """chart-type-btn now drives the daily<->weekly slide transition (replaces the
    old chart-page-btn-left/right arrow buttons removed in the base.html migration)."""
    assert 'id="chart-type-btn"' in html


def test_view_toggle_btn_present(html):
    """view-toggle-btn switches between chart and table view."""
    assert 'id="view-toggle-btn"' in html


def test_filter_btn_present(html):
    """mp-filter-btn opens the date-range filter menu."""
    assert 'id="mp-filter-btn"' in html


def test_goal_line_uses_second_dataset(html):
    """Goal weight line must be a second Chart.js dataset, not a custom plugin."""
    assert 'goalWeightVal' in html
    assert 'goalData' in html

def test_goal_line_uses_border_dash(html):
    """Goal weight dataset must use borderDash for the dashed line style."""
    assert 'borderDash' in html

def test_tooltip_filters_to_weight_dataset(html):
    """External tooltip must filter to datasetIndex 0 to skip the goal line dataset."""
    assert 'datasetIndex===0' in html

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
    assert "/api/weight/'+activeDate+'/note" in html

def test_chart_tooltip_shows_notes(html):
    """Chart tooltip must render the ctt-note div when a note exists."""
    assert 'ctt-note' in html

def test_goal_line_is_teal(html):
    """Goal weight dataset must use a teal border color, not amber."""
    assert 'rgba(0,200,175' in html

def test_goal_label_plugin_registered(html):
    """A Chart.js afterDraw plugin must be registered to draw y-axis labels."""
    assert "id: 'chartAxisLabels'" in html
    assert 'afterDraw' in html

def test_goal_label_reads_window_goal_weight_val(html):
    """Plugin must read window.goalWeightVal to get the goal value."""
    assert 'window.goalWeightVal' in html

def test_goal_line_gated_on_pref_in_load_chart(html):
    """loadChart must read pref_goal_line from localStorage before drawing the line."""
    assert "pref_goal_line" in html
    assert "goalLineOn" in html

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
    assert 'rgba(255,200,50' in html

def test_weekly_chart_canvas_present(html):
    assert 'id="weekly-chart"' in html

def test_weekly_chart_empty_msg_present(html):
    assert 'id="weekly-chart-empty"' in html

def test_weekly_info_icon_present(html):
    assert 'id="weekly-info-icon"' in html

def test_weekly_add_btn_present(html):
    """Shared add-entry button must be present; it's accessible from both daily and weekly views."""
    assert 'id="chart-add-btn"' in html

def test_custom_weeks_input_present(html):
    assert 'id="custom-weeks"' in html

def test_chart_slide_viewport_present(html):
    assert 'id="chart-slide-viewport"' in html

def test_chart_slide_inner_present(html):
    assert 'id="chart-slide-inner"' in html

def test_chart_with_nav_wrapper_present(html):
    assert 'class="chart-with-nav"' in html

def test_at_weekly_css_class_defined(html):
    """JS must use 'at-weekly' class to trigger the slide transition."""
    assert 'at-weekly' in html

def test_table_view_title_present(html):
    """Shared table must have a title element that updates per active chart."""
    assert 'id="table-view-title"' in html

def test_load_weekly_chart_once_defined(html):
    """window.loadWeeklyChartOnce must be assigned so slide nav can trigger lazy load."""
    assert 'window.loadWeeklyChartOnce' in html

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

def test_weekly_chart_slices_to_max_weeks(html):
    """Weekly chart must trim grouped calendar weeks to exactly the requested count."""
    assert 'maxWeeks' in html
    assert 'weeks.slice' in html

def test_get_weekly_chart_range_null_when_empty(html):
    """getWeeklyChartRange must return null (not 4) when the custom-weeks input is empty."""
    idx = html.find('window.getWeeklyChartRange = ')
    assert idx != -1
    snippet = html[idx:idx + 200]
    assert '||null' in snippet

def test_weekly_range_active_button_initialized(html):
    """Weekly chart IIFE must dynamically set the active button from the saved preference."""
    assert 'activeWeeksRange' in html
    assert 'initBtn' in html

def test_missing_row_has_height_spacer(html):
    """Missing table rows must render dash content and action buttons so they match the height of data rows."""
    assert 'row-missing' in html
    assert 'missing-dash' in html

def test_custom_days_default_is_30(html):
    """When no custom-days preference is saved, the daily chart must default to 30 days."""
    assert 'parseInt(savedCustomDaysStr) || 30' in html
