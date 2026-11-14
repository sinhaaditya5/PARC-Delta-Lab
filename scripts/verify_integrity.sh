#!/usr/bin/env bash
# Verify parc-delta/ is byte-identical to the 1.6.0-research release manifest.
# Works with GNU coreutils (sha256sum) or BSD/macOS (shasum).
set -euo pipefail
cd "$(dirname "$0")/../parc-delta"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum --check --quiet SHA256SUMS.txt
else
  shasum -a 256 --check --quiet SHA256SUMS.txt
fi
echo "parc-delta: $(wc -l < SHA256SUMS.txt | tr -d ' ') files match SHA256SUMS.txt"
