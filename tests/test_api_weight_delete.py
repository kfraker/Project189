"""DELETE /api/weight/<date> — remove a weight entry."""
from datetime import date, timedelta
from tests.conftest import seed_weight


TODAY = date.today().isoformat()


def _date_offset(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ── Happy path ────────────────────────────────────────────────────────────────

def test_delete_existing_entry_returns_success(client):
    seed_weight(client, TODAY, 200.0)
    r = client.delete(f"/api/weight/{TODAY}")
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_deleted_entry_no_longer_in_history(client):
    seed_weight(client, TODAY, 200.0)
    client.delete(f"/api/weight/{TODAY}")
    rows = client.get("/api/weights?range=all").get_json()
    assert not any(r["date"] == TODAY for r in rows)


def test_delete_returns_next_latest_weight(client):
    seed_weight(client, _date_offset(1), 195.0)
    seed_weight(client, TODAY, 200.0)
    r = client.delete(f"/api/weight/{TODAY}")
    body = r.get_json()
    assert body["latest"]["weight_lbs"] == 195.0


def test_delete_last_entry_returns_empty_latest(client):
    seed_weight(client, TODAY, 200.0)
    r = client.delete(f"/api/weight/{TODAY}")
    body = r.get_json()
    assert body["latest"] == {}


def test_delete_middle_entry_does_not_affect_others(client):
    seed_weight(client, _date_offset(2), 202.0)
    seed_weight(client, _date_offset(1), 201.0)
    seed_weight(client, TODAY, 200.0)
    client.delete(f"/api/weight/{_date_offset(1)}")
    rows = client.get("/api/weights?range=all").get_json()
    assert len(rows) == 2
    dates = [r["date"] for r in rows]
    assert _date_offset(2) in dates
    assert TODAY in dates


# ── Non-existent entry → 404 ──────────────────────────────────────────────────

def test_delete_nonexistent_date_returns_404(client):
    r = client.delete("/api/weight/2000-01-01")
    assert r.status_code == 404


def test_delete_nonexistent_returns_error_body(client):
    r = client.delete("/api/weight/2000-01-01")
    assert "error" in r.get_json()


# ── Ordering preserved after delete ──────────────────────────────────────────

def test_history_remains_ordered_after_delete(client):
    for i in range(5, 0, -1):
        seed_weight(client, _date_offset(i), 200.0 + i)
    client.delete(f"/api/weight/{_date_offset(3)}")
    rows = client.get("/api/weights?range=all").get_json()
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)
