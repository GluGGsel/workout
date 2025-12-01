from flask import Flask, render_template, jsonify, request
import json, os
from threading import Lock

STATE_FILE = "state.json"
LOCK = Lock()

DEFAULT_STATE = {
    "day": 1,
    "male": {"pushups": False, "situps": False, "squats": False},
    "female": {"pushups": False, "situps": False, "squats": False},
    "reps": {
        "male": {"pushups": 30, "situps": 30, "squats": 30},
        "female": {"pushups": 30, "situps": 30, "squats": 30},
    },
    "skip": {"male": [], "female": []}
}

app = Flask(__name__, static_folder="static", template_folder="templates")


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def _ensure_schema(state):
    # day
    if "day" not in state or not isinstance(state["day"], int):
        state["day"] = 1

    # male / female booleans
    for p in ("male", "female"):
        if p not in state or not isinstance(state[p], dict):
            state[p] = DEFAULT_STATE[p].copy()
        else:
            for ex in DEFAULT_STATE[p]:
                state[p].setdefault(ex, False)

    # reps pro Person
    if "reps" not in state or not isinstance(state["reps"], dict):
        state["reps"] = DEFAULT_STATE["reps"]
    else:
        for p in ("male", "female"):
            if p not in state["reps"]:
                state["reps"][p] = DEFAULT_STATE["reps"][p]
            for ex in ("pushups", "situps", "squats"):
                state["reps"][p].setdefault(ex, 30)

    # skip arrays
    if "skip" not in state or not isinstance(state["skip"], dict):
        state["skip"] = {"male": [], "female": []}
    else:
        state["skip"].setdefault("male", [])
        state["skip"].setdefault("female", [])

    return state


def load_state():
    if not os.path.exists(STATE_FILE) or os.path.getsize(STATE_FILE) == 0:
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except:
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE

    return _ensure_schema(state)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(load_state())


@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.json or {}
    p, e = data.get("person"), data.get("exercise")

    if p not in ("male", "female") or e not in ("pushups", "situps", "squats"):
        return jsonify({"error": "invalid"}), 400

    with LOCK:
        s = load_state()
        s[p][e] = not s[p][e]
        save_state(s)

    return jsonify(s)


@app.route("/api/next_day", methods=["POST"])
def api_next_day():
    with LOCK:
        s = load_state()

        done = lambda p: all(s[p].values())

        if not (done("male") and done("female")):
            return jsonify({"error": "not_completed"}), 400

        # Tag +1
        s["day"] += 1

        # Übungen resetten
        for p in ("male", "female"):
            s[p] = {k: False for k in s[p]}

        # Reps steigen +1 für beide Personen
        for p in ("male", "female"):
            for ex in s["reps"][p]:
                s["reps"][p][ex] = max(1, s["reps"][p][ex] + 1)

        save_state(s)

    return jsonify(s)


@app.route("/api/skip", methods=["POST"])
def api_skip():
    """
    Skip-Day:
    - setzt alle Übungen auf erledigt
    - speichert den Tag
    - wenn 2 Skips in 6 Tagen → Cheater-Warnung
    """
    data = request.json or {}
    p = data.get("person")

    if p not in ("male", "female"):
        return jsonify({"error": "invalid"}), 400

    with LOCK:
        s = load_state()
        current_day = s["day"]

        cheating = any((current_day - d) <= 6 for d in s["skip"][p])
        s["skip"][p].append(current_day)

        # Person komplett auf erledigt setzen
        for ex in s[p]:
            s[p][ex] = True

        save_state(s)

    resp = {"state": s}
    if cheating:
        who = "Mann" if p == "male" else "Frau"
        resp["warning"] = f"{who} versucht zu bescheißen!!!"

    return jsonify(resp)


@app.route("/api/reps_reduce", methods=["POST"])
def api_reps_reduce():
    """
    Button: "Ich kann nicht mehr"
    - Passwort: reset
    - reduziert Reps dieser Person um 10 (min 1)
    """
    data = request.json or {}
    p = data.get("person")
    pw = data.get("password")

    if p not in ("male", "female"):
        return jsonify({"error": "invalid"}), 400

    if pw != "reset":
        return jsonify({"error": "forbidden"}), 403

    with LOCK:
        s = load_state()
        for ex in s["reps"][p]:
            s["reps"][p][ex] = max(1, s["reps"][p][ex] - 10)
        save_state(s)

    return jsonify(s)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
