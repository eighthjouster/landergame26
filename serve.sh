#!/bin/bash
# Simple static file server using Python, serving files from the src directory on port 8099

PORT=8099
DIRECTORY="src"

# Check if src directory exists
if [ ! -d "$DIRECTORY" ]; then
    echo "Directory '$DIRECTORY' does not exist."
    exit 1
fi

# Start Python HTTP server
python3 -m http.server "$PORT" --directory "$DIRECTORY"

