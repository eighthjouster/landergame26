#!/usr/bin/env python3
"""
PacheCode CLI tool
Usage: python pachecode.py <subdirectory>
Reads PacheCode DSL from stdin until EOF (Ctrl+D).
"""

import sys
import os
import subprocess
from pathlib import Path

# ----------------------
# Helpers
# ----------------------
def run_git(cmd, cwd, capture=False):
    return subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture
    )

def ensure_dir(path):
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

def read_stdin():
    return sys.stdin.read()

# ----------------------
# DSL Parsing
# ----------------------
class BlockParseError(Exception):
    pass

class FilePatch:
    def __init__(self, path):
        self.path = Path(path)
        self.ops = []

    def add_op(self, op):
        self.ops.append(op)

class PacheCodeParser:
    def __init__(self, dsl_text):
        self.lines = dsl_text.splitlines()
        self.pos = 0
        self.files = []
        self.queries = []
        self.glossary = {}

    def parse(self):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            if line == "GLOSSARY":
                self.pos += 1
                self.parse_glossary()
            elif line.startswith("F "):
                self.files.append(self.parse_file())
            elif line == "Q":
                self.queries.append(self.parse_query())
            elif not line:
                self.pos += 1
            else:
                raise BlockParseError(f"Unexpected line at {self.pos+1}: {line}")
        return self

    def parse_glossary(self):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1
            if line == "END_GLOSSARY":
                break
            if "=" in line:
                k, v = map(str.strip, line.split("=", 1))
                self.glossary[k] = v

    def parse_file(self):
        line = self.lines[self.pos].strip()
        path = line[2:].strip()
        fp = FilePatch(path)
        self.pos += 1
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            if line == "EF":
                self.pos += 1
                break
            fp.add_op(self.parse_op())
        return fp

    def parse_op(self):
        # skip blank lines safely
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1
            if line:
                break
        else:
            raise BlockParseError("Unexpected EOF while parsing operation")

        # One-word commands
        if line in ("N", "M", "D", "A", "C"):
            content = []
            if line in ("N", "A"):
                term = "EN" if line == "N" else "EA"
                while self.pos < len(self.lines):
                    l = self.lines[self.pos]
                    if l.strip() == term:
                        self.pos += 1
                        return (line, content)
                    if l.strip().startswith(("F ", "Q")):
                        raise BlockParseError(f"Block unterminated before line {self.pos+1}, expected {term}")
                    content.append(l)
                    self.pos += 1
                raise BlockParseError(f"Block unterminated: expected {term} before EOF")
            elif line == "M":
                while self.pos < len(self.lines):
                    l = self.lines[self.pos].strip()
                    if l == "EF":
                        break
                    content.append(self.lines[self.pos])
                    self.pos += 1
            return (line, content)

        # Commands with arguments
        elif line.startswith("R "):
            return ("R", line[2:].strip())
        elif line.startswith("I "):
            return ("I", line[2:].strip(), self.collect_block("EI"))
        elif line.startswith("LR "):
            parts = line.split()
            start, end = int(parts[1]), int(parts[2])
            old = self.collect_block("EOLD")
            new = self.collect_block("ENEW")
            self.expect("ELR")
            return ("LR", start, end, old, new)
        elif line == "SR":
            old = self.collect_block("EOLD")
            new = self.collect_block("ENEW")
            self.expect("ESR")
            return ("SR", old, new)
        else:
            raise BlockParseError(f"Unknown operation: {line}")

    def collect_block(self, end_marker):
        block = []
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if line.strip() == end_marker:
                self.pos += 1
                return block
            if line.strip().startswith(("F ", "Q")):
                raise BlockParseError(f"Block unterminated before line {self.pos+1}, expected {end_marker}")
            block.append(line)
            self.pos += 1
        raise BlockParseError(f"Block unterminated: expected {end_marker} before EOF")

    def expect(self, marker):
        if self.pos >= len(self.lines) or self.lines[self.pos].strip() != marker:
            raise BlockParseError(f"Expected {marker} at line {self.pos+1}")
        self.pos += 1

    def parse_query(self):
        commands = []
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            self.pos += 1
            if line.strip() == "EQ":
                break
            commands.append(line)
        return commands

