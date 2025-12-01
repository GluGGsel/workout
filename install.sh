#!/bin/bash
set -e

echo "=== Workout-App Installation startet ==="

# 1) Pakete installieren
echo "[1/6] Installiere Systempakete..."
apt update
apt install -y python3 python3-venv python3-pip git gunicorn

# 2) Benutzer prüfen
echo "[2/6] Prüfe Benutzer 'ubuntu'..."
id ubuntu 2>/dev/null || useradd -m -s /bin/bash ubuntu

# 3) Projektverzeichnis vorbereiten
echo "[3/6] Sync Projektdateien..."
install -d -o ubuntu -g ubuntu /home/ubuntu/workout-app
cp -r . /home/ubuntu/workout-app

# 4) Python venv + Dependencies
echo "[4/6] Erstelle virtuelle Umgebung..."
cd /home/ubuntu/workout-app
sudo -u ubuntu python3 -m venv venv
sudo -u ubuntu bash -lc 'venv/bin/pip install --upgrade pip'
sudo -u ubuntu bash -lc 'venv/bin/pip install flask gunicorn'

# 5) systemd Service installieren
echo "[5/6] Installiere systemd Service..."
cp systemd/workout.service /etc/systemd/system/workout.service
systemctl daemon-reload

# 6) Service starten
echo "[6/6] Starte Service..."
systemctl enable --now workout.service

sleep 1
curl -s http://127.0.0.1:8000/api/state || true

echo ""
echo "==========================================="
echo "Installation abgeschlossen!"
echo "App erreichbar unter:"
echo "   http://<SERVER-IP>:8000/?view=mann"
echo "   http://<SERVER-IP>:8000/?view=frau"
echo "==========================================="
