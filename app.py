"""
Provenance Guard - Flask app.

Milestone 5 scope: real transparency labels, rate limiting on /submit,
and the finalized /appeal endpoint. Full production layer.
"""

import uuid
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from signals import signal_1_llm_judge, signal_2_stylometric
from scoring import combine_confidence, attribution_from_confidence, label_from_attribution
from storage import log_submission, log_appeal, get_log, get_entry

app = Flask(__name__)

# Rate limiting: 10/minute covers a writer submitting a handful of drafts in
# one sitting with room to spare; 100/day stops a script from flooding the
# endpoint while still allowing a heavy user well beyond normal usage.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True)
    if not data or "text" not in data or "creator_id" not in data:
        return jsonify({"error": "request body must include 'text' and 'creator_id'"}), 400

    text = data["text"]
    creator_id = data["creator_id"]

    if not text.strip():
        return jsonify({"error": "'text' cannot be empty"}), 400

    content_id = str(uuid.uuid4())

    signal_1_result = signal_1_llm_judge(text)
    signal_1_score = signal_1_result["score"]

    signal_2_result = signal_2_stylometric(text)
    signal_2_score = signal_2_result["score"]

    confidence = combine_confidence(signal_1_score, signal_2_score)
    attribution = attribution_from_confidence(confidence)
    label = label_from_attribution(attribution)

    log_submission(
        content_id=content_id,
        creator_id=creator_id,
        signal_1_score=signal_1_score,
        signal_2_score=signal_2_score,
        confidence=confidence,
        attribution=attribution,
        label=label,
    )

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
    })


@app.route("/log", methods=["GET"])
def log():
    """Returns the most recent audit log entries. No auth - grading/documentation visibility only."""
    return jsonify({"entries": get_log()})


@app.route("/appeal", methods=["POST"])
def appeal():
    """
    Accepts an appeal from a creator disputing their content's classification.
    Updates the content's status to under_review and appends the creator's
    reasoning to the original audit log entry. No automated re-classification.
    """
    data = request.get_json(silent=True)
    if not data or "content_id" not in data or "creator_reasoning" not in data:
        return jsonify({"error": "request body must include 'content_id' and 'creator_reasoning'"}), 400

    updated = log_appeal(data["content_id"], data["creator_reasoning"])
    if updated is None:
        return jsonify({"error": "content_id not found"}), 404

    return jsonify({
        "content_id": updated["content_id"],
        "status": updated["status"],
        "message": "Appeal received and logged for review.",
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)