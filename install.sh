#!/bin/bash
set -euo pipefail

echo "=== workout-counter Installation startet ==="

APP_USER="ubuntu"
APP_NAME="workout-counter"
APP_DIR="/home/${APP_USER}/${APP_NAME}"

# Verzeichnis, in dem dieses Skript liegt (also dein Git-Checkout)
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/6] Systempakete installieren..."
apt update
apt install -y python3 python3-venv python3-pip git gunicorn

echo "[2/6] Benutzer '${APP_USER}' prüfen..."
if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "${APP_USER}"
fi

echo "[3/6] Projekt nach ${APP_DIR} synchronisieren..."
mkdir -p "${APP_DIR}"
rsync -a --delete "${REPO_DIR}/" "${APP_DIR}/"

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "[4/6] Python venv & Dependencies..."
cd "${APP_DIR}"
if [ ! -d venv ]; then
  sudo -u "${APP_USER}" python3 -m venv venv
fi

sudo -u "${APP_USER}" bash -lc "
  set -e
  source venv/bin/activate
  if [ -f requirements.txt ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
  fi
"

echo "[5/6] systemd-Service einrichten..."

SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Workout Counter WebApp
After=network.target

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 2 --reload --timeout 90 --bind 0.0.0.0:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "Alten Service 'workout.service' (falls vorhanden) deaktivieren..."
if systemctl list-unit-files | grep -q '^workout.service'; then
  systemctl stop workout.service || true
  systemctl disable workout.service || true
fi

echo "Neuen Service ${APP_NAME}.service aktivieren..."
systemctl daemon-reload
systemctl enable "${APP_NAME}.service"
systemctl restart "${APP_NAME}.service"

echo "[6/6] Status prüfen..."
systemctl --no-pager --full status "${APP_NAME}.service" || true

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [ -z "${IP}" ]; then
  IP="<SERVER-IP>"
fi

echo ""
echo "==========================================="
echo "Installation abgeschlossen!"
echo "App erreichbar unter:"
echo "   http://${IP}:8000/?view=mann"
echo "   http://${IP}:8000/?view=frau"
echo "==========================================="
