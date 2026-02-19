#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="app/data/xwines"
mkdir -p "$TARGET_DIR"

if command -v git >/dev/null 2>&1; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  git clone --depth 1 https://github.com/rogerioxavier/X-Wines "$TMP_DIR/repo"

  if [[ -f "$TMP_DIR/repo/wines.csv" ]]; then
    cp "$TMP_DIR/repo/wines.csv" "$TARGET_DIR/wines.csv"
    echo "Copied wines.csv into $TARGET_DIR"
  else
    echo "No wines.csv found in upstream repo root; inspect $TMP_DIR/repo manually."
    exit 1
  fi
else
  echo "git is required to sync dataset"
  exit 1
fi
