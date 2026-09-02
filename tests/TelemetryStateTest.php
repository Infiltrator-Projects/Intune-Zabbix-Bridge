<?php declare(strict_types = 1);

require_once __DIR__.'/../module/intune_reboot_watch/includes/TelemetryState.php';

use Modules\IntuneRebootWatch\Includes\TelemetryState;

function assert_state(string $label, string $actual, string $expected): void {
    if ($actual !== $expected) {
        fwrite(STDERR, "FAIL: {$label}: expected {$expected}, got {$actual}\n");
        exit(1);
    }
}

$state = new TelemetryState();
$now = new DateTimeImmutable('2026-09-02T03:30:00+00:00');

assert_state('current', $state->evaluate('2026-09-02T03:15:00+00:00', $now, 30)['status'], 'fresh');
assert_state('stale', $state->evaluate('2026-09-02T02:59:00+00:00', $now, 30)['status'], 'stale');
assert_state('missing', $state->evaluate('', $now, 30)['status'], 'unknown');
assert_state('invalid', $state->evaluate('not-a-time', $now, 30)['status'], 'unknown');

fwrite(STDOUT, "TelemetryState tests passed.\n");
