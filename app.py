import json
import os
from datetime import date, datetime, timedelta

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

STATE_FILE = "state.json"

# Namen via ENV (oder Query-Param). Defaults sind bewusst generisch (Public-safe).
DEFAULT_MALE_NAME = os.getenv("WORKOUT_MALE_NAME", "Person A")
DEFAULT_FEMALE_NAME = os.getenv("WORKOUT_FEMALE_NAME", "Person B")

EXERCISES = ["squats", "situps", "pushups"]  # "situps" wird in der UI als "Crunches" angezeigt

SKIP_MIN_DAYS = 7          # Skip höchstens alle 7 Tage
CANT_MIN_DAYS = 10         # "Ich kann nicht mehr!" höchstens alle 10 Tage
CANT_REDUCTION = 10        # Reps -10 bei "Ich kann nicht mehr!"
START_REPS = 15            # Startwiederholungen
CANT_PASSWORD = os.getenv("WORKOUT_CANT_PASSWORD", "reset")

# Mapping zwischen Frontend-Rollen und internem State
ROLE_TO_INTERNAL = {
    "mann": "male",
    "frau": "female",
}
INTERNAL_TO_ROLE = {
    "male": "mann",
    "female": "frau",
}

# Mapping zwischen Frontend-Übungsnamen und internem State
EXTERNAL_TO_INTERNAL_EXERCISE = {
    "crunches": "situps",
    "pushups": "pushups",
    "squats": "squats",
}
INTERNAL_TO_EXTERNAL_EXERCISE = {v: k for k, v in EXTERNAL_TO_INTERNAL_EXERCISE.items()}

MONTH_NAMES_DE = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def _today() -> date:
    """Aktuelles Datum (ohne Uhrzeit) als date-Objekt."""
    return date.today()


def format_date_swiss_long(d: date) -> str:
    """z.B. 12. Dezember 2025"""
    return f"{d.day}. {MONTH_NAMES_DE[d.month - 1]} {d.year}"


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
        try:
            d = int(state.get("day", 1))
        except (TypeError, ValueError):
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
            for person in ["male", "female"]:
                state[key].setdefault(person, [])

    # fehlende Exercises ergänzen
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
    """State mit einfacher, aber sicherer Methode speichern."""
    tmp_file = STATE_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, STATE_FILE)


def calculate_current_date(state):
    """Berechnet Datum & Wochentag für den aktuellen Tag basierend auf start_date und day."""
    try:
        start = datetime.strptime(state["start_date"], "%Y-%m-%d").date()
    except Exception:
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


def is_day_closed_for_person(state, person_internal: str) -> bool:
    """Prüft, ob eine Person den Tag abgeschlossen hat."""
    day = state["day"]
    done_all = all(state["done"][person_internal].get(ex, False) for ex in EXERCISES)
    skipped = day in state["skip"].get(person_internal, [])
    injured = day in state["injured"].get(person_internal, [])
    cant = day in state["cant"].get(person_internal, [])
    return done_all or skipped or injured or cant


def _normalize_role(role_raw: str) -> str:
    role = (role_raw or "").lower()
    if role not in ROLE_TO_INTERNAL:
        role = "mann"
    return role


def _build_totals(state):
    """Aggregierte Totals für Frontend aufbereiten."""
    totals = {}
    for internal in ["male", "female"]:
        role_label = INTERNAL_TO_ROLE[internal]
        overall = state["overall"].get(internal, {})
        totals[role_label] = {INTERNAL_TO_EXTERNAL_EXERCISE[k]: int(v) for k, v in overall.items()}
    return totals


def _build_reps_today(state):
    reps_today = {}
    for internal in ["male", "female"]:
        role_label = INTERNAL_TO_ROLE[internal]
        reps = state["reps"].get(internal, {})
        reps_today[role_label] = {INTERNAL_TO_EXTERNAL_EXERCISE[k]: int(v) for k, v in reps.items()}
    return reps_today


def _build_status(state):
    status = {}
    day = state["day"]
    for internal in ["male", "female"]:
        role_label = INTERNAL_TO_ROLE[internal]
        done_all = all(state["done"][internal].get(ex, False) for ex in EXERCISES)
        status[role_label] = {
            "done_all": done_all,
            "skipped": day in state["skip"].get(internal, []),
            "injured": day in state["injured"].get(internal, []),
            "cant": day in state["cant"].get(internal, []),
        }
    return status


