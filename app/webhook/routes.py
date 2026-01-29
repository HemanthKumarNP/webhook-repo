from flask import Blueprint, request, jsonify
from datetime import datetime
from app.extensions import mongo
from flask import render_template

webhook = Blueprint("webhook", __name__, url_prefix="/webhook")


@webhook.route("/receiver", methods=["POST"])
def receiver():
    event_type = request.headers.get("X-GitHub-Event")
    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({"message": "Invalid or empty payload"}), 400

    if event_type == "push":
        handle_push(payload)

    elif event_type == "pull_request":
        handle_pull_request(payload)

    return jsonify({"status": "ok"}), 200

@webhook.route("/events", methods=["GET"])
def get_events():
    events = mongo.db.events.find().sort("timestamp", -1).limit(10)

    result = []
    for e in events:
        result.append({
            "message": e["message"]
        })

    return jsonify(result)

@webhook.route("/", methods=["GET"])
def home():
    return render_template("index.html")



# ------------------ PUSH EVENT ------------------

def handle_push(payload):
    author = payload.get("pusher", {}).get("name", "Unknown")
    ref = payload.get("ref", "")
    to_branch = ref.split("/")[-1] if ref else "unknown"
    timestamp = payload.get("head_commit", {}).get("timestamp")

    message = f'{author} pushed to "{to_branch}" on {format_time(timestamp)}'

    mongo.db.events.insert_one({
        "event_type": "PUSH",
        "author": author,
        "to_branch": to_branch,
        "timestamp": timestamp,
        "message": message
    })



# ------------------ PULL REQUEST & MERGE ------------------

def handle_pull_request(payload):
    action = payload.get("action")
    pr = payload.get("pull_request")

    author = pr["user"]["login"]
    from_branch = pr["head"]["ref"]
    to_branch = pr["base"]["ref"]

    # Pull Request Created
    if action == "opened":
        timestamp = pr["created_at"]
        message = (
            f'{author} submitted a pull request from '
            f'"{from_branch}" to "{to_branch}" on {format_time(timestamp)}'
        )

        mongo.db.events.insert_one({
            "event_type": "PULL_REQUEST",
            "author": author,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "message": message,
            "timestamp": parse_time(timestamp)
        })

    # Pull Request Merged (Brownie Points)
    elif action == "closed" and pr.get("merged"):
        timestamp = pr["merged_at"]
        message = (
            f'{author} merged branch "{from_branch}" to '
            f'"{to_branch}" on {format_time(timestamp)}'
        )

        mongo.db.events.insert_one({
            "event_type": "MERGE",
            "author": author,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "message": message,
            "timestamp": parse_time(timestamp)
        })


# ------------------ TIME HELPERS ------------------

def parse_time(timestamp):
    if not timestamp:
        return None
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

def format_time(timestamp):
    dt = parse_time(timestamp)
    if not dt:
        return "Unknown time"
    return dt.strftime("%d %B %Y - %I:%M %p UTC")
