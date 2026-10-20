.PHONY: dev test

dev:
	.venv/bin/uvicorn app.main:app --reload --reload-dir app --reload-dir reservoir

test:
	.venv/bin/pytest
