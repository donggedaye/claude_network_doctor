---
name: claude-network-doctor
description: Diagnose local Claude CLI/Claude Code network posture. Use when the user asks to run a Claude network doctor check, inspect proxy/TUN/DNS/IPv6 leaks, inspect Anthropic credential presence or custom API endpoint/base URL risk, compare Claude exit IP or Net.Coffee results, or check browser-only WebRTC, timezone/language, OS/browser, cookie, WebGL/Canvas fingerprint consistency for Claude access.
---

# Claude Network Doctor

Use this skill to produce a grounded, redacted diagnosis of a user's local Claude network environment. Prefer the bundled script first, then add browser-only checks when the user asks about WebRTC, canvas/WebGL fingerprints, browser language/timezone, cookie state, device information, or the exact `https://ip.net.coffee/claude/` page result.

Do not reverse engineer Claude Code by default. Use known public/local-analysis findings only as a risk model, then inspect the user's current environment: endpoint host, timezone, locale, DNS, proxy/TUN, telemetry variables, network egress, browser fingerprint, and consistency between these signals.

## Quick Start

Run:

```bash
python3 /home/dong/.codex/skills/claude-network-doctor/scripts/claude_network_doctor.py
```

The script prints JSON by default. Read the JSON, then produce a concise user-facing diagnosis in Chinese with secrets redacted.

Use this form when you want to emphasize machine-readable output:

```bash
python3 /home/dong/.codex/skills/claude-network-doctor/scripts/claude_network_doctor.py --json
```

`--json` is kept as an explicit/compatibility flag; default output is also JSON. Use `--no-external` when only local config should be inspected. Use `--no-netcoffee-dns` to skip the Net.Coffee DNS resolver probe.

## Workflow

1. Announce that the diagnostic makes external read-only requests unless `--no-external` is used.
2. Run the script. If sandboxing blocks netlink, DNS, or localhost proxy access, report the blocker and use approved read-only escalation only if available.
3. Summarize the verdict first: `OK`, `WARN`, or `HIGH`.
4. Separate direct evidence from inference:
   - Evidence: commands, trace results, DNS resolvers, route tables, endpoint host classifications, telemetry variable presence, Net.Coffee API fields, browser page fields if captured.
   - Inference: whether TUN is catching direct traffic, whether IPv6 can bypass, whether endpoint/timezone/DNS/browser signals are consistent, whether Claude risk is likely network-related.
5. Never print secret values. Report only presence of credential variables and endpoint hosts/categories. Do not print tokens, full URLs with credentials, or raw proxy configs.
6. Keep runtime request-body claims separate. Do not claim `/v1/messages` content was observed unless the user explicitly opted into traffic capture and it actually ran.
7. Browser-only results must state the collection tool and page source, for example Chrome DevTools MCP on `https://ip.net.coffee/claude/`.

## Report Template

For real diagnostics, do not stop at a plan. After running the bundled script, base the user-facing answer on its JSON and use this compact structure:

- `Verdict`: `OK`, `WARN`, or `HIGH`, with one sentence explaining the main reason.
- `Evidence by source`: cite concrete source labels such as `route/DNS/TUN`, `Cloudflare trace`, `Claude trace`, `Net.Coffee`, `endpoint env`, `telemetry env`, `local Claude install`, and `browser page` when browser checks were actually run.
- `Inference`: explain what the evidence suggests about proxy coverage, IPv6, endpoint/request-body exposure, DNS consistency, and browser profile consistency.
- `Limits`: state what was not checked, such as WebRTC/Canvas/WebGL when no browser tool was used, or `/v1/messages` body when traffic capture was not explicitly requested.

## What The Script Checks

- Active Anthropic credential and endpoint-related environment variables, with secret values redacted.
- Custom API endpoint variables such as `ANTHROPIC_BASE_URL`, `ANTHROPIC_FOUNDRY_BASE_URL`, `OPENAI_BASE_URL`, and `OPENAI_API_BASE`; only host/category is interpreted.
- Third-party AI vendor and relay indicators, including known relay seed domains, model-vendor keywords, and relay-pattern keywords. Treat matches as risk signals, not proof of abuse.
- Claude Code telemetry-related variables: `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `CLAUDE_CODE_ENABLE_TELEMETRY`, and OTEL exporter hints.
- Common Claude CLI/Claude Code installation paths and local version directory metadata. This is path/stat inspection only, not binary reverse engineering.
- Proxy variables and localhost proxy listener hints.
- `ip addr`, IPv4/IPv6 routes, policy routing, and likely TUN interfaces such as `Meta`, `tun0`, `utun`, `wg`, `tailscale`, `clash`, and `mihomo`.
- `resolvectl` DNS state, including local physical-link DNS and TUN DNS.
- Clash Verge / Mihomo config hints: TUN enabled, mixed port, `strict-route`, DNS mode, DNS hijack, and IPv6 settings.
- Direct no-proxy Cloudflare trace and proxied Cloudflare trace.
- Direct no-proxy Claude trace (`https://claude.ai/cdn-cgi/trace`) and Anthropic availability checks.
- Net.Coffee Claude parity:
  - `https://ip.net.coffee/api/iprisk/{claude_ip}`
  - `https://ip.net.coffee/api/geoip-batch`
  - `https://ip.net.coffee/claude/status.json`
  - optional DNS probe using `*.d.ip.net.coffee/pixel.gif` plus `/api/dns/result/{token}`

