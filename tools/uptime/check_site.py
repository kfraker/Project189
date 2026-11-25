"""Daily uptime and error check for the live site (run by .github/workflows/uptime.yml).

Visits the pages anyone can reach without signing in and fails if any is down, answers
with a server error, or doesn't look right. A failing run makes GitHub email the owner.

Usage:
    python tools/uptime/check_site.py https://sweatequity.kfraker.dev

Standard library only, so the workflow needs no installs. It fails on the first bad
run rather than retrying: one visit a day is cheap, and a false alarm is easy to rerun.
"""

import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlsplit

TIMEOUT_SECONDS = 30  # generous, so a database waking up from sleep isn't an outage
USER_AGENT = "SweatEquity-uptime-check"
SIGN_IN_TEXT = "Sign in with Google"


@dataclass
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    body: str = ""


@dataclass
class Check:
    path: str
    what: str
    status: int
    body_contains: str | None = None
    body_equals: str | None = None
    redirects_to: str | None = None  # start of the Location header


CHECKS = [
    Check("/health", "app and database", 200, body_equals="ok"),
    Check("/", "home page (signed out)", 200, body_contains=SIGN_IN_TEXT),
    Check("/login", "login page", 200, body_contains=SIGN_IN_TEXT),
    Check("/static/style.css", "stylesheet", 200),
    Check("/workouts", "workouts page sends visitors to sign in", 302, redirects_to="/login"),
    Check("/weights", "weigh-ins page sends visitors to sign in", 302, redirects_to="/login"),
    Check("/api/weights", "API refuses signed-out requests", 401),
    Check("/auth/google", "Google sign-in starts", 302, redirects_to="https://accounts.google.com/"),
]


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirects)


def fetch(url):
    """Visit a URL without following redirects. Raises OSError if it can't be reached."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _opener.open(request, timeout=TIMEOUT_SECONDS) as res:
            return Response(res.status, dict(res.headers), res.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as err:  # 3xx (not followed), 4xx and 5xx all land here
        return Response(err.code, dict(err.headers), err.read().decode("utf-8", "replace"))


def problem_with(check, res):
    """What's wrong with a response, or None if it's as expected. Never quotes the body or
    headers, so nothing from the site ends up in the public Actions log."""
    if res.status != check.status:
        return f"expected {check.status}, got {res.status}"
    if check.body_equals is not None and res.body.strip() != check.body_equals:
        return "unexpected response text"
    if check.body_contains is not None and check.body_contains not in res.body:
        return f'page is missing "{check.body_contains}"'
    if check.redirects_to is not None:
        location = res.headers.get("Location") or res.headers.get("location") or ""
        if check.redirects_to.startswith("http"):
            arrived = location.startswith(check.redirects_to)
        else:  # Flask may send a relative or absolute Location, with ?next=...
            arrived = urlsplit(location).path == check.redirects_to
        if not arrived:
            return f"redirected somewhere other than {check.redirects_to}"
    return None


def run(base_url, fetcher=fetch, checks=CHECKS, out=print):
    """Run every check and report each one. Returns True if all passed."""
    base_url = base_url.rstrip("/")
    failures = 0
    for check in checks:
        try:
            problem = problem_with(check, fetcher(base_url + check.path))
        except OSError as err:  # can't connect, DNS failure, timeout
            problem = f"couldn't reach it ({type(err).__name__})"
        if problem:
            failures += 1
            out(f"FAIL  {check.path:<20} {check.what}: {problem}")
        else:
            out(f"ok    {check.path:<20} {check.what}")
    out(f"\n{len(checks) - failures} of {len(checks)} checks passed for {base_url}")
    return failures == 0


def main(argv):
    if len(argv) != 2 or not argv[1].startswith(("http://", "https://")):
        print("Usage: python tools/uptime/check_site.py https://your-site", file=sys.stderr)
        return 2
    return 0 if run(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
