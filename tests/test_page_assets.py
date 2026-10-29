"""Each page labels its own styles (data-page-style) and script (data-page-script),
so in-page navigation knows what to bring in and remove when it switches pages
(migration M1.2). The shell's own styles and scripts stay unlabelled: they load
once and are never swapped."""
import re

import pytest

from tests.conftest import page_source

# Page → its script, and a style rule only that page defines.
PAGES = [
    ("/", "js/pages/home.js", ".mp-bg"),
    ("/weights", "js/pages/weights.js", ".wt-bg"),
    ("/workouts", "js/pages/workouts.js", ".wp-bg"),
]


def _tags(html, tag):
    return re.findall(rf"<{tag}\b[^>]*>", html)


@pytest.mark.parametrize("path,script,own_rule", PAGES)
def test_page_has_one_labelled_style_with_its_own_rules(client, path, script, own_rule):
    html = client.get(path).data.decode()
    labelled = re.findall(r"<style data-page-style>(.*?)</style>", html, re.S)
    assert len(labelled) == 1
    assert own_rule in labelled[0]


@pytest.mark.parametrize("path,script,own_rule", PAGES)
def test_page_has_one_labelled_script_and_it_is_its_own(client, path, script, own_rule):
    html = client.get(path).data.decode()
    labelled = [t for t in _tags(html, "script") if "data-page-script" in t]
    assert len(labelled) == 1
    assert f'src="/static/{script}?v=' in labelled[0]


@pytest.mark.parametrize("path,script,own_rule", PAGES)
def test_shell_styles_and_scripts_are_not_labelled(client, path, script, own_rule):
    html = client.get(path).data.decode()
    shell_style = [t for t in _tags(html, "style") if "data-page-style" not in t]
    assert len(shell_style) == 1                          # base.html's shell styles
    shell_js = next(t for t in _tags(html, "script") if "js/shell.js" in t)
    assert "data-page-script" not in shell_js
    assert "data-page-style" not in next(t for t in _tags(html, "link") if "style.css" in t)


@pytest.mark.parametrize("path,script,own_rule", PAGES)
def test_scripts_load_shell_then_router_then_page(client, path, script, own_rule):
    """The page script calls registerPage(), so router.js must already be loaded;
    router.js is shell code, loaded once, so it carries no page label."""
    html = client.get(path).data.decode()
    srcs = [t for t in _tags(html, "script") if 'src="/static/' in t]
    names = [re.search(r'src="/static/([^"?]+)', t).group(1) for t in srcs]
    assert names == ["js/shell.js", "js/router.js", script]
    assert "data-page-script" not in srcs[1]


@pytest.mark.parametrize("path,script,own_rule", PAGES)
def test_page_source_still_reads_labelled_scripts(client, path, script, own_rule):
    """page_source() (used by the page tests) must keep finding the page script
    now that its tag carries a label, or those tests would quietly check less."""
    with open(f"static/{script}", encoding="utf-8") as f:
        first_line = f.readline().strip()
    assert first_line and first_line in page_source(client, path)


def test_router_keeps_every_name_the_shell_puts_on_window():
    """router.js clears names a page puts on window when the page is left, except
    its APP_WIDE list. Every name shell.js (loaded once, never swapped) assigns on
    window must be on that list, or leaving a page would delete part of the shell."""
    with open("static/js/router.js", encoding="utf-8") as f:
        router = f.read()
    app_wide = set(re.findall(r"'([\w$]+)'", re.search(r"APP_WIDE = new Set\(\[(.*?)\]\)", router, re.S).group(1)))
    for script in ("static/js/shell.js", "static/js/router.js"):
        with open(script, encoding="utf-8") as f:
            assigned = set(re.findall(r"window\.([\w$]+)\s*=(?!=)", f.read()))
        assert assigned <= app_wide, f"{script}: add {sorted(assigned - app_wide)} to APP_WIDE in router.js"
