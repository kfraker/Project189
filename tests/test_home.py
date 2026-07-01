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


# ── Cursor sets ───────────────────────────────────────────────────────────────

def test_all_cursor_images_referenced(html):
    for name in ('pointer.png', 'pointer2.png', 'pointer3.png',
                 'editpointer.png', 'editpointer2.png', 'editpointer3.png'):
        assert name in html, f'{name} not referenced in page'


def test_cursor_sets_cover_all_profiles(html):
    """CURSOR_SETS in the script must define entries for profiles 1, 2, and 3."""
    assert "pointer2.png" in html
    assert "pointer3.png" in html
    assert "editpointer2.png" in html
    assert "editpointer3.png" in html


def test_change_pic_btn_inside_settings_modal(html):
    """change-pic-btn must appear before the settings modal's closing tag."""
    settings_start = html.find('id="settings-modal"')
    change_pic_pos = html.find('id="change-pic-btn"')
    picker_pos     = html.find('id="profile-pic-picker"')
    assert settings_start < change_pic_pos
    assert change_pic_pos < picker_pos