def _build_can_flags(state):
    """Berechnet, ob skip/cant laut Regeln erlaubt wäre."""
    day = state["day"]
    can_skip = {}
    can_cant = {}

    for internal in ["male", "female"]:
        role_label = INTERNAL_TO_ROLE[internal]

        # Skip: Abstand seit letztem Skip
        skip_days = state["skip"].get(internal, [])
        last_skip = max(skip_days) if skip_days else None
        allow_skip = True
        if last_skip is not None and (day - last_skip) < SKIP_MIN_DAYS:
            allow_skip = False
        if is_day_closed_for_person(state, internal):
            allow_skip = False

        # Cant: Abstand seit letztem Cant
        cant_days = state["cant"].get(internal, [])
        last_cant = max(cant_days) if cant_days else None
        allow_cant = True
        if last_cant is not None and (day - last_cant) < CANT_MIN_DAYS:
            allow_cant = False
        if is_day_closed_for_person(state, internal):
            allow_cant = False

        can_skip[role_label] = allow_skip
        can_cant[role_label] = allow_cant

    return can_skip, can_cant


def _build_phrase_category(state, role_view: str) -> str:
    """
    Gibt eine Kategorie zurück, die direkt einem JSON-File im static/phrases/ Ordner entspricht.
    Kategorien:
      - none_done
      - one_done_male / one_done_female
      - all_done
      - skip_male / skip_female
      - cant_male / cant_female
      - injured_male / injured_female
      - cheater_male / cheater_female
    """
    day = state["day"]
    active_internal = ROLE_TO_INTERNAL.get(role_view, "male")
    other_internal = "female" if active_internal == "male" else "male"

    flags = {}
    for internal in ["male", "female"]:
        flags[internal] = {
            "cheater": day in state["cheater"].get(internal, []),
            "injured": day in state["injured"].get(internal, []),
            "cant": day in state["cant"].get(internal, []),
            "skip": day in state["skip"].get(internal, []),
            "done_all": all(state["done"][internal].get(ex, False) for ex in EXERCISES),
        }

    def _suffix(internal_role: str) -> str:
        return "male" if internal_role == "male" else "female"

    # Priorität: Cheater > Injured > Cant > Skip > Done-Status
    if flags[active_internal]["cheater"]:
        return f"cheater_{_suffix(active_internal)}"
    if flags[other_internal]["cheater"]:
        return f"cheater_{_suffix(other_internal)}"

    if flags[active_internal]["injured"]:
        return f"injured_{_suffix(active_internal)}"
    if flags[other_internal]["injured"]:
        return f"injured_{_suffix(other_internal)}"

    if flags[active_internal]["cant"]:
        return f"cant_{_suffix(active_internal)}"
    if flags[other_internal]["cant"]:
        return f"cant_{_suffix(other_internal)}"

    if flags[active_internal]["skip"]:
        return f"skip_{_suffix(active_internal)}"
    if flags[other_internal]["skip"]:
        return f"skip_{_suffix(other_internal)}"

    # Done-Status
    active_done = flags[active_internal]["done_all"]
    other_done = flags[other_internal]["done_all"]

    if active_done and other_done:
        return "all_done"
    if active_done and not other_done:
        return f"one_done_{_suffix(active_internal)}"
    if other_done and not active_done:
        return f"one_done_{_suffix(other_internal)}"

    return "none_done"


def _build_client_state(state, role_view: str, message: str | None = None):
    """Baut das JSON, das das Frontend erwartet."""
    current_date, weekday = calculate_current_date(state)
    date_str = current_date.strftime("%d.%m.%Y")

    # Startdatum für Anzeige im Schweizer Format
    start_iso = state.get("start_date")
    start_display = start_iso
    try:
        if start_iso:
            sd = datetime.strptime(start_iso, "%Y-%m-%d").date()
            start_display = format_date_swiss_long(sd)
    except Exception:
        start_display = start_iso

    totals = _build_totals(state)
    reps_today = _build_reps_today(state)
    status = _build_status(state)
    can_skip, can_cant = _build_can_flags(state)
    phrase_category = _build_phrase_category(state, role_view)

    # Cheater-Flag nur für die aktive Rolle
    internal = ROLE_TO_INTERNAL.get(role_view, "male")
    day = state["day"]
    cheater_today = day in state["cheater"].get(internal, [])

    response = {
        "weekday": weekday,
        "date": date_str,
        "day": int(state.get("day", 1)),
        "start_date": start_iso,
        "start_date_display": start_display,
        "totals": totals,
        "reps_today": reps_today,
        "status": status,
        "can_skip": can_skip,
        "can_cant": can_cant,
        "phrase_category": phrase_category,
        "cheater_today": cheater_today,
        "message": message or "",
    }
    return response


