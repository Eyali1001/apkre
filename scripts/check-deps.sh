#!/usr/bin/env bash
# check-deps.sh — Verify all apk-audit dependencies
# Checks apkeep + uv, then delegates to the decompile skill for jadx/java.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DECOMPILE_SCRIPTS="$SCRIPT_DIR/../android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/scripts"

errors=0
missing_required=()

echo "=== APK Audit: Dependency Check ==="
echo

# --- apkeep ---
if command -v apkeep &>/dev/null; then
  echo "[OK] apkeep detected"
else
  echo "[MISSING] apkeep is not installed or not in PATH"
  errors=$((errors + 1))
  missing_required+=("apkeep")
fi

# --- uv ---
if command -v uv &>/dev/null; then
  echo "[OK] uv detected"
else
  echo "[MISSING] uv is not installed or not in PATH"
  errors=$((errors + 1))
  missing_required+=("uv")
fi

# --- Delegate to decompile skill for jadx, java, etc. ---
echo
if [[ -x "$DECOMPILE_SCRIPTS/check-deps.sh" ]] || [[ -f "$DECOMPILE_SCRIPTS/check-deps.sh" ]]; then
  bash "$DECOMPILE_SCRIPTS/check-deps.sh" || errors=$((errors + 1))
else
  echo "[WARN] Decompile skill scripts not found at $DECOMPILE_SCRIPTS"
  echo "       Run: git submodule update --init --recursive"
  errors=$((errors + 1))
fi

# --- Machine-readable summary for our deps ---
echo
if [[ ${#missing_required[@]} -gt 0 ]]; then
  for dep in "${missing_required[@]}"; do
    echo "INSTALL_REQUIRED:$dep"
  done
fi

if (( errors > 0 )); then
  echo
  echo "*** Some dependencies are missing. Run install-dep.sh <name> to install. ***"
  exit 1
fi
