"""/health tells the daily uptime check whether the app and its database are up, without
giving anything away to the public."""

import psycopg
import pytest

import app as app_module

SECRET_HINTS = ("postgres", "neon", "password", "traceback", "error", "psycopg", "@")


def test_healthy_app_answers_ok_without_signing_in(unauthenticated_client):
    res = unauthenticated_client.get("/health")
    assert res.status_code == 200
    assert res.get_data(as_text=True) == "ok"
    assert res.mimetype == "text/plain"


def test_health_is_never_cached(unauthenticated_client):
    assert unauthenticated_client.get("/health").headers["Cache-Control"] == "no-store"


def test_head_request_works_for_uptime_tools(unauthenticated_client):
    assert unauthenticated_client.head("/health").status_code == 200


@pytest.fixture()
def database_down(monkeypatch):
    def refuse(*args, **kwargs):
        raise psycopg.OperationalError("connection to postgres@ep-secret.neon.tech failed: password rejected")

    monkeypatch.setattr(app_module.psycopg, "connect", refuse)


def test_database_down_answers_503(unauthenticated_client, database_down):
    res = unauthenticated_client.get("/health")
    assert res.status_code == 503
    assert res.get_data(as_text=True) == "unavailable"
    assert res.headers["Cache-Control"] == "no-store"


def test_failed_query_answers_503(unauthenticated_client, monkeypatch):
    class BrokenConnection:
        closed = False

        def execute(self, *args):
            raise psycopg.OperationalError("SSL connection has been closed unexpectedly")

        def close(self):
            BrokenConnection.closed = True

    monkeypatch.setattr(app_module, "get_db", BrokenConnection)
    res = unauthenticated_client.get("/health")
    assert res.status_code == 503
    assert BrokenConnection.closed, "the connection should still be closed"


def test_failure_details_stay_out_of_the_response(unauthenticated_client, database_down):
    res = unauthenticated_client.get("/health")
    text = res.get_data(as_text=True).lower()
    headers = " ".join(f"{k} {v}" for k, v in res.headers.items()).lower()
    for hint in SECRET_HINTS:
        assert hint not in text and hint not in headers, hint


def test_failure_is_logged_for_the_owner(unauthenticated_client, database_down, caplog):
    unauthenticated_client.get("/health")
    assert "Health check: database unreachable" in caplog.text


def test_health_does_not_reveal_the_signed_in_user(client):
    res = client.get("/health")
    assert res.get_data(as_text=True) == "ok"
    assert "Set-Cookie" not in res.headers
