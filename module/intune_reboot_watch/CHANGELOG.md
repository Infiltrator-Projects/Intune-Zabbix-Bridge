# Changelog

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
- The service now publishes managed-Windows inventory and reboot telemetry without making any update-ring Graph request.
- The ring-report implementation remains packaged but dormant for later re-enablement after permissions are deliberately configured and tested.
- Added a regression proving the shipped runtime does not call ring enumeration or ring-report Graph sources.
- This is an emergency availability hotfix to restore the 15-minute collector cadence while preserving current device identity and reboot telemetry.

## 0.7.8 — 2026-09-04

- Replaced 0.7.7's `getTargetedUsersAndDevices` membership inference with Intune's current `getConfigurationPolicyDevicesReport` device policy report.
- Ring rows now join directly by the report's immutable `IntuneDeviceId`; name/UPN is only an unambiguous fallback.
- Added schema-driven report parsing, paging for every ring and newest-row selection for duplicate device/ring report rows.
- The packaged collector now explicitly runs through the current report-backed ring source while preserving the hardened immutable fleet/reboot logic.
- Added regressions for report parsing, pagination, immutable identity, ambiguity, duplicate report rows and packaged entry-point selection.
- Fixes the collector-stale failure mode caused by unsuccessful ring discovery while retaining fail-closed behaviour when Intune genuinely returns no usable ring report rows.

## 0.7.7 — 2026-09-04

- Replaced deprecated Windows Update Ring `deviceStatuses` with Intune effective targeting membership via `getTargetedUsersAndDevices`.
- Correlates ring targets by immutable managed-device ID or Azure AD device ID, using name/UPN only as a unique fallback.
- Fails closed when update rings exist but no targeted Windows devices can be resolved, preventing a false all-no-ring dashboard.
- Dashboard headline counters now derive from the same device rows displayed in the table, so counters and rows cannot contradict each other.
- Added regressions for targeting membership, duplicate names, multi-ring membership, zero-target failure and deprecated-source exclusion.

## 0.7.6 — 2026-09-04

- Release publication now mirrors the exact tested Debian package into the central Infiltrator APT repository automatically.
- The release fails closed if the same version already exists in the mirror with different bytes.
- The release does not complete until both the public software catalogue and APT `Packages.gz` advertise the same version.
- Added regression coverage for the APT handoff and public-feed verification contract.

## 0.7.5 — 2026-09-04

- Changed the authoritative fleet identity from computer name to immutable Intune `managedDevice.id`; duplicate names no longer collapse or exchange reboot telemetry.
- Accepts reboot telemetry only when the expanded remediation run state identifies its managed device.
- Treats legacy update-ring status identity conservatively: a ring report is attached only when its reported name/UPN uniquely identifies one current managed device.
- Keeps every ring/reboot/telemetry fault row visible regardless of the ordinary row limit or search filter.
- Made the dashboard controller read-only; opening the widget no longer creates Zabbix groups, hosts or items.
- Treats materially future collector timestamps as Unknown.
- Uses the summary JSON as the dashboard generation commit marker, publishing it only after all companion metrics succeed.
- Requires the packaged template, whose trapper items accept loopback submissions only by default.
- Moves deployment configuration into a protected root-only import inbox instead of trusting every user's Downloads directory.
- Adds regression coverage for the new identity, security, publishing and packaging boundaries.

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
