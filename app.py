import uuid
from flask import Flask, request, jsonify 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
from datetime import datetime, timezone
from helper import compute_signal_1, compute_signal_2

DB_PATH = "audit_log.db"

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                content_id TEXT,
                creator_id TEXT,
                timestamp TEXT,
                attribution TEXT,
                confidence REAL,
                signal_1_score REAL,
                signal_2_score REAL,
                appeal_reason TEXT,
                status TEXT,
                event_type TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                content_id TEXT PRIMARY KEY,
                creator_id TEXT,
                timestamp TEXT,
                attribution TEXT,
                label TEXT,
                confidence REAL,
                signal_1_score REAL,
                signal_2_score REAL,
                appeal_reason TEXT,
                status TEXT
            )
        """)

def log_event(entry):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO audit_log (content_id, creator_id, timestamp, attribution, confidence, signal_1_score, signal_2_score, appeal_reason, status, event_type) "
            "VALUES (:content_id, :creator_id, :timestamp, :attribution, :confidence, :signal_1_score, :signal_2_score, :appeal_reason, :status, :event_type)",
            {**entry, "timestamp": datetime.now(timezone.utc).isoformat()},
        )

def read_log(limit=20):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def determine_label(confidence):
    if confidence <= 0.40:
        return "human", "Appears to be written by a person"
    if confidence <= 0.59:
        return "uncertain", "We're not sure if this was written by a person or AI"
    return "ai", "Appears to be created using AI"


def save_submission(submission):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO submissions (content_id, creator_id, timestamp, attribution, label, confidence, signal_1_score, signal_2_score, appeal_reason, status) "
            "VALUES (:content_id, :creator_id, :timestamp, :attribution, :label, :confidence, :signal_1_score, :signal_2_score, :appeal_reason, :status)",
            submission,
        )


def get_submission_by_content_id(content_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM submissions WHERE content_id = ?",
            (content_id,),
        ).fetchone()
    return dict(row) if row else None


def update_submission_appeal(content_id, creator_id, appeal_reason):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE submissions SET status = :status, appeal_reason = :appeal_reason WHERE content_id = :content_id AND creator_id = :creator_id",
            {
                "content_id": content_id,
                "creator_id": creator_id,
                "appeal_reason": appeal_reason,
                "status": "under_review",
            },
        )


def log_appeal(content_id, creator_id, appeal_reason):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO audit_log (content_id, creator_id, timestamp, attribution, confidence, signal_1_score, signal_2_score, appeal_reason, status, event_type) "
            "VALUES (:content_id, :creator_id, :timestamp, :attribution, :confidence, :signal_1_score, :signal_2_score, :appeal_reason, :status, :event_type)",
            {
                "content_id": content_id,
                "creator_id": creator_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attribution": "appeal",
                "confidence": None,
                "signal_1_score": None,
                "signal_2_score": None,
                "appeal_reason": appeal_reason,
                "status": "under_review",
                "event_type": "appeal_submitted",
            },
        )


@app.route("/")
def home():
    return "Provenance Guard is running."


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute; 100 per day", deduct_when=lambda response: response.status_code == 200)
def submit():
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    text = data.get("text")
    if len(text) < 20 or len(text) > 10000:
        return jsonify({"error": "Text length must be between 20 and 10,000 characters"}), 400
    creator_id = data.get("creator_id")
    if not text or not creator_id:
        return jsonify({"error": "Both text and creator_id are required"}), 400

    content_id = str(uuid.uuid4())
    signal_1 = compute_signal_1(text)
    signal_2 = compute_signal_2(text)
    confidence = 0.7 * signal_1 + 0.3 * signal_2

    if abs(signal_1 - signal_2) > 0.45:
        confidence *= 0.6
    confidence = max(0.0, min(1.0, confidence))

    attribution, label = determine_label(confidence)

    result = {
        "content_id": content_id,
        "attribution": attribution,
        "confidence": round(confidence, 3),
        "label": label,
        "signal_1_score": round(signal_1, 3),
        "signal_2_score": round(signal_2, 3),
    }

    save_submission({
        "content_id": result["content_id"],
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        "attribution": result["attribution"],
        "label": result["label"],
        "confidence": result["confidence"],
        "signal_1_score": result["signal_1_score"],
        "signal_2_score": result["signal_2_score"],
        "appeal_reason": None,
        "status": "classified",
    })

    log_event({
        "content_id": result["content_id"],
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        "attribution": result["attribution"],
        "confidence": result["confidence"],
        "signal_1_score": result["signal_1_score"],
        "signal_2_score": result["signal_2_score"],
        "appeal_reason": None,
        "status": "classified",
        "event_type": "classification_completed"
    })
    return jsonify(result)

@app.route("/appeal", methods=["POST"])
def appeal():
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    content_id = data.get("content_id")
    creator_id = data.get("creator_id")
    appeal_reason = data.get("appeal_reason")

    if not content_id or not creator_id or not appeal_reason:
        return jsonify({"error": "content_id, creator_id, and appeal_reason are required"}), 400

    submission = get_submission_by_content_id(content_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    if submission.get("creator_id") != creator_id:
        return jsonify({"error": "Creator ID does not match original submission"}), 403

    update_submission_appeal(content_id, creator_id, appeal_reason)
    log_event({
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        "attribution": submission.get("attribution"),
        "confidence": submission.get("confidence"),
        "signal_1_score": submission.get("signal_1_score"),
        "signal_2_score": submission.get("signal_2_score"),
        "appeal_reason": appeal_reason,
        "status": "under_review",
        "event_type": "appeal_submitted"
    })

    return jsonify({
        "content_id": content_id,
        "appeal_status": "under_review",
        "message": "Your appeal has been recorded and is under review.",
    })


@app.route("/log", methods=["GET"])
def get_log():
    return jsonify({"entries": read_log()})


if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=True)