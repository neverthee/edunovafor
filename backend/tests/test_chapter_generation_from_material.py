import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.rag.chapter_generation_from_material import (  # noqa: E402
    _clean_toc_line,
    _extract_chapters_from_toc_text,
    _find_toc_page_span,
    _looks_like_toc_page,
    _validate_toc_parse_result,
)


class ChapterGenerationFromMaterialTests(unittest.TestCase):
    def test_clean_toc_line_filters_formula_like_body_text(self):
        line, page_number = _clean_toc_line("431 kJ/mol×2 mol = 862 kJ的能量，如图1-5所示。")
        self.assertEqual(line, "")
        self.assertIsNone(page_number)

    def test_looks_like_toc_page_requires_more_than_dense_body_numbering(self):
        body_like_text = "\n".join([
            "1.1 向量抽象数据类型的实现",
            "1.2 优化程序性能",
            "1.3 消除循环的低效率",
            "1.4 减少过程调用",
            "1.5 消除不必要的内存引用",
        ])
        self.assertFalse(_looks_like_toc_page(body_like_text))

    def test_extract_chapters_from_toc_text_keeps_real_catalog_entries(self):
        toc_text = "\n".join([
            "第一章 化学反应与能量 1",
            "1.1 化学反应中的能量变化 3",
            "1.2 反应热与焓变 8",
            "第二章 化学反应速率与化学平衡 21",
            "2.1 化学反应速率 23",
            "2.2 化学平衡 31",
            "431 kJ/mol×2 mol = 862 kJ的能量，如图1-5所示。",
        ])
        chapters = _extract_chapters_from_toc_text(toc_text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]["title"], "第一章 化学反应与能量")
        self.assertEqual(chapters[1]["title"], "第二章 化学反应速率与化学平衡")
        self.assertEqual(
            [section["title"] for section in chapters[0]["sections"]],
            ["1.1 化学反应中的能量变化", "1.2 反应热与焓变"],
        )

    def test_find_toc_page_span_tracks_follow_up_pages_without_toc_word(self):
        page_texts = [
            "封面",
            "\n".join([
                "目录",
                "第一章 化学反应的热效应 3",
                "第一节 反应热 4",
                "第二节 反应热的计算 14",
                "第二章 化学反应速率与化学平衡 23",
            ]),
            "\n".join([
                "第一节 化学反应速率 24",
                "第二节 化学平衡 32",
                "整理与提升 52",
                "实验活动1 探究影响化学平衡移动的因素 55",
            ]),
            "本章主要介绍化学反应速率与化学平衡的基本概念。",
        ]
        toc_span = _find_toc_page_span(page_texts)
        self.assertEqual(len(toc_span), 2)
        self.assertIn("实验活动1 探究影响化学平衡移动的因素 55", toc_span[1])

    def test_find_toc_page_span_handles_split_title_and_page_lines(self):
        page_texts = [
            "封面",
            "\n".join([
                "目录",
                "第一章　化学反应的热效应",
                "3",
                "第一节　反应热",
                "4",
                "第二节　反应热的计算",
                "14",
                "第二章　化学反应速率与化学平衡",
                "23",
            ]),
            "\n".join([
                "第一节　化学反应速率",
                "24",
                "第二节　化学平衡",
                "32",
                "整理与提升",
                "52",
                "实验活动1 探究影响化学平衡移动的因素",
                "55",
            ]),
        ]
        toc_span = _find_toc_page_span(page_texts)
        self.assertEqual(len(toc_span), 2)

        chapters = _extract_chapters_from_toc_text("\n\n".join(toc_span))
        self.assertEqual([chapter["title"] for chapter in chapters], [
            "第一章 化学反应的热效应",
            "第二章 化学反应速率与化学平衡",
        ])
        self.assertEqual(
            [section["title"] for section in chapters[1]["sections"]],
            ["第一节 化学反应速率", "第二节 化学平衡", "整理与提升", "实验活动1 探究影响化学平衡移动的因素"],
        )

    def test_extract_chapters_from_toc_text_supports_chinese_sections_appendix_and_repeated_special_sections(self):
        toc_text = "\n".join([
            "目录",
            "第一章 化学反应的热效应 3",
            "第一节 反应热 4",
            "第二节 反应热的计算 14",
            "整理与提升 20",
            "第二章 化学反应速率与化学平衡 23",
            "第一节 化学反应速率 24",
            "第二节 化学平衡 32",
            "整理与提升 52",
            "实验活动1 探究影响化学平衡移动的因素 55",
            "第四章 化学反应与电能 95",
            "第一节 原电池 96",
            "实验活动5 制作简单的燃料电池 123",
            "附录 I 某些物质的燃烧热（25 ℃，101 kPa） 124",
            "元素周期表 128",
        ])
        chapters = _extract_chapters_from_toc_text(toc_text)
        self.assertEqual(
            [chapter["title"] for chapter in chapters],
            [
                "第一章 化学反应的热效应",
                "第二章 化学反应速率与化学平衡",
                "第四章 化学反应与电能",
                "附录 I 某些物质的燃烧热（25 ℃，101 kPa）",
                "元素周期表",
            ],
        )
        self.assertEqual(
            [section["title"] for section in chapters[0]["sections"]],
            ["第一节 反应热", "第二节 反应热的计算", "整理与提升"],
        )
        self.assertEqual(
            [section["title"] for section in chapters[1]["sections"]],
            ["第一节 化学反应速率", "第二节 化学平衡", "整理与提升", "实验活动1 探究影响化学平衡移动的因素"],
        )
        self.assertEqual(
            [section["title"] for section in chapters[2]["sections"]],
            ["第一节 原电池", "实验活动5 制作简单的燃料电池"],
        )

    def test_extract_chapters_from_toc_text_treats_unicode_roman_appendix_as_chapter(self):
        toc_text = "\n".join([
            "第四章　化学反应与电能",
            "95",
            "第一节　原电池",
            "96",
            "附录Ⅰ 某些物质的燃烧热（25 ℃，101 kPa）",
            "124",
            "附录Ⅱ 某些弱电解质的电离常数（25 ℃）",
            "125",
            "● 暖贴的设计与制作",
            "116",
        ])
        chapters = _extract_chapters_from_toc_text(toc_text)
        self.assertEqual(
            [chapter["title"] for chapter in chapters],
            [
                "第四章 化学反应与电能",
                "附录Ⅰ 某些物质的燃烧热（25 ℃，101 kPa）",
                "附录Ⅱ 某些弱电解质的电离常数（25 ℃）",
            ],
        )
        self.assertEqual([section["title"] for section in chapters[0]["sections"]], ["第一节 原电池"])

    def test_extract_chapters_from_toc_text_requires_page_numbers_for_catalog_entries(self):
        toc_text = "\n".join([
            "目录",
            "第一章 化学反应的热效应 3",
            "第一节 反应热",
            "第二节 反应热的计算 14",
        ])
        chapters = _extract_chapters_from_toc_text(toc_text)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(
            [section["title"] for section in chapters[0]["sections"]],
            ["第二节 反应热的计算"],
        )

    def test_validate_toc_parse_result_rejects_sparse_rule_parse(self):
        is_valid, message = _validate_toc_parse_result([
            {
                "title": "第一章 化学反应的热效应",
                "duration": 60,
                "sections": [],
                "start_page": 3,
            }
        ])
        self.assertFalse(is_valid)
        self.assertIn("质量不足", message)


if __name__ == "__main__":
    unittest.main()
