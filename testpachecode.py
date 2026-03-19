#!/usr/bin/env python3
import unittest
import subprocess
import shutil
from pathlib import Path

TEST_DIR = Path("src.test")
PACHECODE = Path("pachecode.py")
VALIDATOR = Path("validate_pachecode.py")


# -------------------------------
# DSL Validator Tests
# -------------------------------
class TestDSLValidator(unittest.TestCase):
    """Tests the standalone DSL validator"""

    def validate_dsl(self, dsl, expect_fail=False):
        proc = subprocess.run(
            ["python3", str(VALIDATOR)],
            input=dsl,
            text=True,
            capture_output=True
        )
        if expect_fail:
            self.assertNotEqual(proc.returncode, 0)
            print("\n--- DSL VALIDATOR OUTPUT ---")
            print(proc.stdout)
            print(proc.stderr)
        else:
            if proc.returncode != 0:
                print("\n--- DSL VALIDATOR OUTPUT ---")
                print(proc.stdout)
                print(proc.stderr)
            self.assertEqual(proc.returncode, 0)
        return proc

    def test_valid_dsl(self):
        dsl = """GLOSSARY
C = COMMENT
F = FILE
EF = END_FILE
N = NEW
M = MODIFY
D = DELETE
R = RENAME
SR = SEARCH_REPLACE
LR = LINE_REPLACE
A = APPEND
I = INSERT
END_GLOSSARY
F index.html
N
Hello
EN
EF
"""
        self.validate_dsl(dsl)

    def test_missing_terminator(self):
        dsl = """F bad.txt
N
Oops missing terminator
"""
        self.validate_dsl(dsl, expect_fail=True)

    def test_unknown_op(self):
        dsl = """F file.txt
X
EF
"""
        self.validate_dsl(dsl, expect_fail=True)


# -------------------------------
# PacheCode Tool / Parser Tests
# -------------------------------
class TestPacheCodeTool(unittest.TestCase):
    """Tests PacheCode tool execution"""

    def setUp(self):
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)
        TEST_DIR.mkdir(parents=True)

    def tearDown(self):
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)

    def run_pachecode(self, dsl, expect_fail=False):
        proc = subprocess.run(
            ["python3", str(PACHECODE), str(TEST_DIR)],
            input=dsl,
            text=True,
            capture_output=True
        )
        if expect_fail:
            self.assertNotEqual(proc.returncode, 0)
            print("\n--- TOOL STDOUT ---")
            print(proc.stdout)
            print(proc.stderr)
        else:
            if proc.returncode != 0:
                print("\n--- TOOL STDOUT ---")
                print(proc.stdout)
                print(proc.stderr)
            self.assertEqual(proc.returncode, 0)
        return proc

    # -------------------------------
    # Old parser tests
    # -------------------------------

    def test_create_file(self):
        dsl = """F file.txt
N
Hello World
EN
EF
"""
        self.run_pachecode(dsl)
        content = (TEST_DIR / "file.txt").read_text()
        self.assertIn("Hello World", content)

    def test_append_file(self):
        create_dsl = """F file.txt
N
Line1
EN
EF
"""
        self.run_pachecode(create_dsl)
        append_dsl = """F file.txt
A
Line2
EA
EF
"""
        self.run_pachecode(append_dsl)
        content = (TEST_DIR / "file.txt").read_text()
        self.assertIn("Line2", content)

    def test_delete_file(self):
        file_path = TEST_DIR / "del.txt"
        file_path.write_text("To be deleted\n")
        dsl = """F del.txt
D
EF
"""
        self.run_pachecode(dsl)
        self.assertFalse(file_path.exists())

    def test_multiple_files(self):
        dsl = """F a.txt
N
File A
EN
EF
F b.txt
N
File B
EN
EF
"""
        self.run_pachecode(dsl)
        self.assertTrue((TEST_DIR / "a.txt").exists())
        self.assertTrue((TEST_DIR / "b.txt").exists())

    def test_malformed_block(self):
        dsl = """F bad.txt
N
Oops missing terminator
EF
"""
        proc = self.run_pachecode(dsl, expect_fail=True)
        print("\n--- TOOL STDOUT ---")
        print(proc.stdout)
        print(proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
