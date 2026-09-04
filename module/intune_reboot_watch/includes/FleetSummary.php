<?php declare(strict_types = 1);

namespace Modules\IntuneRebootWatch\Includes;

use InvalidArgumentException;
use JsonException;

final class FleetSummary {

    public function parse(string $json, int $row_limit = 10): array {
        try {
            $decoded = json_decode($json, true, 512, JSON_THROW_ON_ERROR);
        }
        catch (JsonException $exception) {
            throw new InvalidArgumentException('Fleet summary is not valid JSON.', 0, $exception);
        }

        if (!is_array($decoded)) {
            throw new InvalidArgumentException('Fleet summary must be a JSON object.');
        }

        $row_limit = max(1, min(10, $row_limit));
        $has_devices = array_key_exists('devices', $decoded) && is_array($decoded['devices']);
        $source_rows = $has_devices
            ? $decoded['devices']
            : (array) ($decoded['top'] ?? []);
        $rows = $this->normaliseRows($source_rows);
        $derived = $has_devices ? $this->deriveCounters($rows) : null;

        return [
            'generated_at' => trim((string) ($decoded['generated_at'] ?? '')),
            'expected_devices' => $derived !== null
                ? count($rows)
                : self::nonNegativeInt(
                    $decoded['expected_devices'] ?? $decoded['reporting_devices'] ?? 0
                ),
            'ring_reporting_devices' => $derived['ring_reporting_devices']
                ?? self::nonNegativeInt($decoded['ring_reporting_devices'] ?? 0),
            'one_ring_devices' => $derived['one_ring_devices']
                ?? self::nonNegativeInt($decoded['one_ring_devices'] ?? 0),
            'no_ring_devices' => $derived['no_ring_devices']
                ?? self::nonNegativeInt($decoded['no_ring_devices'] ?? 0),
            'multiple_ring_devices' => $derived['multiple_ring_devices']
                ?? self::nonNegativeInt($decoded['multiple_ring_devices'] ?? 0),
            'reporting_devices' => $derived['reporting_devices']
                ?? self::nonNegativeInt($decoded['reporting_devices'] ?? 0),
            'fresh_devices' => $derived['fresh_devices']
                ?? self::nonNegativeInt($decoded['fresh_devices'] ?? 0),
            'stale_devices' => $derived['stale_devices']
                ?? self::nonNegativeInt($decoded['stale_devices'] ?? 0),
            'missing_devices' => $derived['missing_devices']
                ?? self::nonNegativeInt($decoded['missing_devices'] ?? 0),
            'reboot_missed_devices' => $derived['reboot_missed_devices']
                ?? self::nonNegativeInt($decoded['reboot_missed_devices'] ?? 0),
            'reboot_current_devices' => $derived['reboot_current_devices']
                ?? self::nonNegativeInt($decoded['reboot_current_devices'] ?? 0),
            'reboot_unknown_devices' => $derived['reboot_unknown_devices']
                ?? self::nonNegativeInt($decoded['reboot_unknown_devices'] ?? 0),
            'reboot_not_active_devices' => $derived['reboot_not_active_devices']
                ?? self::nonNegativeInt($decoded['reboot_not_active_devices'] ?? 0),
            'weekly_restart_day' => trim((string) ($decoded['weekly_restart_day'] ?? '')),
            'weekly_restart_time' => trim((string) ($decoded['weekly_restart_time'] ?? '')),
            'weekly_restart_policy_start' => trim(
                (string) ($decoded['weekly_restart_policy_start'] ?? '')
            ),
            'max_telemetry_age_hours' => self::nonNegativeFloat(
                $decoded['max_telemetry_age_hours'] ?? 0
            ),
            'max_uptime_days' => $derived['max_uptime_days']
                ?? self::nonNegativeFloat($decoded['max_uptime_days'] ?? 0),
            'over_7_days' => $derived['over_7_days']
                ?? self::nonNegativeInt($decoded['over_7_days'] ?? 0),
            'over_14_days' => $derived['over_14_days']
                ?? self::nonNegativeInt($decoded['over_14_days'] ?? 0),
            'over_30_days' => $derived['over_30_days']
                ?? self::nonNegativeInt($decoded['over_30_days'] ?? 0),
            'devices' => $rows,
            'top' => array_slice($rows, 0, $row_limit)
        ];
    }

