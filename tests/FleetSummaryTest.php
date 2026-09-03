<?php declare(strict_types = 1);

require_once __DIR__.'/../module/intune_reboot_watch/includes/FleetSummary.php';

use Modules\IntuneRebootWatch\Includes\FleetSummary;

function fail_fleet(string $message): never {
    fwrite(STDERR, "FAIL: {$message}\n");
    exit(1);
}

$parser = new FleetSummary();

try {
    $parser->parse('{broken');
    fail_fleet('Malformed JSON was accepted.');
}
catch (InvalidArgumentException) {
}

$summary = $parser->parse(json_encode([
    'generated_at' => '2026-09-02T03:00:00+00:00',
    'expected_devices' => 4,
    'ring_reporting_devices' => 3,
    'one_ring_devices' => 3,
    'no_ring_devices' => 1,
    'multiple_ring_devices' => 0,
    'reporting_devices' => 3,
    'fresh_devices' => 2,
    'stale_devices' => 1,
    'missing_devices' => 1,
    'max_uptime_days' => 20.5,
    'over_7_days' => 2,
    'over_14_days' => 1,
    'over_30_days' => 0,
    'top' => [
        ['computer_name' => 'SHORT', 'uptime_days' => 2, 'telemetry_age_hours' => 1],
        ['computer_name' => 'LONG', 'uptime_days' => 20.5, 'telemetry_age_hours' => 1],
        ['computer_name' => '', 'uptime_days' => 999]
    ]
], JSON_THROW_ON_ERROR), 2);

if ($summary['top'][0]['computer_name'] !== 'LONG') {
    fail_fleet('Longest uptime is not first.');
}
if (count($summary['top']) !== 2) {
    fail_fleet('Rows were not bounded correctly.');
}
if ($summary['expected_devices'] !== 4
        || $summary['ring_reporting_devices'] !== 3
        || $summary['one_ring_devices'] !== 3
        || $summary['no_ring_devices'] !== 1
        || $summary['multiple_ring_devices'] !== 0
        || $summary['reporting_devices'] !== 3
        || $summary['stale_devices'] !== 1
        || $summary['missing_devices'] !== 1) {
    fail_fleet('Counters were not preserved.');
}

$full_summary = $parser->parse(json_encode([
    'generated_at' => '2026-09-02T03:00:00+00:00',
    'devices' => [
        [
            'computer_name' => 'PC-3',
            'user' => 'c@example.com',
            'ring_name' => 'Ring B',
            'ring_count' => 1,
            'ring_state' => 'one',
            'ring_status' => 'compliant',
            'ring_last_reported' => '2026-09-02T02:50:00+00:00',
            'uptime_days' => 3
        ],
        [
            'computer_name' => 'PC-1',
            'user' => 'a@example.com',
            'ring_name' => '',
            'ring_count' => 0,
            'ring_state' => 'none',
            'ring_status' => 'not-reported',
            'uptime_days' => 1
        ],
        [
            'computer_name' => 'PC-2',
            'user' => 'b@example.com',
            'ring_name' => 'Ring A; Ring B',
            'ring_count' => 2,
            'ring_state' => 'multiple',
            'ring_status' => 'multiple',
            'uptime_days' => 2
        ],
        [
            'computer_name' => 'PC-MISSING',
            'user' => 'missing@example.com',
            'ring_name' => 'Ring A',
            'ring_count' => 1,
            'ring_state' => 'one',
            'ring_status' => 'compliant',
            'uptime_days' => null,
            'telemetry_age_hours' => null,
            'telemetry_status' => 'missing'
        ]
    ],
    'top' => [
        ['computer_name' => 'PC-3', 'user' => 'c@example.com', 'uptime_days' => 3]
    ]
], JSON_THROW_ON_ERROR), 2);

if (count($full_summary['devices']) !== 4) {
    fail_fleet('Full searchable device list was truncated.');
}
if ($full_summary['devices'][3]['computer_name'] !== 'PC-MISSING'
        || $full_summary['devices'][3]['telemetry_status'] !== 'missing'
        || $full_summary['devices'][3]['ring_name'] !== 'Ring A'
        || $full_summary['devices'][3]['ring_state'] !== 'one'
        || $full_summary['devices'][3]['uptime_days'] !== null) {
    fail_fleet('Ring-reported device with missing telemetry was not preserved.');
}
if (count($full_summary['top']) !== 2) {
    fail_fleet('Visible top list did not honour the row limit.');
}
if ($full_summary['devices'][0]['computer_name'] !== 'PC-3') {
    fail_fleet('Full device list was not ranked by uptime.');
}

fwrite(STDOUT, "FleetSummary tests passed.\n");
