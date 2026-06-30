"""GET /api/latest-weight — most recent entry + oldest date."""
from datetime import date, timedelta
from tests.conftest import seed_weight


TODAY = date.today().isoformat()


def _date_offset(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ── Empty database ────────────────────────────────────────────────────────────

def test_empty_db_returns_empty_object(client):
    r = client.get("/api/latest-weight")
    assert r.status_code == 200
    assert r.get_json() == {}


# ── Single entry ──────────────────────────────────────────────────────────────

def test_single_entry_returns_that_entry(client):
    seed_weight(client, "2026-01-15", 200.0)
    body = client.get("/api/latest-weight").get_json()
    assert body["weight_lbs"] == 200.0
    assert body["weight_kg"]  == round(200.0 / 2.2046, 1)


def test_single_entry_oldest_date_equals_that_entry(client):
    seed_weight(client, "2026-01-15", 200.0)
    body = client.get("/api/latest-weight").get_json()
    assert body["oldest_date"] == "2026-01-15"


# ── Multiple entries ──────────────────────────────────────────────────────────

def test_returns_most_recent_by_date(client):
    seed_weight(client, "2026-01-01", 205.0)
    seed_weight(client, "2026-03-01", 195.0)
    seed_weight(client, "2026-02-01", 200.0)
    body = client.get("/api/latest-weight").get_json()
    assert body["weight_lbs"] == 195.0


def test_oldest_date_is_earliest_entry(client):
    seed_weight(client, "2026-03-01", 195.0)
    seed_weight(client, "2026-01-01", 205.0)
    seed_weight(client, "2026-02-01", 200.0)
    body = client.get("/api/latest-weight").get_json()
    assert body["oldest_date"] == "2026-01-01"


def test_kg_on_latest_matches_conversion(client):
    seed_weight(client, TODAY, 175.0)
    body = client.get("/api/latest-weight").get_json()
    assert body["weight_kg"] == round(175.0 / 2.2046, 1)


def test_response_contains_all_three_fields(client):
    seed_weight(client, TODAY, 200.0)
    body = client.get("/api/latest-weight").get_json()
    assert "weight_lbs"  in body
    assert "weight_kg"   in body
    assert "oldest_date" in body


def test_latest_reflects_overwrite(client):
    seed_weight(client, TODAY, 200.0)
    seed_weight(client, TODAY, 185.0, overwrite=True)
    body = client.get("/api/latest-weight").get_json()
    assert body["weight_lbs"] == 185.0
