.PHONY: help compose-config db-up db-status db-down db-reset test-orion test-orion-pipeline test-orion-db ingest-orion dashboard db-tables db-schema db-records

COMPOSE ?= docker compose
PYTHONPATHS := packages/pipelines/src:packages/streamlit_dashboard/src

help:
	@printf '%s\n' \
		'make compose-config  Validate Compose interpolation' \
		'make db-up           Start TimescaleDB' \
		'make db-status       Show TimescaleDB status' \
		'make db-down         Stop Compose services without removing volumes' \
		'make db-reset        Stop services and remove the database volume (destructive)' \
		'make test-orion      Run all Orion integration tests in Docker' \
		'make test-orion-pipeline  Run only the JPL pipeline test in Docker' \
		'make test-orion-db  Run only TimescaleDB query tests in Docker' \
		'make ingest-orion   Run the Orion JPL ingest job on the host' \
		'make dashboard       Start the Streamlit dashboard' \
		'make db-tables       List database tables' \
		'make db-schema       Describe the Orion table' \
		'make db-records      Show stored Orion records'

compose-config:
	$(COMPOSE) config >/dev/null
	@printf '%s\n' 'Compose configuration: OK'

db-up:
	$(COMPOSE) up -d timescaledb

db-status:
	$(COMPOSE) ps

db-down:
	$(COMPOSE) down

db-reset:
	$(COMPOSE) down -v

test-orion:
	$(COMPOSE) run --rm --build orion-tests

test-orion-pipeline:
	$(COMPOSE) run --rm --build orion-tests \
		uv run --package streamlit-dashboard python -m unittest \
		tests.integration.test_orion_feature.OrionPipelineIntegrationTests -v

test-orion-db:
	$(COMPOSE) run --rm --build orion-tests \
		uv run --package streamlit-dashboard python -m unittest \
		tests.integration.test_orion_feature.OrionTimescaleIntegrationTests -v

ingest-orion:
	@if command -v uv >/dev/null 2>&1; then \
		PYTHONPATH=$(PYTHONPATHS) uv run --package pipelines python -m pipelines.ingest.jpl_orion; \
	else \
		PYTHONPATH=$(PYTHONPATHS) .venv/bin/python -m pipelines.ingest.jpl_orion; \
	fi

dashboard:
	@if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	if command -v uv >/dev/null 2>&1; then \
		uv run --package streamlit_dashboard streamlit run packages/streamlit_dashboard/src/streamlit_dashboard/app.py --server.headless true --browser.gatherUsageStats false; \
	else \
		.venv/bin/streamlit run packages/streamlit_dashboard/src/streamlit_dashboard/app.py --server.headless true --browser.gatherUsageStats false; \
	fi

db-tables:
	$(COMPOSE) exec timescaledb sh -c \
		'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "\\dt"'

db-schema:
	$(COMPOSE) exec timescaledb sh -c \
		'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "\\d+ orion_ephemeris"'

db-records:
	$(COMPOSE) exec timescaledb sh -c \
		'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "SELECT target_id, epoch, jd, speed_kms, range_km FROM orion_ephemeris ORDER BY epoch LIMIT 10;"'
