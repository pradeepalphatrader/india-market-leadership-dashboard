.PHONY: demo test serve build publish

demo:
	python3 scripts/generate_demo_data.py
	PYTHONPATH=src python3 -m india_market_dashboard.cli build --history-dir data/demo --classification-file data/demo/classifications.csv --demo

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'

serve:
	python3 -m http.server 8080 --directory site

build:
	PYTHONPATH=src python3 -m india_market_dashboard.cli build --history-dir data/input/history --classification-file data/input/classifications.csv

publish:
	PYTHONPATH=src python3 -m india_market_dashboard.cli publish --destination build
