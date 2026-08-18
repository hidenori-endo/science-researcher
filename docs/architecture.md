# Architecture

## Objective

The system is designed around a specific hypothesis about AI-assisted science:

> LLMs may have a comparative advantage not merely in reading more literature, but in recognizing weak structural similarities across domains that human specialists rarely hold in working memory simultaneously.

A conventional vector database is insufficient because ordinary semantic embeddings collapse several distinct notions of similarity. A good scientific analogy may be semantically distant but mechanistically close.

The architecture therefore stores the same scientific object under multiple orthogonal representations.

## Six logical layers

### Layer 0: Evidence

Raw sources and observations:

- papers,
- theorem statements,
- experiments,
- datasets,
- code,
- counterexamples,
- negative results.

Evidence should retain provenance and should not be mixed with speculative hypotheses.

### Layer 1: Concepts and results

Domain-level objects such as:

- Lee–Yang zeros,
- renormalization group,
- Navier–Stokes blow-up,
- autocatalytic sets,
- total positivity.

### Layer 2: Structural abstractions

Each concept/result is rewritten in domain-light language. Examples:

- Lee–Yang: `local positivity -> global analytic rigidity`.
- Dirac linearization: `enlarge algebra -> factor a quadratic constraint -> obtain a linear dynamics`.
- Hubbard–Stratonovich: `add latent degrees of freedom -> conditionally linearize an interaction`.
- Renormalization: `discard microscopic information -> retain relevant directions -> identify universality`.

This layer is the main substrate for cross-domain retrieval.

### Layer 3: Analogy graph

Typed edges capture non-topical relationships:

- `SHARES_MECHANISM_WITH`
- `GENERALIZES`
- `DUAL_TO`
- `LINEARIZES`
- `COMPLEXIFIES`
- `COARSE_GRAINS`
- `TRANSFERABLE_TO`
- `FAILED_BECAUSE`

### Layer 4: Hypothesis graph

A generated research idea is stored as a first-class object, not as chat text. It records:

- source problem,
- source analogy,
- proposed bridge,
- predicted consequence,
- novelty rationale,
- status,
- failure reason,
- confidence.

### Layer 5: Proof-obligation graph

A hypothesis is decomposed into implications. Each implication can be:

- known,
- proved,
- computationally supported,
- conjectural,
- false,
- unknown.

This prevents a long speculative argument from hiding a single impossible bridge.

## Graph vs. tree

Long-term memory is a graph because scientific relationships are many-to-many. The temporary reasoning process is a tree because a research run intentionally branches into alternative reframings, analogies, and mutations.

Successful and failed branches are written back into the graph after evaluation.

## Multi-axis vectors

Every scientific card can have more than one embedding.

### Domain vector

What field is this about?

Examples: statistical mechanics, analytic number theory, PDE, molecular biology.

### Mechanism vector

What does the method *do*?

Examples: local positivity constrains global zeros; enlarge state space to linearize; coarse-grain to expose invariants.

### Mathematical-structure vector

What structures does it use?

Examples: positivity, self-adjointness, convexity, topology, spectrum, analyticity, symmetry.

### Problem-shape vector

What abstract problem pattern does it solve?

Examples: local-to-global, nonlinear-to-linear, finite-to-infinite, existence-to-obstruction.

### Failure-mode vector

What breaks the approach?

Examples: non-uniform limits, loss of positivity, circular reformulation, finite-size artifacts, non-commuting limits.

The MVP stores these as independent dense vectors using deterministic feature hashing. Production deployments should replace or augment them with learned embeddings while preserving the separation of axes.

## Retrieval objective

A useful scientific analogy is often *near in mechanism* and *far in domain*.

The MVP uses an interpretable score of the form:

```text
score =
  + 0.50 * mechanism_similarity
  + 0.20 * structure_similarity
  + 0.15 * problem_shape_similarity
  + 0.15 * semantic_similarity
  + 0.20 * domain_distance
  - 0.20 * known_failure_overlap
```

Weights are configuration, not truth. Historical backtesting should eventually learn them.

## Discovery loop

1. **Reframe** the target problem multiple ways without domain jargon.
2. **Retrieve** structurally close but domain-distant historical mechanisms.
3. **Mutate** the analogy rather than copying it literally.
4. **Critique** with an isolated adversarial stage.
5. **Extract proof obligations** from survivors.
6. **Choose the cheapest falsifier**: symbolic check, finite search, simulation, literature no-go theorem, or formal proof.
7. **Persist the trace**, including failures.

## Provider boundary

The core engine is model-agnostic. `ReasoningProvider` owns the generative stages. The default `HeuristicProvider` exists so the architecture can run deterministically in CI and tests.

A production provider should return structured data for each stage and should not receive hidden state from the critic unless explicitly intended.

## Why failed ideas are first-class

Scientific literature is publication-biased. An automated researcher that only stores successful papers repeatedly rediscovers dead ends.

A failure record should include:

- attempted transformation,
- target problem,
- exact failed bridge,
- minimal counterexample if available,
- meta-lesson for future retrieval.

This allows the retrieval policy to penalize approaches whose enabling assumptions are already known to reproduce the original hard problem.
