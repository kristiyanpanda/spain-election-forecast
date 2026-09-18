# One-command pipeline. Requires `uv` (https://docs.astral.sh/uv/). Run `make all`.
PY := uv run --extra dev

.PHONY: all setup data test descriptive aggregate seats backtest forecast report clean

all: setup data test descriptive aggregate seats backtest forecast report

setup:
	uv sync --extra dev

data:            ## download + tidy official results and polls, write dictionary and QA report
	$(PY) electoral build-data

test:
	$(PY) pytest -q

descriptive:     ## phase B: indices and static figures
	$(PY) electoral descriptive

aggregate:       ## phase C: Bayesian poll aggregator
	$(PY) electoral aggregate

seats:           ## phase D: seat projection (Monte Carlo)
	$(PY) electoral seats

backtest:        ## phase E
	$(PY) electoral backtest

forecast:        ## phase F: projection to the legal deadline
	$(PY) electoral forecast

report:          ## phase G: interactive HTML
	$(PY) electoral report

clean:
	rm -rf data/processed/* outputs/* reports/figures/*
