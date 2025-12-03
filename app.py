from flask import Flask, render_template, jsonify, request
import json
import os
from threading import Lock
from datetime import date, timedelta

STATE_FILE = "state.json"
PHRASES_FILE = os.path.join("static", "phrases.json")
LOCK = Lock()

# Startdatum des Programms – muss mit dem Frontend übereinstimmen
START_DATE = date(2025, 11, 12)

EXERCISES = ("squats", "situps", "pushups")
PERSONS = ("male", "female")

DEFAULT_REPS = 10
RESET_PASSWORD = "reset"


# ---------- Phrasen laden ----------

def load_phrases():
    if not os.path.exists(PHRASES_FILE):
        # Minimal-Fallback, falls phrases.json noch fehlt
        return {
            "none_done": [
                "Niemand fertig. Heute gewinnt die Couch.",
                "Zero Aktivität. Beeindruckend konsequent."
            ],
            "one_done": [
                "Einer fertig, einer im Tiefschlaf.",
                "50% Leistung, 100% Potential."
            ],
            "both_done": [
                "Beide fertig! Muskelkater bestellt.",
                "100% erledigt. Respekt."
            ]
        }
    with open(PHRASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


PHRASES = load_phrases()


# ---------- State-Handling ----------

def default_person_block():
    return {ex: False for ex in EXERCISES}


def default_reps_block():
    return {ex: DEFAULT_REPS for ex in EXERCISES}


def default_overall_block():
    return {ex: 0 for ex in EXERCISES}


DEFAULT_STATE = {
    "day": 1,
    "date": START_DATE.isoformat(),
    "male": default_person_block(),
    "female": default_person_block(),
    "reps": {
        "male": default_reps_block(),
        "female": default_reps_block()
    },
    "overall": {
        "male": default_overall_block(),
        "female": default_overall_block()
    },
    "skip": {
        "male": [],
        "female": []
    },
    "injured": {
        "male": [],
        "female": []
    },
    "cant": {
        "male": [],
        "female": []
    },
    # "date_iso" -> { "cat": "phrase" }
    "phrases_used": {}
}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def load_state():
    if not os.path.exists(STATE_FILE) or os.path.getsize(STATE_FILE) == 0:
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))

    # Schema-Auffrischung
    for key in ("male", "female"):
        if key not in state:
            state[key] = default_person_block()
        else:
            for ex in EXERCISES:
                state[key].setdefault(ex, False)

    if "reps" not in state:
        state["reps"] = {"male": default_reps_block(), "female": default_reps_block()}
    for key in PERSONS:
        state["reps"].setdefault(key, default_reps_block())
        for ex in EXERCISES:
            state["reps"][key].setdefault(ex, DEFAULT_REPS)

    if "overall" not in state:
        state["overall"] = {"male": default_overall_block(), "female": default_overall_block()}
    for key in PERSONS:
        state["overall"].setdefault(key, default_overall_block())
        for ex in EXERCISES:
            state["overall"][key].setdefault(ex, 0)

    if "skip" not in state:
        state["skip"] = {"male": [], "female": []}
    if "injured" not in state:
        state["injured"] = {"male": [], "female": []}
    if "cant" not in state:
        state["cant"] = {"male": [], "female": []}
    if "phrases_used" not in state:
        state["phrases_used"] = {}

    if "day" not in state or not isinstance(state["day"], int):
        state["day"] = 1

    if "date" not in state:
        d = START_DATE + timedelta(days=state["day"] - 1)
        state["date"] = d.isoformat()

    return state


# ---------- Hilfsfunktionen ----------

def current_day_date(day: int) -> date:
    return START_DATE + timedelta(days=day - 1)


def today_index() -> int:
    today = date.today()
    return (today - START_DATE).days + 1


def compute_done_flags(state):
    done = {}
    for p in PERSONS:
        done[p] = {}
        for ex in EXERCISES:
            done[p][ex] = bool(state[p].get(ex, False))
    return done


