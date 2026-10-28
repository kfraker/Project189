"""
Browser-test fixtures (Playwright): a live app server and a signed-in page.

The live server runs the real Flask app in a background thread of the pytest
process, so app code exercised by browser tests counts toward Python coverage.
Like the API tests, every browser test runs against the isolated "test" schema
(via the shared `test_db` fixture). get_db() falls back to the real "public"
schema when DB_SCHEMA is unset, so the server refuses every request unless the
test schema is active — a browser test can never read or write real data.
"""
import threading

import pytest
from werkzeug.serving import make_server

from app import app as flask_app
from tests.conftest import TEST_SCHEMA, connect


def pytest_collection_modifyitems(items):
    """Mark everything under tests/browser/ so quick runs can skip it: -m "not browser"."""
    for item in items:
        if "tests/browser/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.browser)


def _test_schema_only(wsgi_app):
    def guarded(environ, start_response):
        if flask_app.config.get("DB_SCHEMA") != TEST_SCHEMA:
            start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
            return [b"Live test server: refusing request, test schema not active"]
        return wsgi_app(environ, start_response)
    return guarded


@pytest.fixture(scope="session")
def app_server():
    """Base URL of the app running in a background thread (random free port)."""
    server = make_server("127.0.0.1", 0, _test_schema_only(flask_app), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, app_server):
    """Every page's relative URLs ("/", "/weights") resolve against the live server."""
    return {**browser_context_args, "base_url": app_server}


@pytest.fixture(autouse=True)
def _fail_on_page_errors(request, page, app_server):
    """Fail any browser test whose page hits a JS error, a failed request, or an
    error response from the app. Opt out with @pytest.mark.allow_page_errors."""
    problems = []
    page.on("pageerror", lambda exc: problems.append(f"JS error: {exc}"))
    page.on("console", lambda msg: msg.type == "error" and problems.append(f"console.error: {msg.text}"))
    page.on("requestfailed", lambda req: "ERR_ABORTED" not in (req.failure or "")
            and problems.append(f"request failed: {req.method} {req.url} ({req.failure})"))
    page.on("response", lambda res: res.url.startswith(app_server) and res.status >= 400
            and problems.append(f"HTTP {res.status}: {res.request.method} {res.url}"))
    yield
    if problems and not request.node.get_closest_marker("allow_page_errors"):
        pytest.fail("Page problems during test:\n  " + "\n  ".join(problems), pytrace=False)


@pytest.fixture()
def signed_out_page(test_db, page):
    """A browser page with no session (test schema active, nobody signed in)."""
    return page


@pytest.fixture()
def signed_in_page(test_db, page, app_server):
    """A browser page signed in as test user 1.

    Signs a Flask session cookie directly instead of going through Google, so
    the app needs no test-only login route. `test_db` comes before `page` so the
    browser closes before the test schema is released.
    """
    conn = connect()
    conn.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (1, 'default', '') "
        "ON CONFLICT (id) DO NOTHING"
    )
    conn.commit()
    conn.close()

    cookie = flask_app.session_interface.get_signing_serializer(flask_app).dumps({"user_id": 1})
    page.context.add_cookies([{
        "name": flask_app.config["SESSION_COOKIE_NAME"],
        "value": cookie,
        "url": app_server,
    }])
    return page
