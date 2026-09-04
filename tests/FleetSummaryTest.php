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
    'reboot_missed_devices' => 1,
    'reboot_current_devices' => 1,
    'reboot_unknown_devices' => 1,
    'reboot_not_active_devices' => 1,
    'weekly_restart_day' => 'sunday',
    'weekly_restart_time' => '03:00',
    'weekly_restart_policy_start' => '2026-09-06T03:00:00',
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
        || $summary['reboot_missed_devices'] !== 1
        || $summary['reboot_current_devices'] !== 1
        || $summary['reboot_unknown_devices'] !== 1
        || $summary['reboot_not_active_devices'] !== 1
        || $summary['reporting_devices'] !== 3
        || $summary['stale_devices'] !== 1
        || $summary['missing_devices'] !== 1) {
    fail_fleet('Counters were not preserved for legacy top-only summaries.');
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
            'ring_status' => 'targeted',
            'ring_last_reported' => '2026-09-02T02:50:00+00:00',
            'reboot_state' => 'missed',
            'reboot_priority' => 3,
            'reboot_due' => '2026-09-05T17:00:00+00:00',
            'uptime_days' => 3,
            'telemetry_status' => 'fresh'
        ],
        [
            'computer_name' => 'PC-1',
            'user' => 'a@example.com',
            'ring_name' => '',
            'ring_count' => 0,
            'ring_state' => 'none',
            'ring_status' => 'not-targeted',
            'reboot_state' => 'unknown',
            'reboot_priority' => 2,
            'reboot_due' => '2026-09-05T17:00:00+00:00',
            'uptime_days' => 1,
            'telemetry_status' => 'fresh'
        ],
        [
            'computer_name' => 'PC-2',
            'user' => 'b@example.com',
            'ring_name' => 'Ring A; Ring B',
            'ring_count' => 2,
            'ring_state' => 'multiple',
            'ring_status' => 'multiple',
            'reboot_state' => 'unknown',
            'reboot_priority' => 2,
            'reboot_due' => '2026-09-05T17:00:00+00:00',
            'uptime_days' => 2,
            'telemetry_status' => 'fresh'
        ],
        [
            'computer_name' => 'PC-MISSING',
            'user' => 'missing@example.com',
            'ring_name' => 'Ring A',
            'ring_count' => 1,
            'ring_state' => 'one',
            'ring_status' => 'targeted',
            'reboot_state' => 'unknown',
            'reboot_priority' => 2,
            'reboot_due' => '2026-09-05T17:00:00+00:00',
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
    fail_fleet('Ring-targeted device with missing telemetry was not preserved.');
}
if (count($full_summary['top']) !== 2) {
    fail_fleet('Visible top list did not honour the row limit.');
}
if ($full_summary['devices'][0]['computer_name'] !== 'PC-3') {
    fail_fleet('Missed-reboot device was not ranked first.');
}
if ($full_summary['devices'][0]['reboot_state'] !== 'missed'
        || $full_summary['devices'][0]['reboot_due'] === '') {
    fail_fleet('Reboot requirement state was not preserved.');
}

if ($full_summary['expected_devices'] !== 4
        || $full_summary['one_ring_devices'] !== 2
        || $full_summary['no_ring_devices'] !== 1
        || $full_summary['multiple_ring_devices'] !== 1
        || $full_summary['ring_reporting_devices'] !== 3
        || $full_summary['reboot_missed_devices'] !== 1
        || $full_summary['reboot_unknown_devices'] !== 3
        || $full_summary['fresh_devices'] !== 3
        || $full_summary['missing_devices'] !== 1) {
    fail_fleet('Full-summary counters were not derived from the authoritative device rows.');
}

$contradictory = $parser->parse(json_encode([
    'expected_devices' => 2,
    'one_ring_devices' => 0,
    'no_ring_devices' => 0,
    'multiple_ring_devices' => 0,
    'reboot_unknown_devices' => 0,
    'fresh_devices' => 0,
    'devices' => [
        [
            'computer_name' => 'PC-A',
            'ring_name' => 'Ring 1',
            'ring_count' => 1,
            'ring_state' => 'one',
            'ring_status' => 'targeted',
            'reboot_state' => 'unknown',
            'telemetry_status' => 'fresh',
            'uptime_days' => 1
        ],
        [
            'computer_name' => 'PC-B',
            'ring_name' => 'Ring 2',
            'ring_count' => 1,
            'ring_state' => 'one',
            'ring_status' => 'targeted',
            'reboot_state' => 'unknown',
            'telemetry_status' => 'fresh',
            'uptime_days' => 2
        ]
    ]
], JSON_THROW_ON_ERROR));

if ($contradictory['one_ring_devices'] !== 2
        || $contradictory['no_ring_devices'] !== 0
        || $contradictory['reboot_unknown_devices'] !== 2
        || $contradictory['fresh_devices'] !== 2) {
    fail_fleet('Dashboard counters can still contradict the device rows.');
}

fwrite(STDOUT, "FleetSummary tests passed.\n");
