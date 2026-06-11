# Anthropic / Claude Proxy Ruleset

Comprehensive proxy ruleset for all Anthropic and Claude services. Covers API, web app, CLI, binary updates, telemetry, and third-party dependencies.

Supports **Surge**, **Clash/Mihomo**, **sing-box**, **Quantumult X**, **Loon**, and plain domain lists.

## Quick Start

### Surge / Surfboard

```ini
RULE-SET,https://raw.githubusercontent.com/YouM1225-1/anthropic-claude-surge-rules-set/main/dist/anthropic.list,YourProxyGroup
```

### Clash / Mihomo

```yaml
rule-providers:
  anthropic:
    type: http
    behavior: classical
    url: https://raw.githubusercontent.com/YouM1225-1/anthropic-claude-surge-rules-set/main/dist/anthropic-clash.yaml
    interval: 86400

rules:
  - RULE-SET,anthropic,YourProxyGroup
```

### sing-box

Source rule-set:

```json
{
  "route": {
    "rule_set": [
      {
        "tag": "anthropic",
        "type": "remote",
        "url": "https://raw.githubusercontent.com/YouM1225-1/anthropic-claude-surge-rules-set/main/dist/anthropic-singbox.json",
        "format": "source"
      }
    ],
    "rules": [
      { "rule_set": "anthropic", "outbound": "proxy" }
    ]
  }
}
```

Binary rule-set (`.srs`):

```json
{
  "route": {
    "rule_set": [
      {
        "tag": "anthropic",
        "type": "remote",
        "url": "https://raw.githubusercontent.com/YouM1225-1/anthropic-claude-surge-rules-set/main/dist/anthropic-singbox.srs",
        "format": "binary"
      }
    ],
    "rules": [
      { "rule_set": "anthropic", "outbound": "proxy" }
    ]
  }
}
```

### Quantumult X

```ini
[filter_remote]
https://raw.githubusercontent.com/YouM1225-1/anthropic-claude-surge-rules-set/main/dist/anthropic-qx.conf, tag=Anthropic, force-policy=proxy, update-interval=86400
```

### Loon

```ini
[Remote Rule]
https://raw.githubusercontent.com/YouM1225-1/anthropic-claude-surge-rules-set/main/dist/anthropic-loon.conf, policy=proxy, tag=Anthropic
```

## What's Covered

| Category | Domains | Why |
|---|---|---|
| **Core API** | `*.anthropic.com` | API, console, statsig, status, sentry, MCP proxy |
| **Claude Web** | `*.claude.ai`, `*.claude.com` | Web app, platform, CLI docs, OAuth |
| **User Content** | `*.claudeusercontent.com` | Artifacts, file previews |
| **Short URL** | `*.clau.de` | URL redirector in CLI output |
| **MCP** | `*.modelcontextprotocol.io` | MCP spec site |
| **CLI Updates** | `downloads.claude.ai`, `storage.googleapis.com` | Binary distribution |
| **Feature Flags** | `cdn.growthbook.io` | A/B testing, rollout gates |
| **Cloudflare Challenge** | `challenges.cloudflare.com` | Login and bot-check challenge resources |
| **IP Ranges** | `160.79.104.0/21`, `2607:6bc0::/48` | Anthropic AS399358 |
| **Support** | `*.intercom.io`, `*.intercomcdn.com` | In-app chat widget |
| **Analytics** | `cdn.usefathom.com` | Privacy-focused analytics |
| **Error Reporting** | `*.sentry.io` | Crash reports |
| **Telemetry** | `*.datadoghq.com` | Logging |

## Source of Truth

Base domains are defined in upstream [`domains.yaml`](domains.yaml). Local additions live in [`supplemental-domains.yaml`](supplemental-domains.yaml), so scheduled upstream syncs can merge cleanly while preserving extra rules.

Output files are generated from both files:

```bash
python3 scripts/generate.py
```

This produces all text/source formats in `dist/`. If `sing-box` is available in `PATH`, it also compiles `dist/anthropic-singbox.srs`.

## Automation

This fork includes a GitHub Actions workflow that:

1. Merges `xiaolai/anthropic-claude-surge-rules-set` `main`
2. Applies [`supplemental-domains.yaml`](supplemental-domains.yaml)
3. Builds all `dist/` outputs, including `dist/anthropic-singbox.srs`
4. Commits generated changes back to this fork

It runs daily and can also be triggered manually from the Actions tab.

## Discovery Method

Domains are discovered through:

1. **Binary analysis** — `strings` on the Claude CLI binary
2. **Network monitoring** — `lsof` / `tcpdump` during active Claude sessions
3. **DNS probing** — Reverse lookups on observed connections
4. **Install script analysis** — Parsing `claude.ai/install.sh`
5. **Official documentation** — Anthropic network docs, API references

## Notes

- `storage.googleapis.com` is a shared Google domain. Only specific GCS buckets are Claude-related, but proxy rules cannot filter by URL path. If you already proxy all Google services, this rule is redundant.
- Third-party services (Intercom, Sentry, Datadog, Fathom) are optional. Blocking them degrades UX but doesn't break core functionality.
- IP-CIDR ranges are from Anthropic's official AS399358 allocation.

## Contributing

Found a missing domain? [Open an issue](https://github.com/xiaolai/anthropic-claude-surge-rules-set/issues) with:
- The domain
- How you discovered it (network trace, error message, etc.)
- Which Claude product it affects (API, web, CLI)

## License

MIT
