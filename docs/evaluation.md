# Evaluation: historical rediscovery

The system should be evaluated before being trusted on open problems.

## Core benchmark idea

For a historical breakthrough, impose a time cutoff before the breakthrough and expose only knowledge that would have been available at that time. Ask whether the system ranks the breakthrough's *structural move* among its top candidates.

Examples:

### Dirac equation

Target state: relativistic quantum mechanics before Dirac's equation.

Desired structural move:

> enlarge the coefficient algebra so a quadratic relativistic constraint can be linearized.

### Lee–Yang zeros

Target state: phase-transition theory before 1952.

Desired structural move:

> complexify a physical control parameter and study partition-function zeros to infer real-axis singular behavior.

### Renormalization group

Target state: critical phenomena before modern RG.

Desired structural move:

> repeatedly discard microscopic degrees of freedom and study the flow of effective theories rather than solving microscopic details directly.

### Hubbard–Stratonovich transformation

Desired structural move:

> add an auxiliary degree of freedom to transform an interacting nonlinear term into a conditionally linear problem.

## Metrics

- `recall@k` of the historical structural move.
- Mean reciprocal rank.
- Domain distance of retrieved analogies.
- Mechanism similarity judged by blinded experts.
- Falsification survival rate.
- Rate of circular/vacuous hypotheses.
- Cost until first decisive counterexample.

## Negative-control benchmarks

The system should also receive problems where a tempting analogy is known to fail. A good critic must demote these candidates for the correct reason.

## Ablations

Compare:

1. ordinary semantic retrieval,
2. mechanism-only retrieval,
3. mechanism-near/domain-far retrieval,
4. full multi-axis retrieval,
5. full retrieval plus failure-memory penalties.

The project is successful only if the more structured system outperforms ordinary semantic retrieval on historical rediscovery without simply generating more candidates.
