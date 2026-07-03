# Provenance Guard - Planning

## Detection Signals

**Signal 1: LLM-as-judge (Groq)**
This one checks for the patterns that make AI text sound like AI text. Stuff like generic transitions ("it is important to note," "furthermore"), phrasing that's hedged but still sounds confident, and paragraphs that are all suspiciously the same length and structure. I prompt the model to give me a structured assessment and parse that into a float between 0 and 1, where 0 means confidently human and 1 means confidently AI.

**Signal 2: Stylometric heuristics**
This one is just math, no API call. I measure sentence length variance and type-token ratio (basically how diverse the vocabulary is), normalize each to 0-1, and average them into one score. Low variance and low diversity trend toward 1 (AI-like). High variance and high diversity trend toward 0 (human-like).

**Combining into confidence score**
`confidence = (0.7 * signal_1_score) + (0.3 * signal_2_score)`
Originally started at 0.5/0.5 with no evidence either signal was more reliable. Once I actually tested it (Milestone 4), Signal 2's type-token-ratio component turned out to be unreliable on short text (see Edge Case #2 below) and was dragging combined scores toward "human" even when Signal 1 was confidently right. Reweighted to trust Signal 1 more. Even at 0.7/0.3, a clearly-AI test case (signal_1=0.90, signal_2=0.14) lands at confidence=0.67, just under the 0.7 "likely_ai" threshold, landing in "uncertain" instead. I'm leaving this as-is rather than tuning weights further to force one test case over a line. It's a real limitation of Signal 2 on short text, documented honestly rather than hidden.

## Uncertainty Representation

A confidence score here isn't a real calibrated probability of "AI-ness." It's just a blend of two heuristic signals, so I want to be upfront that it's an estimate, not a verdict.

- **confidence ≥ 0.7** → "likely_ai"
- **0.4 ≤ confidence < 0.7** → "uncertain"
- **confidence < 0.4** → "likely_human"

So a score of 0.6 basically means both signals are leaning AI-ish, but not enough to be confident about it. The system should treat that as genuine uncertainty instead of just rounding up to "likely AI."

Both raw signal outputs are already 0-1 by design (Signal 1 through the prompted output, Signal 2 through min-max normalization), so I don't need a separate calibration step beyond the weighted average.

## Transparency Label Design

- **High-confidence AI (≥0.7):**
  *"This content shows strong indicators of AI generation. Our detection signals consistently identified patterns associated with AI-written text."*
- **Uncertain (0.4-0.69):**
  *"This content shows some patterns associated with AI generation, but our confidence is not high enough for a definitive classification."*
- **High-confidence human (<0.4):**
  *"This content shows patterns consistent with human authorship. Our detection signals did not identify strong indicators of AI generation."*

## Appeals Workflow

Any creator can appeal their own content by sending the `content_id` plus a `creator_reasoning` field explaining why they think the classification is wrong.

When an appeal comes in:
1. The content's status changes from `"classified"` to `"under_review"`.
2. The appeal gets appended to the same audit log entry as the original classification, not written as a separate record. The reviewer needs both together to make sense of it.
3. The system sends back a confirmation with the updated status.

If a human reviewer opens the appeal queue, they'd see the original text (or a reference to it), both individual signal scores, not just the combined confidence, the combined score and label, the creator's reasoning, and timestamps for the original classification and the appeal. I want the individual signals broken out because it actually tells the reviewer something. If Signal 1 and Signal 2 disagreed, that's a decent sign the case is genuinely ambiguous instead of just a clean miss.

No automated re-classification happens on appeal. This is purely a flag for human review.

## Anticipated Edge Cases

1. **Formal writing by non-native English speakers.** Careful, hedge-heavy, grammatically conservative writing can trip Signal 1's "AI-ish" pattern matching even when it's genuinely human. This is a fairness problem, not just a technical one, and it's the kind of thing I care about generally.
2. **Short-form text (under ~100 words).** Type-token ratio gets noisy at short lengths, so a two-sentence submission could produce a wildly unreliable stylometric score no matter who actually wrote it.
3. **Lightly-edited AI output.** If a human takes AI-generated text and edits it a bit, that can reintroduce enough irregularity to fool Signal 2, even though the underlying generation didn't change. Signal 2 just can't catch that by design.

## Architecture

```
SUBMISSION FLOW
POST /submit (text, creator_id)
      |
      v
  assign content_id
      |
      +--------------+--------------+
      v              v              |
  Signal 1        Signal 2          |
  (LLM judge)    (stylometrics)     |
   score 0-1       score 0-1        |
      +------+-------+              |
             v                      |
     confidence scoring             |
      (weighted combine)            |
             v                      |
      transparency label            |
   (likely AI / uncertain /         |
       likely human)                |
             v                      v
        audit log <----------- content_id, scores
             |
             v
   response: {content_id, attribution, confidence, label}

APPEAL FLOW
POST /appeal (content_id, creator_reasoning)
      |
      v
  status -> "under_review"
      |
      v
  append to existing audit log entry
      |
      v
  response: confirmation
```

A submission gets a `content_id`, runs through both signals independently, gets combined into one confidence score, gets mapped to a label, and gets logged in full before the response goes back. An appeal points at that same `content_id`, flips the status to `under_review`, and adds the creator's reasoning to the original log entry instead of making a new one, so the classification and the dispute over it live in one place.

## AI Tool Plan

**M3 (submission endpoint + first signal):**
- Spec sections I'll give it: Detection Signals + the Architecture diagram
- What I'll ask for: Flask app skeleton with the `POST /submit` route stub, plus the Signal 1 (Groq) function
- How I'll verify: call the Signal 1 function directly with a couple test inputs and check the raw output before wiring it into the endpoint. Make sure the function actually returns a 0-1 float like the spec says.

**M4 (second signal + confidence scoring):**
- Spec sections I'll give it: Detection Signals + Uncertainty Representation + the diagram
- What I'll ask for: the Signal 2 (stylometric) function, plus the scoring logic that combines both signals the way I specified
- How I'll verify: run my four calibration inputs (clear AI, clear human, two borderline) and check the scores come out in the order I'd expect. Also double check the generated code actually uses 0.5/0.5 weighting and the 0.4/0.7 thresholds instead of just making up its own.

**M5 (production layer):**
- Spec sections I'll give it: Transparency Label Design + Appeals Workflow + the diagram
- What I'll ask for: a label function that maps confidence to the right label text, and the `POST /appeal` endpoint
- How I'll verify: submit inputs that hit all three score ranges and check the label text matches what I wrote exactly. Submit an appeal and confirm `GET /log` shows `status: "under_review"` and `appeal_reasoning` on the right entry.