#!/usr/bin/env python3
import unittest
import subprocess
import shutil
from pathlib import Path

TEST_DIR = Path("src.test")
PACHECODE = Path("pachecode.py")

class TestPacheCode(unittest.TestCase):

    def setUp(self):
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)
        TEST_DIR.mkdir(parents=True)

    def tearDown(self):
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)

    def run_pachecode(self, dsl):
        proc = subprocess.run(
            ["python3", str(PACHECODE), str(TEST_DIR)],
            input=dsl,
            text=True,
            capture_output=True
        )
        if proc.returncode != 0:
            print("\n--- TOOL STDOUT ---")
            print(proc.stdout)
            print(proc.stderr)
        self.assertEqual(proc.returncode, 0)
        return proc

    # ------------------------
    # Basic create / append / modify / delete
    # ------------------------

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
        # Create file
        create_dsl = """F file.txt
N
Line1
EN
EF
"""
        self.run_pachecode(create_dsl)
        # Append
        append_dsl = """F file.txt
A
Line2
EA
EF
"""
        self.run_pachecode(append_dsl)
        content = (TEST_DIR / "file.txt").read_text()
        self.assertIn("Line1", content)
        self.assertIn("Line2", content)

    def test_modify_file(self):
        create_dsl = """F file.txt
N
Original Line
EN
EF
"""
        self.run_pachecode(create_dsl)
        modify_dsl = """F file.txt
M
Modified Line
EF
"""
        self.run_pachecode(modify_dsl)
        content = (TEST_DIR / "file.txt").read_text()
        self.assertIn("Modified Line", content)
        self.assertNotIn("Original Line", content)

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
A content
EN
EF
F b.txt
N
B content
EN
EF
"""
        self.run_pachecode(dsl)
        self.assertTrue((TEST_DIR / "a.txt").exists())
        self.assertTrue((TEST_DIR / "b.txt").exists())

    # ------------------------
    # Insert / search-replace / line-replace
    # ------------------------

    def test_insert_file(self):
        create_dsl = """F file.txt
N
Line1
Line3
EN
EF
"""
        self.run_pachecode(create_dsl)
        insert_dsl = """F file.txt
I 2
Line2
EI
EF
"""
        self.run_pachecode(insert_dsl)
        content = (TEST_DIR / "file.txt").read_text()
        lines = content.splitlines()
        self.assertEqual(lines, ["Line1", "Line2", "Line3"])

    def test_search_replace_line_replace(self):
        # Create file
        create_dsl = """F replace.txt
N
one
two
three
EN
EF
"""
        self.run_pachecode(create_dsl)

        # Search/Replace
        sr_dsl = """F replace.txt
SR
two
EOLD
TWO
ENEW
ESR
EF
"""
        self.run_pachecode(sr_dsl)

        # Line Replace (strict terminators)
        lr_dsl = """F replace.txt
LR 1 2
EOLD
one
TWO
EOLD
NEW
uno
DUE
ENEW
ELR
EF
"""
        self.run_pachecode(lr_dsl)

        content = (TEST_DIR / "replace.txt").read_text()
        self.assertIn("TWO", content)
        self.assertIn("uno", content)
        self.assertIn("DUE", content)

    # ------------------------
    # Malformed block test
    # ------------------------

    def test_malformed_block(self):
        # Missing EN terminator
        dsl = """F bad.txt
N
Oops missing terminator
EF
"""
        proc = subprocess.run(
            ["python3", str(PACHECODE), str(TEST_DIR)],
            input=dsl,
            text=True,
            capture_output=True
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Block unterminated", proc.stdout + proc.stderr)
        print("\n--- TOOL STDOUT ---")
        print(proc.stdout)
        print(proc.stderr)


if __name__ == "__main__":
    unittest.main()
