"""DELETE /api/weight/<date>/weight — clear a day's weight but keep its note."""
from datetime import date, timedelta
from tests.conftest import seed_weight


TODAY = date.today().isoformat()


def _date_offset(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def _seed_with_note(client, entry_date, weight_lbs, notes):
    return client.post(
        "/api/weight",
        json={"date": entry_date, "weight_lbs": weight_lbs, "notes": notes},
        content_type="application/json",
    )


def _row(client, entry_date):
    rows = client.get("/api/weights?range=all").get_json()
    return next((r for r in rows if r["date"] == entry_date), None)


# ── Day with a note: weight cleared, note kept ───────────────────────────────

def test_clear_weight_keeps_note(client):
    _seed_with_note(client, TODAY, 200.0, "felt great")
    r = client.delete(f"/api/weight/{TODAY}/weight")
    assert r.status_code == 200
    assert r.get_json()["success"] is True
    row = _row(client, TODAY)
    assert row is not None
    assert row["notes"] == "felt great"
    assert row["weight_lbs"] is None


# ── Day without a note: whole entry removed ──────────────────────────────────

def test_clear_weight_without_note_deletes_entry(client):
    seed_weight(client, TODAY, 200.0)
    client.delete(f"/api/weight/{TODAY}/weight")
    assert _row(client, TODAY) is None


# ── Returned "latest" weight ─────────────────────────────────────────────────

def test_clear_weight_returns_previous_latest(client):
    seed_weight(client, _date_offset(1), 195.0)
    _seed_with_note(client, TODAY, 200.0, "felt great")
    body = client.delete(f"/api/weight/{TODAY}/weight").get_json()
    assert body["latest"]["weight_lbs"] == 195.0


def test_clear_weight_returns_empty_latest_when_no_weights_left(client):
    _seed_with_note(client, TODAY, 200.0, "felt great")
    body = client.delete(f"/api/weight/{TODAY}/weight").get_json()
    assert body["latest"] == {}


# ── Errors ───────────────────────────────────────────────────────────────────

def test_clear_weight_nonexistent_date_returns_404(client):
    r = client.delete("/api/weight/2000-01-01/weight")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_clear_weight_invalid_date_returns_400(client):
    r = client.delete("/api/weight/not-a-date/weight")
    assert r.status_code == 400
