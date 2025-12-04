import json
import os
from datetime import date, datetime, timedelta
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

STATE_FILE = "state.json"
PHRASES_FILE = "static/phrases.json"

# Namen können hier leicht mit nano angepasst werden
DEFAULT_MALE_NAME = os.getenv("WORKOUT_MALE_NAME", "Mann")
DEFAULT_FEMALE_NAME = os.getenv("WORKOUT_FEMALE_NAME", "Frau")

EXERCISES = ["squats", "situps", "pushups"]  # "situps" wird in der UI als "Crunches" angezeigt

SKIP_MIN_DAYS = 7          # Skip höchstens alle 7 Tage
CANT_MIN_DAYS = 10         # "Ich kann nicht mehr" höchstens alle 10 Tage
CANT_REDUCTION = 10        # Reps -10 bei "Ich kann nicht mehr"
START_REPS = 15            # Startwiederholungen
CANT_PASSWORD = os.getenv("WORKOUT_CANT_PASSWORD", "reset")


def _today():
    """Aktuelles Datum (ohne Uhrzeit) als date-Objekt."""
    return date.today()


def load_state():
    """State aus Datei laden oder Initialstate erzeugen."""
    if not os.path.exists(STATE_FILE):
        start = _today()
        state = {
            "day": 1,
            "start_date": start.isoformat(),
            "reps": {
                "male": {ex: START_REPS for ex in EXERCISES},
                "female": {ex: START_REPS for ex in EXERCISES},
            },
            "done": {
                "male": {ex: False for ex in EXERCISES},
                "female": {ex: False for ex in EXERCISES},
            },
            "overall": {
                "male": {ex: 0 for ex in EXERCISES},
                "female": {ex: 0 for ex in EXERCISES},
            },
            "skip": {"male": [], "female": []},
            "injured": {"male": [], "female": []},
            "cant": {"male": [], "female": []},
            "cheater": {"male": [], "female": []},
        }
        save_state(state)
        return state

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Backwards-Kompatibilität: fehlende Felder ergänzen
    if "start_date" not in state:
        # Versuche das Startdatum aus vorhandener day-Nummer zu rekonstruieren
        # (heute - (day-1); ist nur aproximativ, aber besser als gar nichts)
        try:
            d = int(state.get("day", 1))
        except ValueError:
            d = 1
        start = _today() - timedelta(days=max(d - 1, 0))
        state["start_date"] = start.isoformat()

    if "reps" not in state:
        state["reps"] = {
            "male": {ex: START_REPS for ex in EXERCISES},
            "female": {ex: START_REPS for ex in EXERCISES},
        }

    if "done" not in state:
        state["done"] = {
            "male": {ex: False for ex in EXERCISES},
            "female": {ex: False for ex in EXERCISES},
        }

    if "overall" not in state:
        state["overall"] = {
            "male": {ex: 0 for ex in EXERCISES},
            "female": {ex: 0 for ex in EXERCISES},
        }

    for key in ["skip", "injured", "cant", "cheater"]:
        if key not in state:
            state[key] = {"male": [], "female": []}
        else:
            # Sicherstellen, dass beide Personen existieren
            for person in ["male", "female"]:
                state[key].setdefault(person, [])

    # Auch in verschachtelten Dicts fehlende Exercises ergänzen
    for person in ["male", "female"]:
        state["reps"].setdefault(person, {})
        state["done"].setdefault(person, {})
        state["overall"].setdefault(person, {})
        for ex in EXERCISES:
            state["reps"][person].setdefault(ex, START_REPS)
            state["done"][person].setdefault(ex, False)
            state["overall"][person].setdefault(ex, 0)

    return state


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def calculate_current_date(state):
    """Berechnet Datum & Wochentag für den aktuellen Tag basierend auf start_date und day."""
    try:
        start = datetime.strptime(state["start_date"], "%Y-%m-%d").date()
    except Exception:
        # Fallback: wenn start_date kaputt ist, setze es neu
        start = _today()
        state["start_date"] = start.isoformat()
        save_state(state)

    day_index = max(int(state.get("day", 1)), 1) - 1
    current = start + timedelta(days=day_index)
    weekday_names = [
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ]
    weekday = weekday_names[current.weekday()]
    return current, weekday


def is_day_closed_for_person(state, person):
    """Prüft, ob eine Person den Tag abgeschlossen hat."""
    day = state["day"]
    done_all = all(state["done"][person].get(ex, False) for ex in EXERCISES)
    skipped = day in state["skip"].get(person, [])
    injured = day in state["injured"].get(person, [])
    cant = day in state["cant"].get(person, [])
    return done_all or skipped or injured or cant


@app.route("/")
def index():
    view = (request.args.get("view") or "").lower()
    if view in ("frau", "female", "f"):
        active_person = "female"
        manifest_file = "manifest-frau.json"
    else:
        # Default: Mann
        active_person = "male"
        manifest_file = "manifest-mann.json"

    male_name = (
        request.args.get("male_name")
        or request.args.get("mann")
        or DEFAULT_MALE_NAME
    )
    female_name = (
        request.args.get("female_name")
        or request.args.get("frau")
        or DEFAULT_FEMALE_NAME
    )

    return render_template(
        "index.html",
        manifest_file=manifest_file,
        male_name=male_name,
        female_name=female_name,
        active_person=active_person,
    )


