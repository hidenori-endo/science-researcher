# Roadmap

## Milestone 1: auditable discovery substrate

Status: implemented in the MVP.

- Typed scientific cards.
- Multi-axis vector storage.
- Mechanism-near/domain-far retrieval.
- Separate generator and critic stages.
- Hypothesis and proof-obligation persistence.
- Negative-result memory.
- Reproducible offline demo.

## Milestone 2: literature ingestion

- Paper metadata and source provenance.
- Claim extraction with explicit quoted/source spans.
- Claim-to-claim contradiction and dependency edges.
- Deduplication across preprints and published versions.

## Milestone 3: production embeddings and graph retrieval

- Replace hash embeddings with learned embeddings per axis.
- Keep axes independently queryable.
- Add graph-neighborhood expansion after vector retrieval.
- Learn retrieval weights from expert-judged retrieval outcomes.
- Evaluate whether domain-distance reward improves discovery rather than merely novelty.

## Milestone 4: research workers

Route proof obligations to specialized workers:

- web/literature prior-art search,
- symbolic algebra,
- finite counterexample enumeration,
- numerical experiments,
- Lean 4 theorem proving.

Every worker returns evidence with an epistemic status. No worker may silently upgrade computational evidence to proof.

## Milestone 5: policy learning from discovery traces

Once enough traces exist, learn which combinations of:

- reframing,
- retrieval axes,
- analogical mutations,
- critic checks,
- verification actions

lead to cheap decisive falsification.

The target is not a model that produces more ideas. It is a system that spends search budget more intelligently.
