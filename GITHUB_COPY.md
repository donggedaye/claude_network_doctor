# GitHub Copy

Use these snippets when publishing Claude Network Doctor.

## Repository Description

Read-only Claude/Claude Code network posture diagnostic for proxy, TUN, DNS, IPv6, endpoint, Net.Coffee, and browser fingerprint consistency checks.

## Short Tagline

Diagnose Claude network risk without leaking secrets.

## GitHub About

Description:

```text
Read-only Claude/Claude Code network posture diagnostic for proxy, TUN, DNS, IPv6, custom endpoint, Net.Coffee, and browser fingerprint consistency checks.
```

Topics:

```text
claude-code, claude, anthropic, network-diagnostics, proxy, dns-leak, webrtc-leak, ipv6, clash, mihomo, netcoffee, cursor-skill
```

Website:

```text
TBD
```

## Launch Post

I built Claude Network Doctor: a read-only diagnostic tool for checking whether your local Claude / Claude Code access environment is consistent and low risk.

It checks:

- Proxy, TUN, DNS, IPv6, and route state.
- Anthropic and OpenAI-compatible base URL configuration.
- Third-party AI vendor and relay endpoint indicators.
- Claude Code telemetry-related variables.
- Claude / Cloudflare trace results.
- Net.Coffee Claude IP risk and parity data.
- Browser-only WebRTC, timezone/language, Cookie, WebGL, and Canvas checks when run through an agent browser.

It is designed to separate evidence from inference:

- Network evidence is not browser fingerprint evidence.
- Endpoint risk is not the same as confirmed telemetry.
- Third-party relay detection is a risk signal, not an accusation.
- Secrets are redacted by default.

Repo: TBD

## Chinese Launch Post

我整理了一个 Claude Network Doctor，用来检查本机 Claude / Claude Code 的网络风险画像。

它会做只读诊断：

- 代理、TUN、DNS、IPv6、路由状态。
- `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` 等自定义 endpoint。
- 第三方 AI 厂商和中转站特征。
- Claude Code 遥测相关变量。
- Claude / Cloudflare trace。
- Net.Coffee 的 Claude 出口 IP 风险和一致性。
- 需要浏览器时，再单独检查 WebRTC、时区语言、Cookie、WebGL、Canvas 指纹。

重点是边界清楚：

- 网络出口证据不等于浏览器指纹证据。
- endpoint 风险不等于确认遥测上报。
- 命中中转特征只是风险信号，不是恶意结论。
- token、key、Authorization header 默认脱敏。

适合排查“Claude 到底是不是走了我以为的线路”、“DNS/IPv6 有没有旁路”、“第三方 endpoint 有没有暴露请求体风险”这类问题。

Repo: TBD

## README Hero Options

Option A:

```text
Diagnose your local Claude and Claude Code network posture without exposing secrets.
```

Option B:

```text
A read-only doctor for Claude proxy, DNS, IPv6, endpoint, and browser-profile consistency.
```

Option C:

```text
Know what Claude sees: exit IP, DNS, TUN, endpoint, telemetry flags, and browser fingerprint boundaries.
```

## Release Notes

Initial public version:

- Added read-only Python diagnostic script.
- Added endpoint host classification for official, known relay, model vendor, relay pattern, and unknown third-party hosts.
- Added redaction for credential variables and OTEL headers.
- Added local proxy, TUN, route, DNS, Clash/Mihomo, and Claude install metadata checks.
- Added Cloudflare, Claude, Anthropic, and Net.Coffee external checks.
- Added browser-only workflow guidance for WebRTC, DNS leak panel, timezone/language, Cookie, WebGL, Canvas, and Claude AI Trust Score panels.
- Added Cursor/Claude `SKILL.md` workflow.

## Caveats To Mention

- Linux is the primary target for route, DNS, and TUN inspection.
- Browser fingerprint checks require an agent browser tool such as Chrome DevTools MCP or Playwright.
- The script does not validate API keys.
- The script does not reverse engineer Claude Code.
- The script does not observe `/v1/messages` request bodies unless the user explicitly performs traffic capture outside the default flow.
- Add a license before public release.
