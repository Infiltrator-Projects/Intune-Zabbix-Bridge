# Testing strategy

Static checks cover manifest identity/version, PHP, JavaScript, shell and Python syntax.

`FleetSummaryTest.php` covers malformed JSON, row normalisation, sorting and bounds.

`TelemetryStateTest.php` covers current/stale/unknown states with timezone-aware instants.

`WidgetViewSourceContractTest.php` catches helper/constant drift that syntax checking cannot.

`WidgetClientTest.js` proves browser code does not introduce direct network transport or a competing timer.

Python unittests cover timestamp parsing, newest-record de-duplication and longest-uptime ranking.

Packaging tests build both the Debian package and portable module installer, verify metadata and assert the module is installed at the Zabbix module path.

Acceptance: install/update, scan/enable module, confirm widget appears, verify automatic/explicit source selection, stale-state behaviour, descending top-ten ranking and timezone-correct timestamps.
