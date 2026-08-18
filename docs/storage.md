# Storage backends

`science-researcher` supports two storage backends:

- `sqlite`: dependency-free local development and CI.
- `postgres`: production-oriented storage for Neon or any Postgres database with `pgvector`.

The application stores relational graph data and vectors together because discovery runs need to join concepts, analogy edges, hypotheses, proof obligations, and axis-specific embeddings.

## SQLite

SQLite remains the default so a fresh checkout can run without external services.

```bash
uv run science-researcher init --db /tmp/science.db --seed
uv run science-researcher demo --db /tmp/science.db --problem riemann-hypothesis
```

SQLite stores vectors as JSON. This is suitable for tests and small local experiments, not for large-scale retrieval.

## Neon / Postgres + pgvector

Install the optional Postgres dependency:

```bash
uv sync --extra postgres
```

Set a Neon connection string:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST.neon.tech/DB?sslmode=require'
```

Initialize and seed the database:

```bash
uv run science-researcher init \
  --store postgres \
  --seed
```

Run a discovery pass using the Postgres store:

```bash
uv run science-researcher demo \
  --store postgres \
  --problem riemann-hypothesis
```

The Postgres schema creates the `vector` extension and a `vectors` table with one row per entity and axis. The MVP still combines multi-axis scores in application code because the scoring function mixes mechanism similarity, structure similarity, domain distance, and failure penalties. A later storage layer can push the first-stage top-k search into pgvector indexes.

## OpenAI embeddings with Neon

For learned embeddings:

```bash
export OPENAI_API_KEY='...'
export DATABASE_URL='postgresql://USER:PASSWORD@HOST.neon.tech/DB?sslmode=require'

uv run science-researcher init \
  --store postgres \
  --embedder openai \
  --embedding-model text-embedding-3-small \
  --embedding-dimensions 512 \
  --seed
```

Then run:

```bash
uv run science-researcher demo \
  --store postgres \
  --embedder openai \
  --embedding-model text-embedding-3-small \
  --embedding-dimensions 512 \
  --problem navier-stokes
```

`--embedding-dimensions 512` is a practical starting point because each scientific node is embedded along multiple axes. The dimension should eventually be selected by measured retrieval quality rather than by generic retrieval benchmarks.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Postgres/Neon connection string. |
| `OPENAI_API_KEY` | API key for OpenAI embeddings. |
| `OPENAI_BASE_URL` | Optional override for OpenAI-compatible embeddings endpoint. |
| `SCIENCE_RESEARCHER_API_KEY` | API key for OpenAI-compatible chat completions provider. |
