#!/usr/bin/env python3
"""
Basic test runner for pachecode.py

Creates and uses a temporary 'src.test/' directory.
"""

import subprocess
from pathlib import Path
import shutil
import sys

SCRIPT = Path(__file__).parent / "pachecode.py"
TEST_DIR = Path(__file__).parent / "src.test"


def run_pachecode(dsl):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "src.test"],
        input=dsl,
        text=True,
        capture_output=True
    )
    return proc


def assert_exists(path):
    if not path.exists():
        raise AssertionError(f"Expected {path} to exist")


def assert_not_exists(path):
    if path.exists():
        raise AssertionError(f"Expected {path} to NOT exist")


def assert_content(path, expected):
    actual = path.read_text()
    if actual != expected:
        raise AssertionError(
            f"Content mismatch in {path}\nExpected:\n{expected}\nGot:\n{actual}"
        )


def setup():
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir()


def teardown():
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


def test_create():
    dsl = """\
F test.txt
N
hello
world
EN
EF
"""
    res = run_pachecode(dsl)
    assert res.returncode == 0, res.stderr

    f = TEST_DIR / "test.txt"
    assert_exists(f)
    assert_content(f, "hello\nworld\n")


def test_modify():
    f = TEST_DIR / "test.txt"
    f.write_text("old\n")

    dsl = """\
F test.txt
M
new
content
EF
"""
    res = run_pachecode(dsl)
    assert res.returncode == 0, res.stderr

    assert_content(f, "new\ncontent\n")


def test_delete():
    f = TEST_DIR / "delete.txt"
    f.write_text("bye\n")

    dsl = """\
F delete.txt
D
EF
"""
    res = run_pachecode(dsl)
    assert res.returncode == 0, res.stderr

    assert_not_exists(f)


def main():
    print(f"Running tests in: {TEST_DIR}")

    try:
        setup()

        test_create()
        print("✅ create test passed")

        test_modify()
        print("✅ modify test passed")

        test_delete()
        print("✅ delete test passed")

        print("\n🎉 All tests passed")

    finally:
        teardown()


if __name__ == "__main__":
    main()
