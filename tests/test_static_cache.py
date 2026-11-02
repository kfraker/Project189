"""Static files can be reused by browsers and the CDN, without ever showing stale code."""

import re
from pathlib import Path

from app import app as flask_app

ROOT = Path(__file__).resolve().parents[1]


def test_versioned_files_are_kept_for_a_year(client, monkeypatch):
    monkeypatch.setattr(flask_app, "debug", False)
    res = client.get("/static/style.css?v=abc123")
    assert res.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_unversioned_images_are_kept_for_a_day(client, monkeypatch):
    monkeypatch.setattr(flask_app, "debug", False)
    res = client.get("/static/weightplate.webp")
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "public, max-age=86400"


def test_pages_are_not_given_the_static_cache_rule(client, monkeypatch):
    monkeypatch.setattr(flask_app, "debug", False)
    assert "max-age=86400" not in client.get("/").headers.get("Cache-Control", "")
    assert "immutable" not in client.get("/api/weights").headers.get("Cache-Control", "")


def test_missing_files_are_not_cached(client, monkeypatch):
    monkeypatch.setattr(flask_app, "debug", False)
    assert "max-age" not in client.get("/static/nope.png").headers.get("Cache-Control", "")


def test_local_debug_mode_is_not_cached(client, monkeypatch):
    monkeypatch.setattr(flask_app, "debug", True)
    assert "immutable" not in client.get("/static/style.css?v=abc123").headers.get("Cache-Control", "")


def test_every_image_the_templates_and_styles_name_exists():
    sources = [*ROOT.glob("templates/*.html"), ROOT / "static" / "style.css"]
    names = {m for path in sources for m in re.findall(r"/static/([\w.-]+\.(?:png|webp))", path.read_text("utf-8"))}
    assert names, "expected to find image references"
    missing = sorted(name for name in names if not (ROOT / "static" / name).exists())
    assert not missing


def test_served_images_stay_small():
    limits = {
        "profilebutton.png": 150,
        "weightplate.webp": 200,
        "homebackground.webp": 200,
        "weighinsbackground.webp": 300,
        "workoutbackground9.webp": 300,
    }
    for name, kilobytes in limits.items():
        assert (ROOT / "static" / name).stat().st_size <= kilobytes * 1024, name
