# Setup

## 1. Entra application

Create an Entra app registration for the bridge and grant Microsoft Graph **application** permissions sufficient to read Intune device-health-script results and managed-device details. The intended least-privilege set is:

- `DeviceManagementScripts.Read.All`
- `DeviceManagementManagedDevices.Read.All`

Grant tenant admin consent. Create a client secret and record the tenant ID, application/client ID and secret value.

## 2. Zabbix host and template

The Debian package installs the template at:

`/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`

Import it into Zabbix and create a host named exactly:

`Microsoft Intune - Windows Fleet`

Link the template to that host. No agent interface is required for trapper items.

## 3. Install the Debian package

On the Zabbix server:

```bash
sudo apt install ./intune-zabbix-bridge_0.1.0_all.deb
```

APT resolves the package dependencies, including Python 3 and `zabbix-sender`.

The package installs:

- `/usr/bin/intune-zabbix-bridge`
- `/etc/intune-zabbix-bridge/bridge.env`
- `/usr/lib/systemd/system/intune-zabbix-bridge.service`
- `/usr/lib/systemd/system/intune-zabbix-bridge.timer`
- `/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`

The configuration file is a Debian conffile, so upgrades preserve local credentials and settings.

Edit:

```bash
sudo nano /etc/intune-zabbix-bridge/bridge.env
```

Provide the Entra tenant ID, application/client ID and secret.

Test without writing to Zabbix:

```bash
sudo -u intune-zabbix bash -c 'set -a; source /etc/intune-zabbix-bridge/bridge.env; set +a; intune-zabbix-bridge --dry-run'
```

When the dry run is correct:

```bash
sudo systemctl enable --now intune-zabbix-bridge.timer
sudo systemctl start intune-zabbix-bridge.service
systemctl status intune-zabbix-bridge.service --no-pager
```

## 4. Dashboard

Add a **Plain text** widget for `Intune: Top 10 longest uptime` and value/stat widgets for reporting, fresh, stale and maximum uptime.

The collector excludes telemetry older than `MAX_TELEMETRY_AGE_HOURS` (48 hours by default) from the top-10 ranking so disconnected/stale devices cannot masquerade as live long-uptime machines.

## Package updates

Installing a `.deb` makes the software a normal dpkg-managed package. For Update Manager to offer future versions automatically, those future packages must also be published through a configured APT repository. GitHub Actions builds the `.deb` now; APT-repository publication is a separate distribution layer.
