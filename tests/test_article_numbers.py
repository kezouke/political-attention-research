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
    assert "16.8%" in article and "46.8%" in article
    assert "16,8%" in article and "46,8%" in article


def test_climate_chart_and_prose_use_full_ess_sample():
    data = rows("analysis/baseline/outputs/ess_full_country_changes.csv")
    article = (ROOT / "docs/index.html").read_text()
    assert len(data) == 22
    assert sum(float(row["change_pp"]) > 0 for row in data) == 21
    assert round(sum(float(row["pct_2016"]) for row in data) / 22, 1) == 28.7
    assert round(sum(float(row["pct_2020"]) for row in data) / 22, 1) == 39.5
    assert "from 28.7% to 39.5%" in article
    assert "с 28,7% до 39,5%" in article


def test_spain_endpoints_and_2013_peak_match_the_processed_series():
    data = {
        int(row["year"]): row
        for row in rows("data/processed/macro_issue_panel.csv")
        if row["iso"] == "ESP"
    }
    article = (ROOT / "docs/index.html").read_text()
    assert round(float(data[2010]["unemployment"]), 1) == 19.9
    assert round(float(data[2010]["unemploy"]), 1) == 72.1
    assert round(float(data[2013]["unemploy"]), 1) == 78.5
    assert round(float(data[2024]["unemploy"]), 1) == 20.6
    assert round(float(data[2024]["price"]), 1) == 37.9
    for en, ru in [("19.9%", "19,9%"), ("72.1%", "72,1%"),
                   ("78.5%", "78,5%"), ("20.6%", "20,6%"),
                   ("37.9%", "37,9%")]:
        assert en in article and ru in article


def test_housing_and_immigration_comparison_uses_one_cis_question():
    data = {
        (int(row["year"]), row["issue"]): row
        for row in rows("data/processed/identity_spain_cis_selected.csv")
    }
    expected = {
        (2024, "immigration"): 30.4,
        (2024, "housing"): 15.4,
        (2026, "immigration"): 19.7,
        (2026, "housing"): 37.5,
    }
    article = (ROOT / "docs/index.html").read_text()
    for key, value in expected.items():
        row = data[key]
        assert float(row["pct_top3"]) == value
        assert row["response_format"] == "spontaneous; up to three"
        assert row["mode"] == "telephone"
        assert f"{value:.1f}%" in article
        assert f"{value:.1f}".replace(".", ",") + "%" in article


def test_climate_direction_survives_removing_mode_changes():
    data = rows("analysis/baseline/outputs/ess_full_country_changes.csv")
    same_mode = [row for row in data if row["mode"] == "interview"]
    assert len(same_mode) == 16
    assert sum(float(row["change_pp"]) > 0 for row in same_mode) == 15
    article = (ROOT / "docs/index.html").read_text()
    assert "among the other 16, strong climate worry rose in 15" in article
    assert "16 стран рост сильной тревоги виден в 15" in article
