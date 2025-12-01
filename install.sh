#!/usr/bin/env bash
# === Workout WebApp systemd Installer (Git-Version) ===
# Dieses Script setzt voraus, dass der App-Code per git clone vorhanden ist.
# ---------------------------------------------------------------

set -e

echo ""
echo "=== Workout WebApp – systemd Installer ==="
echo ""

REPO_DIR=$(pwd)
SERVICE_NAME="workout"
APP_USER="ubuntu"

# 1) Basis-Pakete installieren
echo "[1/4] Installiere Basis-Pakete..."
apt update -y
apt install -y python3 python3-venv python3-pip gunicorn

# 2) Python venv erstellen
echo "[2/4] Erzeuge virtuelle Umgebung..."
sudo -u $APP_USER python3 -m venv "$REPO_DIR/venv"

if [[ -f "$REPO_DIR/requirements.txt" ]]; then
    echo "Installiere Python-Abhängigkeiten aus requirements.txt..."
    sudo -u $APP_USER bash -lc "cd $REPO_DIR && venv/bin/pip install -r requirements.txt"
else
    echo "Installiere Basis-Pakete (Flask + Gunicorn)..."
    sudo -u $APP_USER bash -lc "cd $REPO_DIR && venv/bin/pip install flask gunicorn"
fi

# 3) systemd Service anlegen
echo "[3/4] Erzeuge systemd-Service /etc/systemd/system/${SERVICE_NAME}.service..."

cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Workout WebApp
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/venv/bin/gunicorn -b 0.0.0.0:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 4) Service aktivieren
echo "[4/4] Service aktivieren & starten..."
systemctl daemon-reload
systemctl enable --now ${SERVICE_NAME}.service

echo ""
echo "=== Fertig! ==="
echo "App läuft unter:  http://<SERVER-IP>:8000/?view=mann"
echo "                  http://<SERVER-IP>:8000/?view=frau"
echo ""
systemctl --no-pager status ${SERVICE_NAME}.service || true
