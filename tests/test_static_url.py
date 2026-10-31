"""static_url(): app scripts and styles are linked with a content-hash version,
so browsers never run a stale cached copy after a deploy."""
import hashlib
import os
import re

import pytest

from app import app as flask_app


def _hash(rel):
    with open(os.path.join(flask_app.static_folder, rel), "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:10]


@pytest.mark.parametrize("path,page_script", [
    ("/", "js/pages/home.js"),
    ("/weights", "js/pages/weights.js"),
    ("/workouts", "js/pages/workouts.js"),
])
def test_pages_link_versioned_scripts(client, path, page_script):
    html = client.get(path).data.decode()
    for rel in ("js/shell.js", page_script):
        assert f'src="/static/{rel}?v={_hash(rel)}"' in html


def test_stylesheet_is_versioned_by_content(client):
    html = client.get("/").data.decode()
    assert f'href="/static/style.css?v={_hash("style.css")}"' in html


def test_no_hand_maintained_version_numbers_left(client):
    html = client.get("/").data.decode()
    assert not re.search(r"\.(css|js)\?v=\d{1,4}\"", html)
