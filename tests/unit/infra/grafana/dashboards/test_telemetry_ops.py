"""Static checks of the provisioned Grafana dashboard (infra/grafana/dashboards/telemetry-ops.json).

The queries themselves are checked against a database by hand (see the #106 PR); these tests
catch the mistakes that only show up after a deploy: broken JSON, a datasource uid Grafana
doesn't know, clashing panel ids, and the status tiles missing a table written every tick.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
DASHBOARD = ROOT / "infra/grafana/dashboards/telemetry-ops.json"
DATASOURCES = ROOT / "infra/grafana/provisioning/datasources/postgres.yml"

# Written once per simulator tick (anomaly_events is a placeholder and stays empty).
TICK_TABLES = (
    "state_snapshot",
    "thermal_output",
    "power_output",
    "comms_output",
    "radiation_output",
    "cross_model_state",
    "telemetry_packet",
    "ml_feature_vectors",
)


@pytest.fixture(scope="module")
def panels():
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    flat = []
    for panel in dashboard["panels"]:
        flat.append(panel)
        flat.extend(panel.get("panels", []))  # collapsed rows hold their panels
    return flat


def _sql(panels, title):
    (panel,) = [p for p in panels if p["title"] == title]
    return panel["targets"][0]["rawSql"]


def test_dashboard_panel_ids_are_unique(panels):
    ids = [p["id"] for p in panels]
    assert len(ids) == len(set(ids))


def test_dashboard_uses_only_provisioned_datasources(panels):
    provisioned = set(re.findall(r"^\s*uid:\s*(\S+)", DATASOURCES.read_text(encoding="utf-8"), re.MULTILINE))
    used = {p["datasource"]["uid"] for p in panels if "datasource" in p}
    used |= {t["datasource"]["uid"] for p in panels for t in p.get("targets", [])}
    assert used <= provisioned


def test_dashboard_panels_fit_the_grid(panels):
    for p in panels:
        pos = p["gridPos"]
        assert pos["x"] + pos["w"] <= 24, p["title"]


@pytest.mark.parametrize("title", ["Pipeline", "Mission checks", "Synthetic writes per minute (8 tick tables)"])
def test_dashboard_tick_checks_cover_every_tick_table(panels, title):
    sql = _sql(panels, title)
    missing = [t for t in TICK_TABLES if not re.search(rf"\bFROM {t}\b", sql)]
    assert missing == []
