#!/bin/bash

set -euo pipefail

# Always resolve relative to the repo root (GITHUB_WORKSPACE or git rev-parse fallback)
REPO_ROOT="${GITHUB_WORKSPACE:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [[ "$SYNC_COMMAND" =~ --directory[=\ ]([^ ]+) ]]; then
  DIR_ARG="${BASH_REMATCH[1]}"
  # If DIR_ARG is not absolute, make it absolute relative to repo root
  if [[ ! "$DIR_ARG" = /* ]]; then
    ABS_DIR_ARG="$REPO_ROOT/$DIR_ARG"
    SYNC_COMMAND="${SYNC_COMMAND/--directory $DIR_ARG/--directory $ABS_DIR_ARG}"
    SYNC_COMMAND="${SYNC_COMMAND/--directory=$DIR_ARG/--directory=$ABS_DIR_ARG}"
  fi
fi

echo "Resolved SYNC_COMMAND: $SYNC_COMMAND"
echo "Running sync command: $SYNC_COMMAND"
eval "$SYNC_COMMAND"

# Check if any existing files have been modified
if ! git diff --exit-code --quiet; then
  echo "❌ Existing files have been modified by sync:"
  git diff --name-only
  echo ""
  echo "This indicates that your lock files or requirements files are out of sync."
  echo "Please run the sync command and commit the changes."
  exit 1
fi

echo "✅ All files are in sync"
