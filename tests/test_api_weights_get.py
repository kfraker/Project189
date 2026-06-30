"""GET /api/weights — date-range filtering."""
import pytest
from datetime import date, timedelta
from tests.conftest import seed_weight


TODAY = date.today().isoformat()


def _date_offset(days: int) -> str:
    """Return ISO date string `days` days before today (negative = future)."""
    return (date.today() - timedelta(days=days)).isoformat()


# ── Empty database ────────────────────────────────────────────────────────────

def test_empty_db_returns_empty_list(client):
    r = client.get("/api/weights?range=all")
    assert r.status_code == 200
    assert r.get_json() == []


def test_empty_db_range_returns_empty_list(client):
    r = client.get("/api/weights?range=7d")
    assert r.get_json() == []


# ── range=all ────────────────────────────────────────────────────────────────

def test_range_all_returns_all_entries(client):
    seed_weight(client, _date_offset(100), 200.0)
    seed_weight(client, _date_offset(50),  195.0)
    seed_weight(client, TODAY, 190.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert len(rows) == 3


def test_default_range_is_all(client):
    seed_weight(client, _date_offset(100), 200.0)
    r_explicit = client.get("/api/weights?range=all").get_json()
    r_default  = client.get("/api/weights").get_json()
    assert r_explicit == r_default


# ── Fixed named ranges ────────────────────────────────────────────────────────

@pytest.mark.parametrize("range_name,days", [
    ("7d",  7),
    ("30d", 30),
    ("90d", 90),
    ("1y",  365),
])
def test_named_range_includes_boundary_entry(client, range_name, days):
    boundary = _date_offset(days - 1)
    seed_weight(client, boundary, 200.0)
    rows = client.get(f"/api/weights?range={range_name}").get_json()
    assert any(r["date"] == boundary for r in rows)


@pytest.mark.parametrize("range_name,days", [
    ("7d",  7),
    ("30d", 30),
    ("90d", 90),
    ("1y",  365),
])
def test_named_range_excludes_entry_one_day_outside(client, range_name, days):
    outside = _date_offset(days)
    seed_weight(client, outside, 200.0)
    rows = client.get(f"/api/weights?range={range_name}").get_json()
    assert not any(r["date"] == outside for r in rows)


@pytest.mark.parametrize("range_name,days", [
    ("7d",  7),
    ("30d", 30),
    ("90d", 90),
    ("1y",  365),
])
def test_named_range_includes_today(client, range_name, days):
    seed_weight(client, TODAY, 200.0)
    rows = client.get(f"/api/weights?range={range_name}").get_json()
    assert any(r["date"] == TODAY for r in rows)


# ── Custom range ──────────────────────────────────────────────────────────────

def test_custom_range_returns_correct_window(client):
    in_window  = _date_offset(6)
    out_window = _date_offset(7)
    seed_weight(client, in_window,  200.0)
    seed_weight(client, out_window, 201.0)
    rows = client.get("/api/weights?range=custom&days=7").get_json()
    dates = [r["date"] for r in rows]
    assert in_window in dates
    assert out_window not in dates


def test_custom_range_days_capped_at_1095(client):
    """Days > 1095 should be silently clamped to 1095."""
    r = client.get("/api/weights?range=custom&days=9999")
    assert r.status_code == 200


def test_custom_range_no_days_defaults_to_30(client):
    seed_weight(client, _date_offset(29), 200.0)
    seed_weight(client, _date_offset(31), 201.0)
    rows = client.get("/api/weights?range=custom").get_json()
    dates = [r["date"] for r in rows]
    assert _date_offset(29) in dates
    assert _date_offset(31) not in dates


def test_custom_range_days_1_returns_only_today(client):
    seed_weight(client, TODAY, 200.0)
    seed_weight(client, _date_offset(1), 201.0)
    rows = client.get("/api/weights?range=custom&days=1").get_json()
    dates = [r["date"] for r in rows]
    assert TODAY in dates
    assert _date_offset(1) not in dates


def test_custom_range_days_1095_is_valid(client):
    seed_weight(client, TODAY, 200.0)
    rows = client.get("/api/weights?range=custom&days=1095").get_json()
    assert any(r["date"] == TODAY for r in rows)


# ── Ordering ──────────────────────────────────────────────────────────────────

def test_results_always_ordered_by_date_ascending(client):
    seed_weight(client, _date_offset(5), 203.0)
    seed_weight(client, _date_offset(1), 200.0)
    seed_weight(client, _date_offset(3), 201.5)
    rows = client.get("/api/weights?range=all").get_json()
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)


# ── Response shape ────────────────────────────────────────────────────────────

def test_each_row_has_required_fields(client):
    seed_weight(client, TODAY, 200.0)
    rows = client.get("/api/weights?range=all").get_json()
    assert "date"       in rows[0]
    assert "weight_lbs" in rows[0]
    assert "weight_kg"  in rows[0]
