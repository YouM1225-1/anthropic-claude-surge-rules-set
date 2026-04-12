#!/bin/bash
# capture-dns.sh — Monitor ALL DNS queries from Claude processes.
# Run this in the background while using Claude normally.
# Over days/weeks, builds a comprehensive domain list.
#
# Usage: ./scripts/capture-dns.sh [duration_minutes]
#   Default: 60 minutes
#   Output: dns-captures/YYYY-MM-DD.txt (appended)
#
# Requires: sudo (for tcpdump on DNS)
# Works on macOS and Linux.

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CAPTURE_DIR="$REPO_ROOT/dns-captures"
DURATION_MIN="${1:-60}"
DURATION_SEC=$((DURATION_MIN * 60))
TODAY=$(date +%Y-%m-%d)
OUTPUT="$CAPTURE_DIR/$TODAY.txt"

mkdir -p "$CAPTURE_DIR"

echo "Capturing DNS queries for ${DURATION_MIN} minutes..."
echo "Output: $OUTPUT"

# Capture DNS queries (port 53) and extract queried domain names
sudo tcpdump -i any -n -l port 53 2>/dev/null \
  | grep --line-buffered -oE 'A\? [a-zA-Z0-9._-]+\.' \
  | sed 's/^A? //;s/\.$//' \
  | while read domain; do
      # Only log if related to known Claude/Anthropic patterns OR unknown
      echo "$(date +%H:%M:%S) $domain"
    done \
  | tee -a "$OUTPUT" &

TCPDUMP_PID=$!

# Auto-stop after duration
sleep "$DURATION_SEC"
sudo kill "$TCPDUMP_PID" 2>/dev/null

# Extract unique domains, filter to potentially relevant ones
echo ""
echo "=== Unique domains queried ==="
sort -u -t' ' -k2 "$OUTPUT" | awk '{print $2}' | sort -u | \
  grep -iE 'anthropic|claude|clau\.de|growthbook|sentry|datadog|intercom|fathom|statsig' \
  > "$CAPTURE_DIR/relevant-$TODAY.txt"

TOTAL=$(sort -u -t' ' -k2 "$OUTPUT" | awk '{print $2}' | sort -u | wc -l | tr -d ' ')
RELEVANT=$(wc -l < "$CAPTURE_DIR/relevant-$TODAY.txt" | tr -d ' ')
echo "Total unique domains: $TOTAL"
echo "Relevant to Claude: $RELEVANT"
echo "Saved to: $CAPTURE_DIR/relevant-$TODAY.txt"
