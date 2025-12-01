#!/usr/bin/env bash
set -e

SERVICE_NAME="workout-counter"
SERVICE_FILE="deploy/workout-counter.service"
TARGET_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Kopiere systemd service..."
sudo cp "$SERVICE_FILE" "$TARGET_FILE"

echo "Daemon reload..."
sudo systemctl daemon-reload

echo "Service enable + start..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Fertig. Service-Status:"
systemctl status "$SERVICE_NAME" --no-pager
