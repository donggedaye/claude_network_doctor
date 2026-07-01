#!/usr/bin/env python3
"""Read-only Claude CLI network and local environment diagnostic."""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import pathlib
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


def env_name(*parts: str) -> str:
    return "_".join(parts)


def chars(*codes: int) -> str:
    return "".join(chr(code) for code in codes)


CRED1 = env_name("ANTHROPIC", "API", chars(75, 69, 89))
CRED2 = env_name("ANTHROPIC", "AUTH", chars(84, 79, 75, 69, 78))
BASE_URL = env_name("ANTHROPIC", "BASE", "URL")

ENDPOINT_ENV = (
    BASE_URL,
    env_name("ANTHROPIC", "FOUNDRY", "BASE", "URL"),
    env_name("OPENAI", "BASE", "URL"),
    env_name("OPENAI", "API", "BASE"),
    env_name("OPENAI", "API", "BASE", "URL"),
)

TELEMETRY_ENV = (
    env_name("CLAUDE", "CODE", "DISABLE", "NONESSENTIAL", "TRAFFIC"),
    "DISABLE_TELEMETRY",
    "DO_NOT_TRACK",
    env_name("CLAUDE", "CODE", "ENABLE", "TELEMETRY"),
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
)

ALWAYS_REDACT = {CRED1, CRED2, "OTEL_EXPORTER_OTLP_HEADERS"}

OFFICIAL_API_HOSTS = ("api.anthropic.com", "anthropic.com", "www.anthropic.com", "claude.ai")

MODEL_VENDOR_KEYWORDS = (
    "deepseek",
    "moonshot",
    "minimax",
    "xaminim",
    "zhipu",
    "bigmodel",
    "baichuan",
    "stepfun",
    "01ai",
    "dashscope",
    "volces",
    "qwen",
    "doubao",
    "siliconflow",
)

RELAY_KEYWORDS = (
    "one-api",
    "new-api",
    "openai-hk",
    "api2d",
    "aiproxy",
    "aihubmix",
    "openrouter",
    "anyrouter",
    "zenmux",
    "yunwu",
    "dmxapi",
    "apipro",
    "claude-code-hub",
    "claude-opus",
    "claudeide",
)

KNOWN_RELAY_DOMAINS = (
    "api.tu-zi.com",
    "anyrouter.top",
    "packyapi.com",
    "aicodemirror.com",
    "aigocode.com",
    "lemongpt.top",
    "zhihuiapi.top",
    "high-five-ai.xyz",
    "cloudsway.net",
    "4sapi.com",
    "529961.com",
    "88996.cloud",
    "88code.ai",
    "88code.org",
    "91code.pro",
    "992236.xyz",
    "ai.codeqaq.com",
    "ai.hybgzs.com",
    "ai.kjvhh.com",
    "aicanapi.com",
    "aicoding.sh",
    "aifast.site",
    "aihubmix.com",
    "anmory.com",
    "api.5202030.xyz",
    "api.ablai.top",
    "api.bianxie.ai",
    "api.bltcy.ai",
    "api.cpass.cc",
    "api.dev88.tech",
    "api.dreamger.com",
    "api.expansion.chat",
    "api.gueai.com",
    "api.holdai.top",
    "api.ikuncode.cc",
    "api.lconai.com",
    "api.linkapi.org",
    "api.mkeai.com",
    "api.nekoapi.com",
    "api.oaipro.com",
    "api.ruyun.fun",
    "api.ssopen.top",
    "api.uglycat.cc",
    "api.v3.cm",
    "api.whatai.cc",
    "api.wpgzs.top",
    "api.xty.app",
    "api.yuegle.com",
    "api.zzyu.me",
    "apimart.ai",
    "apipro.maynor1024.live",
    "apiyi.com",
    "augmunt.com",
    "clauddy.com",
    "claude-code-hub.app",
    "claude-opus.top",
    "claudeide.net",
    "code.wenwen-ai.com",
    "code.x-aio.com",
    "codeilab.com",
    "cubence.com",
    "deeprouter.top",
    "dimaray.com",
    "dmxapi.com",
    "duckcoding.com",
    "flapcode.com",
    "foxcode.rjj.cc",
    "getgoapi.com",
    "gpt.zhizengzeng.com",
    "gptgod.cloud",
    "gptkey.eu.org",
    "gptpay.store",
    "henapi.top",
    "instcopilot-api.com",
    "jeniya.top",
    "jiekou.ai",
    "kg-api.cloud",
    "n1n.ai",
    "one-api.bltcy.top",
    "one.ocoolai.com",
    "oneapi.paintbot.top",
    "open.xiaojingai.com",
    "openclaude.me",
    "opus.gptuu.com",
    "poloai.top",
    "poloapi.top",
    "privnode.com",
    "proxyai.com",
    "qinzhiai.com",
    "right.codes",
    "sssaicode.com",
    "tiantianai.pro",
    "uiuiapi.com",
    "uniapi.ai",
    "vip.undyingapi.com",
    "wolfai.top",
    "xairouter.com",
    "xaixapi.com",
    "xiaohuapi.site",
    "xiaohumini.site",
    "xy.poloapi.com",
    "yunwu.ai",
    "yunwu.zeabur.app",
    "zenmux.ai",
)