# ----------------------
# Executor
# ----------------------
class PacheCodeExecutor:
    def __init__(self, base_dir, parser):
        self.base_dir = Path(base_dir).resolve()
        self.parser = parser

    def run(self):
        git_dir = self.base_dir / ".git"
        if git_dir.exists() and self.repo_dirty():
            run_git(["add", "-A"], cwd=self.base_dir)
            run_git(["commit", "-m", "pre-patch"], cwd=self.base_dir)

        for fp in sorted(self.parser.files, key=lambda f: str(f.path)):
            self.process_file(fp)

        for q in self.parser.queries:
            self.process_query(q)

        if git_dir.exists():
            run_git(["add", "-A"], cwd=self.base_dir)
            run_git(["commit", "-m", "patched"], cwd=self.base_dir)

    def repo_dirty(self):
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.base_dir,
            capture_output=True,
            text=True
        )
        return bool(res.stdout.strip())

    def full_path(self, path):
        full = (self.base_dir / path).resolve()
        if not str(full).startswith(str(self.base_dir)):
            raise RuntimeError(f"Path escapes base directory: {path}")
        return full

    # ----------------------
    # File operations
    # ----------------------
    def process_file(self, fp):
        for op in fp.ops:
            if not op:
                continue
            cmd = op[0]
            if cmd == "N":
                self.create_file(fp.path, op[1])
            elif cmd == "M":
                self.modify_file(fp.path, op[1])
            elif cmd == "D":
                self.delete_file(fp.path)
            elif cmd == "R":
                self.rename_file(fp.path, op[1])
                fp.path = Path(op[1])
            elif cmd == "A":
                self.append_file(fp.path, op[1])
            elif cmd == "I":
                self.insert_file(fp.path, int(op[1]), op[2])
            elif cmd == "SR":
                self.search_replace(fp.path, op[1], op[2])
            elif cmd == "LR":
                self.line_replace(fp.path, op[1], op[2], op[3], op[4])
            elif cmd == "C":
                continue
            else:
                raise RuntimeError(f"Unknown command {cmd}")

    def create_file(self, path, lines):
        full = self.full_path(path)
        ensure_dir(full)
        full.write_text("\n".join(lines) + "\n")

    def modify_file(self, path, lines):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File does not exist: {path}")
        full.write_text("\n".join(lines) + "\n")

    def append_file(self, path, lines):
        full = self.full_path(path)
        ensure_dir(full)
        with open(full, "a") as f:
            f.write("\n".join(lines) + "\n")

    def delete_file(self, path):
        full = self.full_path(path)
        if full.exists():
            full.unlink()

    def insert_file(self, path, lineno, lines):
        full = self.full_path(path)
        ensure_dir(full)
        current = full.read_text().splitlines()
        lineno = max(0, min(lineno-1, len(current)))
        current[lineno:lineno] = lines
        full.write_text("\n".join(current) + "\n")

    def search_replace(self, path, old_lines, new_lines):
        full = self.full_path(path)
        text = full.read_text()
        text = text.replace("\n".join(old_lines), "\n".join(new_lines))
        full.write_text(text)

    def line_replace(self, path, start, end, old_lines, new_lines):
        full = self.full_path(path)
        lines = full.read_text().splitlines()
        lines[start-1:end] = new_lines
        full.write_text("\n".join(lines) + "\n")

    def rename_file(self, path, new_name):
        old_full = self.full_path(path)
        new_full = self.full_path(new_name)
        ensure_dir(new_full)
        old_full.rename(new_full)

    def process_query(self, query_lines):
        # Stub: just print for now
        print("Query:", query_lines)

# ----------------------
# Main
# ----------------------
def main():
    if len(sys.argv) != 2:
        print("Usage: python pachecode.py <subdirectory>")
        sys.exit(1)

    base_dir = Path(sys.argv[1]).resolve()
    dsl_text = read_stdin()

    try:
        parser = PacheCodeParser(dsl_text).parse()
        executor = PacheCodeExecutor(base_dir, parser)
        executor.run()
    except BlockParseError as e:
        print(f"PacheCode parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        if (base_dir / ".git").exists():
            ans = input("Patch failed. Run git reset --hard? (y/n): ").strip().lower()
            if ans == "y":
                run_git(["reset", "--hard"], cwd=base_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()
