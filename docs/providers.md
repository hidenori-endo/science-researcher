# LLM providers

The discovery engine separates the generator and critic behind a small `ReasoningProvider` interface.

## Offline deterministic provider

The default provider is `HeuristicProvider`. It is deliberately simple, deterministic, and dependency-free. Its purpose is architectural testing and CI, not scientific creativity.

```bash
science-researcher demo \
  --db /tmp/science.db \
  --problem riemann-hypothesis \
  --provider heuristic
```

## OpenAI-compatible chat endpoint

The MVP includes a standard-library HTTP adapter for services that implement the widely used `/chat/completions` wire format.

For a local compatible server:

```bash
science-researcher demo \
  --db /tmp/science.db \
  --problem navier-stokes \
  --provider openai-compatible \
  --base-url http://localhost:11434/v1 \
  --model qwen3:8b
```

For a hosted provider:

```bash
export SCIENCE_RESEARCHER_API_KEY='...'
export SCIENCE_RESEARCHER_BASE_URL='https://provider.example/v1'

science-researcher demo \
  --db /tmp/science.db \
  --problem origin-of-life \
  --provider openai-compatible \
  --model generator-model \
  --critic-model critic-model
```

The generator and critic are instantiated as separate provider objects and each stage is stateless. This is intentional: the adversarial critic should not inherit a conversational commitment to the generator's idea.

## Production provider requirements

A production integration should:

- request structured JSON,
- preserve source citations separately from model prose,
- log model/version/sampling parameters,
- isolate generator and critic contexts,
- enforce timeouts and retry budgets,
- record raw provider responses for audit where policy permits,
- support reproducible low-temperature critic runs,
- never promote numerical or LLM-generated claims to `proved` status automatically.
