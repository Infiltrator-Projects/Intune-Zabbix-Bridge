<?php declare(strict_types = 1);

/**
 * INTUNE — Reboot Watch Zabbix widget registration.
 *
 * The module manifest owns the release identity. This class intentionally keeps
 * only Zabbix lifecycle behaviour that cannot be expressed in manifest.json.
 */

namespace Modules\IntuneRebootWatch;

use Zabbix\Core\CWidget;

final class Widget extends CWidget {

    public function getDefaultName(): string {
        return _('INTUNE — Reboot Watch');
    }
}
