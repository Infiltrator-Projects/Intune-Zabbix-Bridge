# Testing strategy

Static checks cover manifest identity/version, PHP, JavaScript, shell and Python syntax.

`FleetSummaryTest.php` covers malformed JSON, ring fields, reboot state, missing telemetry, ranking and bounds.

`TelemetryStateTest.php` covers collector freshness.

`WidgetViewSourceContractTest.php` guards required ring and weekly-reboot trapper keys.

`WidgetClientTest.js` proves browser code opens no network transport/timer and covers computer, username and update-ring search.

Python tests cover:

- telemetry and managed-device de-duplication;
- ring-status de-duplication;
- ring reported + telemetry missing remains visible;
- no ring / multiple ring explicit faults;
- before the first weekly restart = Not active;
- last boot before the Sunday 03:00 boundary = MISSED;
- last boot after the boundary = Current;
- stale/missing telemetry cannot produce a false MISSED result;
- no/multiple ring cannot produce a false MISSED result.

Packaging tests build the Debian package and portable module installer and verify release metadata.

Acceptance requires a tenant-backed first collector run after installation because CI cannot prove the site's Graph permissions or live Intune counts.
