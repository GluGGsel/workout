#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/workout-counter"
VENV_DIR="${APP_DIR}/venv"

cd "${APP_DIR}"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r requirements.txt

sudo systemctl daemon-reload
sudo systemctl restart workout-counter
sudo systemctl --no-pager --full status workout-counter || true
