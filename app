from flask import Flask, render_template, jsonify, request
import json, os
from threading import Lock

STATE_FILE = "state.json"
LOCK = Lock()
DEFAULT_STATE = {
    "day": 1,
    "male": {"pushups": False, "situps": False, "squats": False},
    "female": {"pushups": False, "situps": False, "squats": False},
    "skip": {"male": [], "female": []}
}

app = Flask(__name__, static_folder="static", template_folder="templates")


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def _ensure_schema(state):
    # Fallbacks, falls alte state.json ohne neue Felder existiert
    if "male" not in state:
        state["male"] = DEFAULT_STATE["male"].copy()
    if "female" not in state:
        state["female"] = DEFAULTSTATE["female"].copy()
    if "day" not in state:
        state["day"] = 1
    if "skip" not in state:
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
    except Exception:
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
        s["day"] += 1
        s["male"] = {k: False for k in s["male"]}
        s["female"] = {k: False for k in s["female"]}
        save_state(s)
    return jsonify(s)


@app.route("/api/skip", methods=["POST"])
def api_skip():
    """
    Skip-Day pro Person:
    - setzt alle Übungen für die Person auf erledigt
    - merkt sich den Tag in s["skip"][person]
    - wenn innerhalb der letzten 6 Tage schon ein Skip war -> Cheater-Warnung
    """
    data = request.json or {}
    p = data.get("person")
    if p not in ("male", "female"):
        return jsonify({"error": "invalid"}), 400

    with LOCK:
        s = load_state()
        s = _ensure_schema(s)

        current_day = int(s.get("day", 1))
        skips = s["skip"].get(p, [])

        cheating = any((current_day - d) <= 6 for d in skips)
        skips.append(current_day)
        s["skip"][p] = skips

        # Alle Übungen für diese Person auf erledigt setzen
        for ex in s[p]:
            s[p][ex] = True

        save_state(s)

    resp = {"state": s}
    if cheating:
        who = "Mann" if p == "male" else "Frau"
        resp["warning"] = f"{who} versucht zu bescheißen!!! Zu viele Skip-Days in zu kurzer Zeit!!!"
    return jsonify(resp)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """
    Reset mit Passwort "reset":
    - verringert die Anzahl der 'Übungstage' um 10 (day - 10, mindestens 1)
    - setzt alle aktuellen Checkboxen zurück
    """
    data = request.json or {}
    if data.get("password") != "reset":
        return jsonify({"error": "forbidden"}), 403

    with LOCK:
        s = load_state()
        day = int(s.get("day", 1))
        s["day"] = max(1, day - 10)
        s["male"] = {k: False for k in s["male"]}
        s["female"] = {k: False for k in s["female"]}
        save_state(s)

    return jsonify(s)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
