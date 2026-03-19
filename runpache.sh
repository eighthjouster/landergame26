#!/usr/bin/env bash
# PacheCode Bash Wrapper
# Usage: ./pachecode <project_subdirectory> < patchfile.pachediff

# Check arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <project_subdirectory>"
    exit 1
fi

PROJECT_DIR="$1"

# Ensure python3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc) -ne 1 ]]; then
    echo "Error: Python 3.11+ required. Found $PYTHON_VERSION"
    exit 1
fi

# Run the Python PacheCode tool
python3 pachecode.py "$PROJECT_DIR"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "PacheCode failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
