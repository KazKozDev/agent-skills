# Cost, model choice and pipeline design

Read this when the job is large or budget-bound (many documents, many questions about one document, a tight budget), when choosing models for the steps, or when the user asks which summarization approach to use for their data or how to compare approaches.

## Contents

- Cost and model plan — cascades, reasoning models, caching, batch APIs, distillation, tight budgets
- Designing or comparing a summarization pipeline — test set, variants, measurements, choice by cost of error
- Automatic metrics — what they are good for and their limits

## Cost and model plan

- Cascade: a cheaper/faster model can do per-chunk or per-text extraction (map); a stronger model does aggregation (reduce) and verification. What the cheap model misses cannot be recovered later, so spot-check its extractions.
- Reasoning models: use only where logic is needed — reconciling contradictory sources, finding inconsistencies in a long document, semantic verification, complex reduce. Not for plain retelling or mass map steps. They cost several times more in latency and tokens, do not remove hallucinations, and the gain depends on model and task — measure before adopting.
- Many questions about one document: keep the document as a stable prompt prefix so provider caching can apply.
- Non-urgent batches: use batch APIs where available.
- Very large stable stream of the same document type: suggest distilling into a small local model trained on verified summaries (cheap, offline, private; transfers poorly to new types and inherits the teacher's errors).
- Tight budget: single call, short schema, Layer 1 only, Layer 2 only for flagged or high-risk items; no iterations, variants or reasoning models.

## Designing or comparing a summarization pipeline

When the user asks which approach to use for their data, or to evaluate one:

1. Take 20–50 typical texts; for each, list key claims by hand together with their conditions.
2. Run 2–3 complete variants (e.g. single pass over the whole transcript vs topic chunks with a registry), each with the same add-ons.
3. Measure per variant: share of key claims kept; share kept with their conditions; factual errors (invented, distorted); tokens and time.
4. Choose by cost of error: where omissions hurt, by completeness; where inventions hurt, by precision; on a tie, by cost.

## Automatic metrics

Automatic metrics (NLI-based consistency, QA-based checks, LLM-as-judge with a rubric) help to compare at scale but are noisy on long texts and biased (judges favour longer and familiar-style answers); calibrate them on a small human-labeled gold set and never use them as the only criterion. Do not present quality or cost numbers that were not measured.
