#!/usr/bin/env bash
# Bootstrap ANAMIZED product-repo structure (Server OS parity + USDC).
# Usage: bash scripts/bootstrap_repo_structure.sh /path/to/repo
set -euo pipefail
TARGET="${1:-.}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$TARGET/funding" "$TARGET/.github/workflows" "$TARGET/skills" "$TARGET/docs" "$TARGET/scripts"
cp -f "$ROOT/funding/addresses.json" "$TARGET/funding/addresses.json"
cp -f "$ROOT/funding/USDC.md" "$TARGET/funding/USDC.md"
[[ -f "$TARGET/.github/FUNDING.yml" ]] || cp -f "$ROOT/.github/FUNDING.yml" "$TARGET/.github/FUNDING.yml"
mkdir -p "$TARGET/skills/funding-usdc" "$TARGET/skills/repo-bootstrap"
cp -f "$ROOT/skills/funding-usdc/SKILL.md" "$TARGET/skills/funding-usdc/SKILL.md"
cp -f "$ROOT/skills/repo-bootstrap/SKILL.md" "$TARGET/skills/repo-bootstrap/SKILL.md"
echo "Bootstrapped funding + skills into $TARGET"
