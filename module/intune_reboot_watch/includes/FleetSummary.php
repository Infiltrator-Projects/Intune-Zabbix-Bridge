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
        $rows = [];

        foreach ((array) ($decoded['top'] ?? []) as $candidate) {
            if (!is_array($candidate)) {
                continue;
            }

            $computer = trim((string) ($candidate['computer_name'] ?? ''));
            if ($computer === '') {
                continue;
            }

            $rows[] = [
                'computer_name' => $computer,
                'user' => trim((string) ($candidate['user'] ?? '')),
                'last_restart' => trim((string) ($candidate['last_restart'] ?? '')),
                'telemetry_collected' => trim((string) ($candidate['telemetry_collected'] ?? '')),
                'uptime_days' => self::nonNegativeFloat($candidate['uptime_days'] ?? 0),
                'telemetry_age_hours' => self::nonNegativeFloat($candidate['telemetry_age_hours'] ?? 0),
                'fresh' => (bool) ($candidate['fresh'] ?? false)
            ];
        }

        usort(
            $rows,
            static fn(array $left, array $right): int =>
                $right['uptime_days'] <=> $left['uptime_days']
        );

        return [
            'generated_at' => trim((string) ($decoded['generated_at'] ?? '')),
            'reporting_devices' => self::nonNegativeInt($decoded['reporting_devices'] ?? 0),
            'fresh_devices' => self::nonNegativeInt($decoded['fresh_devices'] ?? 0),
            'stale_devices' => self::nonNegativeInt($decoded['stale_devices'] ?? 0),
            'max_telemetry_age_hours' => self::nonNegativeFloat(
                $decoded['max_telemetry_age_hours'] ?? 0
            ),
            'max_uptime_days' => self::nonNegativeFloat($decoded['max_uptime_days'] ?? 0),
            'over_7_days' => self::nonNegativeInt($decoded['over_7_days'] ?? 0),
            'over_14_days' => self::nonNegativeInt($decoded['over_14_days'] ?? 0),
            'over_30_days' => self::nonNegativeInt($decoded['over_30_days'] ?? 0),
            'top' => array_slice($rows, 0, $row_limit)
        ];
    }

    private static function nonNegativeInt(mixed $value): int {
        return is_numeric($value) ? max(0, (int) $value) : 0;
    }

    private static function nonNegativeFloat(mixed $value): float {
        return is_numeric($value) ? max(0.0, (float) $value) : 0.0;
    }
}
