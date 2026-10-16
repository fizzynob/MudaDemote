#!/usr/bin/env bash
# ==============================================================================
# MudaDemote AWS EC2 1-Click Setup & Optimization Script
# Compatible with Ubuntu 22.04 / 24.04 & Debian
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "⚡ MudaDemote AWS EC2 Production Installer & Optimizer"
echo "=========================================================="

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root or with sudo: sudo bash ec2_setup.sh"
  exit 1
fi

CURRENT_USER="${SUDO_USER:-ubuntu}"
INSTALL_DIR="/opt/mudademote"

# 2. Configure 2GB Swap Space (Essential for t2.micro / t3.micro with 1GB RAM)
echo "[+] Checking swap space..."
if [ "$(swapon --show | wc -l)" -le 1 ]; then
  echo "[+] Allocating 2GB swapfile to prevent OOM on t2.micro/t3.micro..."
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  sysctl vm.swappiness=10
  echo 'vm.swappiness=10' >> /etc/sysctl.conf
  echo "[✓] Swapfile configured successfully."
else
  echo "[✓] Swap already configured."
fi

# 3. Update Package Repositories and Install System Dependencies
echo "[+] Updating apt repositories and installing packages..."
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  python3-venv \
  git \
  gcc \
  libffi-dev \
  curl \
  ca-certificates

# 4. Prepare Application Directory
echo "[+] Setting up installation directory at ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"

# Copy files if running from clone directory, or clone repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "${SCRIPT_DIR}/mudae_server.py" ]; then
  echo "[+] Copying repository files to ${INSTALL_DIR}..."
  cp -r "${SCRIPT_DIR}/." "${INSTALL_DIR}/"
fi

# 5. Create Python Virtual Environment with uvloop & dependencies
echo "[+] Creating Python virtual environment..."
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip setuptools wheel
echo "[+] Installing requirements (including uvloop and psutil)..."
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

# 6. Ensure presets.json exists
if [ ! -f "${INSTALL_DIR}/presets.json" ]; then
  echo "[+] Creating presets.json from template..."
  cp "${INSTALL_DIR}/presets.example.json" "${INSTALL_DIR}/presets.json"
fi

# Set proper ownership
chown -R "${CURRENT_USER}:${CURRENT_USER}" "${INSTALL_DIR}"

# 7. Configure and Enable Systemd Service
echo "[+] Installing systemd service..."
sed -i "s/User=ubuntu/User=${CURRENT_USER}/g" "${INSTALL_DIR}/deploy/mudademote.service"
sed -i "s/Group=ubuntu/Group=${CURRENT_USER}/g" "${INSTALL_DIR}/deploy/mudademote.service"
cp "${INSTALL_DIR}/deploy/mudademote.service" /etc/systemd/system/mudademote.service
systemctl daemon-reload
systemctl enable mudademote.service
systemctl restart mudademote.service

echo "=========================================================="
echo "✓ MudaDemote successfully installed & running!"
echo "=========================================================="
echo "• Dashboard Port:  8080"
echo "• Systemd Service: sudo systemctl status mudademote"
echo "• View Logs:       sudo journalctl -u mudademote -f"
echo "• Stop/Restart:    sudo systemctl restart mudademote"
echo ""
echo "IMPORTANT AWS SECURITY GROUP CONFIGURATION:"
echo "Ensure your EC2 Security Group has an Inbound Rule allowing:"
echo "  Type: Custom TCP | Port Range: 8080 | Source: Your IP (or 0.0.0.0/0)"
echo "Then visit: http://<EC2-PUBLIC-IP>:8080 in your browser."
echo "=========================================================="
