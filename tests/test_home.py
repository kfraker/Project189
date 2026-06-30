"""GET / — home page renders correctly."""


def test_home_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_home_returns_html(client):
    response = client.get("/")
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_home_contains_app_elements(client):
    """Key landmarks exist in the served HTML."""
    html = response = client.get("/").data.decode()
    assert "chart-tooltip" in html or "chart-wrap" in html