def compute_phrase(state):
    """
    Wählt pro Tag + Kategorie genau einen Spruch aus PHRASES.
    Kategorien:
      - injured_day (wenn jemand verletzt markiert ist)
      - skip_abuse (wenn jemand skip benutzt)
      - both_done / one_done / none_done (Standardzustände)
    Prio: injured_day > skip_abuse > normal.
    """
    try:
        day_date = date.fromisoformat(state.get("date", START_DATE.isoformat()))
    except Exception:
        day_date = current_day_date(state.get("day", 1))
        state["date"] = day_date.isoformat()

    today_key = day_date.isoformat()
    day = state.get("day", 1)

    phrases_used = state.setdefault("phrases_used", {})
    day_block = phrases_used.setdefault(today_key, {})

    # Status bestimmen
    male_done = all(state["male"].get(ex, False) for ex in EXERCISES)
    female_done = all(state["female"].get(ex, False) for ex in EXERCISES)

    skip_today = any(day in state["skip"].get(p, []) for p in PERSONS)
    injured_today = any(day in state["injured"].get(p, []) for p in PERSONS)

    # Kategorie bestimmen (Priorität)
    if injured_today and "injured_day" in PHRASES:
        cat = "injured_day"
    elif skip_today and "skip_abuse" in PHRASES:
        cat = "skip_abuse"
    else:
        if male_done and female_done:
            cat = "both_done"
        elif male_done or female_done:
            cat = "one_done"
        else:
            cat = "none_done"

    # Falls wir skip/injured wollen, aber keine Sprüche vorhanden: fallback auf normalen Status
    candidates = PHRASES.get(cat) or []
    if not candidates and cat in ("injured_day", "skip_abuse"):
        if male_done and female_done:
            cat = "both_done"
        elif male_done or female_done:
            cat = "one_done"
        else:
            cat = "none_done"
        candidates = PHRASES.get(cat) or []

    # Wenn schon an diesem Tag + Kategorie ein Spruch gewählt wurde → wiederverwenden
    if cat in day_block:
        return day_block[cat]

    # Keine passenden Sprüche? Fallback-Text
    if not candidates:
        fallback = {
            "none_done": "Niemand fertig. Heute gewinnt die Couch.",
            "one_done": "Eine Seite ist fertig, die andere spielt noch Statue.",
            "both_done": "Beide fertig. Ich bin verblüfft.",
            "skip_abuse": "Skip-Day – deine Ausreden machen heute Überstunden.",
            "injured_day": "Verletzt/krank markiert. Dein Sofa gratuliert ganz herzlich."
        }
        phrase = fallback.get(cat, "Status undefiniert, aber ganz sicher nicht beeindruckend.")
    else:
        multipliers = {
            "none_done": 3,
            "one_done": 7,
            "both_done": 11,
            "skip_abuse": 5,
            "injured_day": 9
        }
        m = multipliers.get(cat, 3)
        idx = (day * m) % len(candidates)
        phrase = candidates[idx]

    day_block[cat] = phrase
    save_state(state)
    return phrase


def can_use_skip(state, person: str):
    """
    Prüft, ob Skip-Day verwendet werden darf, und gibt ggf. Warnung zurück,
    falls innerhalb der letzten 6 Tage schon ein Skip war.
    """
    day = state["day"]
    used_days = state["skip"].get(person, [])
    recent = [d for d in used_days if day - d <= 6]
    if recent:
        return "Achtung: Du hast den Skip-Day in den letzten Tagen schon benutzt. Versuchst du, das System zu bescheißen?"
    return None


def apply_cant_reduce_reps(state, person: str):
    """Reduziert die Reps dieser Person um 10 (min. 1) – für alle Übungen."""
    reps_block = state["reps"].setdefault(person, default_reps_block())
    for ex in EXERCISES:
        current_val = reps_block.get(ex, DEFAULT_REPS)
        new_val = max(1, current_val - 10)
        reps_block[ex] = new_val


