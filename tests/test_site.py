import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class SiteContractTests(unittest.TestCase):
    def test_content_snapshot_is_valid(self):
        from validate_content import validate

        self.assertEqual(validate(ROOT), [], "content validation reported errors")

    def test_content_validation_rejects_incomplete_result_tables(self):
        from validate_content import validate

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "data", root / "data")
            shutil.copytree(ROOT / "assets", root / "assets")
            path = root / "data/site-content.json"
            content = json.loads(path.read_text())
            project = next(item for item in content["projects"] if item["id"] == "tinyr1")
            result = project["resultSections"][0]
            result["columns"].pop("en")
            result["rows"][0].pop()
            result["figure"]["path"] = "assets/projects/missing.png"
            path.write_text(json.dumps(content))
            issues = validate(root)
            self.assertTrue(any("missing bilingual columns" in issue for issue in issues), issues)
            self.assertTrue(any("row width" in issue for issue in issues), issues)
            self.assertTrue(any("missing figure" in issue for issue in issues), issues)

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
            self.assertNotIn('class="paper-summary"', content)
            for badge in ("共同作者", "第一作者", "已发表", "Co-author", "First author", "Published"):
                self.assertNotIn(f'>{badge}</span>', content)
            self.assertNotIn("预印本", content)
            self.assertNotIn("preprint", content.lower())
            triplay = content.split("TriPlay-RL:", 1)[1].split("</article>", 1)[0]
            label = "通讯作者" if route.startswith("publications/") else "Corresponding author"
            self.assertIn(f'Lin Sun</strong><sup class="corresponding-author" aria-label="{label}">*</sup>', triplay)
            preview = content.split("Tinyr1-32b-preview:", 1)[1].split("</article>", 1)[0]
            self.assertNotIn('class="corresponding-author"', preview)
        home = (ROOT / "index.html").read_text()
        self.assertEqual(home.count('class="paper-row"'), 9)
        selected_titles = re.findall(r'class="paper-title-link"[^>]*>(.*?)</a>', home)
        self.assertTrue(selected_titles[0].startswith("When Good OCR"))
        self.assertTrue(selected_titles[1].startswith("BEAR:"))
        self.assertTrue(selected_titles[-1].startswith("Tinyr1-32b-preview:"))
        for title in ("Harness-Bench", "MemAudit", "ArborMem"):
            self.assertFalse(any(title in selected for selected in selected_titles))
        impact = (ROOT / "impact/index.html").read_text()
        about = (ROOT / "about/index.html").read_text()
        self.assertIn("BV1dA7Y6cEgX", home)
        self.assertIn("BV19SKQ6HEau", home)
        self.assertNotIn("CN120409549B", impact)
        self.assertNotIn("第三发明人", impact)
        self.assertIn("GB/T 45288.2", impact)
        self.assertEqual(impact.count("BV1"), 2)
        self.assertEqual(impact.count('class="patent-group"'), 4)
        self.assertEqual(impact.count('class="patent-entry"'), 18)
        self.assertIn("一种获取问答对的相关联程度的装置和方法", impact)
        self.assertIn("百人规模", about)
        for fact in ("大模型专委会主任", "标准规范知识图谱联盟", "ACL、EMNLP、AAAI 等会议审稿人", "上市招股说明书", "北京电视台", "360 智脑事业部", "贝壳找房 语言智能与搜索部 / 如视事业部", "360 搜索事业部", "腾讯 网络媒体产品技术部", "参与的部分国拨项目"):
            self.assertIn(fact, about)
        for text in ("2021.01", "2023.06", "2024.10", "service-period"):
            self.assertNotIn(text, about)
        self.assertIn('data-recognition="personal"', impact)
        self.assertIn('data-recognition="team"', impact)
        for text in ("2025-J-02-2-04", "鉴字", "standard-meta", "主要起草人", "参与标准工作"):
            self.assertNotIn(text, impact)
        for text in ("公开交流与近期动态", "subsection-title"):
            self.assertNotIn(text, home)
        for date in ("2026-06-25", "2026-06-29"):
            self.assertIn(date, home)
        for text in ("凤凰人才", "首都网络安全人才", "发明专利", "国家及行业标准"):
            self.assertIn(text, home)
        self.assertEqual(about.count('class="funded-project"'), 4)
        for fact in ("第五届中国人工智能大赛", "雄安网络安全技术应用大赛", "首都网络安全人才", "大模型安全护栏能力检测"):
            self.assertIn(fact, impact)
        for route in routes:
            self.assertNotIn("涉密", (ROOT / route).read_text())
            self.assertNotIn("鉴字", (ROOT / route).read_text())
        for prefix in ("", "en/"):
            tiny = (ROOT / f"{prefix}projects/tinyr1/index.html").read_text()
            rag = (ROOT / f"{prefix}projects/rag-knowledge/index.html").read_text()
            self.assertEqual(tiny.count('<table'), 3)
            self.assertIn("89.2", tiny)
            self.assertIn("Beyond Parameter Arithmetic", tiny)
            self.assertIn("https://huggingface.co/qihoo360/TinyR1-32B\"", tiny)
            self.assertIn("tinyr1-branch-merge.png", tiny)
            self.assertNotIn("tinyr1-paper-figure1.png", tiny)
            self.assertEqual(rag.count('<table'), 2)
            self.assertIn("PP-StructureV3", rag)
            self.assertIn("91.86", rag)
            self.assertIn("induocr-pipeline.png", rag)
            self.assertIn("bear-evidence-flow.png", rag)
            self.assertNotIn("bear-paper-figure2.png", rag)
        research = (ROOT / "research/index.html").read_text()
        self.assertNotIn("五层技术体系", research)
        self.assertNotIn("thread-grid", research)
        for route in ("index.html", "en/index.html", "impact/index.html", "en/impact/index.html"):
            self.assertNotIn('class="paper-summary"', (ROOT / route).read_text())
        self.assertNotIn("以公开奖项", impact)
        for prefix in ("", "en/"):
            for slug in ("tinyr1", "rag-knowledge", "llm-safety", "memory-agents"):
                content = (ROOT / f"{prefix}projects/{slug}/index.html").read_text()
                for text in ("公开边界", "Public boundary", "个人角色", "Personal role"):
                    self.assertNotIn(text, content)
        self.assertEqual(len(re.findall(r'<a href="https?://[^" ]+"[^>]*target="_blank"[^>]*rel="noopener"', home)), len(re.findall(r'<a href="https?://', home)))


if __name__ == "__main__":
    unittest.main()
