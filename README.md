# Provenance Guard

An AI-powered content attribution system that helps creative platforms distinguish between **human-written** and **AI-generated** text through a transparent, confidence-based decision process.

Unlike traditional binary AI detectors, Provenance Guard combines **semantic analysis using a Large Language Model (LLM)** with **stylometric heuristics** to produce an interpretable confidence score rather than an absolute claim. The system also supports an appeal workflow, structured audit logging, and rate limiting to promote fairness, transparency, and traceability.

---

## Project Overview

The rapid adoption of generative AI has created new challenges for educational institutions, publishers, and online content platforms. Existing AI detectors often return a simple "AI" or "Human" label without explaining how the decision was reached or expressing uncertainty.

Provenance Guard addresses this problem by combining multiple independent detection signals into a single confidence score. Instead of forcing every submission into a binary category, the system communicates uncertainty through transparency labels and allows creators to appeal decisions they believe are incorrect.

The project was implemented using **Flask**, **Groq LLM**, **Python-based stylometric analysis**, **SQLite**, and **Flask-Limiter**.

---

## Features

- Dual-signal AI attribution system
- Groq LLM semantic analysis
- Python stylometric heuristic analysis
- Confidence-based scoring
- Human-readable transparency labels
- Appeal submission workflow
- Structured audit logging
- Rate limiting against abuse
- RESTful API design
- SQLite persistence layer

---

# System Architecture Overview

Every submission follows a transparent processing pipeline instead of a black-box decision.

1. The creator submits text through the `/submit` endpoint.
2. The request passes through rate limiting to prevent automated abuse.
3. The request is validated, including required fields and supported input length.
4. A unique `content_id` is generated.
5. The submission is analyzed independently by two detection signals:
   - LLM Semantic Classification
   - Stylometric Heuristic Analysis
6. The two signals are combined into a weighted confidence score.
7. If the signals strongly disagree, a confidence reduction is applied.
8. The final score is converted into a transparency label.
9. The current submission state is stored in the **Submissions** table.
10. A complete event record is appended to the **Audit Log**.
11. The API returns the attribution result, confidence score, and transparency label.

If a creator disagrees with the result, they may submit an appeal through `/appeal`. The system updates the submission status to **Under Review**, records the appeal in the audit log, and preserves the complete history for future review.

---

# Architecture Diagram

```text
                                        ┌──────────────────────────┐
                                        │        User Client       │
                                        │  (Creator submits text)  │
                                        └─────────────┬────────────┘
                                                      │
                                                      ▼
                                            POST /submit
                                                      │
                                                      ▼
                                        Rate Limiter
                                                      │
                                                      ▼
                                        Request Validation
                                                      │
                                                      ▼
                                        Generate content_id
                                                      │
                                                      ▼
                              ┌─────────────────────────────┐
                              │ Signal 1 : Groq LLM         │
                              │ Semantic Classification     │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                                     LLM Score (0–1)
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │ Signal 2 : Stylometry       │
                              │ Sentence Statistics         │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                                Stylometric Score (0–1)
                                             │
                                             ▼
                               Confidence Scoring Engine
                                             │
                                             ▼
                                 Transparency Label
                                             │
                                             ▼
                  Update Submissions Table + Append Audit Log
                                             │
                                             ▼
                                      JSON Response
```

---

# Detection Signals

Rather than relying on a single detector, Provenance Guard combines two independent signals that evaluate different characteristics of the submitted text.

This multi-signal approach improves robustness and allows the system to express uncertainty whenever the signals disagree.

---

## Signal 1 — LLM Semantic Classification

### What it measures

The first signal evaluates the text holistically using a Groq-hosted Large Language Model.

Instead of looking at grammar or word counts, it examines higher-level characteristics including:

- semantic coherence
- writing consistency
- generic phrasing
- personal grounding
- stylistic predictability
- overall discourse quality

The LLM returns a normalized score between **0.0** and **1.0**.

```text
0.0 → Strongly Human

1.0 → Strongly AI
```

### Why this signal?

Semantic understanding captures patterns that handcrafted statistical features cannot. AI-generated text often maintains highly consistent structure and generalized language across an entire passage, while human writing tends to contain irregularities, personal references, and stylistic variation.

### What it cannot capture

Because this signal is generated by an LLM, it may incorrectly classify:

- academic writing
- technical documentation
- legal documents
- highly formal reports

These writing styles naturally resemble AI output despite being entirely human-written.

---

## Signal 2 — Stylometric Heuristic Analysis

The second signal analyzes measurable writing statistics directly in Python.

Unlike the LLM, this signal focuses on structural characteristics rather than semantic meaning.

The following features are extracted:

- Sentence Length Variance
- Type–Token Ratio (Lexical Diversity)
- Punctuation Density

Each metric is normalized and combined into a single stylometric score.

