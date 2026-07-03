"""
Provenance Guard - Flask app.

Milestone 3 scope: /submit wired to Signal 1 only, with a placeholder
confidence score and label. Signal 2 and real scoring land in Milestone 4.
Labels get their final text in Milestone 5.
"""

import uuid
from flask import Flask, request, jsonify

from signals import signal_1_llm_judge
from storage import log_submission, log_appeal, get_log, get_entry

app = Flask(__name__)


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True)
    if not data or "text" not in data or "creator_id" not in data:
        return jsonify({"error": "request body must include 'text' and 'creator_id'"}), 400

    text = data["text"]
    creator_id = data["creator_id"]

    if not text.strip():
        return jsonify({"error": "'text' cannot be empty"}), 400

    content_id = str(uuid.uuid4())

    # Signal 1 only for now
    signal_1_result = signal_1_llm_judge(text)
    signal_1_score = signal_1_result["score"]

    # Placeholders until Milestone 4 wires in Signal 2 and real combined scoring
    signal_2_score = None
    confidence = signal_1_score  # temporary stand-in
    attribution = "likely_ai" if signal_1_score >= 0.7 else (
        "uncertain" if signal_1_score >= 0.4 else "likely_human"
    )
    label = "placeholder label - real label text lands in Milestone 5"

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
    Stub for Milestone 5. Wired up early here so /log and content_id flow
    can be sanity-checked end to end, but the real appeals workflow (with
    validation and proper response shape) gets built out in Milestone 5.
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