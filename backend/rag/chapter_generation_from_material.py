import json
import math
import os
import re
import tempfile
from difflib import SequenceMatcher
from json import JSONDecoder
from typing import Any, Dict, List, Optional, Tuple

import requests
from pypdf import PdfReader

from backend.rag.parsers.pdf_parser import parse_pdf
from backend.rag.parsers.ppt_parser import parse_ppt


CHAPTER_DIRNAME = "chapters"
CHAPTER_FILENAME = "chapters.json"
PDF_SCOPE = "replace_all"
PPT_SCOPE = "single_chapter"
PPT_IGNORE_KEYWORDS = {
    "封面", "目录", "agenda", "contents", "content", "thanks", "thank you",
    "总结", "参考", "reference", "references", "附录", "q&a", "qa", "结束",
}
FRONT_MATTER_TITLE_KEYWORDS = (
    "封面", "前言", "前沿", "序言", "中文版序", "译者序", "出版社的话", "出版者的话", "出版说明",
    "内容提要", "目录", "扉页", "版权", "关于作者", "作者简介", "致谢",
)


def preview_generate_chapters_from_material(
    *,
    course_name: str,
    course_id: int,
    source_type: str,
    material_title: str,
    material_path: str,
    upload_root: str,
    existing_chapters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    warnings: List[str] = []
    existing = normalize_generated_chapters(existing_chapters or [])

    if source_type == "pdf":
        generated = generate_chapters_from_pdf(
            course_name=course_name,
            pdf_path=material_path,
            warnings=warnings,
            upload_root=upload_root,
            derived_owner=course_id,
        )
        return {
            "status": "success",
            "source_type": "pdf",
            "generation_scope": PDF_SCOPE,
            "generated_chapters": generated,
            "warnings": warnings,
        }

    if source_type == "ppt":
        generated = generate_single_chapter_from_ppt(
            material_title=material_title,
            ppt_path=material_path,
            upload_root=upload_root,
            derived_owner=course_id,
            warnings=warnings,
        )
        result: Dict[str, Any] = {
            "status": "success",
            "source_type": "ppt",
            "generation_scope": PPT_SCOPE,
            "generated_chapters": generated,
            "warnings": warnings,
        }
        if generated:
            match = match_chapter_to_existing(generated[0], existing)
            if match:
                result.update(match)
        return result

    raise ValueError("unsupported source_type")


def apply_generated_chapters(
    *,
    course_id: int,
    upload_root: str,
    source_type: str,
    apply_mode: str,
    generated_chapters: List[Dict[str, Any]],
    target_chapter_index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    normalized_generated = normalize_generated_chapters(generated_chapters)
    existing = load_course_chapters(upload_root, course_id)

    if source_type == "pdf":
        if apply_mode != "replace_all":
            raise ValueError("PDF 模式仅支持 replace_all")
        updated = normalized_generated
    elif source_type == "ppt":
        if len(normalized_generated) != 1:
            raise ValueError("PPT 模式只允许应用单章内容")
        chapter = normalized_generated[0]
        if apply_mode == "append_one":
            updated = existing + [chapter]
        elif apply_mode == "replace_one":
            if target_chapter_index is None:
                raise ValueError("replace_one 模式必须提供 target_chapter_index")
            if target_chapter_index < 0 or target_chapter_index >= len(existing):
                raise ValueError("target_chapter_index 超出范围")
            updated = existing.copy()
            updated[target_chapter_index] = chapter
        else:
            raise ValueError("PPT 模式仅支持 replace_one 或 append_one")
    else:
        raise ValueError("unsupported source_type")

    normalized_updated = normalize_generated_chapters(updated)
    save_course_chapters(upload_root, course_id, normalized_updated)
    return normalized_updated


def load_course_chapters(upload_root: str, course_id: int) -> List[Dict[str, Any]]:
    chapters_file_path = _get_chapters_file_path(upload_root, course_id)
    if not os.path.exists(chapters_file_path):
        return []
    with open(chapters_file_path, "r", encoding="utf-8") as file_obj:
        loaded = json.load(file_obj)
    return normalize_generated_chapters(loaded if isinstance(loaded, list) else [])


def save_course_chapters(upload_root: str, course_id: int, chapters: List[Dict[str, Any]]) -> None:
    course_folder = _ensure_course_chapter_folder(upload_root, course_id)
    final_path = os.path.join(course_folder, CHAPTER_FILENAME)
    normalized = normalize_generated_chapters(chapters)

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=course_folder, suffix=".tmp") as temp_file:
        json.dump(normalized, temp_file, ensure_ascii=False, indent=2)
        temp_path = temp_file.name

    os.replace(temp_path, final_path)


def normalize_generated_chapters(chapters: Any) -> List[Dict[str, Any]]:
    if not isinstance(chapters, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue

        title = _clean_title(chapter.get("title"))
        if not title:
            continue

        raw_sections = chapter.get("sections") if isinstance(chapter.get("sections"), list) else []
        start_page = _coerce_positive_int(chapter.get("start_page") or chapter.get("page"))
        source_material_id = _coerce_positive_int(chapter.get("source_material_id") or chapter.get("material_id"))
        source_material_title = _trim_text(
            chapter.get("source_material_title") or chapter.get("material_title"),
            200,
        )
        source_type = str(chapter.get("source_type") or "").strip().lower()
        sections: List[Dict[str, Any]] = []
        for section in raw_sections:
            if not isinstance(section, dict):
                continue
            section_title = _clean_title(section.get("title"))
            if not section_title:
                continue
            content = _trim_text(section.get("content"), 280)
            section_item = {
                "title": section_title,
                "duration": _coerce_duration(section.get("duration"), fallback=20 if raw_sections else 60),
                "content": content,
            }
            section_start_page = _coerce_positive_int(section.get("start_page") or section.get("page"))
            if section_start_page is not None:
                section_item["start_page"] = section_start_page
                if start_page is None:
                    start_page = section_start_page
            sections.append(section_item)

        if sections:
            chapter_duration = sum(section["duration"] for section in sections)
        else:
            chapter_duration = _coerce_duration(chapter.get("duration"), fallback=60)

        chapter_item = {
            "title": title,
            "duration": chapter_duration,
            "sections": sections,
            "is_front_matter": bool(chapter.get("is_front_matter")),
        }
        if start_page is not None:
            chapter_item["start_page"] = start_page
        if source_material_id is not None:
            chapter_item["source_material_id"] = source_material_id
        if source_material_title:
            chapter_item["source_material_title"] = source_material_title
        if source_type in {"pdf", "ppt"}:
            chapter_item["source_type"] = source_type
        normalized.append(chapter_item)

    first_main_chapter_index = next(
        (index for index, chapter in enumerate(normalized) if _looks_like_main_chapter_title(str(chapter.get("title") or ""))),
        None,
    )

    for index, chapter in enumerate(normalized):
        explicit_front_matter = bool(chapter.get("is_front_matter"))
        inferred_front_matter = (
            first_main_chapter_index is not None
            and index < first_main_chapter_index
            and _looks_like_front_matter_title(str(chapter.get("title") or ""))
        )
        chapter["is_front_matter"] = explicit_front_matter or inferred_front_matter

    return normalized


def match_chapter_to_existing(
    generated_chapter: Dict[str, Any],
    existing_chapters: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    generated_title = _normalize_for_match(generated_chapter.get("title"))
    if not generated_title:
        return None

    best_index = -1
    best_score = 0.0
    for index, chapter in enumerate(existing_chapters):
        title = _normalize_for_match(chapter.get("title"))
        if not title:
            continue
        score = SequenceMatcher(None, generated_title, title).ratio()
        if score > best_score:
            best_index = index
            best_score = score

    if best_index < 0 or best_score < 0.6:
        return None

    return {
        "suggested_target_index": best_index,
        "suggested_target_title": existing_chapters[best_index].get("title", ""),
        "match_confidence": round(best_score, 3),
    }


def generate_chapters_from_pdf(
    course_name: str,
    pdf_path: str,
    warnings: Optional[List[str]] = None,
    upload_root: Optional[str] = None,
    derived_owner: Any = "system",
) -> List[Dict[str, Any]]:
    from backend.api.rag_ai import get_api_config

    warnings = warnings if warnings is not None else []
    reader = PdfReader(pdf_path)

    outline_chapters = _extract_chapters_from_pdf_outline(reader)
    if outline_chapters:
        return normalize_generated_chapters(outline_chapters)

    api_key, api_base, _ = get_api_config()
    parsed_pdf = parse_pdf(
        pdf_path,
        upload_root=upload_root,
        owner_id=derived_owner,
        api_key=api_key,
        api_base=api_base,
        parse_mode="chapter_preview_pdf",
    )
    page_texts = _extract_pdf_page_texts(parsed_pdf, max_pages=20)
    if not any(text.strip() for text in page_texts):
        raise ValueError("PDF 未提取到可用文本")

    parsed_from_text, validation_message = _try_extract_valid_chapters_from_page_texts(page_texts)
    if parsed_from_text:
        return parsed_from_text
    if validation_message:
        warnings.append(validation_message)

    reader_page_texts = _extract_pdf_reader_page_texts(reader, max_pages=20)
    if reader_page_texts and reader_page_texts != page_texts:
        parsed_from_reader, validation_message = _try_extract_valid_chapters_from_page_texts(reader_page_texts)
        if parsed_from_reader:
            return parsed_from_reader
        if validation_message:
            warnings.append(validation_message)

    warnings.append("规则未识别到目录，已使用大模型兜底生成章节。")
    fallback = _fallback_generate_pdf_chapters_with_llm(course_name=course_name, page_texts=page_texts)
    normalized = normalize_generated_chapters(fallback)
    if not normalized:
        raise ValueError("PDF 目录提取失败，且大模型兜底未返回有效章节")
    return normalized


def generate_single_chapter_from_ppt(
    *,
    material_title: str,
    ppt_path: str,
    upload_root: str,
    derived_owner: Any,
    warnings: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    from backend.api.rag_ai import get_api_config

    warnings = warnings if warnings is not None else []
    file_hash = _calculate_file_hash(ppt_path)
    api_key, api_base, _ = get_api_config()
    parsed = parse_ppt(
        ppt_path,
        upload_root=upload_root,
        owner_id=derived_owner,
        file_hash=file_hash,
        api_key=api_key,
        api_base=api_base,
    )
    structure = parsed.get("structure") if isinstance(parsed.get("structure"), dict) else {}
    slides = structure.get("slides") if isinstance(structure.get("slides"), list) else []

    valid_slides: List[Dict[str, Any]] = []
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        title = _clean_title(slide.get("title"))
        text = _trim_text(slide.get("text"), 600)
        notes = _trim_text(slide.get("notes"), 400)
        combined = "\n".join([part for part in [title, text, notes] if part]).strip()
        if not combined:
            continue
        if _is_ignored_ppt_slide(title, combined):
            continue
        if len(re.sub(r"\s+", "", combined)) < 12:
            continue
        valid_slides.append({
            "title": title,
            "text": text,
            "notes": notes,
            "combined": combined,
        })

    if not valid_slides:
        warnings.append("未识别到明显的内容页，已退化为使用所有可提取文本页。")
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            title = _clean_title(slide.get("title"))
            text = _trim_text(slide.get("text"), 600)
            notes = _trim_text(slide.get("notes"), 400)
            combined = "\n".join([part for part in [title, text, notes] if part]).strip()
            if combined:
                valid_slides.append({
                    "title": title,
                    "text": text,
                    "notes": notes,
                    "combined": combined,
                })

    chapter_title = _clean_title(valid_slides[0].get("title") if valid_slides else "") or _material_title_without_extension(material_title)
    sections: List[Dict[str, Any]] = []

    for slide in valid_slides:
        section_title = _clean_title(slide.get("title"))
        content = _build_ppt_section_content(slide.get("text"), slide.get("notes"))

        if not section_title and sections:
            sections[-1]["content"] = _merge_content(sections[-1]["content"], content)
            continue

        if sections and section_title and _normalize_for_match(section_title) == _normalize_for_match(sections[-1]["title"]):
            sections[-1]["content"] = _merge_content(sections[-1]["content"], content)
            continue

        if not section_title:
            section_title = f"{chapter_title} - 内容要点 {len(sections) + 1}"

        sections.append({
            "title": section_title,
            "duration": 0,
            "content": content,
        })

    if not sections:
        raw_text = _trim_text(parsed.get("raw_text"), 280)
        if not raw_text:
            raise ValueError("PPT 未提取到可用内容")
        sections = [{
            "title": f"{chapter_title} - 核心内容",
            "duration": 0,
            "content": raw_text,
        }]

    total_duration = 45 if len(sections) <= 4 else 60
    section_duration = max(10, int(math.ceil((total_duration / max(len(sections), 1)) / 5.0) * 5))
    for section in sections:
        section["duration"] = section_duration

    chapter = {
        "title": chapter_title,
        "duration": sum(section["duration"] for section in sections),
        "sections": sections,
    }
    return normalize_generated_chapters([chapter])


def _extract_chapters_from_pdf_outline(reader: PdfReader) -> List[Dict[str, Any]]:
    outline = getattr(reader, "outline", None)
    if outline is None:
        outline = getattr(reader, "outlines", None)
    if not outline:
        return []

    flattened = _flatten_outline(outline)
    titles = [(level, _clean_title(title), item) for level, title, item in flattened if _clean_title(title)]
    if not titles:
        return []

    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None
    current_chapter_level: Optional[int] = None

    for level, title, item in titles:
        item_page = _get_outline_item_page(reader, item)

        if _looks_like_part_title(title):
            current_chapter = None
            current_chapter_level = None
            continue

        if _looks_like_main_chapter_title(title) or _looks_like_front_matter_title(title):
            current_chapter = {"title": title, "duration": 60, "sections": [], "start_page": item_page}
            chapters.append(current_chapter)
            current_chapter_level = level
            continue

        if current_chapter is None:
            current_chapter = {"title": title, "duration": 60, "sections": [], "start_page": item_page}
            chapters.append(current_chapter)
            current_chapter_level = level
            continue

        if current_chapter_level is not None and level > current_chapter_level:
            current_chapter["sections"].append({
                "title": title,
                "duration": 20,
                "content": "",
                "start_page": item_page,
            })
            if current_chapter.get("start_page") is None and item_page is not None:
                current_chapter["start_page"] = item_page
            continue

        current_chapter = {"title": title, "duration": 60, "sections": [], "start_page": item_page}
        chapters.append(current_chapter)
        current_chapter_level = level

    return chapters


def _flatten_outline(items: Any, level: int = 1) -> List[Tuple[int, str, Any]]:
    flattened: List[Tuple[int, str, Any]] = []
    if not isinstance(items, list):
        items = [items]

    index = 0
    while index < len(items):
        item = items[index]
        if isinstance(item, list):
            flattened.extend(_flatten_outline(item, level + 1))
            index += 1
            continue

        title = getattr(item, "title", None)
        if title:
            flattened.append((level, str(title), item))

        if index + 1 < len(items) and isinstance(items[index + 1], list):
            flattened.extend(_flatten_outline(items[index + 1], level + 1))
            index += 2
        else:
            index += 1

    return flattened


def _extract_pdf_page_texts(parsed_pdf: Dict[str, Any], max_pages: int = 20) -> List[str]:
    page_texts: List[str] = []
    structure = parsed_pdf.get("structure") if isinstance(parsed_pdf.get("structure"), dict) else {}
    pages = structure.get("pages") if isinstance(structure.get("pages"), list) else []
    for page in pages[:max_pages]:
        if not isinstance(page, dict):
            continue
        page_texts.append(str(page.get("text") or page.get("ocr_text") or ""))
    return page_texts


def _extract_pdf_reader_page_texts(reader: PdfReader, max_pages: int = 20) -> List[str]:
    page_texts: List[str] = []
    for page in list(getattr(reader, "pages", []))[:max_pages]:
        try:
            page_texts.append(str(page.extract_text() or ""))
        except Exception:
            page_texts.append("")
    return page_texts


def _try_extract_valid_chapters_from_page_texts(page_texts: List[str]) -> Tuple[List[Dict[str, Any]], str]:
    toc_span_pages = _find_toc_page_span(page_texts)
    if not toc_span_pages:
        return [], ""

    candidate_text = "\n\n".join(toc_span_pages)
    parsed = _extract_chapters_from_toc_text(candidate_text)
    if not parsed:
        return [], "规则目录识别未生成有效章节，已回退到大模型。"

    normalized_parsed = normalize_generated_chapters(parsed)
    is_valid, validation_message = _validate_toc_parse_result(normalized_parsed)
    if is_valid:
        return normalized_parsed, ""
    return [], validation_message


def _find_toc_page_span(page_texts: List[str], max_follow_pages: int = 3) -> List[str]:
    if not isinstance(page_texts, list):
        return []

    start_index: Optional[int] = None
    for index, text in enumerate(page_texts):
        if _looks_like_toc_start_page(text):
            start_index = index
            break
    if start_index is None:
        return []

    span = [page_texts[start_index]]
    for index in range(start_index + 1, min(len(page_texts), start_index + 1 + max_follow_pages)):
        if _looks_like_toc_continuation_page(page_texts[index]):
            span.append(page_texts[index])
            continue
        break
    return span


def _looks_like_toc_start_page(text: str) -> bool:
    metrics = _analyze_toc_page(text)
    return metrics["has_toc_word"] or (
        metrics["entry_count"] >= 4
        and metrics["page_number_count"] >= 3
        and metrics["long_line_ratio"] <= 0.34
    )


def _looks_like_toc_continuation_page(text: str) -> bool:
    metrics = _analyze_toc_page(text)
    return (
        metrics["entry_count"] >= 3
        and metrics["page_number_count"] >= 2
        and metrics["long_line_ratio"] <= 0.42
    )


def _analyze_toc_page(text: str) -> Dict[str, Any]:
    raw_text = str(text or "")
    compact = re.sub(r"\s+", " ", raw_text).strip().lower()
    lines = [line.strip() for line in raw_text.splitlines() if line and line.strip()]
    entries = _extract_toc_entries_from_text(raw_text)
    entry_count = len(entries)
    page_number_count = sum(1 for entry in entries if entry.get("page_number") is not None)
    long_line_count = 0

    for line in lines:
        if len(re.sub(r"\s+", "", line)) >= 28:
            long_line_count += 1

    total_lines = max(len(lines), 1)
    return {
        "has_toc_word": "目录" in compact or "contents" in compact or "content" in compact,
        "entry_count": entry_count,
        "page_number_count": page_number_count,
        "long_line_ratio": long_line_count / total_lines,
    }


def _looks_like_toc_page(text: str) -> bool:
    return _looks_like_toc_start_page(text)


def _extract_chapters_from_toc_text(text: str) -> List[Dict[str, Any]]:
    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None
    seen_titles = set()

    for entry in _extract_toc_entries_from_text(text):
        title = str(entry.get("title") or "").strip()
        page_number = _coerce_positive_int(entry.get("page_number"))
        line_type = str(entry.get("line_type") or "").strip()
        title_key = f"{line_type}:{title}:{page_number or ''}"
        if not title or title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        if line_type == "chapter":
            current_chapter = {
                "title": title,
                "duration": 60,
                "sections": [],
                "start_page": page_number,
            }
            chapters.append(current_chapter)
            continue

        if line_type in {"section", "special"} and current_chapter is not None:
            current_chapter["sections"].append({
                "title": title,
                "duration": 20,
                "content": "",
                "start_page": page_number,
            })
            if current_chapter.get("start_page") is None and page_number is not None:
                current_chapter["start_page"] = page_number
            continue

        if (
            line_type == "unknown"
            and current_chapter is not None
            and _is_conservative_section_candidate(title, page_number, current_chapter)
        ):
            current_chapter["sections"].append({
                "title": title,
                "duration": 20,
                "content": "",
                "start_page": page_number,
            })

    return chapters


def _extract_toc_entries_from_text(text: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    lines = [line.strip() for line in str(text or "").splitlines() if line and line.strip()]
    index = 0
    while index < len(lines):
        line = lines[index]
        entry = _extract_toc_entry(line)
        if entry:
            entries.append(entry)
            index += 1
            continue

        if index + 1 < len(lines) and _is_standalone_page_number(lines[index + 1]):
            merged_entry = _extract_toc_entry(f"{line} {lines[index + 1]}")
            if merged_entry:
                entries.append(merged_entry)
                index += 2
                continue

        index += 1
    return entries


def _is_standalone_page_number(line: Any) -> bool:
    return bool(re.fullmatch(r"\d{1,4}", str(line or "").strip()))


def _clean_toc_line(raw_line: Any) -> Tuple[str, Optional[int]]:
    line = str(raw_line or "").replace("\t", " ").strip()
    if not line:
        return "", None

    page_match = re.search(r"(?:[．。.·•…\.]{2,}|\s{2,}|\s)(\d{1,4})\s*$", line)
    page_number = int(page_match.group(1)) if page_match else None

    line = re.sub(r"[．。.·•…\.]{2,}\s*\d+\s*$", "", line)
    line = re.sub(r"\s{2,}\d+\s*$", "", line)
    line = re.sub(r"\s\d+\s*$", "", line)
    line = re.sub(r"^\d+\s*$", "", line)
    line = re.sub(r"\s+", " ", line).strip(" -:：.·•")

    if len(re.sub(r"\s+", "", line)) < 3:
        return "", page_number
    if re.fullmatch(r"[\dIVXivx]+", line):
        return "", page_number
    if _is_bad_heading_candidate(line):
        return "", page_number
    if page_number is None and not _looks_like_structured_heading(line):
        return "", page_number
    return line, page_number


def _extract_toc_entry(raw_line: Any) -> Optional[Dict[str, Any]]:
    line, page_number = _clean_toc_line(raw_line)
    if not line:
        return None

    if page_number is None:
        return None

    if _is_appendix_line(line):
        return {"title": line, "page_number": page_number, "line_type": "chapter"}
    if _is_chapter_line(line):
        return {"title": line, "page_number": page_number, "line_type": "chapter"}
    if _is_section_line(line):
        return {"title": line, "page_number": page_number, "line_type": "section"}
    if _is_special_section_line(line):
        return {"title": line, "page_number": page_number, "line_type": "special"}
    if _looks_like_main_chapter_title(line):
        return {"title": line, "page_number": page_number, "line_type": "chapter"}
    if len(re.sub(r"\s+", "", line)) <= 18:
        return {"title": line, "page_number": page_number, "line_type": "unknown"}
    return None


def _is_chapter_line(line: str) -> bool:
    lowered = line.lower()
    return bool(
        re.match(r"^第[一二三四五六七八九十百零\d]+章", line)
        or re.match(r"^chapter\s+\d+", lowered)
        or re.match(r"^\d+[、．.]\s*[^\d].+", line)
    )


def _is_section_line(line: str) -> bool:
    lowered = line.lower()
    return bool(
        re.match(r"^\d+\.\d+(\.\d+)?\s*[^\d].*", line)
        or re.match(r"^第[一二三四五六七八九十百零\d]+节", line)
        or re.match(r"^section\s+\d+(\.\d+)?", lowered)
    )


def _is_special_section_line(line: str) -> bool:
    text = str(line or "").strip()
    return bool(
        re.match(r"^整理与提升$", text)
        or re.match(r"^实验活动\s*\d+", text)
    )


def _is_appendix_line(line: str) -> bool:
    text = str(line or "").strip()
    return bool(
        re.match(r"^附录\s*[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ\d一二三四五六七八九十]+", text, re.IGNORECASE)
        or text == "元素周期表"
    )


def _looks_like_structured_heading(line: str) -> bool:
    return (
        _is_chapter_line(line)
        or _is_section_line(line)
        or _is_special_section_line(line)
        or _is_appendix_line(line)
        or _looks_like_main_chapter_title(line)
    )


def _is_bad_heading_candidate(line: str) -> bool:
    text = str(line or "").strip()
    lowered = text.lower()
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return True
    if text.startswith("●"):
        return True
    if _is_appendix_line(text):
        return False

    if any(symbol in text for symbol in ["=", "+", "%", "→", "←", "⇌", "×", "*"]):
        return True
    if any(punct in text for punct in ["，", "。", "；", "！", "？", ",", ";", "!", "?"]):
        return True
    if re.search(r"\b(?:mol|kj|kpa|km|cm|mm|kg|g|ml|l|hz|℃|°c)\b", lowered):
        return True
    if re.search(r"[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+", text):
        return True
    if any(keyword in text for keyword in ["如图", "如下", "发生", "生成", "放出", "所示"]):
        if not re.match(r"^第[一二三四五六七八九十百零\d]+章", text):
            return True
    if len(compact) > 36 and not _looks_like_structured_heading(text):
        return True
    return False


def _is_conservative_section_candidate(title: str, page_number: Optional[int], current_chapter: Dict[str, Any]) -> bool:
    if not title or page_number is None or not isinstance(current_chapter, dict):
        return False
    chapter_start_page = _coerce_positive_int(current_chapter.get("start_page"))
    if chapter_start_page is not None and page_number <= chapter_start_page:
        return False
    compact = re.sub(r"\s+", "", str(title or ""))
    if len(compact) > 18:
        return False
    return not _is_bad_heading_candidate(title)


def _looks_like_main_chapter_title(title: str) -> bool:
    text = str(title or "").strip()
    lowered = text.lower()
    return bool(
        re.match(r"^第[一二三四五六七八九十百零\d]+章", text)
        or re.match(r"^chapter\s+\d+", lowered)
        or re.match(r"^\d+[、．.]\s*[^\d].+", text)
        or _is_appendix_line(text)
    )


def _looks_like_front_matter_title(title: str) -> bool:
    text = str(title or "").strip()
    lowered = text.lower()
    if any(keyword in text for keyword in FRONT_MATTER_TITLE_KEYWORDS):
        return True
    return bool(
        lowered in {"preface", "foreword", "contents", "table of contents", "copyright", "acknowledgements", "acknowledgments"}
    )


def _looks_like_part_title(title: str) -> bool:
    text = str(title or "").strip()
    lowered = text.lower()
    return bool(
        re.match(r"^第[一二三四五六七八九十百零\d]+部分", text)
        or re.match(r"^part\s+[ivx\d]+", lowered)
    )


def _validate_toc_parse_result(chapters: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if not isinstance(chapters, list) or not chapters:
        return False, "规则目录识别未生成有效章节，已回退到大模型。"

    chapter_count = 0
    section_count = 0
    invalid_title_count = 0
    ordered_pages: List[int] = []

    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        title = str(chapter.get("title") or "").strip()
        if title:
            chapter_count += 1
            if _is_bad_heading_candidate(title) or len(re.sub(r"\s+", "", title)) < 2:
                invalid_title_count += 1
        start_page = _coerce_positive_int(chapter.get("start_page"))
        if start_page is not None:
            ordered_pages.append(start_page)

        sections = chapter.get("sections") if isinstance(chapter.get("sections"), list) else []
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_count += 1
            section_title = str(section.get("title") or "").strip()
            if not section_title or _is_bad_heading_candidate(section_title):
                invalid_title_count += 1
            section_page = _coerce_positive_int(section.get("start_page"))
            if section_page is not None:
                ordered_pages.append(section_page)

    if not (chapter_count >= 2 or (chapter_count >= 1 and section_count >= 2)):
        return False, "规则目录识别结果质量不足（章节/小节数量过少），已回退到大模型。"

    if ordered_pages:
        regressions = sum(
            1 for previous, current in zip(ordered_pages, ordered_pages[1:])
            if current < previous
        )
        if regressions >= 2:
            return False, "规则目录识别结果页码顺序异常，已回退到大模型。"

    if invalid_title_count >= max(2, math.ceil((chapter_count + section_count) * 0.35)):
        return False, "规则目录识别结果包含过多异常标题，已回退到大模型。"

    return True, ""


def _fallback_generate_pdf_chapters_with_llm(course_name: str, page_texts: List[str]) -> List[Dict[str, Any]]:
    from backend.api.rag_ai import get_api_config

    api_key, api_base, model_name = get_api_config()
    if not api_key or not api_base or not model_name:
        raise ValueError("未配置可用的大模型接口，无法进行 PDF 目录兜底生成")

    prompt = {
        "course_name": course_name,
        "pdf_excerpt": "\n\n".join(page_texts[:20]),
    }
    system_prompt = (
        "You extract textbook chapters from PDF text. "
        "Return valid JSON only. "
        "The JSON must be an array of chapter objects. "
        "Each chapter object must have keys: title, sections. "
        "sections must be an array of objects with keys: title, content. "
        "Use the PDF content only. Do not invent unrelated chapters."
    )
    user_prompt = (
        "请根据以下 PDF 前 20 页文本，提取教材目录并输出 JSON 数组。"
        "如果无法确认，不要瞎编太多，尽量保守提取。\n"
        f"{json.dumps(prompt, ensure_ascii=False)}"
    )

    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
            "stream": False,
        },
        timeout=90,
    )
    if response.status_code != 200:
        raise ValueError(f"PDF 兜底生成失败: {response.status_code}")

    response_json = response.json()
    raw_content = ""
    choices = response_json.get("choices") if isinstance(response_json, dict) else []
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        raw_content = str(message.get("content") or "").strip()

    parsed = _extract_json_value(raw_content)
    if isinstance(parsed, dict) and isinstance(parsed.get("chapters"), list):
        parsed = parsed.get("chapters")
    if not isinstance(parsed, list):
        raise ValueError("PDF 兜底生成未返回有效章节数组")
    return parsed


def _extract_json_value(text: str) -> Any:
    decoder = JSONDecoder()
    for start in range(len(text)):
        if text[start] not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
            return value
        except Exception:
            continue
    return None


def _build_ppt_section_content(text: Any, notes: Any) -> str:
    parts = [str(text or "").strip(), str(notes or "").strip()]
    merged = "\n".join([part for part in parts if part]).strip()
    return _trim_text(merged, 280)


def _merge_content(left: str, right: str) -> str:
    merged = "\n".join([part for part in [left.strip(), right.strip()] if part]).strip()
    return _trim_text(merged, 280)


def _is_ignored_ppt_slide(title: str, combined_text: str) -> bool:
    title_lower = str(title or "").strip().lower()
    combined_lower = str(combined_text or "").strip().lower()
    return any(keyword in title_lower or keyword in combined_lower[:80] for keyword in PPT_IGNORE_KEYWORDS)


def _material_title_without_extension(material_title: str) -> str:
    base = os.path.splitext(str(material_title or "").strip())[0].strip()
    return base or "新章节"


def _clean_title(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -:：")


def _trim_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _coerce_duration(value: Any, fallback: int) -> int:
    try:
        duration = int(value)
        if duration > 0:
            return duration
    except Exception:
        pass
    return fallback


def _normalize_for_match(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").lower())


def _calculate_file_hash(file_path: str) -> str:
    import hashlib

    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def _coerce_positive_int(value: Any) -> Optional[int]:
    try:
        number = int(value)
        if number > 0:
            return number
    except Exception:
        return None
    return None


def _get_outline_item_page(reader: PdfReader, item: Any) -> Optional[int]:
    try:
        return int(reader.get_destination_page_number(item)) + 1
    except Exception:
        return None


def _get_chapters_file_path(upload_root: str, course_id: int) -> str:
    return os.path.join(_ensure_course_chapter_folder(upload_root, course_id), CHAPTER_FILENAME)


def _ensure_course_chapter_folder(upload_root: str, course_id: int) -> str:
    folder = os.path.join(upload_root, CHAPTER_DIRNAME, str(course_id))
    os.makedirs(folder, exist_ok=True)
    return folder
