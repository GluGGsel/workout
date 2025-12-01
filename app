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
    with open(tmp, "w") as f: json.dump(state, f)
    os.replace(tmp, STATE_FILE)

def load_state():
    if not os.path.exists(STATE_FILE) or os.path.getsize(STATE_FILE) == 0:
        save_state(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except Exception:
        save_state(DEFAULT_STATE); return DEFAULT_STATE

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/state")
def api_state(): return jsonify(load_state())

@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.json or {}
    p, e = data.get("person"), data.get("exercise")
    if p not in ("male","female") or e not in ("pushups","situps","squats"):
        return jsonify({"error":"invalid"}),400
    with LOCK:
        s = load_state(); s[p][e] = not s[p][e]; save_state(s)
    return jsonify(s)

@app.route("/api/next_day", methods=["POST"])
def api_next_day():
    with LOCK:
        s = load_state()
        done = lambda p: all(s[p].values())
        if not (done("male") and done("female")):
            return jsonify({"error":"not_completed"}),400
        s["day"] += 1
        s["male"]   = {k: False for k in s["male"]}
        s["female"] = {k: False for k in s["female"]}
        save_state(s)
    return jsonify(s)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
