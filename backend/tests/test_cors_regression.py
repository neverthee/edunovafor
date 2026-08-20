import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_FILE = PROJECT_ROOT / "backend" / "main.py"
LEARNING_FILE = PROJECT_ROOT / "backend" / "api" / "learning.py"


class CorsRegressionTests(unittest.TestCase):
    def test_main_persists_runtime_cors_origins_into_app_config(self):
        content = MAIN_FILE.read_text(encoding="utf-8")
        self.assertIn("app.config['CORS_ORIGINS'] = CORS_ORIGINS", content)

    def test_main_after_request_adds_authorization_preflight_headers(self):
        content = MAIN_FILE.read_text(encoding="utf-8")
        match = re.search(
            r"@app\.after_request\s+def enforce_configured_cors\(response\):(?P<body>.*?)return response",
            content,
            re.S,
        )
        self.assertIsNotNone(match, "Could not find enforce_configured_cors in backend/main.py")
        body = match.group("body")
        self.assertIn("Access-Control-Allow-Headers", body)
        self.assertIn("Authorization", body)
        self.assertIn("Access-Control-Allow-Methods", body)
        self.assertIn("OPTIONS", body)
        self.assertIn("Access-Control-Max-Age", body)

    def test_courses_options_route_uses_shared_cors_preflight_helper(self):
        content = LEARNING_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "return build_cors_preflight_response('GET,POST,OPTIONS')",
            content,
        )


if __name__ == "__main__":
    unittest.main()
