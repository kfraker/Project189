"""POST /api/weight — save and overwrite weight entries."""
import pytest
from tests.conftest import seed_weight


# ── Happy path ───────────────────────────────────────────────────────────────

def test_insert_new_entry_returns_success(client):
    r = seed_weight(client, "2026-01-01", 200.0)
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_inserted_entry_appears_in_history(client):
    seed_weight(client, "2026-01-01", 200.0)
    r = client.get("/api/weights?range=all")
    rows = r.get_json()
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-01"
    assert rows[0]["weight_lbs"] == 200.0


# ── kg conversion ────────────────────────────────────────────────────────────

def test_kg_is_calculated_from_lbs(client):
    seed_weight(client, "2026-01-01", 200.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_kg"] == round(200.0 / 2.2046, 1)


def test_kg_conversion_precision_one_decimal(client):
    seed_weight(client, "2026-01-01", 155.7)
    rows = client.get("/api/weights?range=all").get_json()
    kg = rows[0]["weight_kg"]
    assert kg == round(155.7 / 2.2046, 1)
    assert len(str(kg).split(".")[-1]) <= 1 or kg == int(kg)


@pytest.mark.parametrize("lbs,expected_kg", [
    (100.0, round(100.0 / 2.2046, 1)),
    (220.46, round(220.46 / 2.2046, 1)),
    (0.1,   round(0.1 / 2.2046, 1)),
    (999.9, round(999.9 / 2.2046, 1)),
])
def test_kg_conversion_table(client, lbs, expected_kg):
    seed_weight(client, "2026-01-01", lbs)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_kg"] == expected_kg


# ── Duplicate / conflict handling ────────────────────────────────────────────

def test_duplicate_without_overwrite_returns_conflict(client):
    seed_weight(client, "2026-01-01", 200.0)
    r = seed_weight(client, "2026-01-01", 210.0)
    body = r.get_json()
    assert body.get("conflict") is True
    assert body.get("date") == "2026-01-01"


def test_duplicate_without_overwrite_does_not_update_value(client):
    seed_weight(client, "2026-01-01", 200.0)
    seed_weight(client, "2026-01-01", 210.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 200.0


def test_overwrite_true_updates_existing_entry(client):
    seed_weight(client, "2026-01-01", 200.0)
    r = seed_weight(client, "2026-01-01", 210.0, overwrite=True)
    assert r.get_json()["success"] is True
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 210.0


def test_overwrite_true_does_not_create_duplicate_row(client):
    seed_weight(client, "2026-01-01", 200.0)
    seed_weight(client, "2026-01-01", 210.0, overwrite=True)
    rows = client.get("/api/weights?range=all").get_json()
    assert len(rows) == 1


def test_overwrite_recalculates_kg(client):
    seed_weight(client, "2026-01-01", 200.0)
    seed_weight(client, "2026-01-01", 180.0, overwrite=True)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_kg"] == round(180.0 / 2.2046, 1)


def test_overwrite_defaults_to_false(client):
    seed_weight(client, "2026-01-01", 200.0)
    r = client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": 210.0},
        content_type="application/json",
    )
    assert r.get_json().get("conflict") is True


# ── Multiple entries ─────────────────────────────────────────────────────────

def test_multiple_entries_on_different_dates(client):
    seed_weight(client, "2026-01-01", 200.0)
    seed_weight(client, "2026-01-02", 199.5)
    seed_weight(client, "2026-01-03", 199.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert len(rows) == 3


def test_entries_are_ordered_by_date_ascending(client):
    seed_weight(client, "2026-01-03", 199.0)
    seed_weight(client, "2026-01-01", 200.0)
    seed_weight(client, "2026-01-02", 199.5)
    rows = client.get("/api/weights?range=all").get_json()
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)


# ── Decimal and boundary weights ─────────────────────────────────────────────

def test_decimal_weight_stored_correctly(client):
    seed_weight(client, "2026-01-01", 155.3)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 155.3


def test_very_large_weight(client):
    seed_weight(client, "2026-01-01", 999.9)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 999.9


def test_very_small_positive_weight(client):
    seed_weight(client, "2026-01-01", 0.1)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows[0]["weight_lbs"] == 0.1


# ── Input validation — invalid weights ───────────────────────────────────────

def test_negative_weight_returns_400(client):
    r = seed_weight(client, "2026-01-01", -10.0)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_zero_weight_returns_400(client):
    r = seed_weight(client, "2026-01-01", 0.0)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_negative_weight_not_stored(client):
    seed_weight(client, "2026-01-01", -10.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert rows == []


def test_string_weight_returns_400(client):
    r = client.post(
        "/api/weight",
        json={"date": "2026-01-01", "weight_lbs": "heavy"},
        content_type="application/json",
    )
    assert r.status_code == 400


# ── Input validation — invalid dates ─────────────────────────────────────────

def test_invalid_date_format_returns_400(client):
    r = client.post(
        "/api/weight",
        json={"date": "not-a-date", "weight_lbs": 200.0},
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_impossible_date_returns_400(client):
    r = client.post(
        "/api/weight",
        json={"date": "2026-02-30", "weight_lbs": 200.0},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_date_wrong_format_slash_returns_400(client):
    r = client.post(
        "/api/weight",
        json={"date": "01/01/2026", "weight_lbs": 200.0},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_invalid_date_not_stored(client):
    client.post(
        "/api/weight",
        json={"date": "bad-date", "weight_lbs": 200.0},
        content_type="application/json",
    )
    rows = client.get("/api/weights?range=all").get_json()
    assert rows == []


# ── Missing fields ────────────────────────────────────────────────────────────

def test_missing_weight_lbs_returns_400(client):
    r = client.post(
        "/api/weight",
        json={"date": "2026-01-01"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_missing_date_returns_400(client):
    r = client.post(
        "/api/weight",
        json={"weight_lbs": 200.0},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_empty_body_returns_400(client):
    r = client.post(
        "/api/weight",
        data="",
        content_type="application/json",
    )
    assert r.status_code == 400