```text
S_sty =
0.4 × Sentence Variance +
0.4 × Type Token Ratio +
0.2 × Punctuation Density
```

The resulting score is normalized between

```text
0.0 → Human-like writing

1.0 → AI-like writing
```

### Why these features?

**Sentence Length Variance (40%)**

Human writing naturally alternates between short and long sentences. AI-generated content often maintains a more uniform rhythm.

**Type–Token Ratio (40%)**

This measures vocabulary diversity. Human writers typically introduce more lexical variation, whereas AI systems frequently reuse similar words and transitions.

**Punctuation Density (20%)**

Punctuation contributes stylistic information but varies considerably across genres. Therefore it serves as a supporting feature rather than a dominant signal.

### What this signal cannot capture

Stylometric analysis is vulnerable to intentional manipulation.

For example:

- manually editing AI text
- adding slang
- inserting spelling mistakes
- changing punctuation

can make AI-generated text appear statistically similar to human writing without changing its semantic origin.

---

# Confidence Scoring

Both detection signals produce normalized scores between **0** and **1**.

These are combined into a single confidence score using weighted averaging.

```text
S_final =
(0.7 × S_ai)
+
(0.3 × S_sty)
```

The LLM receives a higher weight because it captures semantic and contextual properties that stylometric statistics cannot represent.

The stylometric signal acts as a complementary stabilizer, reducing over-reliance on a single model.

---

## Signal Disagreement

If both signals strongly disagree,

```text
D = |S_ai − S_sty|
```

and

```text
D > 0.45
```

the confidence score is reduced:

```text
confidence = confidence × 0.6
```

This prevents the system from making overconfident decisions when the underlying evidence conflicts.

Instead of forcing a binary classification, Provenance Guard intentionally shifts such cases toward the **Uncertain** category.

---

## Why this approach?

A single detector can easily become biased toward one writing style.

Combining semantic reasoning with statistical analysis improves robustness because the two signals evaluate fundamentally different properties of the text.

If deployed in production, future improvements would likely include:

- adaptive weighting
- domain-specific calibration
- additional stylometric features
- ensemble semantic models
- confidence calibration using larger benchmark datasets

rather than relying on fixed thresholds.

---

### Example submissions

High-confidence case:
- Example text: a polished, highly structured paragraph that reads like a formal, model-generated summary.
- Signal 1: 0.91
- Signal 2: 0.82
- Final confidence: 0.88
- Result: high-confidence AI-like classification

Lower-confidence case:
- Example text: a short, conversational, slightly messy passage with irregular phrasing and informal punctuation.
- Signal 1: 0.48
- Signal 2: 0.32
- Final confidence: 0.42
- Result: lower-confidence, more human-leaning classification

If I were deploying this for real, I would want to change the scoring in two ways: first, I would calibrate it against a labeled dataset rather than relying entirely on hand-designed heuristics, and second, I would add a more adaptive weighting scheme that can respond differently depending on how much the two signals disagree.

## Transparency Label

The system displays one of three transparency labels depending on the final confidence score.

### AI
If the confidence score is ≥0.60, the system returns:
Displayed text:

> Appears to be created using AI


### Human
If the confidence score is ≤0.40, the system returns:
Displayed text:

> Appears to be written by a person


### Uncertain
If the confidence score is between 0.41 and 0.59, the system returns:
Displayed text:

> We're not sure if this was written by a person or AI


## Rate Limiting

The `/submit` endpoint uses Flask-Limiter with the following limits:

- 10 requests per minute per IP address
- 100 requests per day per IP address

These values were chosen to allow normal creators to submit a few attempts or corrections without being blocked, while still limiting obvious abuse. The daily cap is especially important because this service uses a relatively expensive LLM-based signal and should not be easily exploited by repeated automated requests. Because the system does not yet implement user authentication, IP-based limiting is the simplest practical safeguard.

## Known Limitations

One clear failure mode is highly structured human writing, such as a formal technical report or research abstract. Those texts often look polished, consistent, and semantically coherent, which can push both signals toward an AI-like reading even when they were written by a person. This is a weakness of the current design because the stylometric signal interprets uniform structure as a possible AI signal, and the LLM signal can overvalue coherence and formal tone.

Other limitations include:
- Very short texts, where the stylometric statistics are not meaningful.
- Deliberately edited AI text that has been mixed with human-like noise.
- Repetitive poetry or artistic writing, where low lexical diversity can look suspicious even when it is intentional.

## Spec Reflection

One way the spec helped was by forcing a clear separation between the current submission state and the immutable audit history. That structure made the implementation much easier to reason about and gave the system a clean path for appeals and traceability.

One place where the implementation diverged from the spec was in the appeals payload. The planning document described a field named `creator_reasoning`, but the implementation uses `appeal_reason` in the API and stores it in the audit record. This change was made to keep the JSON contract consistent with the actual database schema and the shorter request format used by the app.

## AI Usage

