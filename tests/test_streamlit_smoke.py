"""Streamlit smoke test: load app with repository fixtures and assert no uncaught exception."""
import unittest

class DashboardSmokeTest(unittest.TestCase):
    def test_streamlit_boots(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            self.skipTest("Streamlit not installed")
        app = AppTest.from_file("app.py", default_timeout=30)
        app.run()
        self.assertEqual([str(e.message) for e in app.exception], [])

if __name__ == "__main__":
    unittest.main()