## Endpoint Risk Interpretation

Classify endpoint hosts with this priority:

- `official`: script-defined Anthropic/Claude official hosts, including `api.anthropic.com`, `anthropic.com`, `www.anthropic.com`, and `claude.ai`.
- `known_relay`: host exactly matches or is under a known relay seed domain.
- `model_vendor`: host contains model/vendor terms such as `deepseek`, `moonshot`, `minimax`, `zhipu`, `bigmodel`, `baichuan`, `stepfun`, `dashscope`, `volces`, `qwen`, `doubao`, or `siliconflow`.
- `suspicious_relay_pattern`: host contains relay/aggregator terms such as `one-api`, `new-api`, `api2d`, `aiproxy`, `aihubmix`, `openrouter`, `anyrouter`, `zenmux`, `yunwu`, `dmxapi`, `claude-code-hub`, `claude-opus`, or `claudeide`.
- `unknown_third_party`: parseable host that is not official and did not match the seed lists.

Use cautious wording: a match means the endpoint has third-party vendor/relay characteristics. It does not prove telemetry exfiltration, account action, or malicious behavior.

When a non-official endpoint is present, explicitly distinguish:

- Inference/request path: the endpoint or relay can see the API request body it receives.
- Telemetry path: `tengu_*`, Datadog, and OTEL are separate channels and must not be conflated with `/v1/messages`.
- Local environment signals: China timezone, domestic DNS, IPv6, browser language, and exit IP consistency affect risk interpretation.

## Net.Coffee Interpretation

Use these page-derived rules:

- Restricted Claude regions: `CN`, `HK`, `MO`, `RU`, `KP`, `IR`, `SY`, `CU`, `BY`, `VE`.
- Trust score labels:
  - `>=95`: 极度纯净
  - `>=80`: 纯净
  - `>=50`: 良好
  - `>=25`: 中性
  - `<25`: 可疑
- Treat a Claude出口IP in a restricted region as high risk regardless of trust score.
- Warn when Claude trace returns IPv6. IPv6 may be supported by the route table, but it adds account-risk and leak-analysis complexity.
- Warn when direct no-proxy trace and explicit proxy trace disagree in country/IP unexpectedly; this often means CLI/browser traffic is not using the same path.

## Browser-Only Follow-Up

The CLI script cannot faithfully measure WebRTC, canvas, WebGL, browser language, browser timezone, device information, extension behavior, cookie state, or browser-only Claude AI Trust Score panels. If the user asks for those:

1. Use Chrome DevTools MCP if available; otherwise use Playwright as fallback.
2. Open `https://ip.net.coffee/claude/`.
3. Capture the page snapshot and network requests.
4. Report browser-only fields separately from CLI findings:
   - Claude AI exit IP, country/region, ASN/ISP, Trust Score, and IP risk panel
   - WebRTC UDP leak, including local/private IP exposure or non-proxy public IP exposure
   - DNS leak panel
   - browser timezone and UTC offset, for example `Asia/Shanghai (UTC+8)`
   - browser language list, for example `zh-CN, zh, zh-TW, en`
   - operating system and browser version, for example `Linux / Chrome 149.0.0.0`
   - cookie enabled/disabled state
   - WebGL renderer, Canvas fingerprint, and WebGL fingerprint

Use this browser consistency model:

- `OK`: Claude exit IP, DNS, browser timezone, and language are broadly consistent; WebRTC does not expose a non-proxy route.
- `WARN`: exit IP is in an allowed region but browser timezone/language/device signals point elsewhere, or IPv6 adds ambiguity.
- `HIGH`: WebRTC exposes a real non-proxy public route, Claude exit IP is in a restricted region, or DNS/exit/browser signals are severely inconsistent.

Do not claim the CLI script verified browser fingerprint items.
