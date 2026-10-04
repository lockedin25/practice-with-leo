.PHONY: dev test

dev:
	.venv/bin/uvicorn app.main:app --reload --reload-dir app --reload-dir reservoir --reload-dir corpus --reload-include '*.yaml'

test:
	.venv/bin/pytest
