#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="/opt/intune-zabbix-bridge"
CONF_DIR="/etc/intune-zabbix-bridge"
CONF_FILE="${CONF_DIR}/bridge.env"

apt-get update
apt-get install -y python3 python3-venv zabbix-sender

if ! id intune-zabbix >/dev/null 2>&1; then
  useradd --system --home /nonexistent --shell /usr/sbin/nologin intune-zabbix
fi

mkdir -p "${APP_DIR}" "${CONF_DIR}"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install "${ROOT_DIR}"

if [[ ! -f "${CONF_FILE}" ]]; then
  cp "${ROOT_DIR}/config/bridge.env.example" "${CONF_FILE}"
fi

chown root:intune-zabbix "${CONF_FILE}"
chmod 0640 "${CONF_FILE}"

cp "${ROOT_DIR}/systemd/intune-zabbix-bridge.service" /etc/systemd/system/
cp "${ROOT_DIR}/systemd/intune-zabbix-bridge.timer" /etc/systemd/system/
systemctl daemon-reload

echo
echo "Installed Intune-Zabbix-Bridge."
echo "Next:"
echo "  1. Edit ${CONF_FILE}"
echo "  2. Import zabbix/template_intune_zabbix_bridge.yaml"
echo "  3. Create/link host: Microsoft Intune - Windows Fleet"
echo "  4. Test: sudo ${ROOT_DIR}/scripts/test.sh"
echo "  5. Enable: sudo systemctl enable --now intune-zabbix-bridge.timer"