@app.route("/api/state")
def api_state():
    state = load_state()
    current, weekday = calculate_current_date(state)
    response = dict(state)  # flache Kopie
    response["current_date"] = current.isoformat()
    response["current_weekday"] = weekday
    return jsonify(response)


@app.route("/api/done", methods=["POST"])
def api_done():
    data = request.get_json(force=True)
    person = data.get("person")
    exercise = data.get("exercise")

    if person not in ["male", "female"]:
        return jsonify({"error": "Ungültige Person"}), 400
    if exercise not in EXERCISES:
        return jsonify({"error": "Ungültige Übung"}), 400

    state = load_state()

    if state["done"][person].get(exercise):
        # Bereits erledigt – idempotent OK
        return jsonify({"status": "already_done"})

    # Übung als erledigt markieren
    state["done"][person][exercise] = True
    # Zur Gesamtanzahl addieren
    reps_today = state["reps"][person][exercise]
    state["overall"][person][exercise] += reps_today

    save_state(state)
    return jsonify(
        {
            "status": "ok",
            "person": person,
            "exercise": exercise,
            "reps_added": reps_today,
            "overall": state["overall"][person],
        }
    )


@app.route("/api/skip", methods=["POST"])
def api_skip():
    data = request.get_json(force=True)
    person = data.get("person")
    if person not in ["male", "female"]:
        return jsonify({"error": "Ungültige Person"}), 400

    state = load_state()
    day = state["day"]
    skip_days = state["skip"].get(person, [])

    # Prüfen, ob Skip innerhalb von 7 Tagen schon verwendet wurde
    last_skip_day = max(skip_days) if skip_days else None
    if last_skip_day is not None and (day - last_skip_day) < SKIP_MIN_DAYS:
        # Cheater-Versuch
        state["cheater"].setdefault(person, [])
        if day not in state["cheater"][person]:
            state["cheater"][person].append(day)
            save_state(state)
        return jsonify({"status": "cheater", "reason": "skip_too_soon", "day": day})

    # Skip setzen, falls noch nicht vorhanden
    if day not in skip_days:
        skip_days.append(day)
        state["skip"][person] = skip_days
        save_state(state)

    return jsonify({"status": "ok", "person": person, "day": day})


@app.route("/api/injured", methods=["POST"])
def api_injured():
    data = request.get_json(force=True)
    person = data.get("person")
    if person not in ["male", "female"]:
        return jsonify({"error": "Ungültige Person"}), 400

    state = load_state()
    day = state["day"]
    injured_days = state["injured"].get(person, [])

    if day not in injured_days:
        injured_days.append(day)
        state["injured"][person] = injured_days
        save_state(state)

    return jsonify({"status": "ok", "person": person, "day": day})


@app.route("/api/cant", methods=["POST"])
def api_cant():
    data = request.get_json(force=True)
    person = data.get("person")
    password = data.get("password", "")

    if person not in ["male", "female"]:
        return jsonify({"error": "Ungültige Person"}), 400

    if password != CANT_PASSWORD:
        return jsonify({"status": "wrong_password"}), 403

    state = load_state()
    day = state["day"]
    cant_days = state["cant"].get(person, [])

    # Prüfen, ob "ich kann nicht mehr" innerhalb von 10 Tagen schon verwendet wurde
    last_cant_day = max(cant_days) if cant_days else None
    if last_cant_day is not None and (day - last_cant_day) < CANT_MIN_DAYS:
        # Cheater-Versuch
        state["cheater"].setdefault(person, [])
        if day not in state["cheater"][person]:
            state["cheater"][person].append(day)
            save_state(state)
        return jsonify({"status": "cheater", "reason": "cant_too_soon", "day": day})

    # Tag als "cant" markieren
    if day not in cant_days:
        cant_days.append(day)
        state["cant"][person] = cant_days

    # Reps reduzieren (pro Übung -10, Minimum 1)
    for ex in EXERCISES:
        current_reps = state["reps"][person].get(ex, START_REPS)
        new_reps = max(1, current_reps - CANT_REDUCTION)
        state["reps"][person][ex] = new_reps

    save_state(state)

    return jsonify(
        {
            "status": "ok",
            "person": person,
            "day": day,
            "reps": state["reps"][person],
        }
    )


@app.route("/api/nextday", methods=["POST"])
def api_nextday():
    state = load_state()

    # Prüfen, ob beide Personen den Tag abgeschlossen haben
    for person in ["male", "female"]:
        if not is_day_closed_for_person(state, person):
            return (
                jsonify({"error": f"{person} ist für diesen Tag noch nicht fertig."}),
                400,
            )

    # Nächster Tag
    state["day"] += 1

    # Done zurücksetzen und Reps erhöhen
    for person in ["male", "female"]:
        for ex in EXERCISES:
            state["done"][person][ex] = False
            state["reps"][person][ex] += 1  # tägliche Steigerung

    save_state(state)
    return jsonify({"status": "ok", "day": state["day"]})


if __name__ == "__main__":
    # Standard-Port wie bisher
    app.run(host="0.0.0.0", port=8000, debug=False)
