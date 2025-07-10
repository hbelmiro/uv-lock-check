#!/bin/bash

set -euo pipefail

# Debug: Current directory
pwd

echo "Running sync command: $SYNC_COMMAND"
eval "$SYNC_COMMAND"

git status --short

if ! git diff --exit-code > /dev/null; then
    echo "❌ Some files are out of sync (see git diff above)"
    git --no-pager diff
    exit 1
fi

echo "✅ All files are in sync"
