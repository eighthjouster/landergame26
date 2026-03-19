#!/usr/bin/env python3
"""
PacheCode CLI tool

Usage: python pachecode.py <subdirectory>
Reads PacheCode DSL from stdin until EOF (Ctrl+D).
"""

import sys, os, subprocess
from pathlib import Path

# ----------------------
# Helpers
# ----------------------
def run_git(cmd, cwd, capture=False):
    return subprocess.run(["git"] + cmd, cwd=cwd, check=True, text=True, capture_output=capture)

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

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
        line = self.lines[self.pos].strip()
        self.pos += 1
        if not line:
            return self.parse_op()

        # One-word commands
        if line in ("N", "M", "D", "A", "C"):
            content = []
            if line in ("N", "A"):
                term = "EN" if line == "N" else "EA"
                while self.pos < len(self.lines):
                    l = self.lines[self.pos]
                    self.pos += 1
                    if l.strip() == term:
                        break
                    content.append(l)
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
            self.pos += 1
            if line.strip() == end_marker:
                break
            block.append(line)
        return block

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
        self.base_dir = Path(base_dir).resolve()  # <-- absolute path of base_dir
        self.parser = parser

    def run(self):
        # Git pre-check
        git_dir = self.base_dir / ".git"
        if git_dir.exists():
            if self.repo_dirty():
                run_git(["commit", "-am", "pre-patch"], cwd=self.base_dir)

        # Process files
        for fp in sorted(self.parser.files, key=lambda f: str(f.path)):
            self.process_file(fp)

        # Process queries
        for q in self.parser.queries:
            self.process_query(q)

        # Git commit post-patch
        if git_dir.exists():
            run_git(["commit", "-am", "patched"], cwd=self.base_dir)

    def repo_dirty(self):
        res = subprocess.run(["git","status","--porcelain"], cwd=self.base_dir,
                             capture_output=True, text=True)
        return bool(res.stdout.strip())

    def full_path(self, path):
        # Combine base_dir with relative path without jumping to /
        return (self.base_dir / path)

    # ----------------------
    # File operations
    # ----------------------
    def process_file(self, fp: FilePatch):
        for op in fp.ops:
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
                line_num = int(op[1])
                self.insert_file(fp.path, line_num, op[2])
            elif cmd == "SR":
                self.search_replace(fp.path, op[1], op[2])
            elif cmd == "LR":
                self.line_replace(fp.path, op[1], op[2], op[3], op[4])
            elif cmd == "C":
                continue
            else:
                raise RuntimeError(f"Unknown command {cmd}")

    def create_file(self, path, content):
        full = self.full_path(path)
        if full.exists():
            raise RuntimeError(f"File {path} already exists")
        ensure_dir(full)
        full.write_text("\n".join(content) + "\n")

    def delete_file(self, path):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File {path} does not exist")
        full.unlink()

    def rename_file(self, path, new_path):
        full = self.full_path(path)
        target = self.full_path(new_path)
        if not full.exists():
            raise RuntimeError(f"File {path} does not exist for rename")
        if target.exists():
            raise RuntimeError(f"Target {new_path} exists")
        ensure_dir(target)
        full.rename(target)

    def append_file(self, path, content):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File {path} missing for append")
        with full.open("a") as f:
            f.write("\n".join(content) + "\n")

    def insert_file(self, path, line_num, content):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File {path} missing for insert")
        lines = full.read_text().splitlines()
        if line_num < 1 or line_num > len(lines) + 1:
            raise RuntimeError(f"Invalid insert line number {line_num}")
        new_lines = lines[:line_num-1] + content + lines[line_num-1:]
        full.write_text("\n".join(new_lines) + "\n")

    def search_replace(self, path, old_block, new_block):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File {path} missing for search/replace")
        content = full.read_text().splitlines()
        old_len = len(old_block)
        replaced = False
        i = 0
        while i <= len(content) - old_len:
            if content[i:i+old_len] == old_block:
                content[i:i+old_len] = new_block
                replaced = True
                i += len(new_block)
            else:
                i += 1
        if not replaced:
            raise RuntimeError(f"SR: old block not found in {path}")
        full.write_text("\n".join(content) + "\n")

    def line_replace(self, path, start, end, old_block, new_block):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File {path} missing for line replace")
        content = full.read_text().splitlines()
        if start < 1 or end > len(content) or content[start-1:end] != old_block:
            raise RuntimeError(f"LR mismatch or invalid range in {path}")
        content[start-1:end] = new_block
        full.write_text("\n".join(content) + "\n")

    def modify_file(self, path, content):
        full = self.full_path(path)
        if not full.exists():
            raise RuntimeError(f"File {path} missing for modify")
        full.write_text("\n".join(content) + "\n")

    # ----------------------
    # Queries
    # ----------------------
    def process_query(self, commands):
        script = "\n".join(commands)
        print("Query executed. Output:\n")
        res = subprocess.run(script, shell=True, cwd=self.base_dir, text=True)
        print(res.stdout)

# ----------------------
# Main
# ----------------------
def main():
    if len(sys.argv) != 2:
        print("Usage: python pachecode.py <subdirectory>")
        sys.exit(1)

    base_dir = Path(sys.argv[1]).resolve()  # <-- convert relative subdir to absolute

    dsl_text = read_stdin()
    parser = PacheCodeParser(dsl_text).parse()
    executor = PacheCodeExecutor(base_dir, parser)

    try:
        executor.run()
    except Exception as e:
        print(f"ERROR: {e}")
        if (base_dir / ".git").exists():
            ans = input("Patch failed. Run git reset --hard? (y/n): ").strip().lower()
            if ans == "y":
                run_git(["reset", "--hard"], cwd=base_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()
