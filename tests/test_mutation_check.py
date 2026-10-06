import pytest

from mutation_check import classify_mutant_result


@pytest.mark.parametrize(
    ("returncode", "output", "expected"),
    [
        (1, "FAILED tests/test_policy.py::test_boundary - assert False", "killed"),
        (
            1,
            "FAILED tests/test_policy.py::test_guard - Failed: DID NOT RAISE "
            "ValueError",
            "killed",
        ),
        (
            1,
            "FAILED tests/test_policy.py::test_guard - ValueError: unexpected",
            "killed",
        ),
        (2, "ERROR collecting tests/test_policy.py", "harness error"),
        (1, "ImportError while importing test module", "harness error"),
        (0, "1 passed", "survived"),
        (5, "no tests ran", "harness error"),
        (None, "", "harness error"),
    ],
)
def test_classify_mutant_result(returncode, output, expected):
    assert classify_mutant_result(returncode, output) == expected
