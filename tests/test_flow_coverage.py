"""The user flow coverage tooling: device detection, the flow-name check, and the
guard that fails when a covered flow loses its test."""

import importlib.util
import json
from pathlib import Path

import pytest

from tests import flow_coverage

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_flows", ROOT / "tools" / "coverage" / "check_flows.py")
check_flows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_flows)


class _Item:
    """Just enough of a pytest item for the plugin."""

    def __init__(self, flows=(), **context_args):
        self.nodeid = "tests/browser/test_x.py::test_x"
        self._markers = []
        if flows:
            self._markers.append(pytest.mark.flow(*flows).mark)
        if context_args:
            self._markers.append(pytest.mark.browser_context_args(**context_args).mark)

    def iter_markers(self, name):
        return (m for m in self._markers if m.name == name)


@pytest.mark.parametrize(
    "context_args, device",
    [
        pytest.param({}, "desktop", id="default"),
        pytest.param({"timezone_id": "Asia/Tokyo"}, "desktop", id="desktop-with-other-settings"),
        pytest.param({"viewport": {"width": 360, "height": 640}, "is_mobile": True}, "phone", id="phone"),
        pytest.param({"viewport": {"width": 640, "height": 360}, "is_mobile": True}, "phone", id="sideways-phone"),
        pytest.param({"viewport": {"width": 820, "height": 1180}, "is_mobile": True}, "tablet", id="tablet"),
    ],
)
def test_device_comes_from_the_emulated_screen(context_args, device):
    assert flow_coverage.device_for(_Item(**context_args)) == device


def test_every_flow_has_a_name():
    assert flow_coverage.FLOWS
    assert all(info.get("name") for info in flow_coverage.FLOWS.values())


def test_a_test_naming_an_unlisted_flow_stops_the_run():
    with pytest.raises(pytest.UsageError, match="not-a-real-flow"):
        flow_coverage.pytest_collection_modifyitems([_Item(flows=["log-weigh-in", "not-a-real-flow"])])


def test_listed_flows_pass_the_check():
    flow_coverage.pytest_collection_modifyitems([_Item(flows=["log-weigh-in"])])


def _run_check(tmp_path, monkeypatch, tests_by_device, baseline, argv=()):
    flows = {
        "log-weigh-in": {
            "name": "Log a weigh-in",
            "tests": {d: tests_by_device.get(d, []) for d in check_flows.DEVICES},
        }
    }
    result, base = tmp_path / "flows.json", tmp_path / "baseline.json"
    result.write_text(json.dumps({"flows": flows}))
    base.write_text(json.dumps({"covered": baseline}))
    monkeypatch.setattr(check_flows, "RESULT", result)
    monkeypatch.setattr(check_flows, "BASELINE", base)
    monkeypatch.setattr(check_flows, "DOC", tmp_path / "user-flows.md")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr("sys.argv", ["check_flows.py", *argv])
    check_flows.main()
    return base, tmp_path / "user-flows.md"


def test_guard_fails_when_a_covered_flow_loses_its_test(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit, match="log-weigh-in/phone"):
        _run_check(tmp_path, monkeypatch, {"desktop": ["t1"]}, ["log-weigh-in/desktop", "log-weigh-in/phone"])


def test_guard_passes_and_names_the_gaps(tmp_path, monkeypatch, capsys):
    _run_check(tmp_path, monkeypatch, {"desktop": ["t1"]}, ["log-weigh-in/desktop"])
    out = capsys.readouterr().out
    assert "1 of 3 flow-device pairs proven" in out
    assert "- Log a weigh-in: phone, tablet" in out
    assert "guard passed" in out


def test_update_accepts_new_coverage_and_writes_the_flow_list(tmp_path, monkeypatch):
    base, doc = _run_check(tmp_path, monkeypatch, {"desktop": ["t1"], "phone": ["t2"]}, [], ["--update"])
    assert json.loads(base.read_text())["covered"] == ["log-weigh-in/desktop", "log-weigh-in/phone"]
    assert "`t2`" in doc.read_text(encoding="utf-8")
