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
        $source_rows = array_key_exists('devices', $decoded) && is_array($decoded['devices'])
            ? $decoded['devices']
            : (array) ($decoded['top'] ?? []);
        $rows = $this->normaliseRows($source_rows);

        return [
            'generated_at' => trim((string) ($decoded['generated_at'] ?? '')),
            'expected_devices' => self::nonNegativeInt(
                $decoded['expected_devices'] ?? $decoded['reporting_devices'] ?? 0
            ),
            'ring_reporting_devices' => self::nonNegativeInt(
                $decoded['ring_reporting_devices'] ?? 0
            ),
            'one_ring_devices' => self::nonNegativeInt($decoded['one_ring_devices'] ?? 0),
            'no_ring_devices' => self::nonNegativeInt($decoded['no_ring_devices'] ?? 0),
            'multiple_ring_devices' => self::nonNegativeInt(
                $decoded['multiple_ring_devices'] ?? 0
            ),
            'reporting_devices' => self::nonNegativeInt($decoded['reporting_devices'] ?? 0),
            'fresh_devices' => self::nonNegativeInt($decoded['fresh_devices'] ?? 0),
            'stale_devices' => self::nonNegativeInt($decoded['stale_devices'] ?? 0),
            'missing_devices' => self::nonNegativeInt($decoded['missing_devices'] ?? 0),
            'max_telemetry_age_hours' => self::nonNegativeFloat(
                $decoded['max_telemetry_age_hours'] ?? 0
            ),
            'max_uptime_days' => self::nonNegativeFloat($decoded['max_uptime_days'] ?? 0),
            'over_7_days' => self::nonNegativeInt($decoded['over_7_days'] ?? 0),
            'over_14_days' => self::nonNegativeInt($decoded['over_14_days'] ?? 0),
            'over_30_days' => self::nonNegativeInt($decoded['over_30_days'] ?? 0),
            'devices' => $rows,
            'top' => array_slice($rows, 0, $row_limit)
        ];
    }

    /**
     * @param array<int, mixed> $candidates
     *
     * @return list<array<string, mixed>>
     */
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
            $uptime = array_key_exists('uptime_days', $candidate) && is_numeric($candidate['uptime_days'])
                ? self::nonNegativeFloat($candidate['uptime_days']) : null;
            $telemetry_age = array_key_exists('telemetry_age_hours', $candidate) && is_numeric($candidate['telemetry_age_hours'])
                ? self::nonNegativeFloat($candidate['telemetry_age_hours']) : null;
            $ring_state = strtolower(trim((string) ($candidate['ring_state'] ?? 'none')));
            if (!in_array($ring_state, ['one', 'none', 'multiple'], true)) {
                $ring_state = 'none';
            }

            $rows[] = [
                'computer_name' => $computer,
                'user' => trim((string) ($candidate['user'] ?? '')),
                'ring_name' => trim((string) ($candidate['ring_name'] ?? '')),
                'ring_count' => self::nonNegativeInt($candidate['ring_count'] ?? 0),
                'ring_state' => $ring_state,
                'ring_status' => trim((string) ($candidate['ring_status'] ?? '')),
                'ring_last_reported' => trim(
                    (string) ($candidate['ring_last_reported'] ?? '')
                ),
                'last_restart' => trim((string) ($candidate['last_restart'] ?? '')),
                'telemetry_collected' => trim((string) ($candidate['telemetry_collected'] ?? '')),
                'uptime_days' => $uptime,
                'telemetry_age_hours' => $telemetry_age,
                'fresh' => $status === 'fresh',
                'telemetry_status' => $status
            ];
        }

        usort($rows, static function(array $left, array $right): int {
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
