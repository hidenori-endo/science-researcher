# Data model

The project exposes the same high-level graph and research-record APIs through SQLite and Postgres/Neon. SQLite remains the default inspectable local backend; Postgres uses pgvector for production-oriented vector storage.

## Node

A `node` is a scientific object: breakthrough, problem, theorem, mechanism, failure pattern, or concept.

Important fields:

- `id`: stable string identifier.
- `kind`: `breakthrough`, `problem`, `concept`, `theorem`, `failure`, etc.
- `title`.
- `domain`.
- `summary`.
- `mechanism`.
- `math_structure`.
- `problem_shape`.
- `failure_modes`.
- `metadata_json`.

## Edge

A typed relationship between nodes:

- `source_id`
- `target_id`
- `relation`
- `weight`
- `evidence_json`

## Vector

Each node can store several independent embeddings:

- `semantic`
- `domain`
- `mechanism`
- `math_structure`
- `problem_shape`
- `failure`

Vectors are stored as JSON arrays in the MVP. This is intentionally simple; pgvector or a dedicated ANN index can replace it later without changing the conceptual model.

## Research claim

A long-lived scientific statement independent of any one discovery run. Claims include hypotheses, conjectures, obstructions, known results, counterexamples, failed approaches, verified finite results, and methodological lessons. Every claim carries an explicit `record_type` and `epistemic_status`.

Generated discovery hypotheses create a canonical research claim, while manual claims can be registered without a discovery run.

## Evidence

An independently addressable observation, theorem, literature result, counterexample, Lean proof, symbolic calculation, dataset observation, or experiment. Evidence has its own epistemic status so computational or experimental support cannot silently become proof.

## Research relation

A typed graph edge from a claim to either evidence or another claim. Supported relations are `SUPPORTS`, `CONTRADICTS`, `WEAKENS`, `REFINES`, `MOTIVATES`, `FALSIFIES`, `DEPENDS_ON`, and `DERIVED_FROM`.

## Research vector

Claims and evidence can each store separate `semantic`, `domain`, `mechanism`, `math_structure`, `problem_shape`, and `failure` vectors. Canonical text is axis-specific rather than one blob duplicated six times.

## Hypothesis

A generated speculative bridge associated with one discovery run:

- `id`
- `run_id`
- `problem_id`
- `analogy_node_id`
- `claim_id`: canonical `research_claims` record.
- `title`
- `bridge`
- `prediction`
- `rationale`
- `status`
- `critic_score`
- `failure_reason`

## Proof obligation

One independently testable implication inside a hypothesis:

- `id`
- `hypothesis_id`
- `position`
- `statement`
- `status`
- `verification_method`
- `notes`

## Discovery run

Every run has an immutable trace payload containing reframings, retrieval results, mutations, critiques, and final obligations.

This makes the system auditable and supports later training of retrieval/mutation policies from historical outcomes.
