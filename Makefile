.PHONY: test demo

test:
	python -m unittest discover -s tests -v

demo:
	python -m science_researcher demo --db /tmp/science-researcher-demo.db --problem riemann-hypothesis
