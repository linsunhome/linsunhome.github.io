import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class SiteContractTests(unittest.TestCase):
    def test_content_snapshot_is_valid(self):
        from validate_content import validate

        self.assertEqual(validate(ROOT), [], "content validation reported errors")

    def test_generated_pages_expose_public_contract(self):
        subprocess.run([sys.executable, "scripts/generate_site.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        routes = [
            "index.html",
            "en/index.html",
            "about/index.html",
            "en/about/index.html",
            "research/index.html",
            "en/research/index.html",
            "publications/index.html",
            "en/publications/index.html",
            "impact/index.html",
            "en/impact/index.html",
            "projects/llm-safety/index.html",
            "projects/rag-knowledge/index.html",
            "projects/tinyr1/index.html",
            "projects/memory-agents/index.html",
            "404.html",
        ]
        for route in routes:
            self.assertTrue((ROOT / route).exists(), route)
        for route in ("publications/index.html", "en/publications/index.html"):
            content = (ROOT / route).read_text()
            self.assertEqual(content.count('class="paper-row"'), 30, route)
            self.assertEqual(content.count('class="paper-summary"'), 30, route)
            self.assertNotIn("预印本", content)
            self.assertNotIn("preprint", content.lower())
        home = (ROOT / "index.html").read_text()
        impact = (ROOT / "impact/index.html").read_text()
        about = (ROOT / "about/index.html").read_text()
        self.assertIn("BV1dA7Y6cEgX", home)
        self.assertIn("BV19SKQ6HEau", home)
        self.assertIn("CN120409549B", impact)
        self.assertIn("GB/T 45288.2", impact)
        self.assertEqual(impact.count("BV1"), 2)
        self.assertEqual(impact.count('<details class="patent-group">'), 4)
        self.assertLess(about.find("04 / Service"), about.find("CONTACT"))
        self.assertIn("专利号", impact)
        self.assertEqual(len(re.findall(r'<a href="https?://[^" ]+"[^>]*target="_blank"[^>]*rel="noopener"', home)), len(re.findall(r'<a href="https?://', home)))


if __name__ == "__main__":
    unittest.main()
