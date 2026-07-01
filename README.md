# Claude Network Doctor

Diagnose your local Claude and Claude Code network posture without exposing secrets.

Claude Network Doctor is a read-only diagnostic skill and Python script for checking whether your Claude access environment is consistent, proxy-covered, and low risk. It inspects local proxy/TUN/DNS state, Claude/Anthropic endpoint configuration, IPv6 behavior, Net.Coffee Claude parity, and browser-only fingerprint checks when requested.

It is designed for practical risk diagnosis, not Claude reverse engineering.

## What It Checks

- Anthropic and OpenAI-compatible endpoint variables, including `ANTHROPIC_BASE_URL`, `ANTHROPIC_FOUNDRY_BASE_URL`, `OPENAI_BASE_URL`, and `OPENAI_API_BASE`.
- Credential variable presence with secret values redacted.
- Third-party AI vendor and relay endpoint indicators.
- Claude Code telemetry-related variables, including `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `CLAUDE_CODE_ENABLE_TELEMETRY`, and OTEL exporter hints.
- Local proxy listeners and proxy environment variables.
- Linux route tables, policy routing, TUN interfaces, DNS resolvers, and IPv6 route state.
- Clash Verge / Mihomo hints such as TUN mode, `strict-route`, fake-ip DNS, DNS hijack, and IPv6 settings.
- Direct Cloudflare and Claude trace results.
- Net.Coffee Claude IP risk, geoip batch, service status, and optional DNS probe.
- Local Claude CLI / Claude Code installation metadata, using path and file stats only.

## Browser-Only Checks

The CLI script cannot measure browser-only fingerprint data. When used as a Cursor/Claude skill, the agent can perform a separate browser pass with Chrome DevTools MCP or Playwright on:

```text
https://ip.net.coffee/claude/
```

Browser-only output should be reported separately and can include:

- Claude AI exit IP, country/region, ASN/ISP, Trust Score, and IP risk panel.
- WebRTC UDP leak status.
- DNS leak panel.
- Browser timezone and UTC offset.
- Browser language list.
- Operating system and browser version.
- Cookie enabled state.
- WebGL renderer, Canvas fingerprint, and WebGL fingerprint.

## What It Does Not Claim

- It does not verify whether an API key is valid.
- It does not print tokens, API keys, Authorization headers, or proxy credentials.
- It does not reverse engineer Claude Code by default.
- It does not claim `/v1/messages` request-body content was observed unless you explicitly run traffic capture.
- It does not treat third-party endpoint detection as proof of telemetry exfiltration.
- It does not replace account, billing, payment, phone, email, or behavior-based risk analysis.

## Requirements

- Python 3.10 or newer.
- Linux is the primary target for local route/DNS/TUN checks.
- Optional local commands improve coverage: `ip`, `resolvectl`, `nmcli`, `ss`, `pgrep`, and `claude`.
- External checks require HTTPS access to Cloudflare, Claude/Anthropic, and Net.Coffee endpoints.

The script uses only the Python standard library.

## Quick Start

Run the full diagnostic:

```bash
python3 scripts/claude_network_doctor.py --json
```

Inspect only local configuration:

```bash
python3 scripts/claude_network_doctor.py --json --no-external
```

Skip the Net.Coffee DNS pixel probe:

```bash
python3 scripts/claude_network_doctor.py --json --no-netcoffee-dns
```

Set a shorter or longer HTTP timeout:

```bash
python3 scripts/claude_network_doctor.py --json --timeout 12
```

The output is JSON by default. The `--json` flag is kept for explicitness and compatibility.

## Reading The Output

The report contains:

- `env`: redacted endpoint, credential, telemetry, proxy, timezone, and locale information.
- `commands`: local command results such as route tables, DNS status, listening ports, proxy processes, and Claude version.
- `local`: inferred local posture, including TUN candidates, proxy listeners, DNS servers, Clash/Mihomo hints, config endpoints, and Claude installation metadata.
- `external`: Cloudflare, Claude, Anthropic, and proxy trace results when external checks are enabled.
- `netcoffee`: Net.Coffee IP risk, geoip, service status, and optional DNS probe results.
- `findings`: normalized `OK`, `WARN`, or `HIGH` findings with short explanations.

Recommended human-facing summary structure:

- `Verdict`: `OK`, `WARN`, or `HIGH`.
- `Evidence by source`: cite `route/DNS/TUN`, `Cloudflare trace`, `Claude trace`, `Net.Coffee`, `endpoint env`, `telemetry env`, `local Claude install`, and `browser page` only when applicable.
- `Inference`: explain what the evidence suggests about proxy coverage, IPv6, endpoint/request-body exposure, DNS consistency, and browser profile consistency.
- `Limits`: state what was not checked.

## Endpoint Risk Model

Endpoint hosts are classified as:

- `official`: known Anthropic/Claude official hosts.
- `known_relay`: host exactly matches or is under a known relay seed domain.
- `model_vendor`: host contains model/vendor terms such as `deepseek`, `moonshot`, `minimax`, `zhipu`, `bigmodel`, `baichuan`, `stepfun`, `dashscope`, `volces`, `qwen`, `doubao`, or `siliconflow`.
- `suspicious_relay_pattern`: host contains relay/aggregator terms such as `one-api`, `new-api`, `api2d`, `aiproxy`, `aihubmix`, `openrouter`, `anyrouter`, `zenmux`, `yunwu`, `dmxapi`, `claude-code-hub`, `claude-opus`, or `claudeide`.
- `unknown_third_party`: parseable host that is not official and did not match the seed lists.

Use this as a risk signal, not as a verdict of malicious behavior.

## Privacy And Safety

Claude Network Doctor is intentionally conservative:

- Credential-like variables are redacted.
- OTEL headers are redacted.
- URLs with embedded basic auth are redacted.
- Local config scanning reports host/category, not raw full configs.
- Browser fingerprint checks are opt-in and must be labeled as browser-sourced.

External checks are read-only HTTP requests, but they still contact third-party services. Use `--no-external` for local-only inspection.

## Cursor Skill Usage

This repository includes `SKILL.md`, so Cursor/Claude-style agents can use it as a skill.

Typical prompt:

```text
/claude-network-doctor 检查一下
```

Endpoint-focused prompt:

```text
帮我检查 Claude Code 有没有用了第三方中转 endpoint，别泄露 token
```

Browser-focused prompt:

```text
用浏览器检测 Claude AI 出口、WebRTC UDP 泄露、时区语言、Cookie、WebGL/Canvas 指纹一致性
```

## Repository Layout

```text
.
├── SKILL.md
├── README.md
├── GITHUB_COPY.md
├── agents/
│   └── openai.yaml
├── scripts/
│   └── claude_network_doctor.py
└── test-prompts.json
```

## Development

Run a local-only smoke test:

```bash
python3 -m py_compile scripts/claude_network_doctor.py
python3 scripts/claude_network_doctor.py --json --no-external
```

Test endpoint classification without changing your shell config:

```bash
ANTHROPIC_BASE_URL=https://api.example.com \
python3 scripts/claude_network_doctor.py --json --no-external
```

Test OTEL header redaction:

```bash
OTEL_EXPORTER_OTLP_HEADERS='Authorization=Bearer example' \
python3 scripts/claude_network_doctor.py --json --no-external
```

The output should show `OTEL_EXPORTER_OTLP_HEADERS` as redacted.

## License

TBD. Add a license before publishing if you want others to use, modify, or redistribute the project.
