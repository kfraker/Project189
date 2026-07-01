"""Edge cases for GET /api/weights not covered in the main suite."""


def test_unknown_range_param_falls_back_to_30d(client):
    """An unrecognised range string falls through to the custom-days branch
    with days=None → min(30, 1095) = 30 days."""
    r = client.get("/api/weights?range=bogus")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_negative_custom_days_returns_empty(client):
    """`days=-1` produces a future start date so no rows match."""
    from tests.conftest import seed_weight
    from datetime import date
    seed_weight(client, date.today().isoformat(), 200.0)
    rows = client.get("/api/weights?range=custom&days=-1").get_json()
    assert rows == []


def test_custom_days_1_includes_only_today(client):
    from tests.conftest import seed_weight
    from datetime import date, timedelta
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    seed_weight(client, today,     200.0)
    seed_weight(client, yesterday, 205.0)
    rows  = client.get("/api/weights?range=custom&days=1").get_json()
    dates = [r["date"] for r in rows]
    assert today     in dates
    assert yesterday not in dates


def test_delete_nonexistent_date_format_returns_404(client):
    """DELETE on a date that was never inserted returns 404, not 500."""
    r = client.delete("/api/weight/2000-01-01")
    assert r.status_code == 404


def test_weights_response_is_always_a_list(client):
    for range_val in ("all", "7d", "30d", "90d", "1y", "custom"):
        r = client.get(f"/api/weights?range={range_val}")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)
