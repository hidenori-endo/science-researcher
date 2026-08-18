# science-researcher

`science-researcher` is an experimental, AI-native system for scientific discovery. Its goal is not to retrieve papers more efficiently. Its goal is to search for **distant but structurally meaningful connections** between scientific problems, historical breakthroughs, mathematical mechanisms, failure modes, and proof obligations.

The core design separates long-term scientific memory from temporary reasoning:

- **Knowledge graph**: claims, concepts, structures, evidence, and typed relations.
- **Discovery graph**: how ideas were generated, mutated, falsified, and decomposed.
- **Multi-axis vectors**: separate representations for domain, mechanism, mathematical structure, problem shape, and failure mode.
- **Search tree**: temporary branching exploration for a single research run.
- **Hypothesis / proof-obligation graph**: every speculative bridge is decomposed into independently testable edges.

The MVP is intentionally dependency-free at runtime and ships with an offline deterministic reasoning provider so that the full pipeline can be tested without an API key. A provider interface is included for connecting real LLMs later.

## Why this exists

Ordinary scientific retrieval optimizes semantic similarity: papers about the same topic are placed near one another. That is useful for literature review, but it is often the wrong objective for discovery.

This project instead searches for candidates that are:

1. **structurally similar** in mechanism,
2. **scientifically distant** in domain,
3. **mechanistically relevant** to the target bottleneck,
4. **falsifiable cheaply**, and
5. **explicit about the assumptions that could make the analogy circular or vacuous**.

A Lee–Yang theorem card, for example, is not stored only as "statistical mechanics / Ising model". It is also stored as a more abstract mechanism:

> local positivity -> global analytic rigidity

This structural representation can then be retrieved for a problem in number theory, PDEs, biology, or machine learning without requiring topical similarity.

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run science-researcher demo --db /tmp/science.db --problem riemann-hypothesis
```

Add the `postgres` extra to use the Neon/Postgres storage backend:

```bash
uv sync --extra postgres
```

The demo will:

1. initialize the SQLite graph store,
2. load seed breakthrough/problem cards,
3. reframe the target problem into structural descriptions,
4. retrieve analogies using multi-axis vectors,
5. generate mutated hypotheses,
6. run an adversarial critique pass,
7. extract minimal proof obligations, and
8. persist the complete discovery trace.

Inspect a stored run:

```bash
uv run science-researcher runs --db /tmp/science.db
uv run science-researcher show-run --db /tmp/science.db --run-id <RUN_ID>
```

Run tests:

```bash
uv run python -m unittest discover -s tests -v
```

## Architecture

```text
Evidence
   |
   v
Concept / Result Cards
   |
   v
Structural Abstractions ---- Multi-axis vectors
   |                              |
   |                              v
   +----------------------> Analogy retrieval
                                  |
                                  v
                           Analogical mutation
                                  |
                                  v
                         Adversarial falsification
                                  |
                                  v
                        Minimal proof obligations
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
              Python experiment             Lean proof
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                          Discovery memory
```

See [docs/architecture.md](docs/architecture.md) for the full design, [docs/providers.md](docs/providers.md) for LLM integration, [docs/storage.md](docs/storage.md) for SQLite/Neon/Postgres setup, and [docs/evaluation.md](docs/evaluation.md) for the historical-rediscovery benchmark proposal.

## Current scope

The MVP implements:

- SQLite-backed typed graph storage.
- Optional Neon/Postgres + pgvector storage.
- Multiple dense vector representations per node.
- Deterministic local text embeddings based on feature hashing.
- Optional OpenAI `text-embedding-3-small` embeddings.
- Mechanism-near / domain-far analogy scoring.
- Problem reframing and analogical mutation pipeline.
- Separate generator and critic stages.
- Hypothesis and proof-obligation persistence.
- Failed-idea memory.
- A deterministic offline provider for reproducible tests.
- Seed cards for historical breakthroughs and hard scientific problems.

It deliberately does **not** claim autonomous scientific discovery. The immediate objective is to build an auditable search substrate and evaluate whether it can rediscover historical conceptual jumps under time-cutoff constraints.

## Design principles

- **Facts and hypotheses are different entity types.**
- **Negative results are first-class memory.** Publication bias is harmful to an automated researcher.
- **A discovered analogy is not evidence.** Every analogy must become a falsifiable bridge.
- **Generators and critics are isolated.** They should not share the same immediate reasoning context.
- **Distance is useful.** Retrieval should prefer mechanism similarity while penalizing domain similarity.
- **Proof obligations are edges, not prose.** A hypothesis is only as strong as its weakest unknown implication.
- **Historical backtesting comes before grand claims.**

## Roadmap

1. Connect one or more production LLM providers behind the provider protocol.
2. Add paper ingestion with provenance and claim extraction.
3. Push first-stage vector top-k retrieval into pgvector indexes.
4. Add a graph-aware retrieval planner.
5. Add Python experiment workers and Lean 4 proof workers.
6. Build historical rediscovery benchmarks (Dirac, Lee–Yang, RG, Hubbard–Stratonovich, etc.).
7. Learn retrieval and mutation policies from successful and failed discovery traces.

## License

MIT.
