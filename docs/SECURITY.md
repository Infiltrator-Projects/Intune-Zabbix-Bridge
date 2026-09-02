# Security model

The bridge is read-only against Microsoft Intune. It does not connect to laptops, invoke remediation, restart devices, use WinRM or require LAN reachability.

The Entra client secret is stored only in `/etc/intune-zabbix-bridge/bridge.env`, owned by root and readable by the dedicated `intune-zabbix` service account. The systemd service uses hardening such as `NoNewPrivileges`, `ProtectSystem=strict` and `ProtectHome=true`.

The Zabbix widget reads only Zabbix items/history through Zabbix APIs, so frontend permissions remain authoritative. Browser JavaScript never calls Microsoft Graph and receives no Graph credential.

The summary can contain device names, user principal names and reboot timestamps; normal Zabbix access controls should be used.

See `module/intune_reboot_watch/docs/SECURITY.md` for the frontend trust-boundary detail.
