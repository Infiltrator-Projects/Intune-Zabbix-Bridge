#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-0.1.0}"
ARCH="all"
PKG="intune-zabbix-bridge"
BUILD_DIR="${ROOT_DIR}/build/deb/${PKG}_${VERSION}_${ARCH}"
DIST_DIR="${ROOT_DIR}/dist"
DEBIAN_DIR="${BUILD_DIR}/DEBIAN"

rm -rf "${BUILD_DIR}"
mkdir -p "${DEBIAN_DIR}"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib/python3/dist-packages/intune_zabbix_bridge"
mkdir -p "${BUILD_DIR}/usr/lib/systemd/system"
mkdir -p "${BUILD_DIR}/usr/share/intune-zabbix-bridge/zabbix"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PKG}"
mkdir -p "${BUILD_DIR}/etc/intune-zabbix-bridge"
mkdir -p "${DIST_DIR}"

sed "s/^Version: .*/Version: ${VERSION}/" "${ROOT_DIR}/packaging/debian/control" > "${DEBIAN_DIR}/control"

install -m 0755 "${ROOT_DIR}/packaging/debian/postinst" "${DEBIAN_DIR}/postinst"
install -m 0755 "${ROOT_DIR}/packaging/debian/prerm" "${DEBIAN_DIR}/prerm"
install -m 0755 "${ROOT_DIR}/packaging/debian/postrm" "${DEBIAN_DIR}/postrm"
install -m 0644 "${ROOT_DIR}/packaging/debian/conffiles" "${DEBIAN_DIR}/conffiles"

install -m 0644 "${ROOT_DIR}/src/intune_zabbix_bridge/__init__.py" "${BUILD_DIR}/usr/lib/python3/dist-packages/intune_zabbix_bridge/__init__.py"
install -m 0644 "${ROOT_DIR}/src/intune_zabbix_bridge/collector.py" "${BUILD_DIR}/usr/lib/python3/dist-packages/intune_zabbix_bridge/collector.py"

cat > "${BUILD_DIR}/usr/bin/intune-zabbix-bridge" <<'EOF'
#!/usr/bin/python3
from intune_zabbix_bridge.collector import main
raise SystemExit(main())
EOF
chmod 0755 "${BUILD_DIR}/usr/bin/intune-zabbix-bridge"

install -m 0644 "${ROOT_DIR}/packaging/debian/intune-zabbix-bridge.service" "${BUILD_DIR}/usr/lib/systemd/system/intune-zabbix-bridge.service"
install -m 0644 "${ROOT_DIR}/packaging/debian/intune-zabbix-bridge.timer" "${BUILD_DIR}/usr/lib/systemd/system/intune-zabbix-bridge.timer"
install -m 0644 "${ROOT_DIR}/zabbix/template_intune_zabbix_bridge.yaml" "${BUILD_DIR}/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml"
install -m 0644 "${ROOT_DIR}/config/bridge.env.example" "${BUILD_DIR}/etc/intune-zabbix-bridge/bridge.env"
install -m 0644 "${ROOT_DIR}/README.md" "${BUILD_DIR}/usr/share/doc/${PKG}/README.md"

# Validate syntax without shipping build-host-specific bytecode in this Architecture: all package.
python3 -m py_compile "${BUILD_DIR}/usr/lib/python3/dist-packages/intune_zabbix_bridge/__init__.py" "${BUILD_DIR}/usr/lib/python3/dist-packages/intune_zabbix_bridge/collector.py"
find "${BUILD_DIR}" -type d -name __pycache__ -prune -exec rm -rf '{}' '+'

find "${BUILD_DIR}" -type d -exec chmod 0755 '{}' '+'
find "${BUILD_DIR}" -type f -not -path "${DEBIAN_DIR}/*" -not -path "*/usr/bin/*" -exec chmod 0644 '{}' '+'
chmod 0755 "${BUILD_DIR}/usr/bin/intune-zabbix-bridge"
chmod 0755 "${DEBIAN_DIR}/postinst" "${DEBIAN_DIR}/prerm" "${DEBIAN_DIR}/postrm"

OUT="${DIST_DIR}/${PKG}_${VERSION}_${ARCH}.deb"
rm -f "${OUT}"
dpkg-deb --root-owner-group --build "${BUILD_DIR}" "${OUT}"

echo "Built ${OUT}"
dpkg-deb --info "${OUT}"
