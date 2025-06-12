#!/bin/bash

# Exit on error, unset var, or pipefail
set -euo pipefail

# Debug information
echo "Debug: Current directory: $(pwd)"
echo "Debug: REQUIREMENTS_PATH: $REQUIREMENTS_PATH"
echo "Debug: REQUIREMENTS_COMMAND: $REQUIREMENTS_COMMAND"

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found"
    exit 1
fi

# Check uv.lock if it exists
if [ -f "uv.lock" ]; then
    echo "Checking if uv.lock matches pyproject.toml..."
    echo "Running uv sync to check for any differences..."
    if ! uv sync; then
        echo "❌ uv.lock is out of sync with pyproject.toml"
        exit 1
    fi
    echo "✅ uv.lock is in sync with pyproject.toml"
fi

# Check if requirements.txt exists and matches pyproject.toml
if [ -n "${REQUIREMENTS_PATH:-}" ]; then
    # Get the basename of the requirements path
    REQUIREMENTS_FILE=$(basename "$REQUIREMENTS_PATH")
    echo "Debug: Looking for requirements file: $REQUIREMENTS_FILE"
    
    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo "Checking if requirements.txt matches pyproject.toml..."
        # Generate a temporary requirements file
        TEMP_REQUIREMENTS=$(mktemp)
        eval "$REQUIREMENTS_COMMAND" > "$TEMP_REQUIREMENTS"
        
        # Compare the files
        if ! diff -q "$REQUIREMENTS_FILE" "$TEMP_REQUIREMENTS" > /dev/null; then
            echo "❌ requirements.txt is out of sync with pyproject.toml"
            echo "Run the following command to update requirements.txt:"
            echo "$REQUIREMENTS_COMMAND"
            rm "$TEMP_REQUIREMENTS"
            exit 1
        fi
        rm "$TEMP_REQUIREMENTS"
        echo "✅ requirements.txt is in sync with pyproject.toml"
    else
        echo "⚠️  requirements.txt not found at $REQUIREMENTS_FILE. Skipping requirements check."
        echo "If you want to check requirements.txt, generate it with:"
        echo "$REQUIREMENTS_COMMAND"
        # Do not exit with error, just skip
    fi
else
    echo "No requirements.txt specified, skipping requirements check."
fi
