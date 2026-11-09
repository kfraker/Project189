"""The daily uptime check (tools/uptime/check_site.py) passes against a healthy app and
fails, loudly but without leaking anything, when the site is down, broken or missing a page."""

import importlib.util
import socket
import threading
from pathlib import Path

import psycopg
import pytest
from flask import redirect
from werkzeug.serving import make_server

import app as app_module

_spec = importlib.util.spec_from_file_location(
    "check_site", Path(__file__).resolve().parents[1] / "tools" / "uptime" / "check_site.py"
)
check_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_site)


@pytest.fixture()
def google_configured(monkeypatch):
    """Starting Google sign-in normally fetches Google's settings over the network; tests don't."""
    monkeypatch.setattr(
        app_module.oauth.google,
        "authorize_redirect",
        lambda *a, **k: redirect("https://accounts.google.com/o/oauth2/v2/auth?client_id=test"),
    )


@pytest.fixture()
def live_app(test_db, google_configured):
    """The real app, served over real HTTP on a free local port, like the live site."""
    server = make_server("127.0.0.1", 0, app_module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture()
def lines():
    return []


def test_healthy_app_passes_every_check(live_app, lines):
    assert check_site.run(live_app, out=lines.append)
    assert not [line for line in lines if line.startswith("FAIL")]
    assert lines[-1].strip() == f"{len(check_site.CHECKS)} of {len(check_site.CHECKS)} checks passed for {live_app}"


def test_database_down_fails_the_health_check(live_app, lines, monkeypatch):
    def refuse(*args, **kwargs):
        raise psycopg.OperationalError("connection to postgres@ep-secret.neon.tech failed: password rejected")

    monkeypatch.setattr(app_module.psycopg, "connect", refuse)
    assert not check_site.run(live_app, out=lines.append)
    failed = [line for line in lines if line.startswith("FAIL")]
    assert len(failed) == 1 and "/health" in failed[0] and "got 503" in failed[0]
    assert not any(hint in "\n".join(lines).lower() for hint in ("postgres", "neon", "password"))


def test_missing_page_fails(live_app, lines):
    checks = [check_site.Check("/no-such-page", "a page that was removed", 200)]
    assert not check_site.run(live_app, checks=checks, out=lines.append)
    assert "expected 200, got 404" in lines[0]


def _unused_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_broken_address_fails_every_check(lines):
    assert not check_site.run(f"http://127.0.0.1:{_unused_port()}", out=lines.append)
    failed = [line for line in lines if line.startswith("FAIL")]
    assert len(failed) == len(check_site.CHECKS)
    assert all("couldn't reach it" in line for line in failed)


def test_command_line_exit_codes(live_app, capsys):
    assert check_site.main(["check_site.py", live_app]) == 0
    assert check_site.main(["check_site.py", f"http://127.0.0.1:{_unused_port()}"]) == 1
    assert check_site.main(["check_site.py"]) == 2
    assert check_site.main(["check_site.py", "sweatequity.kfraker.dev"]) == 2


def _fake(status, body="", headers=None):
    return lambda url: check_site.Response(status, headers or {}, body)


def test_server_error_fails_without_quoting_the_page(lines):
    page = "Traceback (most recent call last): secret-token-123"
    assert not check_site.run("https://example.test", fetcher=_fake(500, page), out=lines.append)
    output = "\n".join(lines)
    assert "got 500" in output
    assert "Traceback" not in output and "secret-token-123" not in output


def test_page_that_loads_but_looks_wrong_fails(lines):
    login = [c for c in check_site.CHECKS if c.path == "/login"]
    assert not check_site.run(
        "https://example.test", fetcher=_fake(200, "<h1>Maintenance</h1>"), checks=login, out=lines.append
    )
    assert 'missing "Sign in with Google"' in lines[0]


@pytest.mark.parametrize(
    ("location", "passes"),
    [
        ("/login?next=/workouts", True),
        ("https://sweatequity.kfraker.dev/login?next=/workouts", True),
        ("https://evil.example/phish", False),
        ("", False),
    ],
)
def test_sign_in_redirect_must_go_to_login(location, passes, lines):
    workouts = [c for c in check_site.CHECKS if c.path == "/workouts"]
    fetcher = _fake(302, headers={"Location": location})
    assert check_site.run("https://example.test", fetcher=fetcher, checks=workouts, out=lines.append) is passes


def test_google_sign_in_must_go_to_google(lines):
    google = [c for c in check_site.CHECKS if c.path == "/auth/google"]
    fetcher = _fake(302, headers={"Location": "https://accounts.google.com.evil.example/"})
    assert not check_site.run("https://example.test", fetcher=fetcher, checks=google, out=lines.append)
