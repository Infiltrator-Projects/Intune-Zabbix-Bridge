# Architecture

## Purpose

INTUNE — Reboot Watch answers two separate questions for the managed Windows estate:

1. has Intune reported exactly one Windows Update Ring for this machine?
2. has the machine rebooted since the applicable required weekly restart?

Neither policy reporting nor reboot telemetry is allowed to make a computer disappear.

## Data flow

```text
Intune managed Windows inventory
        │
        ├──────────── estate ────────────────────────────────┐
        │                                                    │
Windows Update Ring deviceStatuses                    Windows client
        │                                              LastBootUpTime
        │                                                    │
        └──────────── Microsoft Graph ───────────────────────┘
                              │
                              ▼
                    Intune-Zabbix-Bridge
                              │
              weekly restart schedule evaluator
                              │
                              ▼
       MISSED / Current / Unknown / Not active
                              │
                         zabbix_sender
                              ▼
                    INTUNE — Reboot Watch
```

## Ring state

Every current managed Windows device remains visible and is classified as:

- **one** — exactly one update ring reports it;
- **none** — no update-ring `deviceStatus` is currently reported;
- **multiple** — more than one update ring reports it.

Ring name, raw Intune configuration status and last-report time are retained.

## Weekly reboot state

The current deployment mirrors the endpoint catch-up helper: Sunday at 03:00 in `Australia/Melbourne`, first active occurrence 06/09/2026 03:00. These values are overrideable through the deployment environment file.

For each device:

- before the first active weekly boundary: **Not active**;
- after activation, if ring count is not exactly one or reboot telemetry is stale/missing: **Unknown**;
- with one ring and fresh telemetry, if `LastBootUpTime >= applicable weekly boundary`: **Current**;
- with one ring and fresh telemetry, if `LastBootUpTime < applicable weekly boundary`: **MISSED**.

This duplicates the observation rule of the client catch-up helper without issuing any restart itself.

## Failure model

Graph/read failures fail the collector rather than manufacturing a result. Missing or contradictory per-device signals remain explicit row states.

Browser JavaScript only filters/sorts supplied Zabbix data and performs no network access.
