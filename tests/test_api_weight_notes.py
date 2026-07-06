"""Notes field on weight entries — POST /api/weight stores notes, PATCH /api/weight/<date>/note edits them."""
import pytest
from tests.conftest import seed_weight


# ── GET /api/weights includes notes field ────────────────────────────────────

def test_get_weights_includes_notes_field(client):
    seed_weight(client, "2026-01-01", 200.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert "notes" in rows[0]


def test_notes_defaults_to_empty_string(client):
    seed_weight(client, "2026-01-01", 200.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["notes"] == ""


# ── POST /api/weight stores notes on insert ──────────────────────────────────

def test_insert_with_notes_stores_note(client):
    client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": 200.0, "notes": "felt great"},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["notes"] == "felt great"


def test_insert_notes_truncated_at_500_chars(client):
    long_note = "x" * 600
    client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": 200.0, "notes": long_note},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert len(rows[0]["notes"]) <= 500


# ── POST /api/weight (overwrite) preserves existing notes ────────────────────

def test_weight_overwrite_preserves_existing_note(client):
    client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": 200.0, "notes": "original note"},
        content_type="application/json",
    )
    client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": 195.0, "overwrite": True},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 195.0
    assert rows[0]["notes"] == "original note"


# ── PATCH /api/weight/<date>/note ────────────────────────────────────────────

def test_patch_note_returns_success(client):
    seed_weight(client, "2026-01-01", 200.0)
    r = client.patch(
        "/api/weight/2026-01-01/note",
        json={"notes": "new note"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_patch_note_updates_stored_value(client):
    seed_weight(client, "2026-01-01", 200.0)
    client.patch(
        "/api/weight/2026-01-01/note",
        json={"notes": "edited note"},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["notes"] == "edited note"


def test_patch_note_can_clear_note(client):
    client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": 200.0, "notes": "has a note"},
        content_type="application/json",
    )
    client.patch(
        "/api/weight/2026-01-01/note",
        json={"notes": ""},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["notes"] == ""


def test_patch_note_creates_note_only_row_when_entry_missing(client):
    """PATCH with a non-empty note on a date with no entry creates a note-only row."""
    r = client.patch(
        "/api/weight/2026-06-15/note",
        json={"notes": "ghost note"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is True
    rows = client.get("/api/weights?range=all").get_json()
    created = next((row for row in rows if row["date"] == "2026-06-15"), None)
    assert created is not None
    assert created["notes"] == "ghost note"
    assert created["weight_lbs"] is None


def test_patch_note_invalid_date_returns_400(client):
    r = client.patch(
        "/api/weight/not-a-date/note",
        json={"notes": "bad date"},
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_patch_note_does_not_change_weight(client):
    seed_weight(client, "2026-01-01", 200.0)
    client.patch(
        "/api/weight/2026-01-01/note",
        json={"notes": "some note"},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 200.0


def test_patch_note_truncated_at_500_chars(client):
    seed_weight(client, "2026-01-01", 200.0)
    long_note = "y" * 600
    client.patch(
        "/api/weight/2026-01-01/note",
        json={"notes": long_note},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert len(rows[0]["notes"]) <= 500
