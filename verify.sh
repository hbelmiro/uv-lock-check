#!/bin/bash

set -euo pipefail

# Debug: Current directory
pwd

echo "Running sync command: $SYNC_COMMAND"
eval "$SYNC_COMMAND"

git diff --exit-code

echo "✅ All files are in sync"
