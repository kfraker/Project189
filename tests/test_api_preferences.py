"""Tests for GET /api/preferences and POST /api/preference."""
import pytest


# ── GET /api/preferences ──────────────────────────────────────────────────────

def test_get_preferences_returns_200(client):
    r = client.get("/api/preferences")
    assert r.status_code == 200


def test_get_preferences_returns_dict(client):
    r = client.get("/api/preferences")
    assert isinstance(r.get_json(), dict)


def test_get_preferences_empty_by_default(client):
    r = client.get("/api/preferences")
    assert r.get_json() == {}


# ── POST /api/preference ──────────────────────────────────────────────────────

def test_save_preference_returns_success(client):
    r = client.post("/api/preference", json={"key": "pref_unit", "value": "kg"})
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_save_preference_missing_key(client):
    r = client.post("/api/preference", json={"value": "kg"})
    assert r.status_code == 400


def test_save_preference_missing_value(client):
    r = client.post("/api/preference", json={"key": "pref_unit"})
    assert r.status_code == 400


def test_save_preference_empty_key(client):
    r = client.post("/api/preference", json={"key": "   ", "value": "kg"})
    assert r.status_code == 400


def test_save_preference_no_body(client):
    r = client.post("/api/preference", content_type="application/json", data="")
    assert r.status_code == 400


# ── Round-trip ────────────────────────────────────────────────────────────────

def test_saved_preference_appears_in_get(client):
    client.post("/api/preference", json={"key": "pref_unit", "value": "kg"})
    prefs = client.get("/api/preferences").get_json()
    assert prefs.get("pref_unit") == "kg"


def test_preference_upsert_updates_existing(client):
    client.post("/api/preference", json={"key": "pref_range", "value": "30d"})
    client.post("/api/preference", json={"key": "pref_range", "value": "7d"})
    prefs = client.get("/api/preferences").get_json()
    assert prefs["pref_range"] == "7d"


def test_multiple_preferences_stored_independently(client):
    client.post("/api/preference", json={"key": "pref_unit",  "value": "kg"})
    client.post("/api/preference", json={"key": "pref_range", "value": "1y"})
    prefs = client.get("/api/preferences").get_json()
    assert prefs["pref_unit"]  == "kg"
    assert prefs["pref_range"] == "1y"


def test_preference_value_coerced_to_string(client):
    client.post("/api/preference", json={"key": "pref_custom_days", "value": 30})
    prefs = client.get("/api/preferences").get_json()
    assert prefs["pref_custom_days"] == "30"


def test_profile_pic_pref_saved_and_retrieved(client):
    for val in ("1", "2", "3"):
        client.post("/api/preference", json={"key": "pref_profile_pic", "value": val})
        prefs = client.get("/api/preferences").get_json()
        assert prefs["pref_profile_pic"] == val


def test_all_known_prefs_survive_round_trip(client):
    known = {
        "pref_unit":        "lbs",
        "pref_range":       "30d",
        "pref_custom_days": "14",
        "pref_view":        "chart",
        "pref_height_unit": "us",
        "pref_profile_pic": "2",
        "fight_name":       "Test Fighter",
        "fight_sex":        "male",
        "fight_dob":        "1990-06-15",
        "fight_height_ft":  "5",
        "fight_height_in":  "11",
        "fight_height_cm":  "180",
    }
    for k, v in known.items():
        client.post("/api/preference", json={"key": k, "value": v})
    prefs = client.get("/api/preferences").get_json()
    for k, v in known.items():
        assert prefs[k] == v


# ── Home route passes prefs to template ──────────────────────────────────────

def test_home_renders_without_prefs(client):
    """Home route must render even when preferences table is empty."""
    r = client.get("/")
    assert r.status_code == 200


def test_home_hydrates_saved_preferences(client):
    """Saved prefs must appear as JSON inside the rendered HTML."""
    client.post("/api/preference", json={"key": "pref_unit", "value": "kg"})
    html = client.get("/").data.decode()
    assert '"pref_unit"' in html
    assert '"kg"' in html
