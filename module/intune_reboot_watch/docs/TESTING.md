# Testing strategy

Static checks cover manifest identity/version, PHP, JavaScript, shell and Python syntax.

`FleetSummaryTest.php` covers malformed JSON, row normalisation, ring fields, missing telemetry, sorting and bounds.

`TelemetryStateTest.php` covers current/stale/unknown collector states with timezone-aware instants.

`WidgetViewSourceContractTest.php` catches helper/constant and required-trapper-key drift that syntax checking cannot.

`WidgetClientTest.js` proves browser code does not introduce direct network transport or a competing timer and covers computer, username and update-ring search.

Python unittests cover timestamp parsing, managed-device de-duplication, update-ring report de-duplication, the exact "ring reported but reboot telemetry missing" case, explicit no-ring/multiple-ring states and separation of ring counters from reboot-telemetry counters.

Packaging tests build both the Debian package and portable module installer, verify metadata and assert the module is installed at the Zabbix module path.

Acceptance: install/update, run `intune-zabbix-bridge --dry-run --json`, confirm Windows/ring/telemetry counts are credible, scan/enable the module, verify ring and reboot fault states, search/sort, stale-state behaviour and timezone-correct timestamps.
