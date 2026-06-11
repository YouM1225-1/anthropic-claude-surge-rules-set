#!/usr/bin/env python3
"""
Generate proxy rule-set files in multiple formats from domains.yaml and
supplemental-domains.yaml.

Outputs:
  dist/anthropic.list          — Surge / Surfboard
  dist/anthropic-clash.yaml    — Clash / Mihomo
  dist/anthropic-singbox.json  — sing-box
  dist/anthropic-singbox.srs   — sing-box binary rule-set, when sing-box is installed
  dist/anthropic-qx.conf       — Quantumult X
  dist/anthropic-loon.conf     — Loon
  dist/anthropic-domains.txt   — Plain domain list (one per line)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAINS_YAML = REPO_ROOT / "domains.yaml"
SUPPLEMENTAL_DOMAINS_YAML = REPO_ROOT / "supplemental-domains.yaml"
DIST = REPO_ROOT / "dist"


def generated_date():
    return os.environ.get("GENERATED_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_domains():
    groups = []
    for path in (DOMAINS_YAML, SUPPLEMENTAL_DOMAINS_YAML):
        if not path.exists():
            continue
        with open(path) as f:
            data = yaml.safe_load(f)
        groups.extend(data["groups"])
    return dedupe_groups(groups)


def dedupe_groups(groups):
    """Remove duplicate rules while preserving upstream-first ordering."""
    seen = set()
    deduped = []

    for group in groups:
        entries = []
        for entry in group["entries"]:
            key = (entry["type"], entry["domain"])
            if key in seen:
                continue
            seen.add(key)
            entries.append(entry)
        if entries:
            copied = dict(group)
            copied["entries"] = entries
            deduped.append(copied)

    return deduped


def generate_surge(groups):
    """Surge / Surfboard format."""
    lines = [
        "# ============================================================",
        "# ANTHROPIC / CLAUDE — COMPREHENSIVE PROXY RULESET",
        "# https://github.com/xiaolai/anthropic-claude-surge-rules-set",
        f"# Generated: {generated_date()}",
        "# Format: Surge / Surfboard",
        "# ============================================================",
        "",
    ]
    for group in groups:
        lines.append(f"# {group['name']}")
        for entry in group["entries"]:
            d, t = entry["domain"], entry["type"]
            if t in ("IP-CIDR", "IP-CIDR6"):
                lines.append(f"{t},{d},no-resolve")
            else:
                lines.append(f"{t},{d}")
        lines.append("")
    return "\n".join(lines)


def generate_clash(groups):
    """Clash / Mihomo YAML format."""
    payload = []
    for group in groups:
        for entry in group["entries"]:
            d, t = entry["domain"], entry["type"]
            if t == "DOMAIN-SUFFIX":
                payload.append(f"+.{d}")
            elif t == "DOMAIN":
                payload.append(d)
            elif t == "DOMAIN-KEYWORD":
                payload.append(f"DOMAIN-KEYWORD,{d}")
            elif t in ("IP-CIDR", "IP-CIDR6"):
                payload.append(f"{d}")

    header = (
        f"# Anthropic / Claude — Clash Rule Provider\n"
        f"# https://github.com/xiaolai/anthropic-claude-surge-rules-set\n"
        f"# Generated: {generated_date()}\n"
    )
    data = {"payload": payload}
    return header + yaml.dump(data, default_flow_style=False, allow_unicode=True)


def generate_singbox(groups):
    """sing-box rule-set JSON format."""
    rules = build_singbox_rules(groups)

    header = (
        f"// Anthropic / Claude — sing-box Rule Set\n"
        f"// https://github.com/xiaolai/anthropic-claude-surge-rules-set\n"
        f"// Generated: {generated_date()}\n"
    )
    return header + json.dumps(rules, indent=2)


def build_singbox_rules(groups):
    """Build sing-box source rule-set payload."""
    rules = {"version": 2, "rules": []}
    domains, domain_suffixes, ip_cidrs = [], [], []

    for group in groups:
        for entry in group["entries"]:
            d, t = entry["domain"], entry["type"]
            if t == "DOMAIN":
                domains.append(d)
            elif t == "DOMAIN-SUFFIX":
                domain_suffixes.append(d)
            elif t in ("IP-CIDR", "IP-CIDR6"):
                ip_cidrs.append(d)

    rule = {}
    if domains:
        rule["domain"] = domains
    if domain_suffixes:
        rule["domain_suffix"] = domain_suffixes
    if ip_cidrs:
        rule["ip_cidr"] = ip_cidrs
    rules["rules"].append(rule)

    return rules


def compile_singbox_srs(groups):
    """Compile sing-box source rule-set to binary SRS when sing-box is available."""
    sing_box = os.environ.get("SING_BOX") or shutil.which("sing-box")
    if not sing_box:
        print("  anthropic-singbox.srs        skipped (sing-box not found)")
        return

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(build_singbox_rules(groups), f, indent=2)
        f.write("\n")
        source_path = f.name

    try:
        output_path = DIST / "anthropic-singbox.srs"
        subprocess.run(
            [sing_box, "rule-set", "compile", "--output", str(output_path), source_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(f"  {'anthropic-singbox.srs':30s} {output_path.stat().st_size:>6,} bytes")
    finally:
        Path(source_path).unlink(missing_ok=True)


def generate_quantumultx(groups):
    """Quantumult X format."""
    lines = [
        f"# Anthropic / Claude — Quantumult X Filter",
        f"# https://github.com/xiaolai/anthropic-claude-surge-rules-set",
        f"# Generated: {generated_date()}",
        "",
    ]
    for group in groups:
        for entry in group["entries"]:
            d, t = entry["domain"], entry["type"]
            if t == "DOMAIN-SUFFIX":
                lines.append(f"HOST-SUFFIX,{d},proxy")
            elif t == "DOMAIN":
                lines.append(f"HOST,{d},proxy")
            elif t == "IP-CIDR":
                lines.append(f"IP-CIDR,{d},proxy,no-resolve")
            elif t == "IP-CIDR6":
                lines.append(f"IP6-CIDR,{d},proxy,no-resolve")
    return "\n".join(lines)


def generate_loon(groups):
    """Loon format."""
    lines = [
        f"# Anthropic / Claude — Loon Rule",
        f"# https://github.com/xiaolai/anthropic-claude-surge-rules-set",
        f"# Generated: {generated_date()}",
        "",
    ]
    for group in groups:
        for entry in group["entries"]:
            d, t = entry["domain"], entry["type"]
            if t == "DOMAIN-SUFFIX":
                lines.append(f"DOMAIN-SUFFIX,{d}")
            elif t == "DOMAIN":
                lines.append(f"DOMAIN,{d}")
            elif t in ("IP-CIDR", "IP-CIDR6"):
                lines.append(f"{t},{d},no-resolve")
    return "\n".join(lines)


def generate_plain(groups):
    """Plain domain list (one per line, no IPs)."""
    lines = [
        f"# Anthropic / Claude domains",
        f"# https://github.com/xiaolai/anthropic-claude-surge-rules-set",
        f"# Generated: {generated_date()}",
    ]
    for group in groups:
        for entry in group["entries"]:
            if entry["type"] in ("DOMAIN", "DOMAIN-SUFFIX"):
                lines.append(entry["domain"])
    return "\n".join(lines)


def main():
    groups = load_domains()
    DIST.mkdir(exist_ok=True)

    outputs = {
        "anthropic.list": generate_surge,
        "anthropic-clash.yaml": generate_clash,
        "anthropic-singbox.json": generate_singbox,
        "anthropic-qx.conf": generate_quantumultx,
        "anthropic-loon.conf": generate_loon,
        "anthropic-domains.txt": generate_plain,
    }

    for filename, generator in outputs.items():
        content = generator(groups)
        path = DIST / filename
        path.write_text(content + "\n")
        print(f"  {filename:30s} {len(content):>6,} bytes")

    compile_singbox_srs(groups)

    # Also copy Surge format to repo root for backward compatibility
    (REPO_ROOT / "anthropic.list").write_text(
        (DIST / "anthropic.list").read_text()
    )

    print(f"\nGenerated {len(outputs)} formats in dist/")


if __name__ == "__main__":
    main()
