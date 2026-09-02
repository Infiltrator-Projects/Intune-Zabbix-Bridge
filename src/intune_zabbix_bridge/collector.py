#!/usr/bin/env python3
"""Microsoft Intune -> Zabbix reboot telemetry bridge.

The bridge is deliberately read-only against Microsoft Graph. It reads the
output of an existing Intune Remediation / deviceHealthScript that emits:

    DEVICE=<name>;LASTBOOT=<ISO-8601>;UPTIME_HOURS=<number>

It then publishes fleet-level metrics to a single Zabbix host using
zabbix_sender. No connection to managed laptops is required.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

LOG = logging.getLogger("intune-zabbix-bridge")

GRAPH_ROOT = "https://graph.microsoft.com/beta"
TOKEN_SCOPE = "https://graph.microsoft.com/.default"
TELEMETRY_RE = re.compile(
    r"(?:^|;)DEVICE=(?P<device>[^;]+);LASTBOOT=(?P<lastboot>[^;]+);"
    r"UPTIME_HOURS=(?P<uptime>[0-9.]+)(?:;|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Config:
    tenant_id: str
    client_id: str
    client_secret: str
    telemetry_script_id: str
    zabbix_server: str
    zabbix_port: int
    zabbix_host: str
    zabbix_sender: str
    timezone_name: str
    max_telemetry_age_hours: float
    top_n: int
    http_timeout: float
    http_retries: int

    @classmethod
    def from_env(cls) -> "Config":
        required = {
            "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID", "").strip(),
            "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", "").strip(),
            "AZURE_CLIENT_SECRET": os.getenv("AZURE_CLIENT_SECRET", "").strip(),
            "INTUNE_TELEMETRY_SCRIPT_ID": os.getenv(
                "INTUNE_TELEMETRY_SCRIPT_ID", ""
            ).strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required environment variable(s): " + ", ".join(missing)
            )

        return cls(
            tenant_id=required["AZURE_TENANT_ID"],
            client_id=required["AZURE_CLIENT_ID"],
            client_secret=required["AZURE_CLIENT_SECRET"],
            telemetry_script_id=required["INTUNE_TELEMETRY_SCRIPT_ID"],
            zabbix_server=os.getenv("ZABBIX_SERVER", "127.0.0.1").strip(),
            zabbix_port=int(os.getenv("ZABBIX_PORT", "10051")),
            zabbix_host=os.getenv(
                "ZABBIX_HOST", "Microsoft Intune - Windows Fleet"
            ).strip(),
            zabbix_sender=os.getenv("ZABBIX_SENDER", "zabbix_sender").strip(),
            timezone_name=os.getenv("TIMEZONE", "Australia/Melbourne").strip(),
            max_telemetry_age_hours=float(
                os.getenv("MAX_TELEMETRY_AGE_HOURS", "48")
            ),
            top_n=max(1, int(os.getenv("TOP_N", "10"))),
            http_timeout=float(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
            http_retries=max(0, int(os.getenv("HTTP_RETRIES", "4"))),
        )


@dataclass(frozen=True)
class DeviceTelemetry:
    computer_name: str
    user: str
    last_restart: datetime
    telemetry_collected: datetime
    uptime_days: float
    telemetry_age_hours: float
    fresh: bool

    def as_json(self, local_tz: ZoneInfo) -> dict[str, Any]:
        return {
            "computer_name": self.computer_name,
            "user": self.user,
            "last_restart": self.last_restart.astimezone(local_tz).isoformat(),
            "telemetry_collected": self.telemetry_collected.astimezone(
                local_tz
            ).isoformat(),
            "uptime_days": round(self.uptime_days, 3),
            "telemetry_age_hours": round(self.telemetry_age_hours, 2),
            "fresh": self.fresh,
        }


def parse_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _request_json(
    request: urllib.request.Request,
    *,
    timeout: float,
    retries: int,
) -> dict[str, Any]:
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt >= retries:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"HTTP {exc.code} calling {request.full_url}: {body}"
                ) from exc
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2**attempt
            except ValueError:
                delay = 2**attempt
            delay = min(max(delay, 1.0), 30.0)
            LOG.warning("Graph returned HTTP %s; retrying in %.1fs", exc.code, delay)
            time.sleep(delay)
        except urllib.error.URLError as exc:
            if attempt >= retries:
                raise RuntimeError(
                    f"Network error calling {request.full_url}: {exc}"
                ) from exc
            delay = min(2**attempt, 15)
            LOG.warning("Network error; retrying in %ss: %s", delay, exc)
            time.sleep(delay)
    raise RuntimeError("HTTP retry loop terminated unexpectedly")


def get_access_token(config: Config) -> str:
    token_url = (
        f"https://login.microsoftonline.com/{urllib.parse.quote(config.tenant_id)}/"
        "oauth2/v2.0/token"
    )
    form = urllib.parse.urlencode(
        {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "grant_type": "client_credentials",
            "scope": TOKEN_SCOPE,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        token_url,
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    payload = _request_json(
        request, timeout=config.http_timeout, retries=config.http_retries
    )
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Microsoft identity platform did not return an access token")
    return str(token)


def graph_get(config: Config, token: str, url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    return _request_json(
        request, timeout=config.http_timeout, retries=config.http_retries
    )


def fetch_run_states(config: Config, token: str) -> list[dict[str, Any]]:
    script_id = urllib.parse.quote(config.telemetry_script_id, safe="")
    url = (
        f"{GRAPH_ROOT}/deviceManagement/deviceHealthScripts/{script_id}/"
        "deviceRunStates?$top=999&$expand=managedDevice"
    )
    states: list[dict[str, Any]] = []

    while url:
        page = graph_get(config, token, url)
        states.extend(page.get("value", []))
        url = page.get("@odata.nextLink", "")

    return states


def parse_run_states(
    states: Iterable[dict[str, Any]],
    *,
    now: datetime,
    max_age_hours: float,
) -> list[DeviceTelemetry]:
    newest_by_device: dict[str, DeviceTelemetry] = {}

    for state in states:
        output = str(state.get("preRemediationDetectionScriptOutput") or "")
        match = TELEMETRY_RE.search(output)
        if not match:
            continue

        managed = state.get("managedDevice") or {}
        computer_name = str(
            managed.get("deviceName") or match.group("device") or ""
        ).strip()
        if not computer_name:
            continue

        collected_raw = str(state.get("lastStateUpdateDateTime") or "").strip()
        if not collected_raw:
            continue

        try:
            last_restart = parse_datetime(match.group("lastboot"))
            collected = parse_datetime(collected_raw)
        except (TypeError, ValueError):
            LOG.warning("Skipping malformed telemetry for %s", computer_name)
            continue

        uptime_days = max(0.0, (now - last_restart).total_seconds() / 86400.0)
        age_hours = max(0.0, (now - collected).total_seconds() / 3600.0)
        record = DeviceTelemetry(
            computer_name=computer_name,
            user=str(managed.get("userPrincipalName") or ""),
            last_restart=last_restart,
            telemetry_collected=collected,
            uptime_days=uptime_days,
            telemetry_age_hours=age_hours,
            fresh=age_hours <= max_age_hours,
        )

        existing = newest_by_device.get(computer_name.casefold())
        if existing is None or record.telemetry_collected > existing.telemetry_collected:
            newest_by_device[computer_name.casefold()] = record

    return list(newest_by_device.values())


def build_top_table(
    records: Iterable[DeviceTelemetry], *, top_n: int, local_tz: ZoneInfo
) -> str:
    fresh = sorted(
        (record for record in records if record.fresh),
        key=lambda record: record.uptime_days,
        reverse=True,
    )[:top_n]

    if not fresh:
        return "No fresh Intune reboot telemetry is currently available."

    lines = [
        "#  COMPUTER                 UPTIME   LAST RESTART          USER",
        "-- ------------------------ -------- --------------------- ------------------------------",
    ]
    for index, record in enumerate(fresh, start=1):
        restart = record.last_restart.astimezone(local_tz).strftime("%d/%m/%Y %I:%M %p")
        user = record.user or "-"
        lines.append(
            f"{index:>2} {record.computer_name[:24]:<24} "
            f"{record.uptime_days:>6.1f}d  {restart:<21} {user[:30]}"
        )
    return "\n".join(lines)


def build_metrics(
    records: list[DeviceTelemetry], *, config: Config, now: datetime
) -> dict[str, str]:
    local_tz = ZoneInfo(config.timezone_name)
    fresh = [record for record in records if record.fresh]
    stale = [record for record in records if not record.fresh]
    latest_collection = max(
        (record.telemetry_collected for record in records), default=None
    )
    max_uptime = max((record.uptime_days for record in fresh), default=0.0)

    summary = {
        "generated_at": now.astimezone(local_tz).isoformat(),
        "reporting_devices": len(records),
        "fresh_devices": len(fresh),
        "stale_devices": len(stale),
        "max_telemetry_age_hours": config.max_telemetry_age_hours,
        "max_uptime_days": round(max_uptime, 3),
        "over_7_days": sum(record.uptime_days >= 7 for record in fresh),
        "over_14_days": sum(record.uptime_days >= 14 for record in fresh),
        "over_30_days": sum(record.uptime_days >= 30 for record in fresh),
        "top": [
            record.as_json(local_tz)
            for record in sorted(
                fresh, key=lambda record: record.uptime_days, reverse=True
            )[: config.top_n]
        ],
    }

    return {
        "intune.windows.reporting.count": str(len(records)),
        "intune.windows.fresh.count": str(len(fresh)),
        "intune.windows.stale.count": str(len(stale)),
        "intune.windows.max.uptime.days": f"{max_uptime:.3f}",
        "intune.windows.uptime.over7.count": str(
            sum(record.uptime_days >= 7 for record in fresh)
        ),
        "intune.windows.uptime.over14.count": str(
            sum(record.uptime_days >= 14 for record in fresh)
        ),
        "intune.windows.uptime.over30.count": str(
            sum(record.uptime_days >= 30 for record in fresh)
        ),
        "intune.windows.last.collection.epoch": str(
            int(latest_collection.timestamp()) if latest_collection else 0
        ),
        "intune.windows.top10": build_top_table(
            records, top_n=config.top_n, local_tz=local_tz
        ),
        "intune.windows.summary.json": json.dumps(summary, separators=(",", ":")),
    }


def send_metrics(config: Config, metrics: dict[str, str]) -> None:
    failures: list[str] = []
    for key, value in metrics.items():
        command = [
            config.zabbix_sender,
            "-z",
            config.zabbix_server,
            "-p",
            str(config.zabbix_port),
            "-s",
            config.zabbix_host,
            "-k",
            key,
            "-o",
            value,
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            failures.append(f"{key}: {completed.stdout.strip()}")
        else:
            LOG.debug("Sent %s", key)

    if failures:
        raise RuntimeError("zabbix_sender failure(s): " + " | ".join(failures))


def collect(config: Config) -> tuple[list[DeviceTelemetry], dict[str, str]]:
    now = datetime.now(timezone.utc)
    token = get_access_token(config)
    raw_states = fetch_run_states(config, token)
    records = parse_run_states(
        raw_states,
        now=now,
        max_age_hours=config.max_telemetry_age_hours,
    )
    metrics = build_metrics(records, config=config, now=now)
    return records, metrics


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read Intune reboot telemetry and publish fleet metrics to Zabbix."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read Graph and print generated metrics without calling zabbix_sender.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="With --dry-run, print summary JSON instead of the top-10 table.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        config = Config.from_env()
        records, metrics = collect(config)
        LOG.info(
            "Parsed %d reporting devices (%s fresh, %s stale)",
            len(records),
            metrics["intune.windows.fresh.count"],
            metrics["intune.windows.stale.count"],
        )
        if args.dry_run:
            if args.json_output:
                print(metrics["intune.windows.summary.json"])
            else:
                print(metrics["intune.windows.top10"])
            return 0

        send_metrics(config, metrics)
        LOG.info("Published %d Zabbix items", len(metrics))
        return 0
    except Exception as exc:
        LOG.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
