"""Workout API — GET /api/workouts, POST /api/workout, DELETE /api/workout/<id>."""
import pytest


def seed_workout(client, workout_type="Running (6 mph)", duration_min=30, kcal=300,
                 date="2026-01-01", note=""):
    return client.post(
        "/api/workout",
        json={"date": date, "type": workout_type, "duration_min": duration_min,
              "kcal": kcal, "note": note},
        content_type="application/json",
    )


# ── GET /api/workouts ─────────────────────────────────────────────────────────

def test_get_workouts_empty(client):
    r = client.get("/api/workouts")
    assert r.status_code == 200
    assert r.get_json() == []


def test_get_workouts_returns_saved_entry(client):
    seed_workout(client)
    rows = client.get("/api/workouts").get_json()
    assert len(rows) == 1
    assert rows[0]["type"] == "Running (6 mph)"
    assert rows[0]["duration_min"] == 30
    assert rows[0]["kcal"] == 300


# ── POST /api/workout — happy path ───────────────────────────────────────────

def test_save_workout_returns_success(client):
    r = seed_workout(client)
    data = r.get_json()
    assert r.status_code == 200
    assert data["success"] is True
    assert "id" in data


def test_save_workout_accepts_compendium_name(client):
    """Any non-empty type string must be accepted."""
    r = seed_workout(client, workout_type="Martial Arts")
    assert r.get_json()["success"] is True


def test_save_workout_accepts_quick_pick_name(client):
    """Quick-pick names like 'Strength' must also be accepted."""
    r = seed_workout(client, workout_type="Strength")
    assert r.get_json()["success"] is True


def test_save_workout_note_stored(client):
    seed_workout(client, note="Push day")
    rows = client.get("/api/workouts").get_json()
    assert rows[0]["note"] == "Push day"


def test_save_workout_type_truncated_at_100(client):
    long_type = "A" * 150
    r = seed_workout(client, workout_type=long_type)
    assert r.get_json()["success"] is True
    rows = client.get("/api/workouts").get_json()
    assert len(rows[0]["type"]) == 100


# ── POST /api/workout — validation errors ────────────────────────────────────

def test_save_workout_rejects_empty_type(client):
    r = seed_workout(client, workout_type="")
    assert r.status_code == 400


def test_save_workout_rejects_whitespace_type(client):
    r = seed_workout(client, workout_type="   ")
    assert r.status_code == 400


def test_save_workout_rejects_invalid_date(client):
    r = seed_workout(client, date="not-a-date")
    assert r.status_code == 400


def test_save_workout_rejects_zero_duration(client):
    r = seed_workout(client, duration_min=0)
    assert r.status_code == 400


def test_save_workout_rejects_duration_over_600(client):
    r = seed_workout(client, duration_min=601)
    assert r.status_code == 400


def test_save_workout_rejects_negative_kcal(client):
    r = seed_workout(client, kcal=-1)
    assert r.status_code == 400


def test_save_workout_accepts_zero_kcal(client):
    r = seed_workout(client, kcal=0)
    assert r.get_json()["success"] is True


def test_save_workout_accepts_max_duration(client):
    r = seed_workout(client, duration_min=600)
    assert r.get_json()["success"] is True


# ── DELETE /api/workout/<id> ──────────────────────────────────────────────────

def test_delete_workout_removes_entry(client):
    wid = seed_workout(client).get_json()["id"]
    client.delete(f"/api/workout/{wid}")
    rows = client.get("/api/workouts").get_json()
    assert all(r["id"] != wid for r in rows)


def test_delete_workout_returns_success(client):
    wid = seed_workout(client).get_json()["id"]
    r = client.delete(f"/api/workout/{wid}")
    assert r.get_json()["success"] is True


def test_delete_nonexistent_workout_still_200(client):
    r = client.delete("/api/workout/99999")
    assert r.status_code == 200


# ── GET /api/workout-day-note ─────────────────────────────────────────────────

def test_get_day_note_missing_returns_empty_string(client):
    r = client.get("/api/workout-day-note?date=2026-01-01")
    assert r.status_code == 200
    assert r.get_json()["note"] == ""


def test_save_and_retrieve_day_note(client):
    client.post("/api/workout-day-note",
                json={"date": "2026-01-01", "note": "Push day"},
                content_type="application/json")
    r = client.get("/api/workout-day-note?date=2026-01-01")
    assert r.get_json()["note"] == "Push day"


def test_day_note_upserts_on_same_date(client):
    client.post("/api/workout-day-note",
                json={"date": "2026-01-01", "note": "First"},
                content_type="application/json")
    client.post("/api/workout-day-note",
                json={"date": "2026-01-01", "note": "Second"},
                content_type="application/json")
    assert client.get("/api/workout-day-note?date=2026-01-01").get_json()["note"] == "Second"


def test_save_day_note_returns_success(client):
    r = client.post("/api/workout-day-note",
                    json={"date": "2026-01-01", "note": "Test"},
                    content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_day_notes_are_date_isolated(client):
    """Note on one date does not appear under a different date."""
    client.post("/api/workout-day-note",
                json={"date": "2026-01-01", "note": "Leg day"},
                content_type="application/json")
    assert client.get("/api/workout-day-note?date=2026-01-02").get_json()["note"] == ""


# ── GET /api/workout-day-notes ────────────────────────────────────────────────

def test_get_all_day_notes_empty(client):
    r = client.get("/api/workout-day-notes")
    assert r.status_code == 200
    assert r.get_json() == {}


def test_get_all_day_notes_returns_saved(client):
    client.post("/api/workout-day-note",
                json={"date": "2026-01-01", "note": "Leg day"},
                content_type="application/json")
    client.post("/api/workout-day-note",
                json={"date": "2026-01-02", "note": "Push day"},
                content_type="application/json")
    notes = client.get("/api/workout-day-notes").get_json()
    assert notes.get("2026-01-01") == "Leg day"
    assert notes.get("2026-01-02") == "Push day"


def test_get_all_day_notes_excludes_empty_notes(client):
    """Dates where the note was set to '' must not appear in the map."""
    client.post("/api/workout-day-note",
                json={"date": "2026-01-01", "note": ""},
                content_type="application/json")
    assert "2026-01-01" not in client.get("/api/workout-day-notes").get_json()