    /** @param list<array<string, mixed>> $rows */
    private function deriveCounters(array $rows): array {
        $counts = [
            'ring_reporting_devices' => 0,
            'one_ring_devices' => 0,
            'no_ring_devices' => 0,
            'multiple_ring_devices' => 0,
            'reporting_devices' => 0,
            'fresh_devices' => 0,
            'stale_devices' => 0,
            'missing_devices' => 0,
            'reboot_missed_devices' => 0,
            'reboot_current_devices' => 0,
            'reboot_unknown_devices' => 0,
            'reboot_not_active_devices' => 0,
            'max_uptime_days' => 0.0,
            'over_7_days' => 0,
            'over_14_days' => 0,
            'over_30_days' => 0
        ];

        foreach ($rows as $row) {
            match ($row['ring_state']) {
                'one' => $counts['one_ring_devices']++,
                'multiple' => $counts['multiple_ring_devices']++,
                default => $counts['no_ring_devices']++
            };

            if ($row['ring_state'] !== 'none') {
                $counts['ring_reporting_devices']++;
            }

            match ($row['telemetry_status']) {
                'fresh' => $counts['fresh_devices']++,
                'missing' => $counts['missing_devices']++,
                default => $counts['stale_devices']++
            };
            if ($row['telemetry_status'] !== 'missing') {
                $counts['reporting_devices']++;
            }

            match ($row['reboot_state']) {
                'missed' => $counts['reboot_missed_devices']++,
                'current' => $counts['reboot_current_devices']++,
                'not-active' => $counts['reboot_not_active_devices']++,
                default => $counts['reboot_unknown_devices']++
            };

            if ($row['telemetry_status'] === 'fresh' && $row['uptime_days'] !== null) {
                $uptime = (float) $row['uptime_days'];
                $counts['max_uptime_days'] = max($counts['max_uptime_days'], $uptime);
                if ($uptime >= 7) {
                    $counts['over_7_days']++;
                }
                if ($uptime >= 14) {
                    $counts['over_14_days']++;
                }
                if ($uptime >= 30) {
                    $counts['over_30_days']++;
                }
            }
        }

        return $counts;
    }

    /** @param array<int, mixed> $candidates */
    private function normaliseRows(array $candidates): array {
        $rows = [];

        foreach ($candidates as $candidate) {
            if (!is_array($candidate)) {
                continue;
            }

            $computer = trim((string) ($candidate['computer_name'] ?? ''));
            if ($computer === '') {
                continue;
            }

            $status = strtolower(trim((string) ($candidate['telemetry_status'] ?? '')));
            if (!in_array($status, ['fresh', 'stale', 'missing'], true)) {
                $status = (bool) ($candidate['fresh'] ?? false) ? 'fresh' : 'stale';
            }
            $uptime = array_key_exists('uptime_days', $candidate)
                    && is_numeric($candidate['uptime_days'])
                ? self::nonNegativeFloat($candidate['uptime_days'])
                : null;
            $telemetry_age = array_key_exists('telemetry_age_hours', $candidate)
                    && is_numeric($candidate['telemetry_age_hours'])
                ? self::nonNegativeFloat($candidate['telemetry_age_hours'])
                : null;

            $ring_count = self::nonNegativeInt($candidate['ring_count'] ?? 0);
            $ring_state = strtolower(trim((string) ($candidate['ring_state'] ?? '')));
            if (!in_array($ring_state, ['one', 'none', 'multiple'], true)) {
                $ring_state = $ring_count === 1
                    ? 'one'
                    : ($ring_count > 1 ? 'multiple' : 'none');
            }

            $reboot_state = strtolower(trim((string) ($candidate['reboot_state'] ?? 'unknown')));
            if (!in_array($reboot_state, ['missed', 'current', 'unknown', 'not-active'], true)) {
                $reboot_state = 'unknown';
            }

            $rows[] = [
                'managed_device_id' => trim((string) ($candidate['managed_device_id'] ?? '')),
                'computer_name' => $computer,
                'user' => trim((string) ($candidate['user'] ?? '')),
                'ring_name' => trim((string) ($candidate['ring_name'] ?? '')),
                'ring_count' => $ring_count,
                'ring_state' => $ring_state,
                'ring_status' => trim((string) ($candidate['ring_status'] ?? '')),
                'ring_last_reported' => trim((string) ($candidate['ring_last_reported'] ?? '')),
                'last_restart' => trim((string) ($candidate['last_restart'] ?? '')),
                'telemetry_collected' => trim(
                    (string) ($candidate['telemetry_collected'] ?? '')
                ),
                'uptime_days' => $uptime,
                'telemetry_age_hours' => $telemetry_age,
                'fresh' => $status === 'fresh',
                'telemetry_status' => $status,
                'reboot_state' => $reboot_state,
                'reboot_priority' => self::nonNegativeInt(
                    $candidate['reboot_priority'] ?? 0
                ),
                'reboot_due' => trim((string) ($candidate['reboot_due'] ?? ''))
            ];
        }

        usort($rows, static function(array $left, array $right): int {
            $priority = $right['reboot_priority'] <=> $left['reboot_priority'];
            if ($priority !== 0) {
                return $priority;
            }

            $left_missing = $left['uptime_days'] === null;
            $right_missing = $right['uptime_days'] === null;
            if ($left_missing !== $right_missing) {
                return $left_missing ? 1 : -1;
            }

            return ($right['uptime_days'] ?? 0.0) <=> ($left['uptime_days'] ?? 0.0);
        });

        return $rows;
    }

    private static function nonNegativeInt(mixed $value): int {
        return is_numeric($value) ? max(0, (int) $value) : 0;
    }

    private static function nonNegativeFloat(mixed $value): float {
        return is_numeric($value) ? max(0.0, (float) $value) : 0.0;
    }
}
