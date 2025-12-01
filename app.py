from flask import Flask, render_template, jsonify, request
import json, os
from threading import Lock

STATE_FILE = "state.json"
LOCK = Lock()

DEFAULT_REPS = 10

DEFAULT_STATE = {
    "day": 1,
    "male": {"pushups": False, "situps": False, "squats": False},
    "female": {"pushups": False, "situps": False, "squats": False},
    "reps": {
        "male": {"pushups": DEFAULT_REPS, "situps": DEFAULT_REPS, "squats": DEFAULT_REPS},
        "female": {"pushups": DEFAULT_REPS, "situps": DEFAULT_REPS, "squats": DEFAULT_REPS}
    },
    "skip": {"male": [], "female": []},
    "injured": {"male": [], "female": []},
    "cant": {"male": [], "female": []},
    "overall": {
        "male": {"pushups": 0, "situps": 0, "squats": 0},
        "female": {"pushups": 0, "situps": 0, "squats": 0}
    }
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

    # checkbox-Status
    for p in ("male", "female"):
        if p not in state or not isinstance(state[p], dict):
            state[p] = {"pushups": False, "situps": False, "squats": False}
        for ex in ("pushups", "situps", "squats"):
            state[p].setdefault(ex, False)

    # reps
    if "reps" not in state or not isinstance(state["reps"], dict):
        state["reps"] = DEFAULT_STATE["reps"]
    for p in ("male", "female"):
        if p not in state["reps"] or not isinstance(state["reps"][p], dict):
            state["reps"][p] = DEFAULT_STATE["reps"][p]
        for ex in ("pushups", "situps", "squats"):
            state["reps"][p].setdefault(ex, DEFAULT_REPS)

    # skip
    if "skip" not in state or not isinstance(state["skip"], dict):
        state["skip"] = {"male": [], "female": []}
    for p in ("male", "female"):
        state["skip"].setdefault(p, [])

    # injured
    if "injured" not in state or not isinstance(state["injured"], dict):
        state["injured"] = {"male": [], "female": []}
    for p in ("male", "female"):
        state["injured"].setdefault(p, [])

    # cant (ich kann nicht mehr)
    if "cant" not in state or not isinstance(state["cant"], dict):
        state["cant"] = {"male": [], "female": []}
    for p in ("male", "female"):
        state["cant"].setdefault(p, [])

    # overall
    if "overall" not in state or not isinstance(state["overall"], dict):
        state["overall"] = DEFAULT_STATE["overall"]
    for p in ("male", "female"):
        if p not in state["overall"] or not isinstance(state["overall"][p], dict):
            state["overall"][p] = {"pushups": 0, "situps": 0, "squats": 0}
        for ex in ("pushups", "situps", "squats"):
            state["overall"][p].setdefault(ex, 0)

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

        def done(person):
            return all(s[person].values())

        if not (done("male") and done("female")):
            return jsonify({"error": "not_completed"}), 400

        day = s["day"]

        # Overall-Counter: nur wenn NICHT Skip und NICHT injured
        for p in ("male", "female"):
            if (day not in s["skip"][p]) and (day not in s["injured"][p]):
                for ex in ("pushups", "situps", "squats"):
                    if s[p][ex]:
                        s["overall"][p][ex] += s["reps"][p][ex]

        # nächster Tag
        s["day"] += 1

        # Checkboxes resetten
        for p in ("male", "female"):
            s[p] = {k: False for k in s[p]}

        # Reps +1 für beide Personen / alle Übungen
        for p in ("male", "female"):
            for ex in ("pushups", "situps", "squats"):
                s["reps"][p][ex] = max(1, s["reps"][p][ex] + 1)

        save_state(s)
    return jsonify(s)


@app.route("/api/skip", methods=["POST"])
def api_skip():
    data = request.json or {}
    p = data.get("person")
    if p not in ("male", "female"):
        return jsonify({"error": "invalid"}), 400

    with LOCK:
        s = load_state()
        day = s["day"]

        cheating = any((day - d) <= 6 for d in s["skip"][p])
        if day not in s["skip"][p]:
            s["skip"][p].append(day)

        for ex in ("pushups", "situps", "squats"):
            s[p][ex] = True

        save_state(s)

    resp = {"state": s}
    if cheating:
        who = "Mann" if p == "male" else "Frau"
        resp["warning"] = f"{who} versucht zu bescheißen!!!"
    return jsonify(resp)


@app.route("/api/injured", methods=["POST"])
def api_injured():
    data = request.json or {}
    p = data.get("person")
    if p not in ("male", "female"):
        return jsonify({"error": "invalid"}), 400

    with LOCK:
        s = load_state()
        day = s["day"]
        if day not in s["injured"][p]:
            s["injured"][p].append(day)
        for ex in ("pushups", "situps", "squats"):
            s[p][ex] = True
        save_state(s)
    return jsonify(s)


@app.route("/api/reps_reduce", methods=["POST"])
def api_reps_reduce():
    data = request.json or {}
    p, pw = data.get("person"), data.get("password")
    if p not in ("male", "female"):
        return jsonify({"error": "invalid"}), 400
    if pw != "reset":
        return jsonify({"error": "forbidden"}), 403

    with LOCK:
        s = load_state()
        day = s["day"]
        if day not in s["cant"][p]:
            s["cant"][p].append(day)
        for ex in ("pushups", "situps", "squats"):
            s["reps"][p][ex] = max(1, s["reps"][p][ex] - 10)
        save_state(s)
    return jsonify(s)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
