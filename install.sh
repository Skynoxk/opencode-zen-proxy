#!/usr/bin/env bash
# Install opencode-zen-proxy as a systemd service (Kali / Debian / Ubuntu).
set -euo pipefail

INSTALL_DIR="/opt/opencode-zen-proxy"
SERVICE_NAME="opencode-zen-proxy"
SCRIPT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/opencode-zen-proxy.py"

if [ ! -f "$SCRIPT_SRC" ]; then
  echo "ERROR: opencode-zen-proxy.py not found next to install.sh" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found" >&2
  exit 1
fi

echo "[*] Installing to $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"
sudo cp "$SCRIPT_SRC" "$INSTALL_DIR/opencode-zen-proxy.py"

echo "[*] Installing systemd unit"
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<'EOF'
[Unit]
Description=OpenCode Zen streaming reverse proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/opencode-zen-proxy/opencode-zen-proxy.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo
echo "[*] Status:"
sudo systemctl --no-pager status "$SERVICE_NAME" || true
echo
echo "[*] Test with: curl -s http://127.0.0.1:1787/v1/models"
