# Theory attack verdicts

This document defines the verdict vocabulary for **formal attacks on an open
problem** — the deliverables written as `experiments/<name>/THEORY.md` and
mirrored into `research/*.json` under `metadata.attack_notes.verdict`.

It is deliberately separate from the hypothesis-experiment verdicts
(`SUPPORT` / `AGAINST` / `INCONCLUSIVE` / `DISCARD`) described in
`AGENTS.md` → 検証の梯子. Those grade a pre-registered falsification test
against data. The labels here grade a **proof route**: a lemma chain that
attacks the problem itself. The two vocabularies must not be mixed.

## Structure: two gates, then one ladder label

A theory attack is graded in three steps, in this order:

1. Gate A — chain integrity.
2. Gate B — prior art.
3. Ladder label, only if both gates pass.

A failed gate produces a holding label, not a ladder label. Holding labels
are legitimate outcomes to commit; they are not failures of the session.

### Gate A — chain integrity → `CHAIN-GAP`

Every lemma the verdict leans on must carry a proof **in the document**. A
step that is only confirmed numerically, or asserted "by symmetry" / "clearly"
/ "analogously", is a gap. Computation may confirm a boundary case; it may not
discharge a lemma. If any such gap remains, the verdict is `CHAIN-GAP`
regardless of how promising the route looks.

One failure mode deserves naming because it is easy to miss and has already
occurred in this repo:

> **Equivalence asymmetry.** When the attack ends by proposing a new lemma
> `NL` and claiming "`NL` is equivalent in strength to the target `P`",
> the direction `NL ⇒ P` is normally the easy one and the direction
> `P ⇒ NL` needs its own proof. That converse is an **exhaustion lemma**:
> it must show that every solution the reduction admits can be transported
> into the sub-family `NL` speaks about. If `NL` is stated over a proper
> sub-family of what the reduction produced, the converse is false until
> proved, and the claim of equivalence is a Gate A failure.

Reference case: `experiments/erdos-straus/THEORY.md` §5 asserted that a lemma
stated over the `σ = z'w` sub-family was equivalent in strength to
Erdős–Straus, while the reduction produced the strictly larger family
`σ | z'²`. See that document's §5 and §8 for the corrected statement.

### Gate B — prior art → `PRIOR-ART-PENDING`

Before any ladder label, the document must contain a prior-art section that
names, with resolvable citations, the literature covering:

- the reduction / parametrization the attack uses,
- the classification of solutions or objects it introduces,
- the obstruction it claims to have located.

"From memory, unverified" is not a citation. A search that found nothing is a
valid outcome, but it must be recorded as *what was searched* and *what was
read*, so the next session can extend it rather than repeat it. If this section
is absent, the verdict is `PRIOR-ART-PENDING`.

This gate exists because a reduction that is correct, self-consistent and
already published looks, from inside the session, exactly like a discovery.

## The ladder

Ordered from least to most valuable as a target for further work.

| Label | Meaning | Requires |
| --- | --- | --- |
| `ROUTE-DEAD` | The route is formally closed: an impossibility is *proved*, not conjectured. | The blocking proof, and a statement of exactly which route it kills. |
| `ROUTE-KNOWN` | The reduction is correct but is a change of coordinates on a published parametrization. No new attack surface. | The explicit correspondence — a variable change, or a precise statement of which published result the reduction maps onto. |
| `OBSTRUCTION-IDENTIFIED` | The route is open; the exact point where standard machinery fails is located and argued per technique; the required new input is named but not claimed to be within reach. | Per-technique failure argument, not a blanket "no known method applies". |
| `ROUTE-LIVE` | Everything `OBSTRUCTION-IDENTIFIED` requires, **plus** a specific unblocking lemma that Gate B confirmed is absent from the literature, **plus** a proved implication from that lemma to the target. | Both gates passed, and the implication `lemma ⇒ target` proved in full. |

`ROUTE-DEAD` is a real result and is worth committing: it removes a route from
future search. It is placed lowest only because it offers nothing further to
attack.

`ROUTE-LIVE` is the highest bar in this repo and should be rare. Recording one
is a claim that the literature does not already contain the proposed lemma —
which is why Gate B is mandatory for it rather than advisory.

### What `ROUTE-LIVE` does not mean

It does not mean the open problem is solved, nearly solved, or that the
session produced a proof of anything about the problem itself. It means:
one named lemma, checked against the literature and not found there, would
settle the problem if it were proved. The `THEORY.md` §0 and the claim-card
summary must both state this in their first paragraph, in those terms.

## Recording

`metadata.attack_notes` on the problem claim carries:

```json
{
  "branch": "verify/math-<problem>",
  "commit": "<sha>",
  "verdict": "ROUTE-KNOWN",
  "prior_art": ["arXiv:1107.1010 (Elsholtz-Tao)", "..."],
  "summary": "one paragraph, in the terms of the label",
  "previous": [
    {
      "verdict": "ROUTE-LIVE",
      "commit": "<sha>",
      "reason": "why the earlier label was withdrawn"
    }
  ]
}
```

- `prior_art` is required for every ladder label. For a verdict recorded under
  this system, a document that did not check the literature carries
  `prior_art: "unverified"` and its verdict must be `PRIOR-ART-PENDING`.
  Records predating this system also carry `prior_art: "unverified"` while
  keeping their original label; see *Applicability* below.
- `previous` is append-only.

## Revising a verdict

Verdicts are revisable, and downgrades are the expected outcome of review.
Do not rewrite the old label out of the record: append it to `previous` with
the reason it was withdrawn, and keep the original `THEORY.md` argument in
place, corrected in-line rather than deleted, so the error stays legible.

Downgrade as soon as either gate fails on re-reading — including when the
failure is pointed out by an external reviewer rather than found in-session.

## Applicability to existing records

The two gates apply to verdicts recorded on or after 2026-08-23. Verdicts
recorded before that date are annotated with `prior_art: "unverified"` where
the document did not check the literature. They are **not** retroactively
downgraded, because that would require re-doing each attack. They may not be
cited as precedent when recording a new `ROUTE-LIVE`.
