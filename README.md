# Anthropic / Claude Proxy Ruleset

Comprehensive proxy ruleset for all Anthropic and Claude services. Covers API, web app, CLI, binary updates, telemetry, and third-party dependencies.

Supports **Surge**, **Clash/Mihomo**, **sing-box**, **Quantumult X**, **Loon**, and plain domain lists.

## Quick Start

### Surge / Surfboard

```ini
RULE-SET,https://raw.githubusercontent.com/xiaolai/anthropic-claude-surge-rules-set/main/dist/anthropic.list,YourProxyGroup
```

### Clash / Mihomo

```yaml
rule-providers:
  anthropic:
    type: http
    behavior: classical
    url: https://raw.githubusercontent.com/xiaolai/anthropic-claude-surge-rules-set/main/dist/anthropic-clash.yaml
    interval: 86400

rules:
  - RULE-SET,anthropic,YourProxyGroup
```

### sing-box

```json
{
  "route": {
    "rule_set": [
      {
        "tag": "anthropic",
        "type": "remote",
        "url": "https://raw.githubusercontent.com/xiaolai/anthropic-claude-surge-rules-set/main/dist/anthropic-singbox.json",
        "format": "source"
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
https://raw.githubusercontent.com/xiaolai/anthropic-claude-surge-rules-set/main/dist/anthropic-qx.conf, tag=Anthropic, force-policy=proxy, update-interval=86400
```

### Loon

```ini
[Remote Rule]
https://raw.githubusercontent.com/xiaolai/anthropic-claude-surge-rules-set/main/dist/anthropic-loon.conf, policy=proxy, tag=Anthropic
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
| **IP Ranges** | `160.79.104.0/21`, `2607:6bc0::/48` | Anthropic AS399358 |
| **Support** | `*.intercom.io`, `*.intercomcdn.com` | In-app chat widget |
| **Analytics** | `cdn.usefathom.com` | Privacy-focused analytics |
| **Error Reporting** | `*.sentry.io` | Crash reports |
| **Telemetry** | `*.datadoghq.com` | Logging |

## Source of Truth

All domains are defined in [`domains.yaml`](domains.yaml) with documented reasons and discovery sources. Output files are generated from it:

```bash
python3 scripts/generate.py
```

This produces all formats in `dist/`.

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
