#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <tag>" >&2
  exit 1
fi

tag="$1"

git tag "$tag"
git push origin "$tag"