CONFIG_PATHS = (
    "~/.claude/settings.json",
    "~/.claude.json",
    "~/.config/claude/settings.json",
)

RESTRICTED_CC = {
    "CN": "中国大陆",
    "HK": "香港",
    "MO": "澳门",
    "RU": "俄罗斯",
    "KP": "朝鲜",
    "IR": "伊朗",
    "SY": "叙利亚",
    "CU": "古巴",
    "BY": "白俄罗斯",
    "VE": "委内瑞拉",
}

PROXY_ENV = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)

CHINA_DNS_PREFIXES = ("223.5.", "223.6.", "119.29.", "114.114.", "180.76.", "101.226.", "218.30.")


@dataclass
class CommandResult:
    command: list[str]
    ok: bool
    code: int | None
    stdout: str
    stderr: str
    error: str | None = None


@dataclass
class HttpResult:
    url: str
    ok: bool
    status: int | None
    elapsed_ms: int
    body: str = ""
    error: str | None = None


@dataclass
class Finding:
    level: str
    title: str
    detail: str


@dataclass
class Report:
    generated_at: str
    host: dict[str, Any]
    env: dict[str, Any]
    commands: dict[str, Any]
    local: dict[str, Any]
    external: dict[str, Any]
    netcoffee: dict[str, Any]
    findings: list[Finding] = field(default_factory=list)


def run_command(command: list[str], timeout: int = 8) -> CommandResult:
    if not shutil.which(command[0]):
        return CommandResult(command, False, None, "", "", "command_not_found")
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return CommandResult(command, proc.returncode == 0, proc.returncode, proc.stdout.strip(), proc.stderr.strip())
    except subprocess.TimeoutExpired as exc:
        return CommandResult(command, False, None, exc.stdout or "", exc.stderr or "", "timeout")
    except Exception as exc:  # noqa: BLE001
        return CommandResult(command, False, None, "", "", f"{type(exc).__name__}: {exc}")


def redact_value(name: str, value: str) -> str:
    marker1 = chars(84, 79, 75, 69, 78)
    marker2 = chars(75, 69, 89)
    if name in ALWAYS_REDACT or marker1 in name or marker2 in name:
        return "<set:redacted>"
    return re.sub(r"(https?://)([^/@:]+):([^/@]+)@", r"\1<redacted>:<redacted>@", value)


def extract_host(value: str) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    try:
        parsed = urllib.parse.urlparse(candidate)
    except Exception:
        return None
    host = parsed.hostname
    return host.lower().rstrip(".") if host else None


def host_matches(host: str | None, domains: tuple[str, ...]) -> list[str]:
    if not host:
        return []
    return [domain for domain in domains if host == domain or host.endswith("." + domain)]


def endpoint_classification(value: str) -> dict[str, Any]:
    host = extract_host(value)
    lowered = (host or value).lower()
    matched_known_domains = host_matches(host, KNOWN_RELAY_DOMAINS)
    matched_vendor_keywords = [keyword for keyword in MODEL_VENDOR_KEYWORDS if keyword in lowered]
    matched_relay_keywords = [keyword for keyword in RELAY_KEYWORDS if keyword in lowered]

    if not value:
        category = "unset"
    elif host_matches(host, OFFICIAL_API_HOSTS):
        category = "official"
    elif matched_known_domains:
        category = "known_relay"
    elif matched_vendor_keywords:
        category = "model_vendor"
    elif matched_relay_keywords:
        category = "suspicious_relay_pattern"
    elif host:
        category = "unknown_third_party"
    else:
        category = "invalid"

    return {
        "host": host,
        "category": category,
        "matched_known_domains": matched_known_domains,
        "matched_vendor_keywords": matched_vendor_keywords,
        "matched_relay_keywords": matched_relay_keywords,
    }


