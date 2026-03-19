#!/usr/bin/env python3
"""
PacheCode DSL Validator
Usage: python validate_pachecode.py
Reads PacheCode DSL from stdin and validates structure/schema.
Exits 0 if valid, 1 if invalid.
"""

import sys

VALID_OPS = ("N", "M", "D", "A", "C", "R", "I", "LR", "SR")
TERMINATORS = {
    "N": "EN",
    "A": "EA",
    "I": "EI",
    "LR": "ELR",
    "SR": "ESR"
}


class BlockParseError(Exception):
    pass


class PacheCodeValidator:
    def __init__(self, dsl_text):
        self.lines = dsl_text.splitlines()
        self.pos = 0

    def parse(self):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            if line == "GLOSSARY":
                self.pos += 1
                self.parse_glossary()
            elif line.startswith("F "):
                self.parse_file()
            elif line == "Q":
                self.parse_query()
            elif not line:
                self.pos += 1
            else:
                raise BlockParseError(f"Unexpected line at {self.pos+1}: {line}")

    def parse_glossary(self):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1
            if line == "END_GLOSSARY":
                return
            if "=" not in line:
                raise BlockParseError(f"Invalid glossary line at {self.pos}: {line}")

    def parse_file(self):
        line = self.lines[self.pos].strip()
        if not line.startswith("F "):
            raise BlockParseError(f"Expected F <path> at line {self.pos+1}")
        self.pos += 1
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            if line == "EF":
                self.pos += 1
                return
            self.parse_op()
        raise BlockParseError("File block not terminated with EF")

    def parse_op(self):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1
            if line:
                break
        else:
            raise BlockParseError("Unexpected EOF while parsing operation")

        # One-word commands
        if line in ("N", "M", "D", "A", "C"):
            if line in TERMINATORS:
                self.collect_block(TERMINATORS[line])
            return
        # Commands with arguments
        elif line.startswith("R "):
            return
        elif line.startswith("I "):
            self.collect_block("EI")
            return
        elif line.startswith("LR "):
            self.collect_block("EOLD")
            self.collect_block("ENEW")
            self.expect("ELR")
            return
        elif line == "SR":
            self.collect_block("EOLD")
            self.collect_block("ENEW")
            self.expect("ESR")
            return
        else:
            raise BlockParseError(f"Unknown operation: {line}")

    def collect_block(self, end_marker):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            if line == end_marker:
                self.pos += 1
                return
            if line.startswith(("F ", "Q")):
                raise BlockParseError(f"Block unterminated before line {self.pos+1}, expected {end_marker}")
            self.pos += 1
        raise BlockParseError(f"Block unterminated: expected {end_marker} before EOF")

    def expect(self, marker):
        if self.pos >= len(self.lines) or self.lines[self.pos].strip() != marker:
            raise BlockParseError(f"Expected {marker} at line {self.pos+1}")
        self.pos += 1

    def parse_query(self):
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1
            if line == "EQ":
                return


def main():
    dsl_text = sys.stdin.read()
    try:
        validator = PacheCodeValidator(dsl_text)
        validator.parse()
        sys.exit(0)
    except BlockParseError as e:
        print(f"PacheCode parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