I used AI assistance in a few concrete ways during implementation:

1. I asked it to help draft the Flask endpoint structure and the initial SQLite schema for submissions and audit logging. The AI produced a clean skeleton quickly, but I revised the database design to make the audit trail more explicit and to ensure the status transitions were easy to reason about.
2. I asked it to help shape the explanation and prompt logic for the LLM-based signal. The first version was too verbose and returned extra text beyond a single numeric score, so I revised the prompt to enforce a strict numeric output and to ignore any instruction-like content inside the user submission.
3. I also used it to help refine the README content and the reasoning around why the signal weights and disagreement penalty were chosen. I kept the final framing more conservative and less absolute than the original draft because the system is intended as a transparency tool rather than a definitive detector.

# ⚙️ Tech Stack

Provenance Guard is implemented as a lightweight Flask backend focused on transparency, auditability, and explainable attribution.

### 🧠 Core Backend
- Python 3.10+
- Flask for the REST API
- Flask-Limiter for request throttling and abuse protection

### 🤖 AI / ML Layer
- Groq API for the LLM-based semantic signal
- Custom Python stylometric analysis for the structural signal

### 🗄️ Data Layer
- SQLite for the current MVP implementation
- A simple submissions table plus an audit log table for event history

### 📊 Supporting Tools
- Python standard library for datetime, UUID, and SQLite handling
- Regex-based text processing for stylometric features
- Python-dotenv for loading environment variables from `.env`

---

# 📁 Project Structure

```text
provenance-guard/
├── app.py
├── helper.py
├── requirements.txt
├── README.md
├── planning.md
├── .env
├── audit_log.db
└── test.py
```

### Key Files
- `app.py` — Flask app, routes, database initialization, logging, and submission/appeal logic
- `helper.py` — Groq-based semantic scoring and Python stylometric scoring
- `test.py` — simple local testing utility for inspecting stored submissions
- `requirements.txt` — Python dependencies
- `.env` — environment configuration, including `GROQ_API_KEY`

---

# 🚀 Installation

## 1. Clone the Repository

```bash
git clone https://github.com/Kr1shna304/provenance-guard.git
cd provenance-guard
```

## 2. Create a Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Optional values can also be set for model selection if needed.

---

# ▶️ Running the Project

Start the Flask server with:

```bash
python app.py
```

The app will run locally at:

```text
http://127.0.0.1:5000
```

---

## API Endpoints

### Submit Content

```http
POST /submit
```

Expected JSON:

```json
{
  "text": "This is a sample submission for attribution analysis.",
  "creator_id": "user123"
}
```

### Submit Appeal

```http
POST /appeal
```

Expected JSON:

```json
{
  "content_id": "some-content-id",
  "creator_id": "user123",
  "appeal_reason": "I believe this was misclassified."
}
```

### View Audit Log

```http
GET /log
```

---

# ⚠️ Known Limitations

## 1. Stylometric Fragility

The stylometric signal is sensitive to:

- very short texts
- highly formal academic writing
- technical or domain-specific writing
- intentionally edited or noisy text

## 2. LLM Dependency Risk

The semantic signal depends on Groq and can be affected by:

- API availability
- model behavior changes
- prompt sensitivity

## 3. Fixed Weighting Logic

The current fusion model uses:

```text
S_final = (0.7 × S_ai) + (0.3 × S_sty)
```

This is simple and interpretable, but it may not generalize well for:

- mixed-style or hybrid writing
- adversarial inputs
- highly edited AI-generated content

## 4. Hard Thresholds

The current labels are based on fixed confidence bands, which can make near-boundary cases feel unstable.

## 5. No Authentication Yet

The current MVP uses IP-based rate limiting and does not yet implement persistent user identity, which limits stronger abuse control and creator accountability.

---

# 📐 Spec Reflection

The planning document helped shape the architecture around a clear separation between:

- the latest submission state, stored in the submissions table
- the full event history, stored in the audit log

That structure made the appeal workflow and auditability much easier to implement.

One implementation detail diverged slightly from the spec: the appeal payload uses `appeal_reason` instead of the planning document’s `creator_reasoning`. This was a practical simplification to keep the API contract consistent with the current app and database schema.

---

# 🤖 AI Usage

AI was used in three main ways during this project:

1. Designing the Flask app structure and database layout
2. Drafting the LLM prompt and refining it so the model returned a single numeric score
3. Helping structure the README and explain the scoring rationale in a clearer way

The final scoring logic, audit logging behavior, and rate limiting were still controlled by the project’s own rules rather than by the AI itself.

---

# 🚀 Future Improvements

Possible next steps for the project include:

- adding adaptive weighting for the two signals
- calibrating the scoring system against a labeled dataset
- introducing user authentication and stronger abuse controls
- replacing fixed thresholds with smoother confidence mapping
- adding a more detailed explanation view for each classification
```

---