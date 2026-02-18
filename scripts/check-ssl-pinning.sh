#!/usr/bin/env bash
# check-ssl-pinning.sh — Scan decompiled source for SSL pinning and TLS issues
#
# Usage: check-ssl-pinning.sh <decompiled-dir>
#
# Checks for:
#   1. CertificatePinner usage (OkHttp)
#   2. Network security config (XML)
#   3. Custom TrustManager (dangerous if empty)
#   4. Cleartext traffic allowed
#   5. Hostname verifier bypass
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: check-ssl-pinning.sh <decompiled-dir>"
  exit 1
fi

DIR="$1"

if [[ ! -d "$DIR" ]]; then
  echo "[!] Directory not found: $DIR"
  exit 1
fi

echo "=== SSL/TLS Security Scan ==="
echo "Target: $DIR"
echo

findings=0

# --- 1. CertificatePinner ---
echo "--- Certificate Pinning ---"
pinning_files=$(grep -rl "CertificatePinner\|certificatePinner\|certificate.pinner" "$DIR" --include="*.java" --include="*.kt" --include="*.xml" 2>/dev/null || true)
if [[ -n "$pinning_files" ]]; then
  echo "[+] CertificatePinner FOUND in:"
  echo "$pinning_files" | while read -r f; do echo "    $f"; done
  # Show pinned domains
  grep -rn "\.add(" $pinning_files 2>/dev/null | grep -i "sha256\|sha1" | head -10 || true
else
  echo "[!!] NO CertificatePinner found — app is vulnerable to MITM with user-installed CA"
  findings=$((findings + 1))
fi
echo

# --- 2. Network Security Config ---
echo "--- Network Security Config ---"
nsc_file=$(find "$DIR" -name "network_security_config.xml" -type f 2>/dev/null | head -1)
if [[ -n "$nsc_file" ]]; then
  echo "[+] Found: $nsc_file"
  cat "$nsc_file"
  echo
  # Check for pin-set
  if grep -q "pin-set\|pin " "$nsc_file" 2>/dev/null; then
    echo "[+] Pin-set configured in network security config"
  else
    echo "[!] Network security config exists but has NO pin-set"
  fi
else
  echo "[-] No network_security_config.xml found"
fi
echo

# --- 3. Custom TrustManager (dangerous) ---
echo "--- TrustManager Analysis ---"
tm_files=$(grep -rl "X509TrustManager\|TrustManagerFactory\|checkServerTrusted" "$DIR" --include="*.java" --include="*.kt" 2>/dev/null || true)
if [[ -n "$tm_files" ]]; then
  echo "[!] Custom TrustManager found in:"
  echo "$tm_files" | while read -r f; do echo "    $f"; done
  echo
  # Check for empty checkServerTrusted (disables validation entirely)
  for f in $tm_files; do
    if grep -A5 "checkServerTrusted" "$f" 2>/dev/null | grep -q "^\s*}\s*$\|// *$\|/\*.*\*/"; then
      echo "[!!] CRITICAL: $f may have EMPTY checkServerTrusted — disables ALL cert validation!"
      findings=$((findings + 1))
    fi
  done
else
  echo "[-] No custom TrustManager found (using system default — OK)"
fi
echo

# --- 4. Cleartext traffic ---
echo "--- Cleartext Traffic ---"
manifest=$(find "$DIR" -name "AndroidManifest.xml" -path "*/resources/*" -type f 2>/dev/null | head -1)
if [[ -n "$manifest" ]]; then
  if grep -q 'usesCleartextTraffic="true"' "$manifest" 2>/dev/null; then
    echo "[!!] android:usesCleartextTraffic=\"true\" — HTTP traffic allowed globally"
    findings=$((findings + 1))
  else
    echo "[+] usesCleartextTraffic not enabled (or false)"
  fi
else
  echo "[-] AndroidManifest.xml not found"
fi

if [[ -n "$nsc_file" ]]; then
  if grep -q 'cleartextTrafficPermitted="true"' "$nsc_file" 2>/dev/null; then
    echo "[!!] cleartextTrafficPermitted=\"true\" in network security config"
    findings=$((findings + 1))
  fi
fi
echo

# --- 5. Hostname verifier bypass ---
echo "--- Hostname Verifier ---"
hv_files=$(grep -rl "ALLOW_ALL_HOSTNAME_VERIFIER\|HostnameVerifier\|setHostnameVerifier\|hostnameVerifier" "$DIR" --include="*.java" --include="*.kt" 2>/dev/null || true)
if [[ -n "$hv_files" ]]; then
  echo "[!] Custom HostnameVerifier found in:"
  echo "$hv_files" | while read -r f; do echo "    $f"; done
  # Check for ALLOW_ALL
  if echo "$hv_files" | xargs grep -l "ALLOW_ALL\|return true\|verify.*return true" 2>/dev/null; then
    echo "[!!] CRITICAL: Hostname verification may be DISABLED"
    findings=$((findings + 1))
  fi
else
  echo "[+] No custom HostnameVerifier (using default — OK)"
fi
echo

# --- Summary ---
echo "=== Summary ==="
if (( findings > 0 )); then
  echo "[!!] $findings SSL/TLS issue(s) found — see details above"
else
  echo "[+] No critical SSL/TLS issues detected"
fi
