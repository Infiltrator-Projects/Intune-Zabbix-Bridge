<?php declare(strict_types = 1);

/**
 * Persistent dashboard configuration for INTUNE — Reboot Watch.
 */

namespace Modules\IntuneRebootWatch\Includes;

use Zabbix\Widgets\CWidgetForm;
use Zabbix\Widgets\Fields\CWidgetFieldIntegerBox;
use Zabbix\Widgets\Fields\CWidgetFieldMultiSelectItem;

final class WidgetForm extends CWidgetForm {

    public const MINIMUM_ROW_LIMIT = 1;
    public const MAXIMUM_ROW_LIMIT = 10;
    public const DEFAULT_ROW_LIMIT = 10;

    public const MINIMUM_STALE_MINUTES = 5;
    public const MAXIMUM_STALE_MINUTES = 1440;
    public const DEFAULT_STALE_MINUTES = 30;

    /**
     * Only stable operator choices are persisted. Current telemetry, collector
     * health and ranking state remain data concerns and are never dashboard
     * configuration.
     */
    public function addFields(): self {
        return $this
            ->addField(
                (new CWidgetFieldMultiSelectItem(
                    'itemid',
                    _('Fleet summary item (automatic if blank)')
                ))->setMultiple(false)
            )
            ->addField(
                (new CWidgetFieldIntegerBox(
                    'show_lines',
                    _('Rows displayed'),
                    self::MINIMUM_ROW_LIMIT,
                    self::MAXIMUM_ROW_LIMIT
                ))->setDefault(self::DEFAULT_ROW_LIMIT)
            )
            ->addField(
                (new CWidgetFieldIntegerBox(
                    'stale_minutes',
                    _('Collector stale after (minutes)'),
                    self::MINIMUM_STALE_MINUTES,
                    self::MAXIMUM_STALE_MINUTES
                ))->setDefault(self::DEFAULT_STALE_MINUTES)
            );
    }
}
