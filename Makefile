PY := .venv/bin/python -I
DBX := $(HOME)/.local/bin/databricks
VOL := dbfs:/Volumes/workspace/wtpw/raw
.PHONY: fetch facts program local render lint test contract quotes reconcile upload deploy run parity gate

fetch:      ## networked: download every filing once into data/raw (needs SEC_UA)
	$(PY) -m wtpw.fetch
facts:      ## parse cached XBRL instances to data/work/facts.parquet
	$(PY) -m wtpw.extract_facts
program:    ## synthetic program tables (EVM, revenue, ledger)
	$(PY) -m wtpw.program
local:      ## bronze -> silver -> gold on DuckDB
	$(PY) -m wtpw.pipeline local
render:     ## regenerate pipeline/*.sql for Databricks from sql/
	$(PY) -m wtpw.pipeline render
lint:
	.venv/bin/ruff check src tests
test:
	$(PY) -m pytest -q
contract:
	$(PY) -m wtpw.curation_contract
quotes:
	$(PY) -m wtpw.quote_check
reconcile: local
	$(PY) -m wtpw.reconcile
upload:     ## push inputs to the Unity Catalog volume
	$(DBX) fs cp data/work/facts.parquet $(VOL)/facts.parquet --overwrite
	$(DBX) fs cp -r curated $(VOL)/curated --overwrite
deploy: render
	$(DBX) bundle deploy
run:
	$(DBX) bundle run medallion --refresh-all
parity:     ## Databricks gold == DuckDB gold
	$(PY) -m wtpw.parity

findings: local
	$(PY) -m wtpw.findings

gate: lint test contract quotes reconcile findings
	@echo "local gate: PASS"

.PHONY: xlsx memo
xlsx:       ## Excel FP&A pack from the gold tables -> outputs/where-the-plan-went.xlsx
	$(PY) -m wtpw.export_xlsx
memo:       ## docs/memo-template.md -> docs/memo.md + outputs/memo.pdf; fails on a hand-typed number
	$(PY) -m wtpw.memo
