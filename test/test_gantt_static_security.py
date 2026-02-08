import unittest
from pathlib import Path

from main import app


class TestGanttStaticSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True

    def setUp(self):
        self.client = app.test_client()

    def test_blocks_windows_absolute_path(self):
        response = self.client.get("/gantt/static/C:/Windows/win.ini")
        self.assertIn(response.status_code, {403, 404})
        response.close()

    def test_blocks_unc_path(self):
        response = self.client.get("/gantt/static/%5C%5Cserver%5Cshare%5Cwin.ini")
        self.assertIn(response.status_code, {403, 404})
        response.close()

    def test_blocks_parent_traversal(self):
        response = self.client.get("/gantt/static/..%2F..%2Fmain.py")
        self.assertIn(response.status_code, {403, 404})
        response.close()

    def test_serves_expected_assets(self):
        css = self.client.get("/gantt/static/dhtmlxgantt.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn("text/css", css.content_type)
        css.close()

        js = self.client.get("/gantt/static/scripts/dhtmlxgantt.js")
        self.assertEqual(js.status_code, 200)
        self.assertIn("application/javascript", js.content_type)
        js.close()

        static_folder = app.static_folder or ""
        self.assertTrue(static_folder)
        font_file = next((Path(static_folder) / "gantt" / "fonts").glob("*.ttf")).name
        font = self.client.get(f"/gantt/static/fonts/{font_file}")
        self.assertEqual(font.status_code, 200)
        self.assertIn("font/ttf", font.content_type)
        font.close()
