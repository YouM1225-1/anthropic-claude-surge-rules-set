#!/bin/bash
# exercise-and-capture.sh — Extract domains from Claude binary + DNS probes.
# No interactive Claude execution — avoids CI hangs.

set -eo pipefail

DOMAINS_FILE="${1:-captured-domains.txt}"
CLAUDE_BIN=$(which claude 2>/dev/null || echo "$HOME/.local/bin/claude")

echo "=== Domain Discovery — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# -------------------------------------------------------------------
# 1. Extract domains from Claude binary strings
# -------------------------------------------------------------------
echo "[1/3] Scanning binary: $CLAUDE_BIN"
BINARY_DOMAINS="/tmp/binary-domains.txt"

if [[ -f "$CLAUDE_BIN" ]]; then
  strings "$CLAUDE_BIN" 2>/dev/null \
    | grep -oE 'https?://[a-zA-Z0-9._-]+\.[a-z]{2,6}' \
    | sed 's|^https\{0,1\}://||' \
    | sort -u \
    | grep -vE 'localhost|127\.|example\.com|0\.0\.0|w3\.org|mozilla\.org' \
    | grep -vE 'github\.com|bun\.com|npmjs|feross|sharp|webkit|oven-sh' \
    | grep -vE 'apple\.com|expo\.dev|microsoft\.com|amazon\.com|google\.com$' \
    | grep -vE 'staging|fedstart|canary' \
    > "$BINARY_DOMAINS"
  echo "  Found $(wc -l < "$BINARY_DOMAINS" | tr -d ' ') domains in binary"
else
  echo "  WARNING: Claude binary not found"
  touch "$BINARY_DOMAINS"
fi

# -------------------------------------------------------------------
# 2. Resolve known + discovered domains (validates they're live)
# -------------------------------------------------------------------
echo "[2/3] DNS resolution probes..."

# Combine binary domains with known critical domains
PROBE_DOMAINS=(
  api.anthropic.com
  platform.claude.com
  claude.ai
  claude.com
  downloads.claude.ai
  mcp-proxy.anthropic.com
  statsig.anthropic.com
  cdn.growthbook.io
  sentry.anthropic.com
  status.anthropic.com
  clau.de
  claudeusercontent.com
  modelcontextprotocol.io
  storage.googleapis.com
  cdn.usefathom.com
)

DNS_LOG="/tmp/dns-resolved.txt"
> "$DNS_LOG"

for domain in "${PROBE_DOMAINS[@]}"; do
  if dig +short "$domain" @8.8.8.8 >/dev/null 2>&1; then
    echo "$domain" >> "$DNS_LOG"
  fi
done

# Also try resolving any anthropic/claude-related domains from binary
grep -iE 'anthropic|claude|clau\.de' "$BINARY_DOMAINS" >> "$DNS_LOG" 2>/dev/null || true

echo "  Resolved $(wc -l < "$DNS_LOG" | tr -d ' ') domains"

# -------------------------------------------------------------------
# 3. Combine and output
# -------------------------------------------------------------------
echo "[3/3] Combining results..."

cat "$BINARY_DOMAINS" "$DNS_LOG" \
  | sort -u \
  | grep -vE '^$' \
  > "$DOMAINS_FILE"

TOTAL=$(wc -l < "$DOMAINS_FILE" | tr -d ' ')
echo ""
echo "=== Results ==="
echo "Total unique domains: $TOTAL"
echo ""
cat "$DOMAINS_FILE"

rm -f "$BINARY_DOMAINS" "$DNS_LOG"
