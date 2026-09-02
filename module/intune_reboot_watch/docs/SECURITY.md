# Security and data handling

## Trust boundaries

Windows clients report to Intune; the collector reads Intune through Microsoft Graph; it sends aggregate values to Zabbix; the frontend reads those values through Zabbix APIs.

## Microsoft Graph

The collector is read-only. It does not invoke sync, remediation, reboot, WinRM or endpoint network access. Grant only the Graph application permissions needed to read managed devices and device-health-script results.

Keep the client secret only in `/etc/intune-zabbix-bridge/bridge.env`, mode 0640, available to the dedicated `intune-zabbix` account.

## Frontend authorisation

The widget uses Zabbix APIs, not direct SQL, so item/history visibility follows the authenticated user's permissions.

## Browser boundary

The browser never receives Graph credentials and never calls Graph directly. Widget JavaScript creates no second polling transport.

## Data sensitivity

Summaries can contain computer names, user principal names, reboot times and telemetry timestamps. Restrict dashboard access with normal Zabbix roles.

## Installation permissions

Module directories are 0755 and files 0644 with root ownership. The web-server account is not granted write access to module code.