@app.route("/")
def index():
    view_raw = (request.args.get("view") or "").lower()
    if view_raw in ("frau", "female", "f"):
        role = "frau"
    else:
        role = "mann"

    # Query-Param überschreibt ENV/Default (praktisch für Tests, aber nicht nötig im Public Repo)
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
        role=role,
        male_name=male_name,
        female_name=female_name,
    )


@app.route("/api/state")
def api_state():
    role_view = _normalize_role(request.args.get("role"))
    state = load_state()
    response = _build_client_state(state, role_view)
    return jsonify(response)


# --- ab hier: Rest deiner ursprünglichen Logik unverändert ---
# (Ich lasse den unteren Teil bewusst so, wie er im Repo bereits ist.)

@app.route("/api/action", methods=["POST"])
def api_action():
    data = request.get_json(force=True) or {}
    role_view = _normalize_role(data.get("role"))
    action = data.get("action")
    state = load_state()

    internal_person = ROLE_TO_INTERNAL[role_view]

    message = ""

    try:
        if action == "exercise":
            exercise_external = data.get("exercise")
            if exercise_external not in EXTERNAL_TO_INTERNAL_EXERCISE:
                return jsonify({"error": "Ungültige Übung"}), 400
            internal_ex = EXTERNAL_TO_INTERNAL_EXERCISE[exercise_external]
            state, changed = _apply_exercise(state, internal_person, internal_ex)
            if changed:
                message = f"{exercise_external.capitalize()} erledigt."
            else:
                message = f"{exercise_external.capitalize()} war bereits erledigt."

        elif action == "exercise_undo":
            exercise_external = data.get("exercise")
            if exercise_external not in EXTERNAL_TO_INTERNAL_EXERCISE:
                return jsonify({"error": "Ungültige Übung"}), 400
            internal_ex = EXTERNAL_TO_INTERNAL_EXERCISE[exercise_external]
            state, changed = _apply_exercise_undo(state, internal_person, internal_ex)
            if changed:
                message = f"{exercise_external.capitalize()} wieder abgewählt."
            else:
                message = f"{exercise_external.capitalize()} war nicht als erledigt markiert."

        elif action == "skip":
            state, status = _apply_skip(state, internal_person)
            if status == "cheater_skip":
                message = "Skip zu früh – Cheater erkannt."
            else:
                message = "Skip-Tag gesetzt. Heute offiziell faul."

        elif action == "skip_undo":
            state, status = _apply_skip_undo(state, internal_person)
            if status == "ok":
                message = "Skip-Tag zurückgenommen."
            else:
                message = "Für heute war kein Skip gesetzt."

        elif action == "injured":
            state, _ = _apply_injured(state, internal_person)
            message = "Tag als krank/verletzt markiert."

        elif action == "injured_undo":
            state, status = _apply_injured_undo(state, internal_person)
            if status == "ok":
                message = "krank/verletzt-Status zurückgenommen."
            else:
                message = "Für heute war kein krank/verletzt-Status gesetzt."

        elif action == "cant":
            password = data.get("password", "")
            state, status = _apply_cant(state, internal_person, password)
            if status == "wrong_password":
                # State zurückrollen, falls wir vorher schon etwas verändert hätten
                state = load_state()
                resp = _build_client_state(
                    state,
                    role_view,
                    "Falsches Passwort für „Ich kann nicht mehr!“."
                )
                return jsonify(resp), 403
            elif status == "cheater_cant":
                message = "„Ich kann nicht mehr!“ zu früh – Cheater erkannt."
            else:
                message = "Reps reduziert. Heute war's hart genug."

        elif action == "cant_undo":
            state, status = _apply_cant_undo(state, internal_person)
            if status == "ok":
                message = "„Ich kann nicht mehr!“-Status zurückgenommen."
            else:
                message = "Für heute war kein „Ich kann nicht mehr!“-Status gesetzt."

        else:
            return jsonify({"error": "Ungültige Aktion"}), 400

    finally:
        save_state(state)

    resp = _build_client_state(state, role_view, message)
    return jsonify(resp)


@app.route("/api/nextday", methods=["POST"])
def api_nextday():
    state = load_state()

    for internal in ["male", "female"]:
        if not is_day_closed_for_person(state, internal):
            return (
                jsonify({"error": f"{internal} ist für diesen Tag noch nicht fertig."}),
                400,
            )

    state["day"] += 1

    for internal in ["male", "female"]:
        for ex in EXERCISES:
            state["done"][internal][ex] = False
            state["reps"][internal][ex] += 1

    save_state(state)
    resp = _build_client_state(state, "mann", "Neuer Tag gestartet.")
    return jsonify(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)

