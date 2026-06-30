"""GET /api/settings and POST /api/setting — user preference storage."""
import pytest
from tests.conftest import seed_setting


# ── GET /api/settings ─────────────────────────────────────────────────────────

def test_get_settings_empty_db_returns_empty_object(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.get_json() == {}


def test_get_settings_returns_saved_setting(client):
    seed_setting(client, "start", 220.0)
    body = client.get("/api/settings").get_json()
    assert "start" in body
    assert body["start"]["value_lbs"] == 220.0


def test_get_settings_returns_all_keys(client):
    seed_setting(client, "start",   220.0)
    seed_setting(client, "goal",    175.0)
    body = client.get("/api/settings").get_json()
    assert "start" in body
    assert "goal"  in body


def test_each_setting_has_value_lbs_and_value_kg(client):
    seed_setting(client, "start", 200.0)
    body = client.get("/api/settings").get_json()
    assert "value_lbs" in body["start"]
    assert "value_kg"  in body["start"]


# ── POST /api/setting ─────────────────────────────────────────────────────────

def test_save_new_setting_returns_success(client):
    r = seed_setting(client, "start", 220.0)
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_save_setting_calculates_kg(client):
    seed_setting(client, "start", 220.0)
    body = client.get("/api/settings").get_json()
    assert body["start"]["value_kg"] == round(220.0 / 2.2046, 1)


@pytest.mark.parametrize("lbs,expected_kg", [
    (100.0, round(100.0 / 2.2046, 1)),
    (154.3, round(154.3 / 2.2046, 1)),
    (300.0, round(300.0 / 2.2046, 1)),
])
def test_setting_kg_conversion_parametrized(client, lbs, expected_kg):
    seed_setting(client, "start", lbs)
    body = client.get("/api/settings").get_json()
    assert body["start"]["value_kg"] == expected_kg


# ── Conflict handling ─────────────────────────────────────────────────────────

def test_duplicate_key_without_overwrite_returns_conflict(client):
    seed_setting(client, "start", 220.0)
    r = seed_setting(client, "start", 215.0)
    body = r.get_json()
    assert body.get("conflict") is True
    assert body.get("key") == "start"


def test_duplicate_key_without_overwrite_does_not_change_value(client):
    seed_setting(client, "start", 220.0)
    seed_setting(client, "start", 215.0)
    body = client.get("/api/settings").get_json()
    assert body["start"]["value_lbs"] == 220.0


def test_overwrite_true_updates_existing_setting(client):
    seed_setting(client, "start", 220.0)
    r = seed_setting(client, "start", 215.0, overwrite=True)
    assert r.get_json()["success"] is True
    body = client.get("/api/settings").get_json()
    assert body["start"]["value_lbs"] == 215.0


def test_overwrite_does_not_create_duplicate_key(client):
    seed_setting(client, "start", 220.0)
    seed_setting(client, "start", 215.0, overwrite=True)
    body = client.get("/api/settings").get_json()
    assert len(body) == 1


def test_overwrite_recalculates_kg(client):
    seed_setting(client, "goal", 180.0)
    seed_setting(client, "goal", 170.0, overwrite=True)
    body = client.get("/api/settings").get_json()
    assert body["goal"]["value_kg"] == round(170.0 / 2.2046, 1)


def test_overwrite_defaults_to_false(client):
    seed_setting(client, "start", 220.0)
    r = client.post(
        "/api/setting",
        json={"key": "start", "value_lbs": 210.0},
        content_type="application/json",
    )
    assert r.get_json().get("conflict") is True


# ── Input validation ─────────────────────────────────────────────────────────

def test_negative_value_lbs_returns_400(client):
    r = seed_setting(client, "start", -50.0)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_zero_value_lbs_returns_400(client):
    r = seed_setting(client, "start", 0.0)
    assert r.status_code == 400


def test_negative_value_not_stored(client):
    seed_setting(client, "start", -50.0)
    body = client.get("/api/settings").get_json()
    assert body == {}


def test_string_value_lbs_returns_400(client):
    r = client.post(
        "/api/setting",
        json={"key": "start", "value_lbs": "heavy"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_missing_key_field_returns_400(client):
    r = client.post(
        "/api/setting",
        json={"value_lbs": 200.0},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_missing_value_lbs_field_returns_400(client):
    r = client.post(
        "/api/setting",
        json={"key": "start"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_empty_body_returns_400(client):
    r = client.post(
        "/api/setting",
        data="",
        content_type="application/json",
    )
    assert r.status_code == 400


# ── Multiple independent keys ────────────────────────────────────────────────

def test_two_settings_are_independent(client):
    seed_setting(client, "start", 220.0)
    seed_setting(client, "goal",  175.0)
    seed_setting(client, "start", 218.0, overwrite=True)
    body = client.get("/api/settings").get_json()
    assert body["start"]["value_lbs"] == 218.0
    assert body["goal"]["value_lbs"]  == 175.0