def can_advance_day(state):
    """
    Prüft, ob 'Nächster Tag' erlaubt ist:
      – beide entweder fertig ODER skip ODER verletzt
      – Tag darf nicht in der Zukunft liegen (nur Tage < heute)
    """
    day = state["day"]
    current_d = current_day_date(day)
    state["date"] = current_d.isoformat()

    today_idx = today_index()
    if day >= today_idx:
        return False

    for p in PERSONS:
        exercises_done = all(state[p].get(ex, False) for ex in EXERCISES)
        injured_today = day in state["injured"].get(p, [])
        skipped_today = day in state["skip"].get(p, [])
        if not (exercises_done or injured_today or skipped_today):
            return False
    return True


def advance_day(state):
    """
    Erhöht den Tag, setzt Tages-Flags zurück
    und erhöht die Reps pro Person / Übung um 1.
    """
    state["day"] += 1
    new_day = state["day"]
    d = current_day_date(new_day)
    state["date"] = d.isoformat()

    # Tages-Checkboxen zurücksetzen
    for p in PERSONS:
        state[p] = default_person_block()

    # Reps +1 pro Tag
    for p in PERSONS:
        for ex in EXERCISES:
            current_val = state["reps"][p].get(ex, DEFAULT_REPS)
            state["reps"][p][ex] = current_val + 1

    save_state(state)


# ---------- Flask-App ----------

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    with LOCK:
        state = load_state()
        d = current_day_date(state["day"])
        state["date"] = d.isoformat()
        phrase = compute_phrase(state)
        done = compute_done_flags(state)

        payload = {
            "day": state["day"],
            "date": state["date"],
            "male": state["male"],
            "female": state["female"],
            "reps": state["reps"],
            "overall": state["overall"],
            "skip": state["skip"],
            "injured": state["injured"],
            "cant": state["cant"],
            "done": done,
            "phrase": phrase
        }
        return jsonify(payload)


# ----- Übungen abhaken / toggeln -----

@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.get_json(force=True, silent=True) or {}
    person = data.get("person")
    exercise = data.get("exercise")
    if person not in PERSONS or exercise not in EXERCISES:
        return jsonify({"error": "invalid"}), 400

    with LOCK:
        state = load_state()
        current = bool(state[person].get(exercise, False))
        new = not current
        state[person][exercise] = new

        day = state["day"]
        injured_today = day in state["injured"].get(person, [])
        skipped_today = day in state["skip"].get(person, [])

        if not injured_today and not skipped_today:
            reps_val = state["reps"][person].get(exercise, DEFAULT_REPS)
            if new:
                state["overall"][person][exercise] += reps_val
            else:
                state["overall"][person][exercise] = max(
                    0, state["overall"][person][exercise] - reps_val
                )

        save_state(state)
        phrase = compute_phrase(state)
        done = compute_done_flags(state)

        return jsonify({
            "day": state["day"],
            "male": state["male"],
            "female": state["female"],
            "reps": state["reps"],
            "overall": state["overall"],
            "skip": state["skip"],
            "injured": state["injured"],
            "cant": state["cant"],
            "done": done,
            "phrase": phrase,
            "date": state["date"]
        })


# ----- Skip-Day -----

@app.route("/api/skip", methods=["POST"])
def api_skip():
    person = request.args.get("person")
    if not person:
        data = request.get_json(force=True, silent=True) or {}
        person = data.get("person")

    if person not in PERSONS:
        return jsonify({"error": "invalid_person"}), 400

    with LOCK:
        state = load_state()
        day = state["day"]
        used_list = state["skip"].setdefault(person, [])
        if day not in used_list:
            used_list.append(day)

        warning = can_use_skip(state, person)

        save_state(state)
        phrase = compute_phrase(state)
        done = compute_done_flags(state)
        return jsonify({
            "ok": True,
            "warning": warning,
            "state": {
                "day": state["day"],
                "skip": state["skip"],
                "injured": state["injured"],
                "cant": state["cant"],
                "reps": state["reps"],
                "overall": state["overall"],
                "male": state["male"],
                "female": state["female"],
                "done": done,
                "phrase": phrase,
                "date": state["date"]
            }
        })


