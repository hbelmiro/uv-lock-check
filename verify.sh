#!/usr/bin/env bash

# Exit on error, unset var, or pipefail
set -euo pipefail

echo "Checking if uv.lock matches pyproject.toml..."

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found"
    exit 1
fi

# Check if uv.lock exists
if [ ! -f "uv.lock" ]; then
    echo "Error: uv.lock not found"
    exit 1
fi

# Run uv sync to update the lock file
echo "Running uv sync to check for any differences..."
uv sync

# Check if there are any differences in uv.lock
if ! git diff --quiet -- uv.lock || ! git diff --cached --quiet -- uv.lock; then
    echo "Error: uv.lock is out of sync with pyproject.toml"
    echo "Please run 'uv sync' locally and commit the changes"
    exit 1
fi

echo "✅ uv.lock is in sync with pyproject.toml"

# Check requirements.txt if it exists
if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "Checking if requirements.txt matches pyproject.toml..."
    
    # Create a temporary requirements file
    TEMP_REQUIREMENTS=$(mktemp)
    
    # Generate requirements using the provided command
    echo "Generating requirements using command: $REQUIREMENTS_COMMAND"
    eval "$REQUIREMENTS_COMMAND" -o "$TEMP_REQUIREMENTS"
    
    # Compare the generated requirements with the existing one
    if ! diff -q "$TEMP_REQUIREMENTS" "$REQUIREMENTS_PATH" > /dev/null; then
        echo "Error: requirements.txt is out of sync with pyproject.toml"
        echo "Please run '$REQUIREMENTS_COMMAND' locally and commit the changes"
        rm "$TEMP_REQUIREMENTS"
        exit 1
    fi
    
    rm "$TEMP_REQUIREMENTS"
    echo "✅ requirements.txt is in sync with pyproject.toml"
fi
