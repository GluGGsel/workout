#!/usr/bin/env bash
set -euo pipefail

APP_USER="ubuntu"
APP_NAME="workout-counter"
APP_DIR="/home/${APP_USER}/${APP_NAME}"
SERVICE="${APP_NAME}.service"
PORT="8000"

STATE_FILE="${APP_DIR}/state.json"
BACKUP_DIR="/var/backups/${APP_NAME}"
DROPIN_DIR="/etc/systemd/system/${SERVICE}.d"
DROPIN_FILE="${DROPIN_DIR}/env.conf"
DROPIN_SRC="${APP_DIR}/systemd/workout-counter.env.conf"

echo "=== ${APP_NAME} deploy ==="

cd "${APP_DIR}"

git config --global --add safe.directory "${APP_DIR}" >/dev/null 2>&1 || true
git update-index --skip-worktree state.json >/dev/null 2>&1 || true

sudo mkdir -p "${BACKUP_DIR}"
[ -f "${STATE_FILE}" ] && sudo cp -a "${STATE_FILE}" "${BACKUP_DIR}/state.json.$(date +%F_%H%M%S).bak"

sudo systemctl stop "${SERVICE}" || true

git fetch origin
git checkout -B master origin/master
git reset --hard origin/master

git update-index --skip-worktree state.json >/dev/null 2>&1 || true

sudo mkdir -p "${DROPIN_DIR}"
if [ -f "${DROPIN_SRC}" ]; then
  sudo cp -a "${DROPIN_SRC}" "${DROPIN_FILE}"
else
  sudo tee "${DROPIN_FILE}" >/dev/null <<EOT
[Service]
EnvironmentFile=${APP_DIR}/config/instance.env
EOT
fi

sudo systemctl daemon-reload

if [ -f requirements.txt ]; then
  sudo -u "${APP_USER}" bash -lc "
    cd '${APP_DIR}'
    source venv/bin/activate
    pip install -r requirements.txt
  "
fi

sudo systemctl start "${SERVICE}"
sudo systemctl status "${SERVICE}" --no-pager | sed -n '1,12p'

command -v curl >/dev/null && curl -fsS http://127.0.0.1:${PORT}/ >/dev/null || true
echo "=== deploy done ==="
