import json
import os
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

STATE_FILE = "state.json"
PHRASES_FILE = "static/phrases.json"


def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "day": 1,
            "reps": {
                "male": {"squats": 10, "situps": 10, "pushups": 10},
                "female": {"squats": 10, "situps": 10, "pushups": 10}
            },
            "done": {
                "male": {"squats": False, "situps": False, "pushups": False},
                "female": {"squats": False, "situps": False, "pushups": False}
            },
            "skip": {"male": [], "female": []},
            "cant": {"male": [], "female": []},
            "injured": {"male": [], "female": []},
            "overall": {
                "male": {"squats": 0, "situps": 0, "pushups": 0},
                "female": {"squats": 0, "situps": 0, "pushups": 0}
            },
            "phrase_of_day": {}
        }
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def load_phrases():
    with open(PHRASES_FILE, "r") as f:
        return json.load(f)


@app.route("/")
def index():
    view = request.args.get("view", "").lower()

    if view == "frau" or view == "female":
        manifest_file = "manifest-frau.json"
    else:
        manifest_file = "manifest-mann.json"

    male_name = request.args.get("male_name") or request.args.get("mann") or "Mann"
    female_name = request.args.get("female_name") or request.args.get("frau") or "Frau"

    return render_template(
        "index.html",
        manifest_file=manifest_file,
        male_name=male_name,
        female_name=female_name,
    )


@app.route("/api/state")
def api_state():
    return jsonify(load_state())


@app.route("/api/done", methods=["POST"])
def api_done():
    data = request.json
    person = data["person"]
    exercise = data["exercise"]

    state = load_state()
    state["done"][person][exercise] = True
    state["overall"][person][exercise] += state["reps"][person][exercise]

    save_state(state)
    return jsonify({"status": "ok"})


@app.route("/api/skip", methods=["POST"])
def api_skip():
    data = request.json
    person = data["person"]

    state = load_state()
    state["skip"][person].append(state["day"])
    save_state(state)
    return jsonify({"status": "ok"})


@app.route("/api/cant", methods=["POST"])
def api_cant():
    data = request.json
    person = data["person"]

    state = load_state()
    state["cant"][person].append(state["day"])
    save_state(state)
    return jsonify({"status": "ok"})


@app.route("/api/injured", methods=["POST"])
def api_injured():
    data = request.json
    person = data["person"]

    state = load_state()
    state["injured"][person].append(state["day"])
    save_state(state)
    return jsonify({"status": "ok"})


@app.route("/api/nextday", methods=["POST"])
def api_nextday():
    state = load_state()

    # Voraussetzungen: beide fertig oder Skip/Can't/Verletzt
    for person in ["male", "female"]:
        all_done = all(state["done"][person].values())
        skipped = state["day"] in state["skip"][person]
        cant = state["day"] in state["cant"][person]
        injured = state["day"] in state["injured"][person]

        if not (all_done or skipped or cant or injured):
            return jsonify({"error": f"{person} ist noch nicht fertig."}), 400

    # Reset für nächsten Tag
    state["day"] += 1
    for person in ["male", "female"]:
        for ex in ["squats", "situps", "pushups"]:
            state["done"][person][ex] = False
            state["reps"][person][ex] += 1  # tägliches Steigern

    save_state(state)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
