# 🏋️‍♂️ Workout Counter – Two-Person Edition

Eine kleine, robuste WebApp zum täglichen Workout-Tracking für **zwei Personen**
(z. B. Mann & Frau) – lokal, leichtgewichtig, ohne Cloud-Abhängigkeiten.

---

## 🚀 Kurzüberblick

- tägliche Wiederholungen pro Person & Übung
- automatische Steigerung der Reps
- getrennte Views (`?view=mann` / `?view=frau`)
- Skip & „Ich kann nicht mehr“ **pro Übung**
- zynische Motivationssprüche
- Namen per URL **oder** per Konfigurationsdatei
- Flask + Gunicorn, ideal für LXC / Server

---

## ✔ Features

### Übungen (pro Person getrennt)
- Crunches (intern: Situps)
- Pushups
- Squats

Jede Übung hat **eigene Tages-Reps** und einen eigenen Status.

---

### Automatische Steigerung
Sobald **beide Personen** den Tag abgeschlossen haben:

- alle Übungen für beide Personen: **+1 Rep am nächsten Tag**

---

### Skip (pro Person)
- markiert alle Übungen für **diese Person** als erledigt
- nur alle X Tage erlaubt
- Missbrauch → Cheater-Hinweis

---

### „Ich kann nicht mehr“ (pro Übung)
- **pro Übung separat**
- **toggle-bar**
- Passwortgeschützt (`reset`)
- reduziert die Reps dieser Übung um **−10**
- Mindestwert: **1 Rep**
- jede Nutzung zählt im Cant-Counter

---

### Motivationssprüche
- kategoriebasiert (niemand fertig / einer fertig / beide fertig / skip / cant)
- rotierend, **nicht zufällig**
- Platzhalter:
  - `{male}`
  - `{female}`

---

### Zwei Views – ein Screen
- `?view=mann` → Mann kann nur **seine** Übungen klicken
- `?view=frau` → Frau kann nur **ihre** Übungen klicken
- beide Namen sind immer sichtbar

---

## 📦 Installation (Ubuntu 24.x / LXC)

### 1) System vorbereiten
```bash
sudo apt update
sudo apt install -y git
```

### 2) Repository klonen
```bash
cd /home/ubuntu
git clone https://github.com/GluGGsel/workout.git workout
cd workout-counter
```

### 3) Installationsskript ausführen
```bash
sudo chmod +x install.sh
sudo ./install.sh
```

Das Script installiert:
- Python venv
- Flask
- Gunicorn
- systemd-Service

---

## 🧍 Namen & Passwort anpassen (lokal)

Die **lokale Instanz** wird über `instance.env` konfiguriert
(diese Datei gehört **nicht** ins Public Repo).

```bash
nano config/instance.env
```

Beispiel:
```env
WORKOUT_MALE_NAME=Alex
WORKOUT_FEMALE_NAME=Sam
WORKOUT_CANT_PASSWORD=reset
```

Nach Änderungen:
```bash
sudo systemctl restart workout-counter.service
```

---

## 🌐 Web-UI aufrufen

```text
http://SERVER-IP:8000/?view=mann
http://SERVER-IP:8000/?view=frau
```

Optional (temporär, ohne Config-Datei):
```text
?male_name=Alex&female_name=Sam
```

---

## 🧱 Technik

- Backend: **Flask**
- Server: **Gunicorn**
- State: **lokale JSON-Datei**
- Kein Login, kein Cloud-Kram, kein JS-Framework

---

## ⚠ Hinweise

- `config/instance.env` ist **privat** und gehört nicht ins Public Repo
- Public Repo enthält **keine personenbezogenen Daten**
- Ideal für Paare, WGs oder Trainings-Duos

---

## ✅ Status

Aktiv genutzt.
Stabil.
Brutal ehrlich.
