"""Protect the article's headline comparisons against copy and chart drift."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with (ROOT / path).open(newline="") as file:
        return list(csv.DictReader(file))


def test_2022_price_comparison_uses_the_same_16_countries():
    data = rows("data/processed/common_shock_2021_2022_countries.csv")
    article = (ROOT / "docs/index.html").read_text()
    assert len(data) == 16
    before = sum(float(row["price_2021"]) for row in data) / len(data)
    after = sum(float(row["price_2022"]) for row in data) / len(data)
    assert round(before, 1) == 16.8
    assert round(after, 1) == 46.8
    assert round(after - before, 1) == 30.0
    assert "from 16.8% to 46.8%" in article
    assert "с 16,8% в 2021 году до 46,8% в 2022-м" in article


def test_climate_chart_and_prose_use_full_ess_sample():
    data = rows("analysis/baseline/outputs/ess_full_country_changes.csv")
    article = (ROOT / "docs/index.html").read_text()
    assert len(data) == 22
    assert sum(float(row["change_pp"]) > 0 for row in data) == 21
    assert round(sum(float(row["pct_2016"]) for row in data) / 22, 1) == 28.7
    assert round(sum(float(row["pct_2020"]) for row in data) / 22, 1) == 39.5
    assert "from 28.7% to 39.5%" in article
    assert "с 28,7% до 39,5%" in article
