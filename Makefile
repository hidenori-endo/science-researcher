.PHONY: sync test demo backup restore sync-issues

sync:
	uv sync --extra postgres

test:
	uv run python -m unittest discover -s tests -v

demo:
	uv run python -m science_researcher demo --db /tmp/science-researcher-demo.db --problem riemann-hypothesis

backup:
	bash scripts/backup-db.sh

restore:
	bash scripts/restore-db.sh $(ISSUE)

sync-issues:
	python3 scripts/sync-issues.py --store ${STORE:-postgres}