# ----- Verletzt / krank -----

@app.route("/api/injured", methods=["POST"])
def api_injured():
    person = request.args.get("person")
    if not person:
        data = request.get_json(force=True, silent=True) or {}
        person = data.get("person")

    if person not in PERSONS:
        return jsonify({"error": "invalid_person"}), 400

    with LOCK:
        state = load_state()
        day = state["day"]
        inj_list = state["injured"].setdefault(person, [])
        if day not in inj_list:
            inj_list.append(day)

        save_state(state)
        phrase = compute_phrase(state)
        done = compute_done_flags(state)
        return jsonify({
            "ok": True,
            "state": {
                "day": state["day"],
                "skip": state["skip"],
                "injured": state["injured"],
                "cant": state["cant"],
                "reps": state["reps"],
                "overall": state["overall"],
                "male": state["male"],
                "female": state["female"],
                "done": done,
                "phrase": phrase,
                "date": state["date"]
            }
        })


# ----- "Ich kann nicht mehr" / Reps reduzieren -----

def handle_cant_request(person: str):
    with LOCK:
        state = load_state()
        day = state["day"]
        cant_list = state["cant"].setdefault(person, [])
        if day not in cant_list:
            cant_list.append(day)

        apply_cant_reduce_reps(state, person)

        save_state(state)
        phrase = compute_phrase(state)
        done = compute_done_flags(state)
        return jsonify({
            "ok": True,
            "state": {
                "day": state["day"],
                "skip": state["skip"],
                "injured": state["injured"],
                "cant": state["cant"],
                "reps": state["reps"],
                "overall": state["overall"],
                "male": state["male"],
                "female": state["female"],
                "done": done,
                "phrase": phrase,
                "date": state["date"]
            }
        })


@app.route("/api/cant", methods=["POST"])
def api_cant():
    person = request.args.get("person")
    if not person:
        data = request.get_json(force=True, silent=True) or {}
        person = data.get("person")
        password = data.get("password")
    else:
        password = None

    if person not in PERSONS:
        return jsonify({"error": "invalid_person"}), 400

    if password is None:
        data = request.get_json(force=True, silent=True) or {}
        password = data.get("password")

    if password != RESET_PASSWORD:
        return jsonify({"error": "invalid_password"}), 403

    return handle_cant_request(person)


@app.route("/api/reps_reduce", methods=["POST"])
def api_reps_reduce():
    data = request.get_json(force=True, silent=True) or {}
    person = data.get("person")
    password = data.get("password")

    if person not in PERSONS:
        return jsonify({"error": "invalid_person"}), 400
    if password != RESET_PASSWORD:
        return jsonify({"error": "invalid_password"}), 403

    return handle_cant_request(person)


# ----- Nächster Tag -----

@app.route("/api/next_day", methods=["POST"])
def api_next_day():
    with LOCK:
        state = load_state()
        if not can_advance_day(state):
            return jsonify({"error": "not_allowed"}), 400
        advance_day(state)
        phrase = compute_phrase(state)
        done = compute_done_flags(state)
        return jsonify({
            "day": state["day"],
            "date": state["date"],
            "reps": state["reps"],
            "overall": state["overall"],
            "male": state["male"],
            "female": state["female"],
            "skip": state["skip"],
            "injured": state["injured"],
            "cant": state["cant"],
            "done": done,
            "phrase": phrase
        })


@app.route("/api/next", methods=["POST"])
def api_next():
    return api_next_day()


# ---------- Main ----------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
