import csv
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from india_market_dashboard.config import load_settings
from india_market_dashboard.data import read_classifications, read_history
from india_market_dashboard.models import PriceBar
from india_market_dashboard.pipeline import _latest_complete_session, publish_site, run_pipeline


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_demo_pipeline_is_complete_but_never_publishable(self):
        with tempfile.TemporaryDirectory() as temporary:
            test_root = Path(temporary)
            shutil.copytree(self.root / "config", test_root / "config")
            (test_root / "site/data").mkdir(parents=True)
            run_pipeline(test_root, self.root / "data/demo", self.root / "data/demo/classifications.csv", demo=True)
            dashboard = json.loads((test_root / "site/data/dashboard.json").read_text())
            history = json.loads((test_root / "site/data/history.json").read_text())
            self.assertTrue(dashboard["stocks"])
            sample = dashboard["stocks"][0]
            for field in (
                "return_1_week_percent", "return_12_month_percent", "sma_65", "adr_percent",
                "high_52_week", "low_52_week", "position_52_week_percent",
                "relative_strength_rating", "opportunity_type",
            ):
                self.assertIn(field, sample)
            self.assertTrue(1 <= sample["relative_strength_rating"] <= 99)
            self.assertIn("above_sma_65_percent", dashboard["market"])
            self.assertEqual(13, len(dashboard["scanner_catalog"]))
            self.assertEqual(13, len(dashboard["scanner_results"]))
            self.assertIn("vpk_scans", sample)
            self.assertEqual(len(dashboard["groups"]["macro_sectors"]), 12)
            self.assertFalse(dashboard["metadata"]["publishable"])
            self.assertEqual(history["method"], "current_universe_reconstructed")
            self.assertTrue(history["series"])
            self.assertIn("coverage_percent", history["series"][-1])
            self.assertIn("equal_weight_proxy", history["series"][-1])
            self.assertEqual(history["series"][-1]["date"], dashboard["metadata"]["analysis_date"])
            with self.assertRaisesRegex(RuntimeError, "blocked"):
                publish_site(test_root, test_root / "build-test")

    def test_four_level_classification_schema(self):
        classes = read_classifications(self.root / "data/demo/classifications.csv")
        sample = next(iter(classes.values()))
        self.assertTrue(all((sample.macro_sector, sample.sector, sample.industry, sample.basic_industry)))

    def test_partial_latest_session_is_not_selected(self):
        complete, partial = date(2026, 10, 5), date(2026, 10, 6)
        bars = [
            PriceBar(complete, symbol, 100, 101, 99, 100, 1000, 100000, "EQ")
            for symbol in ("AAA", "BBB", "CCC")
        ]
        bars.append(PriceBar(partial, "AAA", 100, 101, 99, 100, 1000, 100000, "EQ"))
        self.assertEqual(_latest_complete_session(bars, expected_universe=3, minimum_coverage=0.9), complete)

    def test_site_exposes_intelligence_workflow(self):
        html = (self.root / "site/index.html").read_text(encoding="utf-8")
        javascript = (self.root / "site/assets/app.js").read_text(encoding="utf-8")
        for phrase in ("Market X-Ray", "Copy TradingView", "Daily market journal", "global-search", "Thirteen precise scanners"):
            self.assertIn(phrase, html)
        for phrase in ("relative_strength_rating", "near_sma_65", "Interactive price chart", "showList"):
            self.assertIn(phrase, javascript)
