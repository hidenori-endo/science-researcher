# Research claims and evidence

Discovery runs are only one source of scientific memory. Research may also arrive from a separate ChatGPT session, a literature review, a numerical experiment, a Lean proof, a symbolic calculation, or a failed approach. Those records must survive independently of the run that happened to produce them.

The research-record layer therefore makes claims and evidence first-class entities in both SQLite and Postgres/Neon.

## Canonical entities

### Research claim

`research_claims` is the canonical layer for scientific statements that the system may reason about later. A claim can be a known result, derived result, computational observation, hypothesis, conjecture, counterexample, obstruction, failed approach, Lean-verified result, experimental result, or methodological lesson.

Important fields are:

- `id`: internal stable identifier.
- `external_id`: optional user-supplied identifier; required by bundle imports and used for idempotency.
- `title`.
- `statement`.
- `record_type`.
- `epistemic_status`.
- `domain`.
- `source`: provenance text such as a paper, research session, or discovery run.
- `axis_texts_json`: canonical text for retrieval axes.
- `metadata_json`.
- `created_at`.

Generated discovery hypotheses remain in the existing `hypotheses` table because that table contains run-specific data such as `critic_score`, `analogy_node_id`, and the generated bridge. New generated hypotheses also create a canonical `research_claims` row and store its id in `hypotheses.claim_id`.

This preserves the existing discovery-run API while making generated and manually registered hypotheses queryable through the same long-term research-memory layer.

### Evidence

`evidences` stores independently addressable evidence. Evidence types include:

- `computational_observation`
- `literature_result`
- `theorem`
- `counterexample`
- `lean_proof`
- `symbolic_calculation`
- `dataset_observation`
- `experimental_result`

Evidence has its own epistemic status. This is intentional: a Python experiment can support or weaken a claim without becoming a proof.

### Typed relations

`research_relations` is graph-shaped rather than tree-shaped. A claim can point to evidence or another claim using one of:

- `SUPPORTS`
- `CONTRADICTS`
- `WEAKENS`
- `REFINES`
- `MOTIVATES`
- `FALSIFIES`
- `DEPENDS_ON`
- `DERIVED_FROM`

A relation has exactly one target: either an evidence record or another claim.

## Epistemic status

The status vocabulary is deliberately explicit:

| Status | Intended meaning |
| --- | --- |
| `established` | Accepted external result, normally backed by literature or a standard theorem. |
| `lean_verified` | The relevant formal statement has been checked by Lean. The scope is only the formalized statement. |
| `mathematically_derived` | Derived by mathematical reasoning but not represented here as a Lean-checked proof. |
| `computational` | Numerical or symbolic computational evidence. It is not a proof. |
| `experimental` | Empirical experimental evidence. |
| `conjectural` | A concrete unproved mathematical or scientific conjecture. |
| `speculative` | Earlier-stage idea with weaker justification. |
| `falsified` | The recorded statement has been refuted within its stated scope. |
| `unknown` | Status has not yet been classified. |

In particular, numerical Python output must remain `computational`; it must not be promoted to a proof status merely because the experiment is reproducible.

## Knowledge, discovery, evidence, computation, and proof

These concepts intentionally remain separate:

- **Knowledge graph:** long-lived scientific objects, claims, evidence, and typed relationships.
- **Discovery graph:** the path by which a run produced reframings, analogies, mutations, critiques, and proof obligations.
- **Discovery hypothesis:** a speculative result of a particular discovery run. It has run-specific critic metadata and also links to a canonical research claim.
- **Evidence:** an independently addressable reason to support, weaken, contradict, refine, motivate, or falsify a claim.
- **Computational observation:** evidence whose epistemic status is computational. It does not imply proof.
- **Proof:** a mathematical justification with scope matching the claim. A Lean-verified finite lemma may be `lean_verified`; that does not automatically establish a broader infinite-dimensional or asymptotic claim.

## Axis-specific retrieval text

Claims and evidence participate in the same structural retrieval philosophy as scientific nodes. They can provide independent canonical text for:

- `semantic`
- `domain`
- `mechanism`
- `math_structure`
- `problem_shape`
- `failure`

The system does not duplicate one raw text blob across all six axes. If an axis has no meaningful representation, it is allowed to be empty. `ResearchIndex` embeds each canonical axis through the existing embedding interface, so the deterministic hash embedder and OpenAI `text-embedding-3-small` both work without coupling the domain model to OpenAI.

Future retrieval can therefore favor mechanism-near, structure-near, domain-far records while penalizing overlap with known failure modes.

## CLI

Register a manual hypothesis:

```bash
science-researcher add-claim \
  --db science.db \
  --title "Uniform alpha-to-one control" \
  --statement "Continuation requires a parameter-uniform a priori estimate." \
  --record-type hypothesis \
  --epistemic-status conjectural \
  --domain "PDE/fluid-dynamics" \
  --mechanism "Transfer regularity through a parameter-uniform compactness argument" \
  --failure "The uniform estimate may encode the original theorem"
```

Register computational evidence:

```bash
science-researcher add-evidence \
  --db science.db \
  --title "Random-label control" \
  --summary "The closest-zero signature also appears in a null control." \
  --evidence-type computational_observation \
  --epistemic-status computational \
  --domain "machine-learning/statistical-physics"
```

Link them after obtaining their ids:

```bash
science-researcher link-evidence \
  --db science.db \
  --claim-id CLAIM_ID \
  --evidence-id EVIDENCE_ID \
  --relation WEAKENS
```

Inspect records:

```bash
science-researcher list-claims --db science.db
science-researcher list-evidence --db science.db
science-researcher show-claim --db science.db --claim-id CLAIM_ID
```

The same commands work with the existing Neon backend by adding `--store postgres` and providing `DATABASE_URL`.

## Versioned JSON import

A research bundle has `schema_version: 1` and three arrays: `claims`, `evidence`, and `relations`.

```json
{
  "schema_version": 1,
  "claims": [
    {
      "external_id": "grokking-lee-yang-001",
      "title": "Dynamical Lee-Yang hypothesis",
      "statement": "Training trajectories may admit a useful dynamical partition function.",
      "record_type": "hypothesis",
      "epistemic_status": "conjectural",
      "domain": "machine-learning/statistical-physics",
      "axis_texts": {
        "mechanism": "Tilt a trajectory order parameter and study complex zeros.",
        "failure": "Finite-size controls can mimic the zero signature."
      }
    }
  ],
  "evidence": [
    {
      "external_id": "grokking-control-001",
      "title": "Random-label control",
      "summary": "A similar closest-zero pattern appears in a null control.",
      "evidence_type": "computational_observation",
      "epistemic_status": "computational"
    }
  ],
  "relations": [
    {
      "claim": "grokking-lee-yang-001",
      "evidence": "grokking-control-001",
      "relation": "WEAKENS"
    }
  ]
}
```

Import it with:

```bash
science-researcher import-research research.json --db science.db
```

`external_id` is mandatory for bundle records. The full bundle is validated before database writes, then claims, evidence, and relations are imported in one database transaction. Re-importing the same bundle updates the existing records rather than creating duplicates. Embeddings are refreshed after the transactional record import.

The repository includes `research/initial-research.json`, which records the current grokking, origin-of-life, Navier-Stokes, Riemann/Lee-Yang, and cross-project methodological threads. Its statuses intentionally remain conjectural, computational, speculative, or otherwise appropriately qualified.
