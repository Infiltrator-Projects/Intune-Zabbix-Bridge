<?php declare(strict_types = 1);

namespace Modules\IntuneRebootWatch\Includes;

use DateTimeImmutable;
use DateTimeZone;
use Throwable;

final class TelemetryState {

    public function evaluate(
        string $generated_at,
        DateTimeImmutable $now,
        int $stale_minutes
    ): array {
        $stale_minutes = max(1, $stale_minutes);

        if (trim($generated_at) === '') {
            return [
                'status' => 'unknown',
                'age_minutes' => null,
                'label' => 'Collector time unavailable'
            ];
        }

        try {
            $generated = (new DateTimeImmutable($generated_at))
                ->setTimezone(new DateTimeZone('UTC'));
            $now_utc = $now->setTimezone(new DateTimeZone('UTC'));
        }
        catch (Throwable) {
            return [
                'status' => 'unknown',
                'age_minutes' => null,
                'label' => 'Collector time invalid'
            ];
        }

        $age_minutes = max(
            0,
            $now_utc->getTimestamp() - $generated->getTimestamp()
        ) / 60;

        if ($age_minutes > $stale_minutes) {
            return [
                'status' => 'stale',
                'age_minutes' => $age_minutes,
                'label' => 'Collector stale'
            ];
        }

        return [
            'status' => 'fresh',
            'age_minutes' => $age_minutes,
            'label' => 'Collector current'
        ];
    }
}
