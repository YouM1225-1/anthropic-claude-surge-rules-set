#!/bin/bash
# audit.sh — Daily probe for Claude CLI network dependencies.
# Scans the Claude binary for domains, checks DNS for IP changes,
# diffs against the current ruleset, reports gaps.
#
# Usage: ./scripts/audit.sh [--fix]
#   --fix: auto-patch anthropic.list with missing domains
#
# Exit codes: 0 = no gaps, 1 = gaps found (printed to stdout)

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RULESET="$REPO_ROOT/anthropic.list"
CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"
LOG="$REPO_ROOT/audit.log"
FIX=false
[[ "${1:-}" == "--fix" ]] && FIX=true

exec > >(tee "$LOG") 2>&1
echo "=== Claude Surge Ruleset Audit — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo ""

# -------------------------------------------------------------------
# 1. Extract domains from Claude binary
# -------------------------------------------------------------------
echo "[1/4] Scanning Claude binary for domains..."

BINARY_DOMAINS=$(mktemp)
if [[ -f "$CLAUDE_BIN" ]]; then
  strings "$CLAUDE_BIN" 2>/dev/null \
    | grep -oE 'https?://[a-zA-Z0-9._-]+\.[a-z]{2,6}' \
    | sed 's|^https\{0,1\}://||' \
    | sort -u \
    | grep -vE 'localhost|127\.0\.0|example\.com|0\.0\.0\.0|w3\.org|mozilla\.org|github\.com|bun\.com|npm|feross|sharp|webkit|apple\.com|expo\.dev|microsoft\.com|amazon\.com|google\.com$|staging|fedstart' \
    > "$BINARY_DOMAINS"
  echo "  Found $(wc -l < "$BINARY_DOMAINS" | tr -d ' ') unique domains in binary"
else
  echo "  WARNING: Claude binary not found at $CLAUDE_BIN"
  touch "$BINARY_DOMAINS"
fi

# -------------------------------------------------------------------
# 2. Known Claude-critical domains (hardcoded watchlist)
# -------------------------------------------------------------------
echo "[2/4] Checking critical domain watchlist..."

CRITICAL_DOMAINS=(
  api.anthropic.com
  anthropic.com
  claude.ai
  claude.com
  platform.claude.com
  console.anthropic.com
  statsig.anthropic.com
  status.anthropic.com
  sentry.anthropic.com
  mcp-proxy.anthropic.com
  downloads.claude.ai
  code.claude.com
  docs.claude.com
  support.claude.com
  cdn.growthbook.io
  clau.de
  claudeusercontent.com
  modelcontextprotocol.io
  storage.googleapis.com
  cdn.usefathom.com
  http-intake.logs.us5.datadoghq.com
  intercom.io
  sentry.io
)

# -------------------------------------------------------------------
# 3. Check each domain against the ruleset
# -------------------------------------------------------------------
echo "[3/4] Checking coverage..."

GAPS=()
COVERED=0

check_domain() {
  local domain="$1"
  # Extract the base domain (last 2 parts) for DOMAIN-SUFFIX matching
  local base
  base=$(echo "$domain" | rev | cut -d. -f1-2 | rev)

  # Check if covered by DOMAIN-SUFFIX or DOMAIN rule
  if grep -q "DOMAIN-SUFFIX,$base" "$RULESET" 2>/dev/null; then
    return 0
  fi
  if grep -q "DOMAIN-SUFFIX,$domain" "$RULESET" 2>/dev/null; then
    return 0
  fi
  if grep -q "DOMAIN,$domain" "$RULESET" 2>/dev/null; then
    return 0
  fi
  return 1
}

for domain in "${CRITICAL_DOMAINS[@]}"; do
  if check_domain "$domain"; then
    COVERED=$((COVERED + 1))
  else
    GAPS+=("$domain")
    echo "  GAP: $domain"
  fi
done

echo "  Covered: $COVERED/${#CRITICAL_DOMAINS[@]}"

# Also check binary-extracted domains for Anthropic/Claude-related ones
BINARY_GAPS=()
while IFS= read -r domain; do
  if echo "$domain" | grep -qiE 'anthropic|claude|clau\.de'; then
    if ! check_domain "$domain"; then
      BINARY_GAPS+=("$domain")
      echo "  GAP (from binary): $domain"
    fi
  fi
done < "$BINARY_DOMAINS"

rm -f "$BINARY_DOMAINS"

# -------------------------------------------------------------------
# 4. Check Anthropic IP ranges via DNS
# -------------------------------------------------------------------
echo "[4/4] Verifying Anthropic IP ranges..."

API_IPS=$(dig +short api.anthropic.com @1.1.1.1 2>/dev/null | sort)
if [[ -n "$API_IPS" ]]; then
  for ip in $API_IPS; do
    if grep -q "$(echo "$ip" | cut -d. -f1-2)" "$RULESET" 2>/dev/null; then
      echo "  OK: $ip covered by IP-CIDR rule"
    else
      echo "  WARNING: $ip may not be covered by IP-CIDR rules"
      GAPS+=("IP:$ip")
    fi
  done
else
  echo "  WARNING: Could not resolve api.anthropic.com"
fi

# -------------------------------------------------------------------
# Report
# -------------------------------------------------------------------
echo ""
TOTAL_GAPS=$(( ${#GAPS[@]} + ${#BINARY_GAPS[@]} ))

if [[ $TOTAL_GAPS -eq 0 ]]; then
  echo "RESULT: No gaps found. Ruleset is up to date."
  exit 0
else
  echo "RESULT: $TOTAL_GAPS gap(s) found:"
  for gap in "${GAPS[@]+"${GAPS[@]}"}" "${BINARY_GAPS[@]+"${BINARY_GAPS[@]}"}"; do
    [[ -n "$gap" ]] && echo "  - $gap"
  done

  if $FIX; then
    echo ""
    echo "Auto-fixing..."
    for gap in "${GAPS[@]+"${GAPS[@]}"}" "${BINARY_GAPS[@]+"${BINARY_GAPS[@]}"}"; do
      [[ -z "$gap" ]] && continue
      if [[ "$gap" == IP:* ]]; then
        continue  # Don't auto-add IPs
      fi
      # Add as DOMAIN entry before the IP-CIDR section
      sed -i.bak "/^# .* Anthropic IP Ranges/i\\
DOMAIN,$gap" "$RULESET" 2>/dev/null || \
      sed -i '' "/^# .* Anthropic IP Ranges/i\\
DOMAIN,$gap" "$RULESET"
      echo "  Added: DOMAIN,$gap"
    done
    # Update timestamp
    sed -i '' "s/^# Last updated:.*/# Last updated: $(date -u +%Y-%m-%d)/" "$RULESET"
    echo "Ruleset patched. Review changes before committing."
  fi

  exit 1
fi
