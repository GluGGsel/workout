#!/usr/bin/env bash
# === Workout WebApp Installation via Git (root / LXC) ===
# - Erwartet: Code liegt bereits per git clone im aktuellen Ordner
# - Installiert: venv, Python-Pakete, systemd-Service
# --------------------------------------------------------------

set -e

echo ""
echo "=== Workout WebApp Installer (via Git, root-Version) ==="
echo ""

REPO_DIR=$(pwd)
SERVICE_NAME="workout"
APP_USER="root"

echo "Projektordner: $REPO_DIR"
echo "Service-Name:  $SERVICE_NAME"
echo "User:          $APP_USER"
echo ""

# 1) Basis-Pakete installieren
echo "[1/4] Installiere Basis-Pakete..."
apt update -y
apt install -y python3 python3-venv python3-pip gunicorn curl

# 2) Python venv erstellen + Pakete installieren
echo "[2/4] Erzeuge Python-venv im Projektordner..."
python3 -m venv "$REPO_DIR/venv"

if [[ -f "$REPO_DIR/requirements.txt" ]]; then
    echo "Installiere Python-Abhängigkeiten aus requirements.txt..."
    bash -lc "cd '$REPO_DIR' && venv/bin/pip install -r requirements.txt"
else
    echo "Installiere Basis-Pakete (Flask + Gunicorn)..."
    bash -lc "cd '$REPO_DIR' && venv/bin/pip install flask gunicorn"
fi

# 3) systemd-Service anlegen
echo "[3/4] Erzeuge systemd-Service unter /etc/systemd/system/${SERVICE_NAME}.service ..."

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

# 4) Service aktivieren & starten
echo "[4/4] Service aktivieren & starten..."
systemctl daemon-reload
systemctl enable --now ${SERVICE_NAME}.service

echo ""
echo "=== Installation abgeschlossen ==="
echo "Die App sollte jetzt laufen unter:"
echo "  http://<SERVER-IP>:8000/?view=mann"
echo "  http://<SERVER-IP>:8000/?view=frau"
echo ""
systemctl --no-pager status ${SERVICE_NAME}.service || true