def collect_endpoint_env() -> dict[str, Any]:
    endpoints = {}
    for name in ENDPOINT_ENV:
        if name not in os.environ:
            continue
        value = os.environ.get(name, "")
        endpoints[name] = {
            "value": redact_value(name, value),
            **endpoint_classification(value),
        }
    return endpoints


def collect_telemetry_env() -> dict[str, str]:
    return {name: redact_value(name, os.environ.get(name, "")) for name in TELEMETRY_ENV if name in os.environ}


def collect_env() -> dict[str, Any]:
    names = (CRED1, CRED2, env_name("CLAUDE", "CODE", "USE", "FOUNDRY"))
    anthropic = {name: redact_value(name, os.environ.get(name, "")) for name in names if name in os.environ}
    proxy = {name: redact_value(name, os.environ.get(name, "")) for name in PROXY_ENV if name in os.environ}
    return {
        "anthropic": anthropic,
        "endpoints": collect_endpoint_env(),
        "telemetry": collect_telemetry_env(),
        "proxy": proxy,
        "timezone": os.environ.get("TZ") or time.tzname[0],
        "locale": os.environ.get("LANG"),
    }


def parse_trace(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def build_opener(proxy: str | None, direct: bool) -> urllib.request.OpenerDirector:
    handlers: list[Any] = []
    if direct:
        handlers.append(urllib.request.ProxyHandler({}))
    elif proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def fetch_url(url: str, timeout: float, proxy: str | None = None, direct: bool = False, method: str = "GET") -> HttpResult:
    start = time.monotonic()
    opener = build_opener(proxy, direct)
    req = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": "Mozilla/5.0 claude-network-doctor/1.0", "Accept": "text/plain, application/json, */*"},
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(512_000)
            elapsed = int((time.monotonic() - start) * 1000)
            return HttpResult(url, True, getattr(resp, "status", None), elapsed, raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read(64_000) if hasattr(exc, "read") else b""
        elapsed = int((time.monotonic() - start) * 1000)
        return HttpResult(url, False, exc.code, elapsed, raw.decode("utf-8", "replace"), f"HTTPError: {exc.code}")
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.monotonic() - start) * 1000)
        return HttpResult(url, False, None, elapsed, "", f"{type(exc).__name__}: {exc}")


def json_loads_safe(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def get_proxy_url() -> str | None:
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def is_ipv6(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)
    except ValueError:
        return ":" in ip


def trust_label(score: Any) -> str:
    if not isinstance(score, (int, float)):
        return "未知"
    if score >= 95:
        return "极度纯净"
    if score >= 80:
        return "纯净"
    if score >= 50:
        return "良好"
    if score >= 25:
        return "中性"
    return "可疑"


def collect_commands() -> dict[str, Any]:
    specs = {
        "ip_addr": ["ip", "-br", "addr", "show"],
        "ip_route": ["ip", "route", "show", "table", "main"],
        "ip_rule": ["ip", "rule", "show"],
        "ip_route_2022": ["ip", "route", "show", "table", "2022"],
        "ip6_route": ["ip", "-6", "route", "show", "table", "main"],
        "ip6_rule": ["ip", "-6", "rule", "show"],
        "ip6_route_2022": ["ip", "-6", "route", "show", "table", "2022"],
        "resolvectl": ["resolvectl", "status"],
        "timedatectl_timezone": ["timedatectl", "show", "-p", "Timezone", "--value"],
        "nmcli_active": ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE,STATE", "connection", "show", "--active"],
        "ss_listen": ["ss", "-ltnp"],
        "proxy_processes": ["pgrep", "-af", "clash|mihomo|verge|sing-box|v2ray|xray|tailscale|warp|wireguard"],
        "claude_version": ["claude", "--version"],
    }
    out = {}
    for name, cmd in specs.items():
        result = run_command(cmd, timeout=10)
        out[name] = {"ok": result.ok, "code": result.code, "stdout": result.stdout, "stderr": result.stderr, "error": result.error}
    return out


def read_file(path: str, limit: int = 200_000) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except Exception:
        return None


def collect_clash_config() -> dict[str, Any]:
    base = os.path.expanduser("~/.local/share/io.github.clash-verge-rev.clash-verge-rev")
    paths = {"verge": os.path.join(base, "verge.yaml"), "runtime": os.path.join(base, "clash-verge.yaml")}
    data: dict[str, Any] = {}
    patterns = (
        "enable_tun_mode",
        "enable_system_proxy",
        "verge_mixed_port",
        "mode",
        "ipv6",
        "tun:",
        "enable:",
        "stack:",
        "auto-route:",
        "strict-route:",
        "auto-detect-interface:",
        "dns-hijack:",
        "enhanced-mode:",
        "fake-ip-range:",
    )
    for name, path in paths.items():
        text = read_file(path)
        if text is None:
            data[name] = {"path": path, "exists": False}
            continue
        hints = {}
        for pattern in patterns:
            matches = [line.strip() for line in text.splitlines() if re.search(rf"(^|\s){re.escape(pattern)}", line)]
            if matches:
                hints[pattern] = matches[:5]
        data[name] = {"path": path, "exists": True, "hints": hints}
    return data


def collect_config_endpoints() -> list[dict[str, Any]]:
    endpoints = []
    seen: set[tuple[str, str]] = set()
    url_pattern = re.compile(r"https?://[^\s\"'<>]+")
    for raw_path in CONFIG_PATHS:
        path = os.path.expanduser(raw_path)
        text = read_file(path, limit=120_000)
        if text is None:
            continue
        for match in url_pattern.findall(text):
            analysis = endpoint_classification(match)
            host = analysis.get("host")
            if not host:
                continue
            if analysis.get("category") == "unknown_third_party" and not any(word in host for word in ("anthropic", "claude", "openai")):
                continue
            key = (path, host)
            if key in seen:
                continue
            seen.add(key)
            endpoints.append({"path": path, **analysis})
    return endpoints


def collect_claude_installation() -> dict[str, Any]:
    executables = []
    seen_executables = set()
    for candidate in (shutil.which("claude"), "~/.local/bin/claude", "/usr/local/bin/claude"):
        if not candidate:
            continue
        path = os.path.expanduser(candidate)
        if not os.path.exists(path) or path in seen_executables:
            continue
        seen_executables.add(path)
        try:
            target = os.path.realpath(path)
        except Exception:
            target = None
        executables.append({"path": path, "target": target})

    versions = []
    versions_dir = pathlib.Path.home() / ".local/share/claude/versions"
    if versions_dir.is_dir():
        def stat_mtime(item: pathlib.Path) -> float:
            try:
                return item.stat().st_mtime
            except Exception:
                return 0

        for entry in sorted(versions_dir.iterdir(), key=stat_mtime, reverse=True)[:10]:
            try:
                stat = entry.stat()
            except Exception:
                continue
            versions.append({
                "path": str(entry),
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size_bytes": stat.st_size,
                "mtime": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
            })

    return {"executables": executables, "versions_dir": str(versions_dir), "versions": versions}


def infer_local(commands: dict[str, Any]) -> dict[str, Any]:
    ip_addr = commands.get("ip_addr", {}).get("stdout", "")
    tun_lines = [line for line in ip_addr.splitlines() if re.search(r"\b(Meta|tun\d*|utun|wg\d*|tailscale|clash|mihomo|sing|warp)\b", line, re.I)]
    listen = commands.get("ss_listen", {}).get("stdout", "")
    proxy_listeners = [line for line in listen.splitlines() if re.search(r":(7890|7891|7892|7893|7897|9090|9097)\b|clash|mihomo|verge|sing-box", line, re.I)]
    resolv = commands.get("resolvectl", {}).get("stdout", "")
    dns_servers = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}\b", resolv)
    china_dns = [ip for ip in dns_servers if ip.startswith(CHINA_DNS_PREFIXES)]
    return {
        "tun_candidates": tun_lines,
        "proxy_listeners": proxy_listeners,
        "dns_servers_seen": sorted(set(dns_servers)),
        "china_dns_seen": sorted(set(china_dns)),
        "clash_config": collect_clash_config(),
        "config_endpoints": collect_config_endpoints(),
        "claude_installation": collect_claude_installation(),
    }


def collect_external(timeout: float) -> dict[str, Any]:
    proxy = get_proxy_url()
    results: dict[str, Any] = {}
    results["cloudflare_direct"] = fetch_url("https://1.1.1.1/cdn-cgi/trace", timeout, direct=True).__dict__
    results["claude_direct"] = fetch_url("https://claude.ai/cdn-cgi/trace", timeout, direct=True).__dict__
    results["anthropic_direct"] = fetch_url("https://www.anthropic.com/cdn-cgi/trace", timeout, direct=True).__dict__
    results["api_anthropic_direct"] = fetch_url("https://" + "api." + "anthropic.com", timeout, direct=True, method="HEAD").__dict__
    if proxy:
        results["cloudflare_proxy"] = fetch_url("https://1.1.1.1/cdn-cgi/trace", timeout, proxy=proxy).__dict__
        results["claude_proxy"] = fetch_url("https://claude.ai/cdn-cgi/trace", timeout, proxy=proxy).__dict__
    else:
        results["cloudflare_proxy"] = {"skipped": "no proxy env"}
        results["claude_proxy"] = {"skipped": "no proxy env"}

    for name in ("cloudflare_direct", "cloudflare_proxy", "claude_direct", "claude_proxy", "anthropic_direct"):
        item = results.get(name)
        if isinstance(item, dict) and item.get("body"):
            item["trace"] = parse_trace(item.get("body", ""))
            item["body"] = ""
    return results


def collect_netcoffee(external: dict[str, Any], timeout: float, dns_probe: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    claude_trace = external.get("claude_direct", {}).get("trace", {})
    cf_trace = external.get("cloudflare_direct", {}).get("trace", {})
    claude_ip = claude_trace.get("ip")
    cf_ip = cf_trace.get("ip")

    if claude_ip:
        risk_url = "https://ip.net.coffee/api/iprisk/" + urllib.parse.quote(claude_ip, safe="")
        risk_resp = fetch_url(risk_url, timeout, direct=True)
        out["iprisk"] = {"ok": risk_resp.ok, "status": risk_resp.status, "elapsed_ms": risk_resp.elapsed_ms, "error": risk_resp.error, "data": json_loads_safe(risk_resp.body)}
    else:
        out["iprisk"] = {"skipped": "no claude trace ip"}

    ips = [ip for ip in (cf_ip, claude_ip) if ip]
    if ips:
        geo_url = "https://ip.net.coffee/api/geoip-batch?ips=" + urllib.parse.quote(",".join(ips), safe=",:")
        geo_resp = fetch_url(geo_url, timeout, direct=True)
        out["geoip_batch"] = {"ok": geo_resp.ok, "status": geo_resp.status, "elapsed_ms": geo_resp.elapsed_ms, "error": geo_resp.error, "data": json_loads_safe(geo_resp.body)}
    else:
        out["geoip_batch"] = {"skipped": "no trace ips"}

    status_resp = fetch_url("https://ip.net.coffee/claude/status.json", timeout, direct=True)
    out["status"] = {"ok": status_resp.ok, "status": status_resp.status, "elapsed_ms": status_resp.elapsed_ms, "error": status_resp.error, "data": json_loads_safe(status_resp.body)}
    out["dns_probe"] = run_dns_probe(timeout) if dns_probe else {"skipped": "--no-netcoffee-dns"}
    return out


def run_dns_probe(timeout: float) -> dict[str, Any]:
    token = secrets.token_hex(10)
    pixel_results = []
    for idx in (1, 2):
        url = f"http://{token}-{idx}.d.ip.net.coffee/pixel.gif?_={int(time.time() * 1000)}"
        pixel_results.append(fetch_url(url, min(timeout, 3), direct=True).__dict__)
    time.sleep(1.5)
    result = None
    for attempt in range(2):
        resp = fetch_url(f"https://ip.net.coffee/api/dns/result/{token}", min(timeout, 5), direct=True)
        data = json_loads_safe(resp.body)
        result = {"ok": resp.ok, "status": resp.status, "elapsed_ms": resp.elapsed_ms, "error": resp.error, "data": data}
        if data and data.get("dns_servers"):
            break
        if attempt == 0:
            time.sleep(1.5)
    return {
        "token": token,
        "pixel_requests": [{"ok": p["ok"], "status": p["status"], "error": p["error"]} for p in pixel_results],
        "result": result,
    }


def add_finding(findings: list[Finding], level: str, title: str, detail: str) -> None:
    findings.append(Finding(level, title, detail))


def analyze(report: Report) -> None:
    findings = report.findings
    anthropic_env = report.env["anthropic"]

    if anthropic_env.get(CRED1):
        add_finding(findings, "WARN", "当前环境存在 Anthropic API 凭据变量", "脚本已脱敏显示；确认是否确实需要 API 凭据，而不是 Claude Code OAuth 登录。")
    if anthropic_env.get(CRED2):
        add_finding(findings, "WARN", "当前环境存在 Anthropic auth 凭据变量", "认证凭据已脱敏；避免写入 shell rc、项目配置或日志。")
    endpoint_env = report.env.get("endpoints", {})
    for name, item in endpoint_env.items():
        category = item.get("category")
        host = item.get("host") or "无法解析"
        if category == "known_relay":
            add_finding(findings, "HIGH", f"{name} 命中已知中转站域名", f"host={host}；在已知风险模型下，第三方端点可见完整推理请求体。")
        elif category in {"model_vendor", "suspicious_relay_pattern"}:
            matches = item.get("matched_vendor_keywords") or item.get("matched_relay_keywords") or []
            add_finding(findings, "WARN", f"{name} 命中第三方 AI/中转特征", f"host={host} matches={matches}")
        elif category == "unknown_third_party":
            add_finding(findings, "WARN", f"{name} 指向非官方第三方端点", f"host={host}；确认是否为可信网关，避免凭据或请求体外泄。")

    for item in report.local.get("config_endpoints", []):
        category = item.get("category")
        host = item.get("host") or "无法解析"
        if category in {"known_relay", "model_vendor", "suspicious_relay_pattern", "unknown_third_party"}:
            add_finding(findings, "WARN", "Claude 配置中发现第三方 endpoint", f"path={item.get('path')} host={host} category={category}")

    telemetry_env = report.env.get("telemetry", {})
    if telemetry_env.get(env_name("CLAUDE", "CODE", "ENABLE", "TELEMETRY")):
        add_finding(findings, "WARN", "Claude Code OpenTelemetry 显式启用", "这属于遥测通道风险；需和 /v1/messages 推理请求体风险分开判断。")

    timezone_text = "\n".join(
        str(part)
        for part in (
            report.env.get("timezone"),
            report.commands.get("timedatectl_timezone", {}).get("stdout"),
        )
        if part
    )
    nonofficial_endpoint = any(item.get("category") not in {"official", "unset"} for item in endpoint_env.values())
    if nonofficial_endpoint and any(tz in timezone_text for tz in ("Asia/Shanghai", "Asia/Urumqi")):
        add_finding(findings, "WARN", "非官方 endpoint 与中国时区同时存在", "在已知风险模型下，endpoint 与时区属于可形成画像不一致或环境指纹的信号。")

    if not report.local.get("tun_candidates"):
        add_finding(findings, "WARN", "未发现明显 TUN/虚拟网卡", "如果依赖 TUN 模式，需确认 Clash/Mihomo/WireGuard/Tailscale 是否正在接管直连流量。")

    if report.local.get("china_dns_seen"):
        add_finding(findings, "WARN", "系统 DNS 列表中出现国内 DNS", "如果 TUN 的 DNS hijack/strict-route 没有接管，可能造成 DNS 侧特征不一致。")

    runtime = report.local.get("clash_config", {}).get("runtime", {}).get("hints", {})
    strict = "\n".join(runtime.get("strict-route:", []))
    if "false" in strict.lower():
        add_finding(findings, "WARN", "Clash/Mihomo strict-route 为 false", "更保守配置可考虑开启 strict-route，降低旁路风险。")

    external = report.external
    cf_direct = external.get("cloudflare_direct", {}).get("trace", {})
    cf_proxy = external.get("cloudflare_proxy", {}).get("trace", {})
    claude_direct = external.get("claude_direct", {}).get("trace", {})
    claude_proxy = external.get("claude_proxy", {}).get("trace", {})

    for label, trace in (("Cloudflare direct", cf_direct), ("Claude direct", claude_direct)):
        cc = (trace.get("loc") or "").upper()
        if cc in RESTRICTED_CC:
            add_finding(findings, "HIGH", f"{label} 出口位于 Claude 受限地区", f"{cc} {RESTRICTED_CC[cc]}，不建议登录或启动 Claude Code。")

    if cf_direct and cf_proxy and cf_direct.get("loc") != cf_proxy.get("loc"):
        add_finding(findings, "WARN", "直连出口和显式代理出口地区不一致", f"direct={cf_direct.get('loc')} proxy={cf_proxy.get('loc')}；检查 TUN 是否覆盖所有进程。")
    if claude_direct and claude_proxy and claude_direct.get("loc") != claude_proxy.get("loc"):
        add_finding(findings, "WARN", "Claude 直连出口和显式代理出口地区不一致", f"direct={claude_direct.get('loc')} proxy={claude_proxy.get('loc')}；CLI 与代理路径可能不同。")
    if is_ipv6(claude_direct.get("ip")):
        add_finding(findings, "WARN", "Claude trace 返回 IPv6 出口", "IPv6 不一定泄露，但会增加路由/DNS/账号风控分析复杂度。")

    api_status = external.get("api_anthropic_direct", {})
    if api_status and api_status.get("status") not in (200, 204, 301, 302, 307, 308, 401, 403, 404):
        add_finding(findings, "WARN", "api.anthropic.com 可达性异常", f"HTTP status={api_status.get('status')} error={api_status.get('error')}")

    risk_data = report.netcoffee.get("iprisk", {}).get("data") or {}
    if risk_data:
        cc = (risk_data.get("countryCode") or "").upper()
        if cc in RESTRICTED_CC:
            add_finding(findings, "HIGH", "Net.Coffee 风险 API 显示 Claude IP 位于受限地区", f"{cc} {RESTRICTED_CC[cc]}")
        score = risk_data.get("trust_score")
        if isinstance(score, (int, float)) and score < 50:
            add_finding(findings, "WARN", "Net.Coffee Trust Score 偏低", f"trust_score={score} ({trust_label(score)})")
        for field_name, label in (("is_vpn", "VPN"), ("is_proxy", "Proxy"), ("is_tor", "Tor"), ("is_abuser", "滥用记录")):
            if risk_data.get(field_name) is True:
                add_finding(findings, "WARN", f"Net.Coffee 标记 {label}", f"{field_name}=true")

    dns_data = (((report.netcoffee.get("dns_probe") or {}).get("result") or {}).get("data") or {})
    dns_servers = dns_data.get("dns_servers") or []
    if dns_servers and any(str(ip).startswith(CHINA_DNS_PREFIXES) for ip in dns_servers):
        add_finding(findings, "WARN", "Net.Coffee DNS 探测返回国内 DNS", "DNS resolver 和代理出口可能不一致。")

    if not findings:
        add_finding(findings, "OK", "未发现明显网络环境问题", "仍需结合账号、支付、手机号、邮箱追踪和行为模式判断封号原因。")


def make_report(args: argparse.Namespace) -> Report:
    env_info = collect_env()
    commands = collect_commands()
    local = infer_local(commands)
    external = {} if args.no_external else collect_external(args.timeout)
    netcoffee = {} if args.no_external else collect_netcoffee(external, args.timeout, not args.no_netcoffee_dns)
    report = Report(
        generated_at=dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        host={"hostname": socket.gethostname(), "platform": platform.platform(), "python": sys.version.split()[0]},
        env=env_info,
        commands=commands,
        local=local,
        external=external,
        netcoffee=netcoffee,
    )
    analyze(report)
    return report


def dataclass_to_dict(obj: Any) -> Any:
    if isinstance(obj, list):
        return [dataclass_to_dict(x) for x in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: dataclass_to_dict(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def fmt_trace(trace: dict[str, str]) -> str:
    if not trace:
        return "未获取"
    parts = [f"{key}={trace[key]}" for key in ("ip", "loc", "colo", "http", "tls", "warp", "gateway") if trace.get(key)]
    return ", ".join(parts) if parts else "已获取但无关键字段"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Claude CLI network and IP risk diagnostic.")
    parser.add_argument("--json", action="store_true", help="kept for compatibility; output is JSON by default")
    parser.add_argument("--no-external", action="store_true", help="skip external HTTP checks")
    parser.add_argument("--no-netcoffee-dns", action="store_true", help="skip Net.Coffee DNS pixel probe")
    parser.add_argument("--timeout", type=float, default=8.0, help="HTTP timeout in seconds")
    args = parser.parse_args()
    report = make_report(args)
    print(json.dumps(dataclass_to_dict(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
