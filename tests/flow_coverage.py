"""User flow coverage: which user flows (tests/flows.toml) passing tests prove, and on
which devices.

Line coverage shows which code ran, not whether a person can do what they came for.
Browser tests name the flows they prove with @pytest.mark.flow("id", ...). This plugin
checks every name is on the list, works out each test's device from its screen width,
and writes coverage/flows.json at the end of the run. tools/coverage/check_flows.py
turns that into the report and fails CI if a covered flow loses its test.
"""

import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FLOWS_FILE = ROOT / "tests" / "flows.toml"
RESULT_FILE = ROOT / "coverage" / "flows.json"
DEVICES = ("desktop", "phone", "tablet")

FLOWS = tomllib.loads(FLOWS_FILE.read_text(encoding="utf-8"))
_proven = {}  # nodeid -> (flows, device), for tests that passed


def device_for(item):
    """desktop, phone or tablet. Tests emulating a mobile device are a phone or a tablet
    by the screen's shorter side, so a phone turned sideways is still a phone. Everything
    else runs at Playwright's default desktop size."""
    for marker in item.iter_markers("browser_context_args"):
        if marker.kwargs.get("is_mobile"):
            viewport = marker.kwargs["viewport"]
            return "phone" if min(viewport["width"], viewport["height"]) < 600 else "tablet"
    return "desktop"


def _flows_named_by(item):
    return [name for marker in item.iter_markers("flow") for name in marker.args]


def pytest_configure(config):
    config.addinivalue_line("markers", "flow(*ids): the user flows (tests/flows.toml) this test proves")


def pytest_collection_modifyitems(items):
    unknown = sorted(
        {f"{item.nodeid}: {name}" for item in items for name in _flows_named_by(item) if name not in FLOWS}
    )
    if unknown:
        raise pytest.UsageError("Tests name flows that aren't in tests/flows.toml:\n  " + "\n  ".join(unknown))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    flows = _flows_named_by(item)
    if flows and report.when == "call" and report.passed:
        _proven[item.nodeid] = (flows, device_for(item))


def pytest_sessionfinish(session):
    """Write what this run proved. Partial runs write it too; only CI's full run is checked."""
    if not _proven:
        return
    coverage = {flow: {device: [] for device in DEVICES} for flow in FLOWS}
    for nodeid, (flows, device) in sorted(_proven.items()):
        for flow in flows:
            coverage[flow][device].append(nodeid)
    RESULT_FILE.parent.mkdir(exist_ok=True)
    result = {"flows": {flow: {"name": FLOWS[flow]["name"], "tests": coverage[flow]} for flow in FLOWS}}
    RESULT_FILE.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def pytest_terminal_summary(terminalreporter):
    if not _proven:
        return
    pairs = {(flow, device) for flows, device in _proven.values() for flow in flows}
    total = len(FLOWS) * len(DEVICES)
    terminalreporter.write_line(
        f"User flow coverage: {len(pairs)} of {total} flow-device pairs proven "
        f"({100 * len(pairs) / total:.0f}%). Details: python tools/coverage/check_flows.py"
    )
