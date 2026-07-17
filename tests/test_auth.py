"""Google OAuth login flow: gating of existing routes, the login/logout
routes themselves, and the /auth/google/callback exchange."""
import app as app_module
from tests.conftest import connect


def _fake_token(email, sub="sub-test-1", name="Test User", picture="http://pic"):
    return {"userinfo": {"sub": sub, "email": email, "name": name, "picture": picture}}


# ── Route gating ──────────────────────────────────────────────────────────────

def test_home_shows_login_card_when_unauthenticated(unauthenticated_client):
    r = unauthenticated_client.get("/")
    assert r.status_code == 200
    assert b"Sign in with Google" in r.data


def test_weights_page_redirects_to_login_when_unauthenticated(unauthenticated_client):
    r = unauthenticated_client.get("/weights", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_workouts_page_redirects_to_login_when_unauthenticated(unauthenticated_client):
    r = unauthenticated_client.get("/workouts", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_api_route_returns_401_json_when_unauthenticated(unauthenticated_client):
    r = unauthenticated_client.get("/api/weights")
    assert r.status_code == 401
    assert r.get_json() == {"error": "authentication required"}


# ── /login and /logout ────────────────────────────────────────────────────────

def test_login_page_renders_when_unauthenticated(unauthenticated_client):
    r = unauthenticated_client.get("/login")
    assert r.status_code == 200
    assert b"Sign in with Google" in r.data


def test_login_page_redirects_home_when_already_authenticated(client):
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "/"


def test_logout_then_home_shows_login_again(client):
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "/login"

    r2 = client.get("/")
    assert b"Sign in with Google" in r2.data


# ── /auth/google/callback ─────────────────────────────────────────────────────

def test_callback_allowed_email_creates_user_and_sets_session(unauthenticated_client, test_db, monkeypatch):
    monkeypatch.setattr(
        app_module.oauth.google, "authorize_access_token",
        lambda: _fake_token("you@example.com", sub="sub-new-1"),
    )
    r = unauthenticated_client.get("/auth/google/callback", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "/"

    conn = connect()
    row = conn.execute("SELECT id, email FROM users WHERE google_sub = %s", ("sub-new-1",)).fetchone()
    conn.close()
    assert row is not None
    assert row["email"] == "you@example.com"

    with unauthenticated_client.session_transaction() as sess:
        assert sess["user_id"] == row["id"]


def test_callback_repeat_login_reuses_same_user(unauthenticated_client, test_db, monkeypatch):
    monkeypatch.setattr(
        app_module.oauth.google, "authorize_access_token",
        lambda: _fake_token("you@example.com", sub="sub-repeat-1"),
    )
    unauthenticated_client.get("/auth/google/callback")
    with unauthenticated_client.session_transaction() as sess:
        first_user_id = sess["user_id"]

    unauthenticated_client.get("/auth/google/callback")
    with unauthenticated_client.session_transaction() as sess:
        second_user_id = sess["user_id"]

    assert first_user_id == second_user_id

    conn = connect()
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE google_sub = %s", ("sub-repeat-1",)
    ).fetchone()["c"]
    conn.close()
    assert count == 1


def test_callback_denies_non_allowlisted_email(unauthenticated_client, test_db, monkeypatch):
    monkeypatch.setattr(
        app_module.oauth.google, "authorize_access_token",
        lambda: _fake_token("stranger@example.com", sub="sub-stranger"),
    )
    r = unauthenticated_client.get("/auth/google/callback")
    assert r.status_code == 403
    assert b"Access Denied" in r.data

    conn = connect()
    row = conn.execute("SELECT id FROM users WHERE google_sub = %s", ("sub-stranger",)).fetchone()
    conn.close()
    assert row is None

    with unauthenticated_client.session_transaction() as sess:
        assert "user_id" not in sess


def test_fresh_user_home_renders_without_error(unauthenticated_client, monkeypatch):
    """A brand-new account has no preferences/weights yet — home() must not
    assume any prior data exists (keeps the onboarding-wizard backlog item
    unblocked)."""
    monkeypatch.setattr(
        app_module.oauth.google, "authorize_access_token",
        lambda: _fake_token("you@example.com", sub="sub-fresh-1"),
    )
    unauthenticated_client.get("/auth/google/callback")

    r = unauthenticated_client.get("/")
    assert r.status_code == 200
    assert b"Sign in with Google" not in r.data
