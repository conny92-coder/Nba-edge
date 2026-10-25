import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def test_dashboard_and_simulation(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            shutil.copytree(ROOT / 'data', data)
            day = datetime.now(timezone.utc).date().isoformat()
            (data / 'live_projections.csv').write_text(
                'UTC tipoff,Away,Home,Away projected,Home projected,Status\n'
                f'{day}T23:00Z,GSW,NYK,114.5,116.5,STATUS_SCHEDULED\n')
            try:
                os.chdir(directory)
                st.cache_data.clear()
                app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.tabs), 10)
                self.assertTrue(any(len(table.value) == 30 for table in app.dataframe))
                app.select_slider[0].set_value(1000).run(timeout=30)
                self.assertFalse(app.exception)
                self.assertTrue(any(metric.label == 'Home win %' for metric in app.metric))
            finally:
                os.chdir(original)
                st.cache_data.clear()
