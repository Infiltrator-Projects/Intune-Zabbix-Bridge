# Changelog

## 0.7.4 - 2026-09-03

- Reconnected Reboot Watch to the weekly restart requirement instead of merely displaying ring and uptime telemetry.
- Compares fresh real Windows last-boot time with the applicable Sunday 03:00 restart boundary, beginning 06/09/2026 for the current deployment.
- Adds MISSED/Current/Unknown/Not active states, due/next time, and matching Zabbix counters.
- Avoids false missed-reboot claims when ring status or reboot telemetry is missing/stale.
- Supersedes 0.7.3 before deployment.

## 0.7.3 - 2026-09-03

- Reworked Reboot Watch around three independent signals: managed Windows inventory, Windows Update Ring device status, and reboot telemetry.
- Devices that have reported an update ring remain visible even when reboot telemetry is missing.
- Devices with no ring reported or multiple rings reported are explicit faults instead of silently disappearing.
- Added ring names, ring configuration status, ring last-report time, ring health counters and ring-aware search/sort.
- Supersedes the incomplete 0.7.2 inventory-plus-reboot-only model.

## 0.7.2 - 2026-09-03

- Made the managed Windows inventory authoritative for Reboot Watch and left-joined reboot telemetry onto it.
- Missing or stale telemetry devices now stay visible instead of silently dropping out of the fleet.
- Added Expected/Missing counters and an explicit telemetry-status column.

## 0.7.1 - 2026-09-03

- Rebuilt and requalified the current bridge on GitHub-hosted CI as part of the coordinated project release refresh.
- Preserved the 0.7.0 import, packaging and Zabbix integration behaviour unchanged.

## 0.7.0 — 2026-09-02

- added case-insensitive computer-name and username search across fresh fleet telemetry;
- made every fleet-table column sortable in both directions;
- retained search and sort state across normal Zabbix widget refreshes;
- preserved the legacy top-list payload while adding the full fresh-device list.

## 0.6.1 — 2026-09-02

- aligned release metadata after the private-distribution hardening update;
- retains the confidential/private-only distribution policy introduced in 0.6.0.

## 0.6.0 — 2026-09-02

- replaced 0.5's GUI credential form with one universal package plus one deployment-specific environment file;
- the Debian package no longer installs a blank site config;
- added automatic Downloads-folder config import and immediate first collection;
- removed GTK/PolicyKit GUI dependencies;
- removed all public release/APT dispatch behavior from this confidential project.

## 0.5.0 — 2026-09-02

- superseded by 0.6.0.
