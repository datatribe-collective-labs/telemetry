import pandas as pd
import pytest

from dashboard.src.prototype.views._link import duration_text


@pytest.mark.parametrize(("delta", "text"), [
    ("0s", "less than a minute"),
    ("59s", "less than a minute"),
    ("17min", "17 min"),
    ("60min", "1 h 0 min"),
    ("148min", "2 h 28 min"),
])
def test_duration_text_uses_plain_words(delta, text):
    assert duration_text(pd.Timedelta(delta)) == text
