#!/usr/bin/env python3
"""
judge.py — LLM-powered domain classification for the Anthropic ruleset.

Given a list of candidate domains (from audit.sh gaps), asks Claude to:
1. Determine if each domain is Anthropic/Claude-related
2. Classify its purpose
3. Decide add/skip
4. Write the domains.yaml entry if adding

Input:  list of domains (one per line, stdin or --domains)
Output: JSON decisions + patched domains.yaml if --apply

Requires: ANTHROPIC_API_KEY environment variable
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAINS_YAML = REPO_ROOT / "domains.yaml"

SYSTEM_PROMPT = """\
You are an expert network analyst maintaining a proxy ruleset for Anthropic/Claude services.

Given a domain discovered in the Claude CLI binary or network traffic, determine:
1. Is it related to Anthropic, Claude, or their infrastructure?
2. What is its purpose?
3. Should it be added to the proxy ruleset?

Context: Users behind restrictive firewalls (e.g., China's GFW) need ALL Claude-related
domains proxied. Missing a domain breaks Claude functionality. But adding unrelated domains
(generic CDNs, bundled runtime dependencies) pollutes the ruleset.

Rules:
- Anthropic/Claude first-party domains: ALWAYS add
- Third-party services that Claude DEPENDS on (telemetry, auth, feature flags): add
- Generic infrastructure (Google Fonts, npm, GitHub): skip — not Claude-specific
- Staging/test domains (*.staging.*, *.dev): skip — not production

Respond with JSON only. No markdown fencing.\
"""

USER_TEMPLATE = """\
Classify these domains found in the Claude CLI binary/network traffic.
For each, respond with a JSON array of objects:

{{
  "domain": "the.domain.com",
  "decision": "add" | "skip",
  "reason": "one sentence why",
  "type": "DOMAIN" | "DOMAIN-SUFFIX",
  "group": "Core API & Services" | "Claude Web & CLI" | "Updates & Distribution" | "Feature Flags & Telemetry" | "Third-Party Dependencies" | "MCP & Ecosystem",
  "yaml_reason": "description for domains.yaml (only if decision=add)"
}}

Domains to classify:
{domains}

Current ruleset covers these base domains:
{existing}
"""


def load_existing():
    """Extract currently covered base domains from domains.yaml."""
    import yaml
    with open(DOMAINS_YAML) as f:
        data = yaml.safe_load(f)
    domains = []
    for group in data["groups"]:
        for entry in group["entries"]:
            domains.append(entry["domain"])
    return domains


def classify_domains(candidate_domains, api_key):
    """Ask Claude to classify candidate domains."""
    import anthropic

    existing = load_existing()
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": USER_TEMPLATE.format(
                domains="\n".join(f"- {d}" for d in candidate_domains),
                existing="\n".join(f"- {d}" for d in existing),
            ),
        }],
    )

    text = response.content[0].text.strip()
    return json.loads(text)


def apply_decisions(decisions):
    """Patch domains.yaml with 'add' decisions."""
    import yaml
    from datetime import date

    with open(DOMAINS_YAML) as f:
        data = yaml.safe_load(f)

    additions = [d for d in decisions if d["decision"] == "add"]
    if not additions:
        return 0

    # Find or create the target group for each addition
    group_map = {}
    for group in data["groups"]:
        group_map[group["name"]] = group

    for d in additions:
        target_group = d.get("group", "Third-Party Dependencies")
        if target_group not in group_map:
            new_group = {"name": target_group, "entries": []}
            data["groups"].append(new_group)
            group_map[target_group] = new_group

        group_map[target_group]["entries"].append({
            "domain": d["domain"],
            "type": d["type"],
            "reason": d.get("yaml_reason", d["reason"]),
            "source": "Automated LLM classification (judge.py)",
            "added": str(date.today()),
        })

    with open(DOMAINS_YAML, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    return len(additions)


def main():
    parser = argparse.ArgumentParser(description="LLM-powered domain classifier")
    parser.add_argument("--domains", nargs="*", help="Domains to classify")
    parser.add_argument("--apply", action="store_true", help="Apply add decisions to domains.yaml")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Read domains from args or stdin
    if args.domains:
        candidates = args.domains
    else:
        candidates = [line.strip() for line in sys.stdin if line.strip()]

    if not candidates:
        print("No domains to classify.")
        return

    print(f"Classifying {len(candidates)} domain(s)...", file=sys.stderr)
    decisions = classify_domains(candidates, api_key)

    # Print decisions
    for d in decisions:
        icon = "+" if d["decision"] == "add" else "-"
        print(f"  [{icon}] {d['domain']:40s} {d['decision']:5s}  {d['reason']}")

    if args.apply:
        count = apply_decisions(decisions)
        if count:
            print(f"\nApplied {count} addition(s) to domains.yaml", file=sys.stderr)
        else:
            print("\nNo additions to apply.", file=sys.stderr)

    # Output JSON for pipeline consumption
    json.dump(decisions, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
