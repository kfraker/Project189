"""
Browser-test fixtures (Playwright): a live app server and a signed-in page.

The live server runs the real Flask app in a background thread of the pytest
process, so app code exercised by browser tests counts toward Python coverage.
Like the API tests, every browser test runs against the isolated "test" schema
(via the shared `test_db` fixture). get_db() falls back to the real "public"
schema when DB_SCHEMA is unset, so the server refuses every request unless the
test schema is active — a browser test can never read or write real data.

Page-code coverage: each test switches on Chromium's built-in (V8) coverage,
saves the counts for the app's own scripts (static/js/**) to coverage/js-raw/,
and at the end of the run tools/coverage/report-js.mjs turns them into
coverage/js-html/ + coverage/js.lcov.
"""
import hashlib
import json
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from app import app as flask_app
from tests.conftest import TEST_SCHEMA, connect

ROOT = Path(__file__).resolve().parents[2]
JS_RAW = ROOT / "coverage" / "js-raw"
JS_REPORT = ROOT / "tools" / "coverage" / "report-js.mjs"
STATIC_DIR = Path(flask_app.static_folder)


def pytest_collection_modifyitems(items):
    """Mark everything under tests/browser/ so quick runs can skip it: -m "not browser"."""
    for item in items:
        if "tests/browser/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.browser)


def pytest_sessionfinish(session):
    """Build the page-code coverage report if this run collected any."""
    if not JS_RAW.is_dir() or not any(JS_RAW.glob("*.json")):
        return
    node = shutil.which("node")
    if not node or not (JS_REPORT.parent / "node_modules").is_dir():
        print("\nPage-code coverage collected but not reported: install the tooling with "
              "`npm install --prefix tools/coverage` (needs Node.js).")
        return
    print()
    subprocess.run([node, str(JS_REPORT)], cwd=ROOT, check=False)


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


@pytest.fixture(scope="session", autouse=True)
def _fresh_js_coverage_dir():
    """Each run's page-code coverage starts from zero."""
    JS_RAW.mkdir(parents=True, exist_ok=True)
    for old in JS_RAW.glob("*.json"):
        old.unlink()


@pytest.fixture(autouse=True)
def _collect_js_coverage(request, page, app_server, browser_name):
    """Record V8 coverage for the app's own scripts while this test's page is open."""
    if browser_name != "chromium":
        yield
        return
    cdp = page.context.new_cdp_session(page)
    cdp.send("Profiler.enable")
    cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": True})
    yield
    try:
        scripts = cdp.send("Profiler.takePreciseCoverage")["result"]
    except Exception:
        return
    prefix = f"{app_server}/static/"
    ours = []
    for script in scripts:
        url = script["url"].split("?")[0]
        if url.startswith(prefix) and url.endswith(".js"):
            script["url"] = (STATIC_DIR / url[len(prefix):]).as_uri()   # map to the file on disk
            ours.append(script)
    if ours:
        name = hashlib.md5(request.node.nodeid.encode()).hexdigest()
        (JS_RAW / f"{name}.json").write_text(json.dumps({"result": ours}), encoding="utf-8")


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Keep same-site navigations in one renderer process. By default Chromium may
    move each new page into a fresh process, which discards the coverage counts of
    the pages a test visited before it (only the last page would be measured)."""
    return {**browser_type_launch_args, "args": [
        *browser_type_launch_args.get("args", []),
        "--disable-features=RenderDocument,BackForwardCache,ProactivelySwapBrowsingInstance",
    ]}


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
