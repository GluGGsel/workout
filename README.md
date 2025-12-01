# 🏋️‍♂️ Workout Counter – Mann & Frau Edition

Eine kleine, aber brutale WebApp, um zwei Personen täglich zu tracken:

- tägliche Reps pro Person (steigen automatisch)
- jeder klickt nur seine eigenen Häkchen an (`?view=mann` / `?view=frau`)
- Skip-Day pro Person
- “Ich kann nicht mehr”-Button → reduziert Reps um 10
- witzige, zynische, dumme Sprüche zur Motivation
- Passwortschutz (`reset`) für Rep-Reduktion
- skalierbar, leichtgewichtig (Flask + Gunicorn)

---

## 🚀 Features

### ✔ Reps pro Person
Jede Person hat:
- Squats  
- Situps  
- Push Ups  

Die Wiederholungszahl ist **pro Person separat** gespeichert.

### ✔ Automatische Steigerung
Wenn beide Personen fertig sind:
- Reps steigen für jede Übung pro Person um **+1**

### ✔ Skip-Day
- pro Person einzeln aktivierbar  
- setzt alle Übungen dieser Person auf ✓  
- Missbrauch wird erkannt → fette Cheater-Warnung

### ✔ "Ich kann nicht mehr"-Button
- pro Person einzeln
- Passwortgeschützt (`reset`)
- reduziert Reps um **10**, aber niemals unter **1**

### ✔ Zynische Motivationssprüche
- 20 Sprüche für "Niemand fertig"
- 20 für "Mann fertig, Frau nicht"
- 20 für "Frau fertig, Mann nicht"
- alle rotierend, nicht zufällig (damit man alles einmal sieht)

### ✔ Voll responsive (Handy-optimiert)
Perfekt für Mann & Frau auf getrennten Smartphones.

---

# 📦 Installation

Auf einem frischen Ubuntu 24.x oder LXC:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/GluGGsel/workout-counter.git
cd workout-counter
sudo chmod +x install.sh
sudo ./install.sh
```

# WebUI aufrufen unter:
http://<SERVER-IP>:8000/?view=mann
http://<SERVER-IP>:8000/?view=frau
