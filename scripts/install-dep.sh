#!/usr/bin/env bash
# install-dep.sh — Install a single apk-audit dependency
# Handles apkeep and uv; delegates java/jadx/vineflower/dex2jar to the decompile skill.
#
# Exit codes:
#   0 — installed successfully
#   1 — installation failed
#   2 — requires manual action
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DECOMPILE_SCRIPTS="$SCRIPT_DIR/../android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/scripts"

if [[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  cat <<EOF
Usage: install-dep.sh <dependency>

Available dependencies:
  apkeep       APK downloader (requires Rust/cargo)
  uv           Python package runner
  java         Java JDK 17+ (delegated to decompile skill)
  jadx         jadx decompiler (delegated to decompile skill)
  vineflower   Vineflower decompiler (delegated to decompile skill)
  dex2jar      DEX to JAR converter (delegated to decompile skill)
EOF
  exit 0
fi

DEP="$1"

info()  { echo "[INFO] $*"; }
ok()    { echo "[OK] $*"; }
fail()  { echo "[FAIL] $*" >&2; }
manual() {
  echo "[MANUAL] $*" >&2
  exit 2
}

install_apkeep() {
  if command -v apkeep &>/dev/null; then
    ok "apkeep already installed"
    return 0
  fi

  if ! command -v cargo &>/dev/null; then
    info "Rust/cargo not found. Installing via rustup..."
    if command -v curl &>/dev/null; then
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
      source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
    else
      manual "Install Rust from https://rustup.rs, then run: cargo install apkeep"
    fi
  fi

  info "Installing apkeep via cargo..."
  cargo install apkeep

  if command -v apkeep &>/dev/null; then
    ok "apkeep installed"
  else
    export PATH="$HOME/.cargo/bin:$PATH"
    if command -v apkeep &>/dev/null; then
      ok "apkeep installed (in ~/.cargo/bin)"
    else
      fail "apkeep installation failed"
      exit 1
    fi
  fi
}

install_uv() {
  if command -v uv &>/dev/null; then
    ok "uv already installed"
    return 0
  fi

  # Try brew first
  if command -v brew &>/dev/null; then
    info "Installing uv via Homebrew..."
    brew install uv
  elif command -v curl &>/dev/null; then
    info "Installing uv via install script..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    manual "Install uv from https://github.com/astral-sh/uv"
  fi

  if command -v uv &>/dev/null; then
    ok "uv installed"
  else
    fail "uv installation may require a new shell"
    exit 1
  fi
}

case "$DEP" in
  apkeep)  install_apkeep ;;
  uv)      install_uv ;;
  java|jadx|vineflower|fernflower|dex2jar|apktool|adb)
    if [[ -f "$DECOMPILE_SCRIPTS/install-dep.sh" ]]; then
      bash "$DECOMPILE_SCRIPTS/install-dep.sh" "$DEP"
    else
      fail "Decompile skill scripts not found. Run: git submodule update --init --recursive"
      exit 1
    fi
    ;;
  *)
    echo "Error: Unknown dependency '$DEP'" >&2
    echo "Available: apkeep, uv, java, jadx, vineflower, dex2jar" >&2
    exit 1
    ;;
esac
