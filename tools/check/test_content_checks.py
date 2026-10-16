"""Regression tests for the blocking gates and deterministic content generation."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from check_images import collect_references
from content_catalog import build_catalog, md_link, title_of
from generate_catalog import main as generate_main, outputs, replace_block
from lib_links import anchors_in, check_links, content_files, links_in


class LinkChecks(TestCase):
    def test_reserved_filenames_balanced_parentheses_html_and_references(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "README.md"
            (root / "C#语言.md").write_text("## 中文标题\n", encoding="utf-8")
            (root / "图(新版).png").write_bytes(b"image")
            (root / "data.js").write_text("", encoding="utf-8")
            source.write_text('[C#](C%23语言.md#中文标题)\n![图](图(新版).png)\n'
                              '<img src="图(新版).png">\n[参考][doc]\n[doc]: C%23语言.md#中文标题\n'
                              '<script src="data.js">const example = "[x](missing.md)";</script>', encoding="utf-8")
            errors, checked = check_links([source], root)
            self.assertEqual(errors, [])
            self.assertEqual(checked, 5)
            refs = collect_references([source], root)
            self.assertEqual(set(refs), {root / "图(新版).png"})

    def test_missing_file_and_anchor_fail_with_source_locations(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "README.md"
            source.write_text('## 正文\n[x](missing.md)\n[bad](#不存在)\n<img src="missing.png">', encoding="utf-8")
            errors, checked = check_links([source], root)
            self.assertEqual(checked, 3)
            self.assertEqual(len(errors), 3)
            self.assertIn("README.md:2", errors[0])
            self.assertIn("missing anchor", errors[1])

    def test_examples_comments_and_remote_urls_are_not_local_links(self):
        text = ('```markdown\n[x](missing.md)\n<script src="fake.js"></script>\n```\n'
                '> ```\n> [x](missing.md)\n> ```\n'
                '`[example](missing.md)`\n<!-- [x](missing.md) -->\n'
                '[remote](https://example.com/page)\n')
        targets = [link.target for link in links_in(text)]
        self.assertEqual(targets, ["https://example.com/page"])

    def test_github_chinese_duplicate_and_formatted_heading_anchors(self):
        anchors = anchors_in('## 📝 文档编写规范\n## **第三方接口 / SDK**\n## 同名\n## 同名\n')
        self.assertEqual(anchors, {"-文档编写规范", "第三方接口--sdk", "同名", "同名-1"})

    def test_repository_escape_is_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "README.md"
            source.write_text('[escape](../)\n', encoding="utf-8")
            errors, _ = check_links([source], root)
            self.assertEqual(len(errors), 1)

    def test_scan_includes_nested_code_docs_and_skips_build_outputs(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for name in ["README.md", "code/example/README.md", "code/example/build/generated.md"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            self.assertEqual(len(content_files(root)), 2)


class CatalogChecks(TestCase):
    def fixture(self, root):
        sources = {
            "mds/1.基础能力/1.基础能力.md": "## 基础能力\n## 目录\n<!-- BEGIN GENERATED:module-index -->\n<!-- END GENERATED:module-index -->\n",
            "mds/1.基础能力/1.1.编程语言.md": "## 编程语言\n",
            "mds/1.基础能力/1.1.3.C#语言.md": "## C#语言\n**关键词:**<br/>\n*C#,语言*\n**标签:**\n*等级: 初级|中级, 角色: 客户端开发*\n",
            "mds/topics/推荐阅读路径.md": "<!-- BEGIN GENERATED:document-count -->\n<!-- END GENERATED:document-count -->\n## 路径 A：新人入门线\n[C#](../1.基础能力/1.1.3.C%23语言.md)\n## 路径 B：研发实战线\n[C#](../1.基础能力/1.1.3.C%23语言.md)\n## 路径 C：上线运营线\n[C#](../1.基础能力/1.1.3.C%23语言.md)\n",
            "README.md": "Preserve my prose\n<!-- BEGIN GENERATED:content-stats -->\n<!-- END GENERATED:content-stats -->\n",
        }
        for name, text in sources.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_new_documents_flow_into_inventory_counts_and_generated_indexes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            self.fixture(root)
            first = build_catalog(root)
            self.assertEqual(first["stats"]["documents"], 4)
            self.assertEqual(first["paths"][0]["paths"], ["mds/1.基础能力/1.1.3.C#语言.md"])
            self.assertEqual(first["docs"][-1]["l"], 1)
            (root / "mds/1.基础能力/1.1.4.新增.md").write_text("## 新增\n", encoding="utf-8")
            generated = outputs(root)
            self.assertIn("新增", generated[root / "INDEX.md"])
            self.assertIn("5 篇文档", generated[root / "README.md"])
            self.assertIn("Preserve my prose", generated[root / "README.md"])
            self.assertIn("C%23语言.md", generated[root / "KEYWORDS.md"])
            self.assertEqual(generated, outputs(root))

    def test_mismatched_generated_markers_fail_instead_of_erasing_prose(self):
        with self.assertRaises(ValueError):
            replace_block("handwritten prose", "missing", "new data")

    def test_logical_parent_can_differ_from_historical_file_number(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            self.fixture(root)
            for name, title in [("2.技术能力/2.技术能力.md", "技术能力"),
                                ("2.技术能力/2.1.客户端技术.md", "客户端技术"),
                                ("4.生产能力/4.生产能力.md", "生产能力"),
                                ("4.生产能力/4.1.游戏生产.md", "游戏生产"),
                                ("4.生产能力/4.1.3.引擎.md", "引擎")]:
                p = root / "mds" / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(f"## {title}\n", encoding="utf-8")
            doc = next(d for d in build_catalog(root)["docs"] if d["t"] == "引擎")
            self.assertEqual(doc["c"], 2)
            self.assertEqual(doc["parent"], "mds/2.技术能力/2.1.客户端技术.md")

    def test_leading_table_of_contents_is_not_used_as_document_title(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "chapter.md"
            source.write_text("## 目录\n\n## 正文标题\n", encoding="utf-8")
            self.assertEqual(title_of(source), "正文标题")

    def test_check_mode_returns_nonzero_without_writing_stale_output(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            stale = root / "content.js"
            stale.write_text("old", encoding="utf-8")
            with patch("generate_catalog.ROOT", root), patch("generate_catalog.outputs", return_value={stale: "new"}), patch("sys.argv", ["generate_catalog.py", "--check"]), redirect_stdout(StringIO()):
                self.assertEqual(generate_main(), 1)
            self.assertEqual(stale.read_text(), "old")

    def test_markdown_path_encoding_keeps_fragment_characters_in_filenames(self):
        self.assertEqual(md_link("C#", "C#语言.md"), "[C#](C%23语言.md)")


if __name__ == "__main__":
    main()
