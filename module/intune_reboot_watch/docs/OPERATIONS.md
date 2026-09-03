# Operations guide

## Normal operation

The collector runs every 15 minutes. The widget uses normal Zabbix refresh scheduling and reads the newest fleet summary.

The fleet row population is the current Intune managed-Windows estate. Ring reporting, reboot telemetry and weekly restart compliance are separate attributes.

## Reboot state semantics

**MISSED** means there is exactly one reported update ring, reboot telemetry is fresh, and the actual Windows last boot is earlier than the most recent applicable weekly restart boundary.

**Current** means the last boot is at or after that boundary. The Due / next column shows the next weekly boundary.

**Unknown** means the weekly policy is active but Reboot Watch cannot safely decide because ring reporting is none/multiple or reboot telemetry is stale/missing.

**Not active** means the first configured weekly boundary has not happened yet. For the current deployment this is Sunday 06/09/2026 at 03:00 Australia/Melbourne.

The dashboard must not substitute "uptime >= 7 days" for this test. Uptime remains useful context only.

## Ring and telemetry semantics

**Update ring** is the ring name observed through Windows Update Ring `deviceStatuses`. **Ring state** is One ring, No ring reported, or Multiple rings.

**Telemetry** is Fresh, Stale or Missing for `Windows - Reboot Telemetry`. **Last restart** comes from Windows `LastBootUpTime`.

Search matches computer names, usernames and update-ring names. Default sorting puts MISSED first, then Unknown, then Not active, then Current.

## Fault isolation

If **MISSED** is non-zero, those machines have fresh evidence that they have not rebooted since the required weekly boundary.

If **Unknown** is non-zero, inspect ring/telemetry columns before drawing a reboot conclusion.

If **No ring reported** or **Multiple rings** is non-zero, fix the update-ring coverage issue rather than silently selecting a ring.

If **Telemetry missing/stale** is non-zero, the machine remains visible but its weekly restart state cannot be proven after policy activation.

Graph permission failures should fail the collector rather than produce a misleading dashboard.
