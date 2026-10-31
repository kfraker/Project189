"""The badge that says which database this copy of the app is using."""
import pytest

from app import app as flask_app

BADGE = 'id="env-badge"'


@pytest.mark.parametrize("path", ["/", "/weights", "/workouts"])
def test_sandbox_shows_the_sandbox_badge_on_every_page(client, monkeypatch, path):
    monkeypatch.setenv("APP_ENV", "sandbox")
    html = client.get(path).get_data(as_text=True)
    assert BADGE in html and "SANDBOX" in html and "PRODUCTION DATA" not in html


def test_debug_mode_without_the_setting_warns_about_real_data(client, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(flask_app, "debug", True)
    html = client.get("/").get_data(as_text=True)
    assert BADGE in html and "PRODUCTION DATA" in html and "SANDBOX" not in html


def test_the_live_site_shows_no_badge(client, monkeypatch):
    """Not debug mode and no APP_ENV, whatever Vercel does or doesn't set."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(flask_app, "debug", False)
    assert BADGE not in client.get("/").get_data(as_text=True)


def test_the_login_page_shows_the_badge_too(test_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "sandbox")
    html = flask_app.test_client().get("/login").get_data(as_text=True)
    assert BADGE in html and "SANDBOX" in html


def test_the_live_login_page_shows_no_badge(test_db, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(flask_app, "debug", False)
    assert BADGE not in flask_app.test_client().get("/login").get_data(as_text=True)
