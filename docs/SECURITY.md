# Security model

The bridge is read-only against Microsoft Intune. It does not connect to laptops, invoke remediation, restart devices, use WinRM, or require LAN reachability.

Use an Entra application with only the Microsoft Graph application permissions required to read the existing Intune device-health-script results. Store its client secret only in `/etc/intune-zabbix-bridge/bridge.env`, owned by `root:intune-zabbix` with mode `0640`.

The systemd service runs as the dedicated unprivileged `intune-zabbix` account and uses hardening options including `NoNewPrivileges`, `ProtectSystem=strict`, and `ProtectHome=true`.

Rotate the Entra client secret before expiry. Never commit credentials to this repository.
