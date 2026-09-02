# Setup

## 1. Entra application

Create an Entra app registration for the bridge and grant Microsoft Graph **application** permissions sufficient to read Intune device-health-script results and managed-device details. The intended least-privilege set is:

- `DeviceManagementScripts.Read.All`
- `DeviceManagementManagedDevices.Read.All`

Grant tenant admin consent. Create a client secret and record the tenant ID, application/client ID and secret value.

## 2. Zabbix host and template

Import `zabbix/template_intune_zabbix_bridge.yaml` and create a host named exactly:

`Microsoft Intune - Windows Fleet`

Link the template to that host. No agent interface is required for trapper items.

## 3. Install on the Zabbix server

```bash
sudo apt update
sudo apt install -y python3 python3-venv zabbix-sender
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin intune-zabbix || true
sudo mkdir -p /opt/intune-zabbix-bridge /etc/intune-zabbix-bridge
sudo python3 -m venv /opt/intune-zabbix-bridge/venv
sudo /opt/intune-zabbix-bridge/venv/bin/pip install /path/to/Intune-Zabbix-Bridge
sudo cp config/bridge.env.example /etc/intune-zabbix-bridge/bridge.env
sudo chown root:intune-zabbix /etc/intune-zabbix-bridge/bridge.env
sudo chmod 0640 /etc/intune-zabbix-bridge/bridge.env
```

Edit `/etc/intune-zabbix-bridge/bridge.env` and provide the Entra credentials.

Test without writing to Zabbix:

```bash
sudo -u intune-zabbix bash -c 'set -a; source /etc/intune-zabbix-bridge/bridge.env; set +a; /opt/intune-zabbix-bridge/venv/bin/intune-zabbix-bridge --dry-run'
```

Then install the timer:

```bash
sudo cp systemd/intune-zabbix-bridge.service /etc/systemd/system/
sudo cp systemd/intune-zabbix-bridge.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now intune-zabbix-bridge.timer
sudo systemctl start intune-zabbix-bridge.service
systemctl status intune-zabbix-bridge.service --no-pager
```

## 4. Dashboard

Add a **Plain text** widget for `Intune: Top 10 longest uptime` and value/stat widgets for reporting, fresh, stale and maximum uptime.

The collector excludes telemetry older than `MAX_TELEMETRY_AGE_HOURS` (48 hours by default) from the top-10 ranking so disconnected/stale devices cannot masquerade as live long-uptime machines.
