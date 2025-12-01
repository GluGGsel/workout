from flask import Flask, render_template, jsonify, request
import json, os
from threading import Lock

STATE_FILE = "state.json"
LOCK = Lock()

DEFAULT_STATE = {
    "day": 1,
    "male": {"pushups": False, "situps": False, "squats": False},
    "female": {"pushups": False, "situps": False, "squats": False}
}

app = Flask(__name__, static_folder="static", template_folder="templates")

def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)

def load_state():
    # Falls Datei fehlt oder leer ist: initialisieren
    if not os.path.exists(STATE_FILE) or os.path.getsize(STATE_FILE) == 0:
        save_state(DEFAULT_STATE)
    # Versuche zu laden, bei Fehlern zurücksetzen
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(load_state())

@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.json or {}
    person = data.get("person")
    exercise = data.get("exercise")
    if person not in ("male", "female") or exercise not in ("pushups","situps","squats"):
        return jsonify({"error":"invalid"}), 400
    with LOCK:
        state = load_state()
        state[person][exercise] = not bool(state[person][exercise])
        save_state(state)
    return jsonify(state)

@app.route("/api/next_day", methods=["POST"])
def api_next_day():
    with LOCK:
        state = load_state()
        def completed(p):
            return all(bool(v) for v in state[p].values())
        if not (completed("male") and completed("female")):
            return jsonify({"error":"not_completed"}), 400
        state["day"] += 1
        state["male"] = {k: False for k in state["male"].keys()}
        state["female"] = {k: False for k in state["female"].keys()}
        save_state(state)
    return jsonify(state)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
