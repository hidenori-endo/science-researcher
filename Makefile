.PHONY: sync test demo

sync:
	uv sync --extra postgres

test:
	uv run python -m unittest discover -s tests -v

demo:
	uv run python -m science_researcher demo --db /tmp/science-researcher-demo.db --problem riemann-hypothesis
