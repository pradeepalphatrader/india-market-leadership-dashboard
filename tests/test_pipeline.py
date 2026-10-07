import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from india_market_dashboard.config import load_settings
from india_market_dashboard.data import read_classifications, read_history
from india_market_dashboard.pipeline import publish_site, run_pipeline


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
            self.assertTrue(dashboard["stocks"])
            self.assertEqual(len(dashboard["groups"]["macro_sectors"]), 12)
            self.assertFalse(dashboard["metadata"]["publishable"])
            with self.assertRaisesRegex(RuntimeError, "blocked"):
                publish_site(test_root, test_root / "build-test")

    def test_four_level_classification_schema(self):
        classes = read_classifications(self.root / "data/demo/classifications.csv")
        sample = next(iter(classes.values()))
        self.assertTrue(all((sample.macro_sector, sample.sector, sample.industry, sample.basic_industry)))
