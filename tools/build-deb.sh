#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly MANIFEST="$ROOT_DIR/module/intune_reboot_watch/manifest.json"
readonly PKG="intune-zabbix-bridge"
readonly ARCH="all"
readonly DIST_DIR="${1:-$ROOT_DIR/dist}"

command -v awk >/dev/null 2>&1 || { echo "ERROR: awk is required." >&2; exit 1; }
command -v dpkg-deb >/dev/null 2>&1 || { echo "ERROR: dpkg-deb is required." >&2; exit 1; }

readonly VERSION="$(awk -F'"' '/^[[:space:]]*"version"[[:space:]]*:/ {print $4; exit}' "$MANIFEST")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: invalid manifest version." >&2; exit 1; }

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
root="$stage/${PKG}_${VERSION}_${ARCH}"

mkdir -p "$root/DEBIAN" \
    "$root/usr/bin" \
    "$root/usr/lib/intune-zabbix-bridge" \
    "$root/usr/lib/python3/dist-packages/intune_zabbix_bridge" \
    "$root/usr/lib/systemd/system" \
    "$root/usr/share/applications" \
    "$root/usr/share/intune-zabbix-bridge/zabbix" \
    "$root/usr/share/zabbix/modules" \
    "$root/usr/share/doc/$PKG" \
    "$root/etc/intune-zabbix-bridge"

sed "s/^Version: .*/Version: $VERSION/" "$ROOT_DIR/packaging/debian/control" > "$root/DEBIAN/control"
install -m 0755 "$ROOT_DIR/packaging/debian/postinst" "$root/DEBIAN/postinst"
install -m 0755 "$ROOT_DIR/packaging/debian/prerm" "$root/DEBIAN/prerm"
install -m 0755 "$ROOT_DIR/packaging/debian/postrm" "$root/DEBIAN/postrm"
install -m 0644 "$ROOT_DIR/packaging/debian/conffiles" "$root/DEBIAN/conffiles"

install -m 0644 "$ROOT_DIR/src/intune_zabbix_bridge/__init__.py" "$root/usr/lib/python3/dist-packages/intune_zabbix_bridge/__init__.py"
install -m 0644 "$ROOT_DIR/src/intune_zabbix_bridge/collector.py" "$root/usr/lib/python3/dist-packages/intune_zabbix_bridge/collector.py"
install -m 0644 "$ROOT_DIR/src/intune_zabbix_bridge/config_gui.py" "$root/usr/lib/python3/dist-packages/intune_zabbix_bridge/config_gui.py"

cat > "$root/usr/bin/intune-zabbix-bridge" <<'PY'
#!/usr/bin/python3
from intune_zabbix_bridge.collector import main
raise SystemExit(main())
PY
chmod 0755 "$root/usr/bin/intune-zabbix-bridge"

install -m 0755 "$ROOT_DIR/packaging/linux/intune-zabbix-bridge-config" "$root/usr/bin/intune-zabbix-bridge-config"
install -m 0755 "$ROOT_DIR/packaging/linux/config-helper" "$root/usr/lib/intune-zabbix-bridge/config-helper"
install -m 0644 "$ROOT_DIR/packaging/linux/intune-zabbix-bridge-config.desktop" "$root/usr/share/applications/intune-zabbix-bridge-config.desktop"

install -m 0644 "$ROOT_DIR/packaging/debian/intune-zabbix-bridge.service" "$root/usr/lib/systemd/system/intune-zabbix-bridge.service"
install -m 0644 "$ROOT_DIR/packaging/debian/intune-zabbix-bridge.timer" "$root/usr/lib/systemd/system/intune-zabbix-bridge.timer"
install -m 0644 "$ROOT_DIR/zabbix/template_intune_zabbix_bridge.yaml" "$root/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml"
install -m 0644 "$ROOT_DIR/config/bridge.env.example" "$root/etc/intune-zabbix-bridge/bridge.env"
cp -a "$ROOT_DIR/module/intune_reboot_watch" "$root/usr/share/zabbix/modules/intune_reboot_watch"
install -m 0644 "$ROOT_DIR/README.md" "$root/usr/share/doc/$PKG/README.md"

find "$root/usr/share/zabbix/modules/intune_reboot_watch" -type d -exec chmod 0755 {} +
find "$root/usr/share/zabbix/modules/intune_reboot_watch" -type f -exec chmod 0644 {} +
find "$root" -type d -exec chmod a-s {} +

mkdir -p "$DIST_DIR"
out="$DIST_DIR/${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group --build "$root" "$out" >/dev/null
printf 'Built %s\n' "$out"
