#!/bin/bash
set -euo pipefail

APP_USER="ubuntu"
APP_NAME="workout-counter"
APP_DIR="/home/${APP_USER}/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
DROPIN_DIR="/etc/systemd/system/${APP_NAME}.service.d"
DROPIN_FILE="${DROPIN_DIR}/env.conf"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

apt update
apt install -y python3 python3-venv python3-pip git gunicorn rsync curl

id "${APP_USER}" >/dev/null 2>&1 || useradd -m -s /bin/bash "${APP_USER}"

mkdir -p "${APP_DIR}"

[ -f "${APP_DIR}/state.json" ] && cp -a "${APP_DIR}/state.json" /tmp/state.json.$$

rsync -a "${REPO_DIR}/" "${APP_DIR}/"

[ -f /tmp/state.json.$$ ] && cp -a /tmp/state.json.$$ "${APP_DIR}/state.json"

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

cd "${APP_DIR}"
[ ! -d venv ] && sudo -u "${APP_USER}" python3 -m venv venv

sudo -u "${APP_USER}" bash -lc "
  cd '${APP_DIR}'
  source venv/bin/activate
  pip install -r requirements.txt
"

cat > "${SERVICE_FILE}" <<EOT
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
EOT

mkdir -p "${DROPIN_DIR}"
if [ -f "${APP_DIR}/systemd/workout-counter.env.conf" ]; then
  cp -a "${APP_DIR}/systemd/workout-counter.env.conf" "${DROPIN_FILE}"
else
  cat > "${DROPIN_FILE}" <<EOT
[Service]
EnvironmentFile=${APP_DIR}/config/instance.env
EOT
fi

mkdir -p "${APP_DIR}/config"
[ -f "${APP_DIR}/config/instance.env" ] || cat > "${APP_DIR}/config/instance.env" <<EOT
WORKOUT_MALE_NAME=Person A
WORKOUT_FEMALE_NAME=Person B
WORKOUT_CANT_PASSWORD=reset
EOT

chmod 600 "${APP_DIR}/config/instance.env"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/config/instance.env"

systemctl daemon-reload
systemctl enable "${APP_NAME}.service"
systemctl restart "${APP_NAME}.service"
