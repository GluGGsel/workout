# Workout WebApp

Kleine Flask-App für ein gemeinsames Daily-Workout (Mann/Frau), mit persistentem JSON-Status.

## Struktur

- `app.py` – Flask-App und API
- `templates/index.html` – Frontend (Single-Page)
- `static/` – Platzhalter für statische Assets
- `systemd/workout.service` – Beispiel-Unit für systemd
- `requirements.txt` – Python-Abhängigkeiten


# To install:
## 1) Git installieren
sudo apt update
sudo apt install -y git

## 2) Repo klonen
git clone https://github.com/GluGGsel/workout-counter.git

## 3) In das Projekt wechseln
cd workout-counter

## 4) Installationsscript ausführbar machen
sudo chmod +x install.sh

## 5) Installationsscript ausführen
sudo ./install.sh


# Works so far in:
- ubuntu lxc on proxmox
