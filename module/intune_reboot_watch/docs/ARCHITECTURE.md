# Architecture

## Purpose

INTUNE — Reboot Watch answers two separate questions for the managed Windows estate:

1. is this machine effectively targeted by exactly one Windows Update Ring?
2. has the machine rebooted since the applicable required weekly restart?

Neither policy targeting nor reboot telemetry is allowed to make a computer disappear.

## Data flow

```text
Intune managed Windows inventory
        │
        ├──────────── estate ────────────────────────────────┐
        │                                                    │
Windows Update Ring targeting                         Windows client
getTargetedUsersAndDevices                            LastBootUpTime
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

Windows Update Ring membership is an assignment/targeting question. The collector asks Intune for the effective targeted users/devices of each discovered Windows Update Ring instead of relying on the deprecated `deviceConfigurationDeviceStatus`/`deviceStatuses` resource.

Targets are correlated to the current managed-Windows inventory first by immutable `managedDevice.id`, then by Azure AD device ID. A name/UPN fallback is accepted only when it resolves to exactly one current device.

Every current managed Windows device remains visible and is classified as:

- **one** — exactly one update ring targets it;
- **none** — no discovered update ring targets it;
- **multiple** — more than one update ring targets it.

Ring name and the targeting record's latest check-in time are retained. If rings exist but no targeting records can be resolved at all, collection fails rather than publishing an all-unassigned fleet.

## Weekly reboot state

The current deployment mirrors the endpoint catch-up helper: Sunday at 03:00 in `Australia/Melbourne`, first active occurrence 06/09/2026 03:00. These values are overrideable through the deployment environment file.

For each device:

- before the first active weekly boundary: **Not active**;
- after activation, if ring count is not exactly one or reboot telemetry is stale/missing: **Unknown**;
- with one ring and fresh telemetry, if `LastBootUpTime >= applicable weekly boundary`: **Current**;
- with one ring and fresh telemetry, if `LastBootUpTime < applicable weekly boundary`: **MISSED**.

This duplicates the observation rule of the client catch-up helper without issuing any restart itself.

## Failure model

Graph/read failures fail the collector rather than manufacturing a result. Missing or contradictory per-device signals remain explicit row states. The Zabbix widget derives fleet counters from the same normalized device rows it displays so aggregate cards cannot contradict the table.

Browser JavaScript only filters/sorts supplied Zabbix data and performs no network access.
