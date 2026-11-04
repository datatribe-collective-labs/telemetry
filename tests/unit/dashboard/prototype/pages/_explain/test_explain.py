import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dashboard.src.prototype.pages import _explain
from dashboard.src.prototype.pages._explain import (
    EXPLAINERS,
    SOURCES,
    SUMMARIES,
    explain,
)

PAGES_DIR = Path(_explain.__file__).parent


@pytest.fixture
def fake_st(monkeypatch):
    st = MagicMock()
    monkeypatch.setattr(_explain, "st", st)
    return st


def _keys_used_by_pages() -> set[str]:
    keys = set()
    # Pages only: the `_`-prefixed helper modules (incl. _explain's docstring) don't count.
    for page in PAGES_DIR.glob("[!_]*.py"):
        keys |= set(re.findall(r'explain\(\s*"([^"]+)"\s*\)', page.read_text(encoding="utf-8")))
    return keys


def test_explain_has_source_summary_and_explainer_for_every_chart_key_in_pages():
    keys = _keys_used_by_pages()
    assert keys, "no explain() calls found - did the pages move?"
    assert keys <= SOURCES.keys()
    assert keys <= SUMMARIES.keys()
    assert keys <= EXPLAINERS.keys()


def test_explain_dicts_share_the_same_keys():
    assert SOURCES.keys() == SUMMARIES.keys() == EXPLAINERS.keys()


def test_explain_has_no_text_for_charts_that_no_page_shows():
    assert SOURCES.keys() <= _keys_used_by_pages()


def test_explain_renders_badges_then_summary_then_expander(fake_st):
    explain("mission.map")

    line = fake_st.markdown.call_args_list[0].args[0]
    assert line.startswith(_explain.data_badge("real", "synthetic"))
    assert line.endswith(SUMMARIES["mission.map"])
    fake_st.expander.assert_called_once_with("About this chart")


def test_explain_renders_nothing_for_unknown_key(fake_st):
    explain("no.such.chart")

    fake_st.markdown.assert_not_called()
    fake_st.expander.assert_not_called()
