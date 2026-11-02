"""TEMPORARY drill: this test always fails, to prove failing code can't merge to main."""


def test_deliberate_failure():
    assert False, "Deliberate failure for the CI gate drill"
