<?php declare(strict_types = 1);

$source = file_get_contents(__DIR__.'/../module/intune_reboot_watch/actions/WidgetView.php');
if ($source === false) {
    fwrite(STDERR, "FAIL: unable to read WidgetView.php\n");
    exit(1);
}

foreach ([
    'FleetSummary',
    'TelemetryState',
    'WidgetForm',
    'ensureFleetDataModel',
    'API::HostGroup()->create',
    'API::Host()->create',
    'API::Item()->create',
    'intune.windows.ring.reporting.count',
    'intune.windows.ring.one.count',
    'intune.windows.ring.none.count',
    'intune.windows.ring.multiple.count',
    'intune.windows.reboot.missed.count',
    'intune.windows.reboot.current.count',
    'intune.windows.reboot.unknown.count',
    'intune.windows.reboot.notactive.count'
] as $symbol) {
    if (strpos($source, $symbol) === false) {
        fwrite(STDERR, "FAIL: WidgetView no longer references {$symbol}.\n");
        exit(1);
    }
}

preg_match_all('/\bprivate\s+const\s+([A-Z][A-Z0-9_]*)\b/', $source, $declared_matches);
preg_match_all('/\bself::([A-Z][A-Z0-9_]*)\b/', $source, $used_matches);
$declared = array_unique($declared_matches[1] ?? []);

foreach (array_unique($used_matches[1] ?? []) as $constant) {
    if (!in_array($constant, $declared, true)) {
        fwrite(STDERR, "FAIL: undefined self::{$constant}\n");
        exit(1);
    }
}

fwrite(STDOUT, "WidgetView source-contract tests passed.\n");
