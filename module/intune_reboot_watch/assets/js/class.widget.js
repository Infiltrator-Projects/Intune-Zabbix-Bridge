/**
 * INTUNE — Reboot Watch client controller.
 *
 * The widget deliberately has no browser-side data source. Zabbix owns refresh
 * scheduling and the PHP controller obtains data through authenticated Zabbix
 * APIs. Keeping the browser passive avoids duplicate schedulers, direct Graph
 * credentials and client-side trust-boundary expansion.
 */
class WidgetIntuneRebootWatch extends CWidget {
}
