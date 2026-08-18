# Data model

The MVP uses SQLite because it is inspectable, portable, and sufficient for early experiments. Dedicated vector or graph databases can be introduced only after the access patterns justify them.

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

## Hypothesis

A generated speculative bridge:

- `id`
- `run_id`
- `problem_id`
- `analogy_node_id`
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
