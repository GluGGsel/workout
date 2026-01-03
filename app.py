import os
import json
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_STATE_FILE = os.path.join(BASE_DIR, "state.json")
STATE_FILE = os.environ.get("WC_STATE_FILE", DEFAULT_STATE_FILE)

DEFAULT_INSTANCE_FILE = os.path.join(BASE_DIR, "config", "instance.json")
INSTANCE_FILE = os.environ.get("WC_INSTANCE_FILE", DEFAULT_INSTANCE_FILE)

OVERRIDE_STATIC_DIR = os.environ.get("WC_STATIC_DIR", os.path.join(BASE_DIR, "config", "static"))

DEFAULT_MALE_NAME = "A"
DEFAULT_FEMALE_NAME = "B"
DEFAULT_TITLE = "Daily Workout"

def load_instance():
    data = {}
    try:
        if os.path.exists(INSTANCE_FILE):
            with open(INSTANCE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
    except Exception:
        data = {}
    male = data.get("male_name", DEFAULT_MALE_NAME)
    female = data.get("female_name", DEFAULT_FEMALE_NAME)
    title = data.get("title", DEFAULT_TITLE)
    return male, female, title

def state_default():
    male, female, _ = load_instance()
    return {
        "male_name": male,
        "female_name": female,
        "male_count": 0,
        "female_count": 0,
        "male_skipped": 0,
        "female_skipped": 0,
        "male_cant": 0,
        "female_cant": 0,
        "male_cheater": 0,
        "female_cheater": 0,
        "male_injured": 0,
        "female_injured": 0,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = state_default()
        except Exception:
            data = state_default()
    else:
        data = state_default()

    male, female, _ = load_instance()
    data["male_name"] = male
    data["female_name"] = female

    if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
        data.update({
            "male_count": 0,
            "female_count": 0,
            "male_skipped": 0,
            "female_skipped": 0,
            "male_cant": 0,
            "female_cant": 0,
            "male_cheater": 0,
            "female_cheater": 0,
            "male_injured": 0,
            "female_injured": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
        })
        save_state(data)

    return data

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)
    os.replace(tmp, STATE_FILE)

def load_phrases(filename, fallback):
    paths = [
        os.path.join(OVERRIDE_STATIC_DIR, "phrases", filename),
        os.path.join(BASE_DIR, "static", "phrases", filename),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
            except Exception:
                pass
    return fallback

def render_phrase(template, male_name, female_name):
    return (template
            .replace("{male_name}", male_name)
            .replace("{female_name}", female_name))

@app.route("/")
def index():
    state = load_state()
    _, _, title = load_instance()
    return render_template(
        "index.html",
        male_name=state["male_name"],
        female_name=state["female_name"],
        male_count=state["male_count"],
        female_count=state["female_count"],
        male_skipped=state["male_skipped"],
        female_skipped=state["female_skipped"],
        male_cant=state["male_cant"],
        female_cant=state["female_cant"],
        male_cheater=state["male_cheater"],
        female_cheater=state["female_cheater"],
        male_injured=state["male_injured"],
        female_injured=state["female_injured"],
        title=title,
    )

@app.route("/static/<path:filename>")
def static_files(filename):
    candidate = os.path.join(OVERRIDE_STATIC_DIR, filename)
    if os.path.exists(candidate) and os.path.isfile(candidate):
        return send_from_directory(OVERRIDE_STATIC_DIR, filename)
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

@app.route("/update_count", methods=["POST"])
def update_count():
    data = request.get_json() or {}
    person = data.get("person")
    action = data.get("action")
    state = load_state()

    def bump(prefix):
        key = f"{prefix}_{action}"
        mapping = {
            "done": f"{prefix}_count",
            "skip": f"{prefix}_skipped",
            "cant": f"{prefix}_cant",
            "cheater": f"{prefix}_cheater",
            "injured": f"{prefix}_injured",
        }
        k = mapping.get(action)
        if k:
            state[k] = int(state.get(k, 0)) + 1

    if person == "male":
        bump("male")
    elif person == "female":
        bump("female")

    save_state(state)
    return jsonify(state)

@app.route("/get_state")
def get_state():
    return jsonify(load_state())

@app.route("/get_phrase", methods=["POST"])
def get_phrase():
    state = load_state()
    male_name = state["male_name"]
    female_name = state["female_name"]

    male_count = state["male_count"]
    female_count = state["female_count"]

    all_done_phrases = load_phrases("all_done", ["{male_name} and {female_name} did it. Miracles happen."])
    none_done_phrases = load_phrases("none_done.json", ["{male_name} and {female_name} did nothing. Consistency is overrated."])
    one_done_male_phrases = load_phrases("one_done_male.json", ["{male_name} did it, {female_name} didn’t. Democracy has failed."])
    one_done_female_phrases = load_phrases("one_done_female.json", ["{female_name} did it, {male_name} didn’t. Equality achieved."])

    if male_count > 0 and female_count > 0:
        phrase = random.choice(all_done_phrases)
    elif male_count == 0 and female_count == 0:
        phrase = random.choice(none_done_phrases)
    elif male_count > 0:
        phrase = random.choice(one_done_male_phrases)
    else:
        phrase = random.choice(one_done_female_phrases)

    return jsonify({"phrase": render_phrase(phrase, male_name, female_name)})

@app.route("/reset", methods=["POST"])
def reset():
    state = load_state()
    state.update({
        "male_count": 0,
        "female_count": 0,
        "male_skipped": 0,
        "female_skipped": 0,
        "male_cant": 0,
        "female_cant": 0,
        "male_cheater": 0,
        "female_cheater": 0,
        "male_injured": 0,
        "female_injured": 0,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    save_state(state)
    return jsonify(state)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
