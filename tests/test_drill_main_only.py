"""TEMPORARY drill: passes on the pull request, fails once it's on main, to prove
a failure after merging doesn't reach the live site. Removed right after the drill."""
import os


def test_fails_only_on_main():
    assert os.environ.get("GITHUB_REF") != "refs/heads/main", "Deliberate failure for the deploy gate drill"
