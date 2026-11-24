"""Static checks of the Grafana alert rules (infra/grafana/provisioning/alerting/telemetry-alerts.yml).

Each rule must run its dashboard tile's query unchanged, so an alert email and the dashboard
always agree; the rest catches mistakes that only show up when Grafana starts on the server.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[6]
ALERTS = ROOT / "infra/grafana/provisioning/alerting/telemetry-alerts.yml"
DASHBOARD = ROOT / "infra/grafana/dashboards/telemetry-ops.json"
DATASOURCES = ROOT / "infra/grafana/provisioning/datasources/postgres.yml"

# rule title -> the status tile whose query it runs
RULE_TILES = {
    "Pipeline stopped": "Pipeline",
    "Missing ticks": "Pipeline",
    "Real-data refresh failed": "Airflow",
    "Database almost full": "Database use",
}


@pytest.fixture(scope="module")
def alerts():
    return yaml.safe_load(ALERTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rules(alerts):
    return {r["title"]: r for g in alerts["groups"] for r in g["rules"]}


@pytest.fixture(scope="module")
def tiles():
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    return {p["title"]: p for p in dashboard["panels"] if p["type"] == "stat"}


def _query(rule):
    (query,) = [d for d in rule["data"] if d["refId"] == "A"]
    return query


def test_alerts_define_the_expected_rules(rules):
    assert set(rules) == set(RULE_TILES)


@pytest.mark.parametrize("title", sorted(RULE_TILES))
def test_alerts_rule_runs_its_tile_query_unchanged(rules, tiles, title):
    tile = tiles[RULE_TILES[title]]
    query = _query(rules[title])
    assert query["model"]["rawSql"].strip() == tile["targets"][0]["rawSql"].strip()
    assert query["datasourceUid"] == tile["targets"][0]["datasource"]["uid"]


@pytest.mark.parametrize("title", sorted(RULE_TILES))
def test_alerts_rule_fires_when_the_database_is_unreachable(rules, title):
    assert rules[title]["noDataState"] == "Alerting"
    assert rules[title]["execErrState"] == "Alerting"


def test_alerts_use_only_provisioned_datasources(rules):
    provisioned = set(re.findall(r"^\s*uid:\s*(\S+)", DATASOURCES.read_text(encoding="utf-8"), re.MULTILINE))
    used = {d["datasourceUid"] for r in rules.values() for d in r["data"]} - {"__expr__"}
    assert used <= provisioned


def test_alerts_file_has_no_dollar_sign_but_the_recipient(alerts):
    # Grafana interpolates $VARS in provisioning files: a $ in the SQL would be replaced.
    text = ALERTS.read_text(encoding="utf-8")
    assert re.findall(r"\$\w+", text) == ["$GF_ALERT_EMAIL"]


def test_alerts_notify_the_provisioned_contact_point(alerts):
    names = {c["name"] for c in alerts["contactPoints"]}
    assert {p["receiver"] for p in alerts["policies"]} <= names
