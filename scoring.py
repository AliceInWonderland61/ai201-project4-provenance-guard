"""
Confidence scoring for Provenance Guard.

Combines Signal 1 (LLM judge) and Signal 2 (stylometric) into a single
confidence score, and maps that score to an attribution category, per the
thresholds defined in planning.md's Uncertainty Representation section.
"""

SIGNAL_1_WEIGHT = 0.7
SIGNAL_2_WEIGHT = 0.3

LIKELY_AI_THRESHOLD = 0.7
UNCERTAIN_THRESHOLD = 0.4


def combine_confidence(signal_1_score: float, signal_2_score: float) -> float:
    """Weighted average of both signal scores, per planning.md."""
    confidence = (SIGNAL_1_WEIGHT * signal_1_score) + (SIGNAL_2_WEIGHT * signal_2_score)
    return max(0.0, min(1.0, confidence))


def attribution_from_confidence(confidence: float) -> str:
    """Maps a confidence score to one of three attribution categories."""
    if confidence >= LIKELY_AI_THRESHOLD:
        return "likely_ai"
    elif confidence >= UNCERTAIN_THRESHOLD:
        return "uncertain"
    else:
        return "likely_human"


# Exact label text from planning.md's Transparency Label Design section.
# These are final copy, not placeholders -- keep in sync with planning.md
# if either changes.
LABEL_TEXT = {
    "likely_ai": (
        "This content shows strong indicators of AI generation. Our detection "
        "signals consistently identified patterns associated with AI-written text."
    ),
    "uncertain": (
        "This content shows some patterns associated with AI generation, but "
        "our confidence is not high enough for a definitive classification."
    ),
    "likely_human": (
        "This content shows patterns consistent with human authorship. Our "
        "detection signals did not identify strong indicators of AI generation."
    ),
}


def label_from_attribution(attribution: str) -> str:
    """Maps an attribution category to its exact transparency label text."""
    return LABEL_TEXT.get(attribution, "Unable to generate a label for this classification.")


if __name__ == "__main__":
    # Quick sanity check on the threshold boundaries and label text.
    test_cases = [0.0, 0.39, 0.4, 0.6, 0.69, 0.7, 1.0]
    for score in test_cases:
        attribution = attribution_from_confidence(score)
        label = label_from_attribution(attribution)
        print(f"confidence={score:.2f} -> {attribution} -> {label}")