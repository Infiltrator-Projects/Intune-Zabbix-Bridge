# Changelog

## 0.7.12 — 2026-09-04

- Fixed the valid-collector/invalid-dashboard failure where the full 176-device summary could exceed Zabbix's text-history storage limit and be truncated after `zabbix_sender` reported success.
- Compacts the telemetry-only wire summary by removing dormant ring/identity fields and the redundant top-ten copy while preserving every dashboard-visible row value and fleet counter.
- Adds an explicit safe-size guard so an oversized summary fails closed before the generation commit marker is sent instead of replacing a valid dashboard generation with truncated JSON.
- Added regression coverage using the current 176-device fleet size plus an intentionally oversized payload.

## 0.7.11 — 2026-09-04

- Restored the proven remediation-telemetry population used by the working collector instead of expanding Reboot Watch to every managed Windows inventory record.
- Kept immutable `managedDevice.id` identity for reporting devices while leaving Windows Update Ring Graph collection disabled.
- Publish only the original long-standing Zabbix companion trapper keys plus the summary JSON; optional ring/reboot companion keys can no longer make an older deployed template reject the generation before the summary commit marker is sent.
- Reboot and telemetry counters used by the widget remain authoritative inside the summary JSON.
- Added regressions for the restored operational population, backward-compatible publication key set and zero-telemetry fail-closed behaviour.

## 0.7.10 — 2026-09-04

- Removed update-ring cards, columns, search terms and ring fault styling from the shipped Reboot Watch widget while ring collection is disabled.
- Weekly reboot compliance now evaluates from fresh reboot telemetry alone in telemetry-only mode instead of forcing every zero-ring device to Unknown.
- The shipped collector still makes no update-ring Graph calls, so `DeviceManagementConfiguration.Read.All` is not required for normal inventory/reboot collection.
- Kept the dormant ring-report implementation packaged for later deliberate re-enablement, but it is no longer part of the operational UI or runtime decision path.
- Added regression coverage for telemetry-only reboot evaluation and for the ring-free widget client.

## 0.7.9 — 2026-09-04

- Temporarily removed Windows Update Ring collection from the shipped runtime so a missing `DeviceManagementConfiguration.Read.All` permission cannot stop the collector.
- The service publishes managed-Windows inventory and reboot telemetry without making any update-ring Graph request.
- The ring-report implementation remains packaged but dormant for later re-enablement after permissions are deliberately configured and tested.
- Added a regression proving the shipped runtime does not call ring enumeration or ring-report Graph sources.

## 0.7.8 — 2026-09-04

- Replaced the `getTargetedUsersAndDevices` ring-membership inference introduced in 0.7.7 with Intune's current `getConfigurationPolicyDevicesReport` device policy report.
- Joins each ring report directly by `IntuneDeviceId` to immutable `managedDevice.id`; name/UPN is retained only as an unambiguous compatibility fallback.
- Parses the report's returned schema instead of assuming fixed column positions, paginates every ring, and collapses duplicate device/ring rows to the newest report record.
- The shipped Debian entry point now binds the hardened fleet/reboot collector to the current report-backed ring source.
- Added regressions for schema parsing, report pagination, immutable identity, ambiguity, duplicate report rows, shipped entry-point selection, and removal of the old ring API path.
- This addresses the failure mode where ring lookup stopped successful collector generations, leaving Reboot Watch stale while reboot telemetry in the last committed snapshot still appeared fresh.

## 0.7.7 — 2026-09-04

- Replaced the deprecated Windows Update Ring `deviceStatuses` runtime path with Intune's current `getTargetedUsersAndDevices` targeting action, queried separately for each discovered Windows Update Ring.
- Ring membership is correlated to the managed Windows estate by immutable `managedDevice.id`, then Azure AD device ID, with name/UPN fallback only when it uniquely identifies one current device.
- If update rings exist but no targeted Windows devices can be resolved, the collector now fails closed instead of publishing a misleading fleet in which every machine appears to have no ring.
- Dashboard headline counters are derived from the same authoritative device rows rendered in the table, preventing impossible card/table contradictions such as zero no-ring devices above rows marked no ring.
- Added regressions that forbid the deprecated ring-status source from returning to the shipped hardened collector and exercise direct ID, Azure AD ID, ambiguity, multi-ring and zero-target behavior.

## 0.7.6 — 2026-09-04

- Fixed the release pipeline itself rather than relying on manual APT repair: the exact tested Intune DEB is now mirrored into `Infiltrator-Repository` as part of the release job.
- A released version is immutable in the mirror; the workflow refuses to overwrite an existing same-version DEB with different bytes.
- The Intune release job now fails unless both the public software catalogue and the live APT `Packages.gz` advertise the release version.
- The central repository no longer pins Intune to one hard-coded version. It discovers mirrored Intune DEBs by filename and orders them using Debian version semantics.
- Added regression guards so the Intune APT handoff, public-feed verification and version-dynamic central mirror cannot silently disappear.

## 0.7.5 — 2026-09-04

- Replaced hostname as the fleet join key with immutable Intune `managedDevice.id`; duplicate computer names now remain distinct devices.
- Reboot telemetry is accepted only when the expanded run-state record supplies `managedDevice.id`.
- Legacy Windows Update Ring `deviceStatuses` are attached only when name/UPN maps uniquely to one current managed device; ambiguous reports are left unresolved instead of guessed.
- Refuses to publish a zero-device Windows estate after a successful Graph call.
- Publishes the summary JSON last, only after every companion Zabbix metric succeeds, so the dashboard generation does not advance on a partial sender failure.
- Restricted every packaged Zabbix trapper item to `127.0.0.1,::1` by default.
- Removed dashboard-time Zabbix provisioning; Reboot Watch rendering is now read-only.
- Replaced the all-users Downloads configuration watcher with a root-only `/etc/intune-zabbix-bridge/import/` inbox and validates source ownership/mode before importing secrets.
- Fault rows remain visible beyond the normal row limit and through search filtering.
- Collector timestamps more than five minutes in the future are Unknown instead of Fresh.
- Release publication now requires an explicit `Release ` commit or manual dispatch instead of publishing every push to `main`.
- Expanded regression coverage for immutable identity, ambiguous ring status, zero-fleet handling, generation publishing, importer security, trapper allow-lists and packaged hardened collector selection.

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
