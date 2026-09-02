<?php declare(strict_types = 1);

namespace Modules\IntuneRebootWatch;

use Zabbix\Core\CWidget;

final class Widget extends CWidget {

    public function getDefaultName(): string {
        return _('INTUNE — Reboot Watch');
    }
}
