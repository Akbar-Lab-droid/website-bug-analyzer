"""Tests for analyzer.py.

Serves the buggy fixture (plus one healthy page) from a local HTTP server
that also sends the security headers a real well-configured site would, so
the tests measure the content checks rather than the test server itself.
"""

import functools
import http.server
import os
import shutil
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analyzer

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": "default-src 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

HEALTHY_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>A tidy little page</title>
  <meta name="description" content="A short description of this page.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="/healthy.html">
</head>
<body>
  <h1>Hello</h1>
  <p>Written by a person, on a quiet afternoon.</p>
  <img src="/ok.png" alt="A fine image" width="100" height="100">
  <p><a href="/healthy.html">Self link</a></p>
</body>
</html>
"""


class HeaderHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def log_message(self, *args):
        pass


class AnalyzerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="wba-test-")
        shutil.copy(os.path.join(FIXTURE_DIR, "fixture-buggy.html"),
                    os.path.join(cls.tmpdir, "fixture-buggy.html"))
        # 250 KB unminified stylesheet, served as /big.css.
        with open(os.path.join(cls.tmpdir, "big.css"), "w") as handle:
            handle.write("/* unminified stylesheet */\n" + "body { color: #333; }\n" * 12000)
        # Tiny valid PNG for the healthy image.
        with open(os.path.join(cls.tmpdir, "ok.png"), "wb") as handle:
            handle.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
                b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            )
        with open(os.path.join(cls.tmpdir, "healthy.html"), "w") as handle:
            handle.write(HEALTHY_PAGE)
        handler = functools.partial(HeaderHandler, directory=cls.tmpdir)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def messages(self, report):
        return [f["message"] for f in report["findings"]]

    def test_fixture_missing_seo_basics(self):
        report = analyzer.analyze(self.url("/fixture-buggy.html"))
        messages = self.messages(report)
        self.assertTrue(any("Missing <title>" in m for m in messages))
        self.assertTrue(any("Missing meta description" in m for m in messages))
        self.assertTrue(any("Missing lang attribute" in m for m in messages))
        self.assertTrue(any("Missing viewport meta tag" in m for m in messages))
        self.assertTrue(any("No <h1> heading" in m for m in messages))

    def test_fixture_broken_link_and_images(self):
        report = analyzer.analyze(self.url("/fixture-buggy.html"))
        messages = self.messages(report)
        self.assertTrue(any("Broken link" in m and "missing-page" in m for m in messages))
        self.assertTrue(any("missing alt text" in m for m in messages))
        self.assertTrue(any("Broken image" in m and "does-not-exist.png" in m
                            for m in messages))

    def test_fixture_large_unminified_asset(self):
        report = analyzer.analyze(self.url("/fixture-buggy.html"))
        messages = self.messages(report)
        self.assertTrue(any("Large unminified asset" in m for m in messages))

    def test_fixture_ai_verdict(self):
        report = analyzer.analyze(self.url("/fixture-buggy.html"))
        self.assertEqual(report["ai"]["verdict"], "Likely AI-built")
        details = " ".join(s["detail"] for s in report["ai"]["signals"])
        self.assertIn("Durable", details)

    def test_fixture_scores_poor(self):
        report = analyzer.analyze(self.url("/fixture-buggy.html"))
        self.assertEqual(report["health"], "Poor")
        self.assertLess(report["score"], 60)

    def test_mixed_content_detected_on_https(self):
        html = '<script src="http://example.com/tracker.js"></script>'
        page = analyzer.PageParser()
        page.feed(html)
        self.assertEqual(
            analyzer.find_mixed_content(page, True),
            ["http://example.com/tracker.js"],
        )
        self.assertEqual(analyzer.find_mixed_content(page, False), [])

    def test_healthy_page_scores_well(self):
        report = analyzer.analyze(self.url("/healthy.html"))
        messages = self.messages(report)
        self.assertFalse(any("Missing <title>" in m for m in messages))
        self.assertFalse(any("Broken link" in m for m in messages))
        self.assertFalse(any("missing alt text" in m for m in messages))
        self.assertEqual(report["ai"]["verdict"], "Likely human-built")
        # Only the plain-HTTP finding should cost points here.
        self.assertEqual(report["health"], "Good")
        self.assertGreaterEqual(report["score"], 85)

    def test_unreachable_url_reports_poor(self):
        report = analyzer.analyze("http://127.0.0.1:1/nope")
        self.assertEqual(report["health"], "Poor")
        self.assertEqual(report["score"], 0)


if __name__ == "__main__":
    unittest.main()
