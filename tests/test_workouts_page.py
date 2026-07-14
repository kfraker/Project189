"""GET /workouts — standalone workout page renders correctly."""
import pytest


@pytest.fixture()
def html(client):
    return client.get("/workouts").data.decode()


def test_workouts_page_returns_200(client):
    assert client.get("/workouts").status_code == 200


def test_workouts_page_has_log_modal(html):
    assert 'id="wp-log-modal"' in html


def test_workouts_page_has_date_input(html):
    assert 'id="wp-date-input"' in html


def test_workouts_page_has_search_input(html):
    assert 'id="workout-type-input"' in html


def test_workouts_page_has_add_button(html):
    assert 'id="wp-add-btn"' in html


def test_workouts_page_has_back_link(html):
    assert 'href="/"' in html


def test_workouts_page_has_search_dropdown(html):
    assert 'id="workout-search-dropdown"' in html


def test_workouts_page_has_selected_chip(html):
    assert 'id="workout-selected-chip"' in html


def test_workouts_page_has_chip_clear(html):
    assert 'id="workout-chip-clear"' in html


def test_workouts_page_has_compendium(html):
    assert 'const WORKOUTS' in html


def test_workouts_page_compendium_entries(html):
    assert 'Running' in html
    assert 'Yoga' in html
    assert 'Cycling' in html


def test_workouts_page_tier_classes(html):
    assert 'tier-intense'  in html
    assert 'tier-hard'     in html
    assert 'tier-moderate' in html
    assert 'tier-light'    in html


def test_api_workouts_date_filter_returns_empty(client):
    """?date= filter returns empty list when no workouts on that date."""
    r = client.get("/api/workouts?date=2000-01-01")
    assert r.status_code == 200
    assert r.get_json() == []


def test_api_workouts_date_filter_returns_matching(client):
    """?date= filter returns only workouts on that date."""
    client.post("/api/workout", json={
        "date": "2026-01-05", "type": "Yoga", "duration_min": 30, "kcal": 100, "note": ""
    }, content_type="application/json")
    client.post("/api/workout", json={
        "date": "2026-01-06", "type": "Running", "duration_min": 20, "kcal": 200, "note": ""
    }, content_type="application/json")
    rows = client.get("/api/workouts?date=2026-01-05").get_json()
    assert len(rows) == 1
    assert rows[0]["type"] == "Yoga"


def test_api_workouts_invalid_date_returns_all(client):
    """?date= with invalid date falls back to returning all workouts."""
    client.post("/api/workout", json={
        "date": "2026-02-01", "type": "Boxing", "duration_min": 45, "kcal": 400, "note": ""
    }, content_type="application/json")
    rows_filtered = client.get("/api/workouts?date=not-a-date").get_json()
    rows_all      = client.get("/api/workouts").get_json()
    assert len(rows_filtered) == len(rows_all)


# ── v2.6.0 UI structure ───────────────────────────────────────────────────────

def test_workouts_page_has_staged_entries(html):
    assert 'id="wpm-staged-entries"' in html


def test_workouts_page_has_add_activity_btn(html):
    assert 'id="wpm-add-activity-btn"' in html


def test_workouts_page_has_entries_scroll(html):
    assert 'id="wpm-entries-scroll"' in html


def test_workouts_page_has_custom_scroll_thumb(html):
    assert 'id="wpm-scroll-thumb"' in html


def test_workouts_page_has_del_check_modal(html):
    assert 'id="wp-del-check-modal"' in html


def test_workouts_page_has_day_note_input(html):
    assert 'id="workout-note-input"' in html


def test_workouts_page_has_confirm_modal(html):
    """Per-page wp-confirm-modal was consolidated into the shared app-confirm-modal
    (base.html migration) — used via window.showAppConfirm()."""
    assert 'id="app-confirm-modal"' in html


def test_workouts_page_has_day_heading(html):
    assert 'id="wpm-day-heading"' in html


# ── v2.7.0 UI structure — filter menu + custom range modal ───────────────────

def test_workouts_page_has_filter_btn(html):
    assert 'id="wp-filter-btn"' in html


def test_workouts_page_has_range_menu(html):
    assert 'id="wp-range-menu"' in html


def test_workouts_page_has_all_range_buttons(html):
    for label in ('all', '1y', '90d', '30d', '7d', 'custom'):
        assert f'data-range="{label}"' in html


def test_workouts_page_has_no_custom_range_modal(html):
    """The old start/end calendar-based Custom Range modal was replaced by a rolling days input."""
    assert 'id="wp-custom-modal"' not in html
    assert 'id="wp-cr-start-input"' not in html
    assert 'id="wp-cr-end-input"' not in html
    assert 'makeRangePicker' not in html


def test_workouts_page_has_custom_days_input(html):
    assert 'id="wp-custom-days-wrap"' in html
    assert 'id="wp-custom-days"' in html


def test_workouts_page_custom_days_default_is_30(html):
    """When no custom-days preference is saved, the workouts filter must default to 30 days."""
    assert 'parseInt(savedCustomDaysStr) || 30' in html


def test_workouts_page_range_persists_to_prefs(html):
    """Selecting a range or custom day count must persist under workouts-specific pref keys."""
    assert "savePref('pref_workouts_range'" in html
    assert "savePref('pref_workouts_custom_days'" in html
    assert "localStorage.getItem('pref_workouts_range')" in html


def test_workouts_page_filter_btn_has_aria_label(html):
    assert 'aria-label="Filter by date range"' in html
