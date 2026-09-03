# Changelog

## 0.7.4 — 2026-09-03

- Restored the actual purpose of Reboot Watch: identify whether each ring-covered Windows workstation has satisfied the required weekly restart.
- Added weekly schedule evaluation against real `LastBootUpTime`, matching the deployed Sunday 03:00 catch-up policy and its first active occurrence on 06/09/2026.
- Added explicit **MISSED**, **Current**, **Unknown**, and **Not active** reboot states and a Due / next timestamp.
- Fresh telemetry plus exactly one ring is required before claiming a machine missed its restart; stale/missing telemetry and no/multiple ring states are Unknown instead of false positives.
- Made reboot state the default table ranking and added fleet counters/Zabbix items for missed/current/unknown/not-active.
- Added schedule settings to deployment configuration and regressions around the first Sunday, missed restart, successful restart, stale telemetry and broken ring state.
- Supersedes 0.7.3, which fixed ring/telemetry visibility but still did not calculate whether a restart was actually due.

## 0.7.3 — 2026-09-03

- Corrected the 0.7.2 model after re-checking the original update-ring audit and Reboot Watch purpose.
- Kept the managed Windows inventory as the non-disappearing estate, but added Windows Update Ring `deviceStatuses` as a separate observed policy plane.
- Every Windows device now shows exactly one ring, no ring reported, or multiple rings reported; ring name, configuration status and last-report time are retained in the fleet payload.
- Reboot telemetry remains a separate left-joined signal, so a computer can be ring-compliant while reboot telemetry is Missing instead of being omitted.
- Added ring health trapper items, ring-aware search/sort UI, and regressions for the exact "ring reported but no reboot telemetry" failure.
- Supersedes 0.7.2's incomplete inventory-plus-reboot-only model.

## 0.7.2 — 2026-09-03

- Fixed Reboot Watch population semantics: the managed Windows inventory is authoritative and reboot telemetry is left-joined onto it.
- Devices without reboot-telemetry run states now remain visible as explicit Missing rows.
- Added Expected and Missing counters plus per-device telemetry state without changing existing Zabbix trapper keys.
- Added regressions for inventory de-duplication and missing telemetry.

## 0.7.1 — 2026-09-03

- Rebuilt and requalified the current bridge on GitHub-hosted CI for the coordinated project release refresh.
- Preserved the 0.7.0 import, packaging and Zabbix integration behaviour unchanged.

## 0.7.0 — 2026-09-02

- added case-insensitive computer-name and username search across fresh fleet telemetry;
- made every fleet-table column sortable in both directions;
- retained search and sort state across normal Zabbix widget refreshes;
- preserved the legacy top-list payload while adding the full fresh-device list.

## 0.6.1 — 2026-09-02

- aligned module release metadata with the private 0.6.1 package;
- retained the confidential/private-only distribution policy.

## 0.6.0 — 2026-09-02

- simplified deployment to one universal package plus one deployment-specific environment file;
- removed the 0.5 GTK setup path;
- added automatic Downloads-folder config import and first collection.

## 0.5.0 — 2026-09-02

- superseded by 0.6.0.

## 0.4.0 — 2026-09-02

- self-provisioned the Zabbix fleet host and trapper items.
