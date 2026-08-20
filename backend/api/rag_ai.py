from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import time
import requests
import json
import sys
import logging
import shutil
import tempfile
import subprocess
import uuid
import re
import glob
from dotenv import load_dotenv
from backend.config.model_routing import get_chat_base_url, get_model_primary
from backend.models.learning import ChatHistory, KnowledgeBaseQueue
from backend.extensions import db
from backend.models.course import Course
from backend.models.material import Material
from backend.models.user import User
from backend.rag.lesson_plan_support import (
    build_game_plan_seed_from_core_spec,
    build_query_terms,
    build_source_evidence_bundle,
    core_spec_to_requirement_summary,
    load_prompt_bundle,
    normalize_core_teaching_spec,
    render_prompt_template,
)
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from werkzeug.utils import secure_filename


# 绂佺敤 ChromaDB telemetry 浠ラ槻姝㈠穿婧?
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "False"

# 设置日志记录
logger = logging.getLogger(__name__)

# 定义全局变量
RAG_AVAILABLE = False
hybrid_retriever = None
format_docs = None
DERIVED_CHAPTER_CACHE: Dict[str, List[Dict[str, Any]]] = {}
ALLOWED_PURPOSES = {"general", "lesson_plan"}
ALLOWED_SOURCE_MAPPING_USAGES = {"content", "format", "case", "image_asset"}
GLOBAL_KNOWLEDGE_BASE_NAMESPACE = "global"
DOCX_SECTION_RULES = [
    {
        "title": "教学目标",
        "keywords": ["教学目标", "学习目标", "目标"],
        "goal": "明确本课的知识、能力与素养目标",
    },
    {
        "title": "学情分析",
        "keywords": ["学情", "学生", "基础"],
        "goal": "分析学生基础、认知特点与学习偏好",
    },
    {
        "title": "教学重点难点",
        "keywords": ["重点难点", "重点", "难点"],
        "goal": "聚焦本课重点与难点，明确突破策略",
    },
    {
        "title": "教学流程",
        "keywords": ["流程", "过程", "环节", "步骤", "安排"],
        "goal": "组织课堂教学环节与时间推进",
    },
    {
        "title": "课堂活动",
        "keywords": ["活动", "互动", "讨论", "实验", "任务", "游戏"],
        "goal": "设计可执行的互动任务与实践活动",
    },
    {
        "title": "作业布置",
        "keywords": ["作业", "课后", "练习"],
        "goal": "安排课后巩固、迁移与拓展任务",
    },
    {
        "title": "板书建议",
        "keywords": ["板书", "黑板", "板演"],
        "goal": "沉淀课堂核心结构与板书呈现方式",
    },
    {
        "title": "教学反思",
        "keywords": ["反思", "复盘", "改进", "总结"],
        "goal": "复盘教学效果并为后续优化提供依据",
    },
]

def normalize_purpose(purpose: Optional[str], default: str = "general") -> Optional[str]:
    """Normalize and validate knowledge-base purpose."""
    if purpose is None:
        return default
    p = str(purpose).strip().lower()
    if not p:
        return default
    if p not in ALLOWED_PURPOSES:
        return None
    return p

def normalize_relative_upload_path(path_value: Any) -> Optional[str]:
    """Normalize a client-provided relative upload path."""
    if not isinstance(path_value, str):
        return None
    candidate = path_value.strip().replace("\\", "/")
    if not candidate:
        return None
    candidate = candidate.lstrip("/")
    normalized = os.path.normpath(candidate).replace("\\", "/")
    if not normalized or normalized == ".":
        return None
    if normalized == ".." or normalized.startswith("../") or "/../" in f"/{normalized}/":
        return None
    return normalized

def normalize_knowledge_file_path(path_value: Any) -> Optional[str]:
    """Normalize knowledge-base file paths to be relative to UPLOAD_FOLDER."""
    normalized = normalize_relative_upload_path(path_value)
    if not normalized:
        return None
    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/"):]
    return normalized or None


def resolve_upload_path(path_value: Any) -> Optional[str]:
    normalized = normalize_knowledge_file_path(path_value)
    if not normalized:
        return None
    upload_root = str(current_app.config.get("UPLOAD_FOLDER") or "").strip()
    if not upload_root:
        return None
    absolute_path = os.path.join(upload_root, normalized.replace("/", os.sep))
    if os.path.exists(absolute_path):
        return absolute_path
    return None


def get_authenticated_user() -> Optional[User]:
    try:
        user_id = get_jwt_identity()
        if user_id in (None, "", "null"):
            return None
        return User.query.get(int(user_id))
    except Exception:
        return None


def ensure_course_teacher_access(course: Optional[Course], current_user: Optional[User]):
    if not course:
        return jsonify({'status': 'error', 'message': '课程不存在'}), 404
    if not current_user:
        return jsonify({'status': 'error', 'message': '未登录，无法访问课程资源'}), 401
    if current_user.role == 'admin':
        return None
    if current_user.role != 'teacher' or course.teacher_id != current_user.id:
        return jsonify({'status': 'error', 'message': '无权访问该课程资源'}), 403
    return None


def ensure_course_knowledge_access(course: Optional[Course], current_user: Optional[User]):
    if not course:
        return jsonify({'status': 'error', 'message': '课程不存在'}), 404
    if not current_user:
        return jsonify({'status': 'error', 'message': '未登录，无法访问课程资源'}), 401
    if current_user.role == 'admin':
        return None
    if current_user.role == 'teacher':
        if course.teacher_id != current_user.id:
            return jsonify({'status': 'error', 'message': '无权访问该课程资源'}), 403
        return None
    if current_user.role == 'student':
        if any(student.id == current_user.id for student in (course.students or [])):
            return None
        return jsonify({'status': 'error', 'message': '仅已加入该课程的学生可访问知识库'}), 403
    return jsonify({'status': 'error', 'message': '无权访问该课程资源'}), 403


def ensure_queue_item_teacher_access(queue_item: Optional[KnowledgeBaseQueue], current_user: Optional[User]):
    if not queue_item:
        return jsonify({'status': 'error', 'message': '队列项不存在'}), 404
    course = Course.query.get(queue_item.course_id) if queue_item.course_id else None
    return ensure_course_teacher_access(course, current_user)


KNOWLEDGE_FILE_SCOPE_PATTERNS = (
    "知识库",
    "文件",
    "资料",
    "文档",
)

KNOWLEDGE_FILE_LIST_INTENT_PATTERNS = (
    "哪些",
    "有哪些",
    "哪几个",
    "有什么",
    "都有什么",
    "列出",
    "列表",
    "清单",
    "全部",
    "所有",
    "查看文件",
    "看看文件",
)

KNOWLEDGE_FILE_EXPLANATION_PATTERNS = (
    "讲",
    "讲解",
    "解释",
    "分析",
    "介绍",
    "说明",
    "总结",
    "概括",
    "内容",
    "原理",
    "知识点",
    "学习",
    "对应",
    "根据",
    "基于",
    "围绕",
)

CHAPTER_QUERY_PATTERNS = (
    "章节",
    "几章",
    "多少章",
    "目录",
    "章目",
)

CHAPTER_COUNT_PATTERNS = (
    "几个章节",
    "多少章节",
    "有几个章节",
    "有多少章节",
    "有几章",
    "多少章",
    "几章",
)

CHAPTER_LIST_PATTERNS = (
    "章节有哪些",
    "有哪些章节",
    "目录是什么",
    "目录有哪些",
    "列出章节",
    "章节列表",
    "章节清单",
)


def is_knowledge_file_list_request(message: Any) -> bool:
    if not isinstance(message, str):
        return False
    normalized = re.sub(r"\s+", "", message).lower()
    if not normalized:
        return False
    if not any(pattern in normalized for pattern in KNOWLEDGE_FILE_SCOPE_PATTERNS):
        return False
    if not any(pattern in normalized for pattern in KNOWLEDGE_FILE_LIST_INTENT_PATTERNS):
        return False
    if any(pattern in normalized for pattern in KNOWLEDGE_FILE_EXPLANATION_PATTERNS):
        return False
    return True


def get_chapter_query_type(message: Any) -> Optional[str]:
    if not isinstance(message, str):
        return None
    normalized = re.sub(r"\s+", "", message).lower()
    if not normalized:
        return None
    if not any(pattern in normalized for pattern in CHAPTER_QUERY_PATTERNS):
        return None
    if any(pattern in normalized for pattern in CHAPTER_COUNT_PATTERNS):
        return "count"
    if any(pattern in normalized for pattern in CHAPTER_LIST_PATTERNS):
        return "list"
    if "章节" in normalized or "目录" in normalized:
        return "list"
    return None


def _build_kb_file_item_label(queue_item: KnowledgeBaseQueue) -> str:
    normalized_path = normalize_knowledge_file_path(queue_item.file_path) or str(queue_item.file_path or "").strip()
    filename = os.path.basename(normalized_path) if normalized_path else f"文件 {queue_item.id}"
    status_map = {
        "completed": "已入库",
        "processing": "处理中",
        "pending": "排队中",
        "failed": "失败",
    }
    purpose_map = {
        "general": "通用",
        "lesson_plan": "备课",
    }
    status_text = status_map.get(queue_item.status, queue_item.status or "未知")
    purpose_text = purpose_map.get(queue_item.purpose, queue_item.purpose or "未标记")
    return f"- {filename} [{status_text}，用途：{purpose_text}]"


def build_knowledge_file_listing_reply(course_id: Any, course_name: str = "") -> str:
    cleanup_stale_material_and_queue_records(course_id=course_id)
    queue_items = (
        KnowledgeBaseQueue.query
        .filter_by(course_id=course_id)
        .order_by(KnowledgeBaseQueue.created_at.desc(), KnowledgeBaseQueue.id.desc())
        .all()
    )
    course_label = course_name or f"课程 {course_id}"
    if not queue_items:
        return f"当前课程“{course_label}”的知识库里还没有已登记的文件。"

    completed_items = [item for item in queue_items if item.status == "completed"]
    processing_items = [item for item in queue_items if item.status in {"pending", "processing"}]
    failed_items = [item for item in queue_items if item.status == "failed"]

    lines = [f"当前课程“{course_label}”的知识库文件如下："]
    if completed_items:
        lines.append("")
        lines.append("已入库文件：")
        lines.extend(_build_kb_file_item_label(item) for item in completed_items[:20])
        if len(completed_items) > 20:
            lines.append(f"- 其余 {len(completed_items) - 20} 个文件未展开")

    if processing_items:
        lines.append("")
        lines.append("处理中或排队中的文件：")
        lines.extend(_build_kb_file_item_label(item) for item in processing_items[:10])
        if len(processing_items) > 10:
            lines.append(f"- 其余 {len(processing_items) - 10} 个文件未展开")

    if failed_items:
        lines.append("")
        lines.append("入库失败的文件：")
        lines.extend(_build_kb_file_item_label(item) for item in failed_items[:10])
        if len(failed_items) > 10:
            lines.append(f"- 其余 {len(failed_items) - 10} 个文件未展开")

    return "\n".join(lines)


def _get_knowledge_queue_items(course_id: Any) -> List[KnowledgeBaseQueue]:
    cleanup_stale_material_and_queue_records(course_id=course_id)
    return (
        KnowledgeBaseQueue.query
        .filter_by(course_id=course_id)
        .order_by(KnowledgeBaseQueue.created_at.desc(), KnowledgeBaseQueue.id.desc())
        .all()
    )


def _get_course_kb_roots(course_id: Any) -> List[str]:
    try:
        normalized_course_id = str(int(course_id))
    except (TypeError, ValueError):
        return []

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_roots = [
        os.path.join(project_root, "uploads", "knowledge_base", normalized_course_id),
        os.path.join(project_root, "backend", "uploads", "knowledge_base", normalized_course_id),
    ]
    return [path for path in candidate_roots if os.path.isdir(path)]


def _load_course_structured_indexes(course_id: Any) -> List[Dict[str, Any]]:
    indexes: List[Dict[str, Any]] = []
    seen_hashes = set()
    for kb_root in _get_course_kb_roots(course_id):
        structured_dir = os.path.join(kb_root, "structured")
        if not os.path.isdir(structured_dir):
            continue
        for filename in sorted(os.listdir(structured_dir)):
            if not filename.lower().endswith(".json"):
                continue
            file_path = os.path.join(structured_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file_obj:
                    payload = json.load(file_obj)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            file_hash = str(payload.get("file_hash") or filename)
            if file_hash in seen_hashes:
                continue
            seen_hashes.add(file_hash)
            indexes.append(payload)
    return indexes


def _get_or_create_primary_kb_root(course_id: Any) -> str:
    existing_roots = _get_course_kb_roots(course_id)
    if existing_roots:
        return existing_roots[0]
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    target_root = os.path.join(project_root, "uploads", "knowledge_base", str(int(course_id)))
    os.makedirs(target_root, exist_ok=True)
    return target_root


def _normalize_structured_keyword(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^第[一二三四五六七八九十百0-9]+章\s*", "", text)
    text = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", text)
    return text[:16]


def _extract_structured_keywords(summary_text: str, chapters: List[Dict[str, Any]], file_name: str) -> List[str]:
    candidates: List[str] = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        title = _normalize_structured_keyword(chapter.get("title"))
        if title:
            candidates.append(title)
    for token in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,10}", summary_text):
        normalized = _normalize_structured_keyword(token)
        if normalized:
            candidates.append(normalized)
    file_token = _normalize_structured_keyword(os.path.splitext(file_name)[0])
    if file_token:
        candidates.append(file_token)

    blocked = {"人民教育出版社", "zlibrarysk", "1libsk", "zlibsk", "librarysk"}
    keywords: List[str] = []
    for item in candidates:
        lowered = item.lower()
        if lowered in blocked:
            continue
        if len(item) < 2:
            continue
        if item not in keywords:
            keywords.append(item)
        if len(keywords) >= 12:
            break
    return keywords


def _derive_structured_index_from_queue_item(queue_item: KnowledgeBaseQueue, course_name: str = "") -> Optional[Dict[str, Any]]:
    normalized_path = normalize_knowledge_file_path(queue_item.file_path)
    if not normalized_path:
        return None

    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], normalized_path)
    if not os.path.exists(full_path):
        return None

    file_ext = os.path.splitext(normalized_path)[1].lower()
    if file_ext != ".pdf":
        return None

    from backend.rag.parsers import calculate_file_hash as calculate_parser_file_hash, clip_text, load_cached_parse_result
    from backend.rag.parsers.pdf_parser import parse_pdf
    from backend.rag.chapter_generation_from_material import preview_generate_chapters_from_material

    upload_root = current_app.config["UPLOAD_FOLDER"]
    parser_hash = calculate_parser_file_hash(full_path)
    parsed_result = load_cached_parse_result(upload_root, parser_hash, "create_db")
    if not parsed_result:
        parsed_result = parse_pdf(full_path, upload_root=upload_root, owner_id="kb", parse_mode="create_db")
    if not isinstance(parsed_result, dict):
        return None

    try:
        chapter_preview = preview_generate_chapters_from_material(
            course_name=course_name or f"课程 {queue_item.course_id}",
            course_id=int(queue_item.course_id),
            source_type="pdf",
            material_title=os.path.basename(normalized_path),
            material_path=full_path,
            upload_root=upload_root,
            existing_chapters=[],
        )
        chapters = chapter_preview.get("generated_chapters") if isinstance(chapter_preview, dict) else []
    except Exception as exc:
        current_app.logger.warning("derive structured chapters failed: course_id=%s file=%s error=%s", queue_item.course_id, normalized_path, exc)
        chapters = []

    if not isinstance(chapters, list):
        chapters = []

    summary_text = clip_text(str(parsed_result.get("summary") or parsed_result.get("raw_text") or "").strip(), 600)
    outline = [str(chapter.get("title") or "").strip() for chapter in chapters if isinstance(chapter, dict) and str(chapter.get("title") or "").strip()]
    keywords = _extract_structured_keywords(summary_text, chapters, os.path.basename(normalized_path))
    assets = parsed_result.get("assets") if isinstance(parsed_result.get("assets"), dict) else {}
    page_count = 0
    try:
        page_count = int((assets or {}).get("page_count") or 0)
    except (TypeError, ValueError):
        page_count = 0

    payload = {
        "file_name": os.path.basename(normalized_path),
        "file_path": normalized_path,
        "file_hash": parser_hash,
        "course_id": queue_item.course_id,
        "file_type": "pdf",
        "purpose": queue_item.purpose or "general",
        "summary": summary_text,
        "keywords": keywords,
        "outline": outline,
        "chapters": chapters,
        "page_count": page_count,
        "updated_at": int(time.time()),
    }

    structured_dir = os.path.join(_get_or_create_primary_kb_root(queue_item.course_id), "structured")
    os.makedirs(structured_dir, exist_ok=True)
    output_path = os.path.join(structured_dir, f"{parser_hash}.json")
    with open(output_path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)
    return payload


def _ensure_course_structured_indexes(course_id: Any, course_name: str = "") -> List[Dict[str, Any]]:
    indexes = _load_course_structured_indexes(course_id)
    if indexes:
        return indexes

    queue_items = _get_knowledge_queue_items(course_id)
    completed_items = [item for item in queue_items if item.status == "completed"]
    for item in completed_items[:3]:
        try:
            _derive_structured_index_from_queue_item(item, course_name=course_name)
        except Exception as exc:
            current_app.logger.warning("lazy structured index build failed: course_id=%s queue_id=%s error=%s", course_id, item.id, exc)
            continue
    return _load_course_structured_indexes(course_id)


def _normalize_query_terms(message: str) -> List[str]:
    normalized = re.sub(r"\s+", "", str(message or "").lower())
    terms = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,16}", normalized)
    unique_terms: List[str] = []
    for term in [normalized, *terms]:
        clean_term = str(term or "").strip()
        if clean_term and clean_term not in unique_terms:
            unique_terms.append(clean_term)
    return unique_terms


def _score_structured_index_match(query_terms: List[str], index_item: Dict[str, Any]) -> int:
    haystacks: List[str] = []
    for key in ("file_name", "summary"):
        value = str(index_item.get(key) or "").strip()
        if value:
            haystacks.append(value.lower())
    for key in ("keywords", "outline"):
        raw_list = index_item.get(key)
        if isinstance(raw_list, list):
            haystacks.extend(str(item or "").strip().lower() for item in raw_list if str(item or "").strip())
    chapters = index_item.get("chapters")
    if isinstance(chapters, list):
        haystacks.extend(str(item.get("title") or "").strip().lower() for item in chapters if isinstance(item, dict))

    score = 0
    for term in query_terms:
        for haystack in haystacks:
            if not haystack:
                continue
            if term == haystack:
                score += 8
            elif term in haystack or haystack in term:
                score += 4
    return score


def build_structured_index_context(course_id: Any, message: Any, course_name: str = "") -> Tuple[str, List[Dict[str, Any]], str]:
    if not isinstance(message, str):
        return "", [], ""

    indexes = _ensure_course_structured_indexes(course_id, course_name=course_name)
    if not indexes:
        return "", [], ""

    query_terms = _normalize_query_terms(message)
    ranked_indexes = sorted(
        indexes,
        key=lambda item: _score_structured_index_match(query_terms, item),
        reverse=True,
    )
    selected_indexes = [item for item in ranked_indexes if _score_structured_index_match(query_terms, item) > 0][:3]
    if not selected_indexes:
        selected_indexes = ranked_indexes[:2]

    context_lines = [
        f"当前课程：{course_name or f'课程 {course_id}'}",
        "以下是课程知识库中的教材结构化索引摘要，不是逐字原文，但可用于先定位主题、目录和核心概念：",
    ]
    sources: List[Dict[str, Any]] = []

    for item in selected_indexes:
        file_name = str(item.get("file_name") or "未命名文件").strip()
        summary = str(item.get("summary") or "").strip()
        keywords = item.get("keywords") if isinstance(item.get("keywords"), list) else []
        outline = item.get("outline") if isinstance(item.get("outline"), list) else []
        chapters = item.get("chapters") if isinstance(item.get("chapters"), list) else []

        context_lines.append("")
        context_lines.append(f"文件：{file_name}")
        if summary:
            context_lines.append(f"摘要：{summary}")
        if keywords:
            context_lines.append(f"关键词：{'、'.join(str(keyword) for keyword in keywords[:10])}")
        if outline:
            context_lines.append(f"目录：{'；'.join(str(title) for title in outline[:8])}")
        elif chapters:
            chapter_titles = [str(chapter.get('title') or '').strip() for chapter in chapters if isinstance(chapter, dict)]
            chapter_titles = [title for title in chapter_titles if title]
            if chapter_titles:
                context_lines.append(f"章节：{'；'.join(chapter_titles[:8])}")

        sources.append({
            "title": f"{file_name}（结构化索引）",
            "url": str(item.get("file_path") or file_name),
        })

    return "\n".join(context_lines).strip(), sources, "structured_index"


def build_natural_fallback_instruction(course_id: Any, course_name: str = "", reason: str = "no_relevant_docs") -> str:
    course_label = course_name or f"课程 {course_id}"
    queue_items = _get_knowledge_queue_items(course_id)
    completed_items = [item for item in queue_items if item.status == "completed"]
    processing_items = [item for item in queue_items if item.status in {"pending", "processing"}]

    instruction_lines = [
        f"当前用户选择的是课程“{course_label}”的知识库增强模式。",
        "如果知识库没有直接命中原文，请不要对用户说“检索失败”“执行失败”“无法回退”等内部措辞。",
        "优先保持服务连续性：能基于课程通用知识回答，就先自然回答；回答后可顺带建议用户补充章节名、教材术语或目录位置。",
    ]
    if completed_items:
        instruction_lines.append("当前课程已有已入库教材，可在回答中自然提示你还能继续按教材目录、章节标题或关键词帮用户定位。")
    elif processing_items:
        instruction_lines.append("当前课程知识库仍在处理中；如果问题能用通用知识解释，可以先解释，再轻描淡写提示教材处理完成后还能继续精确定位。")
    else:
        instruction_lines.append("当前课程暂无可直接引用的知识库内容；如果问题属于课程基础知识，可先按通用教学知识回答。")
    if reason == "retrieval_error":
        instruction_lines.append("当前只是内部检索链路未顺利命中，不要把内部异常细节暴露给用户。")
    return "\n".join(instruction_lines)


def _filter_main_chapters(chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(chapters, list):
        return []
    main_chapters = [chapter for chapter in chapters if isinstance(chapter, dict) and not chapter.get("is_front_matter")]
    return main_chapters or [chapter for chapter in chapters if isinstance(chapter, dict)]


def _resolve_course_chapters(course_id: Any, course_name: str = "") -> Tuple[List[Dict[str, Any]], str]:
    try:
        normalized_course_id = int(course_id)
    except (TypeError, ValueError):
        return [], ""

    from backend.rag.chapter_generation_from_material import load_course_chapters, preview_generate_chapters_from_material

    upload_root = current_app.config["UPLOAD_FOLDER"]
    stored_chapters = _filter_main_chapters(load_course_chapters(upload_root, normalized_course_id))
    if stored_chapters:
        return stored_chapters, "课程章节数据"

    for index_item in _ensure_course_structured_indexes(normalized_course_id, course_name=course_name):
        structured_chapters = _filter_main_chapters(index_item.get("chapters") if isinstance(index_item.get("chapters"), list) else [])
        if structured_chapters:
            return structured_chapters, str(index_item.get("file_name") or "结构化索引")

    queue_items = _get_knowledge_queue_items(normalized_course_id)
    completed_items = [item for item in queue_items if item.status == "completed"]
    supported_suffixes = {".pdf", ".ppt", ".pptx"}

    for item in completed_items:
        normalized_path = normalize_knowledge_file_path(item.file_path)
        if not normalized_path:
            continue
        file_ext = os.path.splitext(normalized_path)[1].lower()
        if file_ext not in supported_suffixes:
            continue

        full_path = os.path.join(upload_root, normalized_path)
        if not os.path.exists(full_path):
            continue

        cache_key = f"{normalized_course_id}:{normalized_path}:{int(os.path.getmtime(full_path))}"
        cached = DERIVED_CHAPTER_CACHE.get(cache_key)
        if cached:
            return list(cached), os.path.basename(normalized_path)

        try:
            preview_result = preview_generate_chapters_from_material(
                course_name=course_name or f"课程 {normalized_course_id}",
                course_id=normalized_course_id,
                source_type="pdf" if file_ext == ".pdf" else "ppt",
                material_title=os.path.basename(normalized_path),
                material_path=full_path,
                upload_root=upload_root,
                existing_chapters=[],
            )
            derived_chapters = _filter_main_chapters(preview_result.get("generated_chapters") or [])
            if derived_chapters:
                DERIVED_CHAPTER_CACHE[cache_key] = list(derived_chapters)
                return derived_chapters, os.path.basename(normalized_path)
        except Exception as exc:
            current_app.logger.warning(
                "derive chapter outline failed: course_id=%s file=%s error=%s",
                normalized_course_id,
                normalized_path,
                exc,
            )
            continue

    return [], ""


def build_chapter_query_reply(course_id: Any, course_name: str, message: Any) -> str:
    query_type = get_chapter_query_type(message)
    if not query_type:
        return ""

    chapters, source_label = _resolve_course_chapters(course_id, course_name=course_name)
    course_label = course_name or f"课程 {course_id}"

    if not chapters:
        lines = [
            f"当前课程“{course_label}”暂时没有可直接回答章节数量的结构化目录数据。",
            "我已经识别到你是在问章节问题，但目前未读取到课程章节文件，也没能从已入库教材中成功提取目录。",
        ]
        queue_items = _get_knowledge_queue_items(course_id)
        if queue_items:
            lines.append("")
            lines.append(build_knowledge_file_listing_reply(course_id=course_id, course_name=course_name))
        return "\n".join(lines)

    chapter_titles = [str(chapter.get("title") or "").strip() for chapter in chapters if str(chapter.get("title") or "").strip()]
    count = len(chapter_titles)
    preview_titles = chapter_titles[:12]

    source_note = f"（依据：{source_label}）" if source_label else ""
    if query_type == "count":
        lines = [f"当前课程“{course_label}”对应教材共识别到 {count} 个章节{source_note}。"]
    else:
        lines = [f"当前课程“{course_label}”识别到的章节如下{source_note}："]

    for index, title in enumerate(preview_titles, start=1):
        lines.append(f"{index}. {title}")

    if count > len(preview_titles):
        lines.append(f"其余 {count - len(preview_titles)} 个章节未展开。")

    return "\n".join(lines)


def build_strict_rag_reply(course_id: Any, course_name: str = "", reason: str = "no_relevant_docs") -> str:
    course_label = course_name or f"课程 {course_id}"
    queue_items = _get_knowledge_queue_items(course_id)
    completed_items = [item for item in queue_items if item.status == "completed"]
    processing_items = [item for item in queue_items if item.status in {"pending", "processing"}]
    failed_items = [item for item in queue_items if item.status == "failed"]

    if reason == "rag_unavailable":
        lead = f"我先继续帮你处理这个问题。当前课程“{course_label}”的教材检索链路暂时没有直接给出可引用片段。"
    elif reason == "retrieval_error":
        lead = f"我先继续帮你处理这个问题。当前课程“{course_label}”的教材检索没有直接命中到可用片段。"
    else:
        lead = f"我暂时没有在课程“{course_label}”的教材原文里直接定位到与你问题高度相关的段落。"

    lines = [lead]

    if completed_items:
        lines.append("我可以继续按教材目录、章节标题、文件名或关键术语帮你缩小范围；如果你愿意，也可以先让我按这门课的通用知识直接解释。")
    elif processing_items:
        lines.append("当前课程知识库还在处理中；如果你现在就想继续，我可以先按该课程的通用知识解释，再等教材处理完成后帮你精确定位。")
    elif failed_items:
        lines.append("当前课程有部分教材处理未完成；如果你继续追问，我可以先给出通用解释，并提示你后续怎样更快定位到教材原文。")
    else:
        lines.append("当前课程还没有可直接引用的知识库文件；如果这个问题属于课程基础概念，我也可以先直接解释。")

    if queue_items:
        lines.append("")
        lines.append(build_knowledge_file_listing_reply(course_id=course_id, course_name=course_name))

    return "\n".join(lines)


def build_direct_assistant_response(
    *,
    assistant_reply: str,
    user_id: Any,
    course_id: Any,
    conversation_id: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
):
    response_sources = sources or []
    if stream:
        def generate_direct_reply():
            yield f"data: {json.dumps({'content': assistant_reply})}\n\n"
            _save_assistant_chat_message(user_id, course_id, conversation_id, assistant_reply)
            yield f"data: {json.dumps({'status': 'done', 'conversation_id': conversation_id, 'sources': response_sources})}\n\n"

        return Response(stream_with_context(generate_direct_reply()), content_type='text/event-stream')

    _save_assistant_chat_message(user_id, course_id, conversation_id, assistant_reply)
    return jsonify({
        'status': 'success',
        'response': assistant_reply,
        'conversation_id': conversation_id,
        'sources': response_sources
    })


def _save_assistant_chat_message(user_id: Any, course_id: Any, conversation_id: str, message: str) -> None:
    ai_chat = ChatHistory(
        user_id=user_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role='assistant',
        message=message,
        timestamp=int(time.time())
    )
    db.session.add(ai_chat)
    db.session.commit()

def parse_selected_knowledge_items(raw_items: Any) -> List[Dict[str, Any]]:
    """Normalize selected knowledge item payload from the frontend."""
    if not isinstance(raw_items, list):
        return []

    normalized_items: List[Dict[str, Any]] = []
    seen_ids = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            item_id = None

        file_path = normalize_knowledge_file_path(item.get("file_path") or item.get("filePath"))
        purpose = normalize_purpose(item.get("purpose"), default=None)
        usage = str(item.get("usage") or "").strip().lower()
        knowledge_point = str(item.get("knowledgePoint", item.get("knowledge_point")) or "").strip()
        is_required = item.get("isRequired", item.get("is_required"))

        raw_course_id = item.get("course_id", item.get("courseId"))
        try:
            course_id = int(raw_course_id) if raw_course_id not in (None, "", "null") else None
        except (TypeError, ValueError):
            course_id = None

        if item_id and item_id in seen_ids:
            continue
        if item_id:
            seen_ids.add(item_id)

        normalized_items.append({
            "id": item_id,
            "course_id": course_id,
            "file_path": file_path,
            "purpose": purpose,
            "file_name": os.path.basename(file_path) if file_path else "",
            "usage": usage if usage in ALLOWED_SOURCE_MAPPING_USAGES else "",
            "knowledge_point": knowledge_point,
            "is_required": is_required if isinstance(is_required, bool) else None,
        })

    return normalized_items


def validate_selected_knowledge_items(selected_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate selected knowledge items carry explicit lesson-planning intent."""
    if not isinstance(selected_items, list):
        return {"ok": False, "message": "selectedKnowledgeItems must be an array"}

    for item in selected_items:
        if not isinstance(item, dict):
            return {"ok": False, "message": "selectedKnowledgeItems contains invalid item"}
        if not str(item.get("file_path") or "").strip():
            return {"ok": False, "message": "selectedKnowledgeItems.file_path is required"}
        if str(item.get("usage") or "").strip().lower() not in ALLOWED_SOURCE_MAPPING_USAGES:
            return {"ok": False, "message": "selectedKnowledgeItems.usage is invalid"}
        if not str(item.get("knowledge_point") or "").strip():
            return {"ok": False, "message": "selectedKnowledgeItems.knowledgePoint is required"}
        if not isinstance(item.get("is_required"), bool):
            return {"ok": False, "message": "selectedKnowledgeItems.isRequired must be boolean"}
    return {"ok": True}


def _build_selected_knowledge_lookup(selected_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_path: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    for item in selected_items:
        if not isinstance(item, dict):
            continue
        file_path = normalize_knowledge_file_path(item.get("file_path") or item.get("filePath"))
        file_name = str(item.get("file_name") or os.path.basename(file_path or "") or "").strip()
        normalized = dict(item)
        if file_path:
            normalized["file_path"] = file_path
            by_path[file_path.lower()] = normalized
        if file_name:
            normalized["file_name"] = file_name
            by_name[file_name.lower()] = normalized
    return {"by_path": by_path, "by_name": by_name}


def _match_selected_knowledge_item(
    source_url: Any,
    source_title: Any,
    lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    by_path = lookup.get("by_path") if isinstance(lookup.get("by_path"), dict) else {}
    by_name = lookup.get("by_name") if isinstance(lookup.get("by_name"), dict) else {}
    normalized_path = normalize_knowledge_file_path(source_url)
    if normalized_path and normalized_path.lower() in by_path:
        return by_path[normalized_path.lower()]
    source_name = os.path.basename(str(normalized_path or source_url or source_title or "")).strip().lower()
    if source_name and source_name in by_name:
        return by_name[source_name]
    title_name = os.path.basename(str(source_title or "")).strip().lower()
    if title_name and title_name in by_name:
        return by_name[title_name]
    return {}


def _build_selected_knowledge_identity(item: Dict[str, Any]) -> str:
    file_path = normalize_knowledge_file_path(item.get("file_path") or item.get("filePath"))
    if file_path:
        return f"path:{file_path.lower()}"
    file_name = str(item.get("file_name") or os.path.basename(str(item.get("file_path") or "")) or "").strip().lower()
    if file_name:
        return f"name:{file_name}"
    return ""

def build_knowledge_retrieval_namespaces(
    active_course_id: Any,
    selected_items: List[Dict[str, Any]]
) -> List[str]:
    """Build knowledge namespaces, preferring the global namespace and keeping legacy fallbacks."""
    namespaces: List[str] = [GLOBAL_KNOWLEDGE_BASE_NAMESPACE]
    seen = {GLOBAL_KNOWLEDGE_BASE_NAMESPACE}

    for item in selected_items:
        course_id = item.get("course_id")
        if not course_id:
            continue
        namespace = str(course_id).strip()
        if namespace and namespace not in seen:
            namespaces.append(namespace)
            seen.add(namespace)

    course_namespace = str(active_course_id).strip() if active_course_id not in (None, "", "null") else ""
    if course_namespace and course_namespace not in seen:
        namespaces.append(course_namespace)

    return namespaces

def filter_retrieved_docs_by_selected_items(
    docs: List[Any],
    selected_items: List[Dict[str, Any]]
) -> List[Any]:
    """Filter retrieved docs to only the selected knowledge-base files when selection exists."""
    if not selected_items:
        return docs

    selected_paths = {
        str(item.get("file_path") or "").strip().lower()
        for item in selected_items
        if str(item.get("file_path") or "").strip()
    }
    selected_names = {
        str(item.get("file_name") or "").strip().lower()
        for item in selected_items
        if str(item.get("file_name") or "").strip()
    }
    if not selected_paths and not selected_names:
        return docs

    filtered: List[Any] = []
    for doc in docs:
        metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
        source_path = normalize_knowledge_file_path(metadata.get("file_path") or metadata.get("source"))
        source_name = os.path.basename(str(source_path or metadata.get("source") or "")).strip().lower()

        if source_path and source_path.lower() in selected_paths:
            filtered.append(doc)
            continue
        if source_name and source_name in selected_names:
            filtered.append(doc)

    return filtered

def dedupe_retrieved_docs(docs: List[Any]) -> List[Any]:
    """Deduplicate retrieved docs merged from multiple namespaces."""
    deduped: List[Any] = []
    seen = set()

    for doc in docs:
        metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
        key = (
            str(metadata.get("file_path") or metadata.get("source") or "").strip(),
            str(metadata.get("page") or "").strip(),
            str(metadata.get("slide_index") or "").strip(),
            str(getattr(doc, "page_content", "") or "").strip()[:240],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)

    return deduped

def parse_source_mappings(
    raw_mappings: Any,
    normalized_temp_files: List[str],
    user_id: Any,
    upload_root: str
) -> Dict[str, Any]:
    """Validate sourceMappings and return normalized mapping info."""
    temp_file_set = set(normalized_temp_files)
    if not isinstance(raw_mappings, list):
        return {"ok": False, "message": "sourceMappings must be an array"}

    mapping_by_file: Dict[str, Dict[str, Any]] = {}
    for item in raw_mappings:
        if not isinstance(item, dict):
            return {"ok": False, "message": "sourceMappings contains invalid item"}

        file_path = normalize_relative_upload_path(item.get("filePath"))
        usage = str(item.get("usage") or "").strip().lower()
        knowledge_point = str(item.get("knowledgePoint") or "").strip()
        is_required = item.get("isRequired")

        if not file_path or file_path not in temp_file_set:
            return {"ok": False, "message": "sourceMappings.filePath not in tempFiles"}
        if usage not in ALLOWED_SOURCE_MAPPING_USAGES:
            return {"ok": False, "message": "sourceMappings.usage is invalid"}
        if not knowledge_point:
            return {"ok": False, "message": "sourceMappings.knowledgePoint is required"}
        if not isinstance(is_required, bool):
            return {"ok": False, "message": "sourceMappings.isRequired must be boolean"}
        if file_path in mapping_by_file:
            return {"ok": False, "message": "sourceMappings.filePath is duplicated"}

        expected_prefix = f"temp/{user_id}/"
        if not file_path.startswith(expected_prefix):
            return {"ok": False, "message": "sourceMappings.filePath does not belong to current user"}
        full_path = os.path.join(upload_root, file_path)
        if not os.path.exists(full_path):
            return {"ok": False, "message": f"temp file does not exist: {file_path}"}

        mapping_by_file[file_path] = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "usage": usage,
            "knowledge_point": knowledge_point,
            "is_required": is_required
        }

    if len(mapping_by_file) != len(normalized_temp_files):
        return {"ok": False, "message": "every temp file must have sourceMappings"}

    ordered_mappings = [mapping_by_file[file_path] for file_path in normalized_temp_files]
    return {"ok": True, "mapping_by_file": mapping_by_file, "ordered_mappings": ordered_mappings}

def normalize_temp_file_list(raw_paths: Any) -> Dict[str, Any]:
    """Validate and normalize temp file path array."""
    if raw_paths is None:
        raw_paths = []
    if not isinstance(raw_paths, list):
        return {"ok": False, "message": "tempFiles must be an array"}

    normalized_temp_files: List[str] = []
    seen_temp_files = set()
    for path_value in raw_paths:
        normalized = normalize_relative_upload_path(path_value)
        if not normalized:
            return {"ok": False, "message": "tempFiles contains invalid path"}
        if normalized in seen_temp_files:
            continue
        seen_temp_files.add(normalized)
        normalized_temp_files.append(normalized)

    return {"ok": True, "files": normalized_temp_files}

def convert_snake_to_legacy_source_mappings(raw_mappings: Any) -> Any:
    """Convert snake_case mapping payload to legacy camelCase schema."""
    if raw_mappings is None:
        return []
    if not isinstance(raw_mappings, list):
        return raw_mappings

    converted = []
    for item in raw_mappings:
        if not isinstance(item, dict):
            converted.append(item)
            continue
        converted.append({
            "filePath": item.get("filePath", item.get("file_path")),
            "usage": item.get("usage"),
            "knowledgePoint": item.get("knowledgePoint", item.get("knowledge_point")),
            "isRequired": item.get("isRequired", item.get("is_required")),
        })
    return converted

def build_default_source_mappings(
    normalized_temp_files: List[str],
    user_id: Any,
    upload_root: str
) -> Dict[str, Any]:
    """Build default content mappings for legacy callers without sourceMappings."""
    ordered_mappings: List[Dict[str, Any]] = []
    expected_prefix = f"temp/{user_id}/"

    for file_path in normalized_temp_files:
        if not file_path.startswith(expected_prefix):
            return {"ok": False, "message": "file_path does not belong to current user"}
        full_path = os.path.join(upload_root, file_path)
        if not os.path.exists(full_path):
            return {"ok": False, "message": f"temp file does not exist: {file_path}"}
        ordered_mappings.append({
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "usage": "content",
            "knowledge_point": os.path.splitext(os.path.basename(file_path))[0],
            "is_required": False
        })

    return {"ok": True, "ordered_mappings": ordered_mappings}

def locate_ffmpeg_binary() -> str:
    """Locate ffmpeg executable in env or PATH."""
    ffmpeg_env = os.getenv("FFMPEG_PATH", "").strip()
    if ffmpeg_env and os.path.isfile(ffmpeg_env):
        return ffmpeg_env
    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg_bin:
        return ffmpeg_bin
    raise FileNotFoundError(
        "ffmpeg not found. Install ffmpeg and add it to PATH, or set FFMPEG_PATH."
    )

def convert_audio_to_wav_16k_mono(source_path: str) -> str:
    """Convert source audio to wav/16kHz/mono using ffmpeg and return wav path."""
    ffmpeg_bin = locate_ffmpeg_binary()
    temp_dir = tempfile.mkdtemp(prefix="asr_")
    wav_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}.wav")
    cmd = [
        ffmpeg_bin,
        "-i", source_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        wav_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path

def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract first JSON object from model output."""
    if not text:
        return None
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", stripped)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None

LESSON_PLAN_CORE_FALLBACK_SYSTEM_PROMPT = """You are 易度新星 EduNova teaching assistant.
Generate exactly one JSON object and do not output markdown fences or explanations.
The JSON must contain exactly these top-level keys:
- lesson_identity
- teaching_objectives
- student_profile
- knowledge_structure
- teaching_flow
- assessment_plan
- visual_asset_hints
- source_grounding
- style

Requirements:
1. Every key conclusion must be grounded in the provided source evidence when sources exist.
2. teaching_flow must be a list of 4-6 stage objects with keys id, title, goal, activities, teacher_actions, student_actions, assessment, source_refs.
3. Every teaching_flow stage should include multiple concrete teacher actions, student actions, interaction cues, and assessment points, not short placeholders.
4. teaching_objectives.goals, key_points, difficult_points, knowledge_structure.knowledge_points, assessment_plan.questions, assessment_plan.homework, and assessment_plan.extension_tasks should all be sufficiently rich for direct downstream Word/PPT generation.
5. student_profile must include not only foundation, but also likely misconceptions and support strategies when they can be inferred.
6. visual_asset_hints must help later PPT generation and use keys topic, visual_type, hint, source_refs.
7. source_grounding must be a list of objects with keys claim, source_refs, evidence.
8. Every selected source in source_notes/source_contract must appear in at least one teaching_flow stage source_refs.
9. For required=true sources, their knowledge_point and intended usage must be reflected in teaching_flow, knowledge_structure, or assessment_plan, not just cited by name.
10. Prefer fuller, classroom-executable content over concise summaries.
11. Return valid JSON only."""

LESSON_PLAN_CORE_FALLBACK_USER_PROMPT = """请根据课程信息、需求摘要、结构化教学要素和资料证据，生成核心教学 spec。

课程信息:
{{course_info_json}}

需求摘要:
{{requirement_summary_json}}

结构化教学要素:
{{structured_requirement_json}}

其他表单信息:
{{form_context_json}}

资料证据:
{{source_evidence_json}}

请确保输出聚焦教学设计本身，不要直接生成 Word/PPT 文案。

同时请加大内容密度：
1. teaching_objectives.goals 请尽量写成 4-6 条完整教学句，覆盖知识技能、过程方法、情感价值三个维度。
2. teaching_flow 请尽量写成 4-6 个完整环节，每个环节都补足 activities、teacher_actions、student_actions、assessment，不要只有标题。
3. assessment_plan.questions、homework、extension_tasks 请分别尽量写 3 条左右的完整句子，保证后续 Word 导出不至于过短。
4. student_profile 请尽量写出已有基础、可能误区、学习偏好与支持策略。
5. knowledge_structure 请尽量补足关键概念、概念关系、典型案例或情境，不要只给几个词。
6. 若资料证据中出现 source_notes/source_contract，请把每个资料的 usage、knowledge_point、required 当作硬约束处理。
7. 每个被选资料至少要落到一个教学环节中，并在对应环节的 source_refs 中显式写出 source_title。
8. required=true 的资料必须体现在教学流程、知识结构或评价任务中，不能只出现在泛泛表述里。
9. knowledge_point 非空时，相关知识点必须在教学流程、活动设计或评价任务中被明确展开。
10. 如果资料不足，可以结合课程主题、章节信息和教学目标做合理教学补全，但要保持像真实教师备课内容。"""

LESSON_PLAN_DOCX_FALLBACK_SYSTEM_PROMPT = """You are 易度新星 EduNova teaching assistant.
Generate exactly one JSON object with a single top-level key: docx_outline.
docx_outline must be an array of objects with keys section_title, section_goal, bullets, source_refs.
Requirements:
1. Focus on a teacher-ready Word lesson plan that can be used directly by a teacher, not a sparse summary.
2. Prefer 7-9 concrete sections covering goals, student analysis, key/difficult points, teaching flow, classroom activities, homework, board design, reflection, and assessment when appropriate.
3. Each section should contain 5-8 bullets whenever the material supports it; bullets should be specific, operational, and useful for classroom execution.
4. For teaching flow, include stage purpose, approximate time, teacher action, student action, interaction or questioning, and expected output when possible.
5. For goals, distinguish knowledge, ability/method, and value/attitude dimensions when possible.
6. For activities, include grouping method, task description, materials, feedback or evaluation cue when possible.
7. Every bullet should be a complete teacher-facing sentence, not a short phrase or slogan.
8. Avoid empty placeholders, generic slogans, or one-line sections.
9. When material is insufficient, infer reasonable classroom details from the topic and requirement_summary so the output still feels complete.
10. source_refs must reference provided source titles.
11. Every selected source in source_notes/source_contract must appear in at least one section source_refs.
12. For required=true sources, bullets must explicitly reflect the source knowledge_point or intended usage.
13. Return valid JSON only."""

LESSON_PLAN_DOCX_FALLBACK_USER_PROMPT = """请基于核心教学 spec 和资料证据，生成适合 Word 教案导出的 docx_outline。

核心教学 spec:
{{core_spec_json}}

需求摘要:
{{requirement_summary_json}}

资料证据:
{{source_evidence_json}}

请按下面要求补充得更充实一些：
1. 目标部分尽量拆成知识与技能、过程与方法、情感态度与价值观三个维度。
2. 学情分析不要只写“基础一般”，要写已有基础、可能误区、学习偏好、课堂支持策略。
3. 教学重点难点除了列点，还要写突破办法或处理策略。
4. 教学流程尽量写出“环节名称 + 时间建议 + 教师行为 + 学生活动 + 提问/评价提示”。
5. 课堂活动尽量写清任务要求、分组方式、产出形式、反馈方式。
6. 作业部分尽量区分基础巩固和拓展迁移。
7. 板书建议尽量写出主线结构与关键词，不要只写一句“概念-方法-总结”。
8. 如果资料里有案例、图片、实验、真实情境，请尽量吸收到对应 section 的 bullets 里。
9. 每条 bullet 尽量写成 30-60 个字左右的完整教学语句，不要只有一个短词或半句话。
10. 输出内容以“教师拿到后可以直接改成成稿教案”为目标，宁可更具体，不要过于概括。
11. 资料证据中的每个 source_notes/source_contract 都至少要在一个 section 的 source_refs 中出现一次。
12. required=true 的资料不能只挂引用名，必须在 bullets 中体现其知识点或使用方式。"""

LESSON_PLAN_PPT_FALLBACK_SYSTEM_PROMPT = """You are 易度新星 EduNova teaching assistant.
Generate exactly one JSON object with a single top-level key: ppt_outline.
ppt_outline must be an array of objects with keys slide_type, title, goal, bullets, visual_suggestion, source_refs.
Requirements:
1. Optimize for classroom presentation rhythm, not Word prose.
2. Include cover/toc/content/summary style semantics when useful, but keep most slides content-oriented.
3. Prefer 10-12 meaningful slides in total, with 7-9 content slides when the material supports it.
4. Each content slide should fit one page but still include 4-6 concrete bullets, not sparse placeholder text.
5. Bullets should mention examples, questions, activities, comparisons, or classroom prompts when appropriate.
6. visual_suggestion should be specific enough for local asset matching.
7. source_refs must reference provided source titles.
8. Every selected source in source_notes/source_contract must appear in at least one slide source_refs.
9. For required=true or usage=image_asset sources, the slide bullets or visual_suggestion must explicitly reflect the intended usage.
10. Return valid JSON only."""

LESSON_PLAN_PPT_FALLBACK_USER_PROMPT = """请基于核心教学 spec 和资料证据，生成适合课堂展示的 ppt_outline。

核心教学 spec:
{{core_spec_json}}

需求摘要:
{{requirement_summary_json}}

资料证据:
{{source_evidence_json}}

请额外遵守：
1. 不要只给标题和两个短 bullet，每页尽量写满 4-6 条有效要点。
2. 重点页面要体现“概念解释 + 例子/情境 + 提问或互动 + 小结/提醒”中的至少两类内容。
3. 若适合课堂演示，可加入“教师提问”“学生观察点”“当堂练习”这类 bullet。
4. bullet 要适合上屏展示，但不能过于空泛，尽量写成 18-32 个字左右的完整表达。
5. 如果资料不足，可根据 topic、knowledge_points、teaching_goals 合理补全典型课堂内容。
6. 资料证据中的每个 source_notes/source_contract 都至少要在一个 slide 的 source_refs 中出现一次。
7. required=true 或 usage=image_asset 的资料，必须在对应 slide 的 bullets 或 visual_suggestion 中明确体现。"""

LESSON_PLAN_REVISION_FALLBACK_SYSTEM_PROMPT = """You are 易度新星 EduNova teaching assistant.
Revise the provided core teaching spec incrementally according to the revision request.
Return exactly one JSON object with the same top-level schema as the existing core teaching spec.
Do not output markdown or explanations."""

LESSON_PLAN_REVISION_FALLBACK_USER_PROMPT = """请基于现有核心教学 spec 做增量修改，不要从头重写。

当前核心教学 spec:
{{core_spec_json}}

当前 lesson_plan_spec:
{{lesson_plan_spec_json}}

修改意见:
{{revision_request}}

资料证据:
{{source_evidence_json}}"""


def _request_chat_completion_json(
    *,
    api_key: str,
    api_base: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: int = 120,
) -> Dict[str, Any]:
    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        json={
            'model': model_name or get_model_primary("text"),
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False,
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(f'API request failed: {response.status_code}, {response.text}')

    response_json = response.json()
    content = ''
    choices = response_json.get('choices') if isinstance(response_json, dict) else []
    if isinstance(choices, list) and choices:
        message = choices[0].get('message', {}) if isinstance(choices[0], dict) else {}
        raw_content = message.get('content')
        if isinstance(raw_content, list):
            parts: List[str] = []
            for item in raw_content:
                if isinstance(item, dict):
                    text = item.get('text')
                    if text:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)
            content = ''.join(parts).strip()
        else:
            content = str(raw_content or '').strip()

    if not content:
        raise RuntimeError('model response content is empty')

    parsed = _extract_first_json_object(content)
    if not parsed:
        raise RuntimeError('model did not return valid JSON')
    return parsed

def normalize_requirement_summary(raw: Dict[str, Any], form_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize requirement summary schema and fill required keys."""
    learning_objectives = str(form_snapshot.get("learningObjectives", "") or "").strip()
    key_points = str(form_snapshot.get("keyPoints", "") or "").strip()
    duration = str(form_snapshot.get("duration", "") or "").strip()
    style = str(form_snapshot.get("teachingStyle", "") or "").strip()
    free_teaching_idea = str(form_snapshot.get("freeTeachingIdea", "") or "").strip()
    hints = _extract_requirement_hints_from_text(free_teaching_idea)
    inferred_duration = _extract_duration_from_text(
        "\n".join([
            str(raw.get("duration") or "").strip(),
            duration,
            free_teaching_idea,
        ])
    )
    raw_goals = raw.get("teaching_goals") if isinstance(raw.get("teaching_goals"), list) else []
    raw_knowledge = raw.get("knowledge_points") if isinstance(raw.get("knowledge_points"), list) else []

    summary = {
        "teaching_goals": _dedupe_non_empty_str_list([*raw_goals, *hints.get("teaching_goals", [])]),
        "knowledge_points": _dedupe_non_empty_str_list([*raw_knowledge, *hints.get("knowledge_points", [])]),
        "duration": inferred_duration or str(raw.get("duration") or duration or ""),
        "style": str(raw.get("style") or style or hints.get("teaching_style") or ""),
        "output_targets": raw.get("output_targets") if isinstance(raw.get("output_targets"), list) else []
    }

    if not summary["teaching_goals"] and learning_objectives:
        summary["teaching_goals"] = [learning_objectives]
    if not summary["knowledge_points"] and key_points:
        summary["knowledge_points"] = [key_points]
    if not summary["output_targets"]:
        outline_type = str(form_snapshot.get("outlineType", "") or "").strip().lower()
        summary["output_targets"] = ["课程总纲"] if outline_type == "course" else ["课堂教案"]

    return summary

def _normalize_number_token(token: str) -> Optional[float]:
    clean_token = str(token or "").strip().replace("个", "")
    if not clean_token:
        return None
    try:
        return float(clean_token)
    except (TypeError, ValueError):
        pass

    mapping = {
        "半": 0.5,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    if clean_token in mapping:
        return float(mapping[clean_token])
    if clean_token.endswith("半") and len(clean_token) >= 2:
        prefix = _normalize_number_token(clean_token[:-1])
        if prefix is not None:
            return prefix + 0.5
    if clean_token.startswith("十"):
        suffix = clean_token[1:]
        suffix_value = _normalize_number_token(suffix) if suffix else 0
        if suffix_value is not None:
            return 10 + suffix_value
    if clean_token.endswith("十"):
        prefix = _normalize_number_token(clean_token[:-1])
        if prefix is not None:
            return prefix * 10
    if "十" in clean_token:
        parts = clean_token.split("十", 1)
        left = _normalize_number_token(parts[0]) if parts[0] else 1
        right = _normalize_number_token(parts[1]) if parts[1] else 0
        if left is not None and right is not None:
            return left * 10 + right
    return None

def _format_duration_minutes(minutes: float) -> str:
    rounded = int(round(minutes))
    if rounded <= 0:
        return ""
    return f"{rounded}分钟"

def _extract_duration_from_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""

    hour_match = re.search(r'([0-9]+(?:\.[0-9]+)?|[一二两三四五六七八九十半个]+)\s*小时', normalized, re.IGNORECASE)
    if hour_match:
        value = _normalize_number_token(hour_match.group(1))
        if value is not None:
            return _format_duration_minutes(value * 60)

    minute_match = re.search(r'([0-9]+(?:\.[0-9]+)?|[一二两三四五六七八九十半个]+)\s*分钟', normalized, re.IGNORECASE)
    if minute_match:
        value = _normalize_number_token(minute_match.group(1))
        if value is not None:
            return _format_duration_minutes(value)

    period_match = re.search(r'([0-9]+(?:\.[0-9]+)?|[一二两三四五六七八九十半个]+)\s*课时', normalized, re.IGNORECASE)
    if period_match:
        value = _normalize_number_token(period_match.group(1))
        if value is not None:
            if abs(value - round(value)) < 1e-6:
                return f"{int(round(value))}课时"
            return f"{value}课时"

    lesson_match = re.search(r'([0-9]+(?:\.[0-9]+)?|[一二两三四五六七八九十半个]+)\s*(?:节|堂)课', normalized, re.IGNORECASE)
    if lesson_match:
        value = _normalize_number_token(lesson_match.group(1))
        if value is not None:
            if abs(value - round(value)) < 1e-6:
                return f"{int(round(value))}节课"
            return f"{value}节课"

    return ""

def _extract_clause_after_keyword(text: str, keywords: List[str]) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    for keyword in keywords:
        pattern = rf'{re.escape(keyword)}(?:\s*(?:[:：]|是|为|有|包括|包含|在于))?\s*([^。\n；;！？!?]+)'
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            return str(match.group(1) or "").strip(" ，,；;。！!？?")
    return ""

def _extract_list_after_keyword(text: str, keywords: List[str]) -> List[str]:
    clause = _extract_clause_after_keyword(text, keywords)
    if not clause:
        return []
    return _normalize_text_list(clause)

def _extract_teaching_goals_from_text(text: str) -> List[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []

    goals = _extract_list_after_keyword(
        normalized,
        ["教学目标", "学习目标", "本节课目标", "这节课目标", "目标"],
    )
    if goals:
        goals = [
            item for item in goals
            if (
                any(marker in item for marker in ["让学生", "掌握", "理解", "学会", "认识", "能够", "会"])
                and not any(marker in item for marker in ["知识点", "难点", "学生基础", "学情", "采用", "教学风格"])
            )
        ]
        if goals:
            return goals[:4]

    sentence_candidates = re.split(r"[。！？!?；;\n]+", normalized)
    extracted: List[str] = []
    for sentence in sentence_candidates:
        candidate = sentence.strip(" ，,；;。")
        if not candidate:
            continue
        if any(marker in candidate for marker in ["让学生", "学生能够", "学生可以", "希望学生", "帮助学生"]):
            extracted.append(candidate)
            continue
        if any(marker in candidate for marker in ["掌握", "理解", "学会", "认识", "能够"]) and len(candidate) <= 40:
            extracted.append(candidate)
    return _dedupe_non_empty_str_list(extracted[:4])

def _extract_teaching_style_from_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""

    explicit = _extract_clause_after_keyword(normalized, ["教学风格", "授课风格", "课堂风格", "上课方式"])
    if explicit:
        for option in ["讲授型", "探究式", "项目式", "合作学习", "翻转课堂"]:
            if option in explicit:
                return option

    style_rules = [
        ("翻转课堂", ["翻转课堂", "课前自学", "先学后教"]),
        ("项目式", ["项目式", "项目学习", "任务驱动"]),
        ("合作学习", ["合作学习", "小组合作", "合作探究"]),
        ("探究式", ["探究式", "探究", "启发式", "问题驱动"]),
        ("讲授型", ["讲授", "讲解为主", "老师讲", "系统讲解"]),
    ]
    for label, keywords in style_rules:
        if any(keyword in normalized for keyword in keywords):
            return label
    return ""

def _extract_student_foundation_from_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""

    if any(keyword in normalized for keyword in ["基础薄弱", "底子薄", "跟不上", "较弱"]):
        return "基础薄弱"
    if any(keyword in normalized for keyword in ["中等水平", "基础一般", "一般水平"]):
        return "中等水平"
    if any(keyword in normalized for keyword in ["基础较好", "较高水平", "能力较强", "拔高"]):
        return "较高水平"

    return _extract_clause_after_keyword(normalized, ["学生基础", "学情", "学生情况", "基础情况"])

def _extract_activity_options_from_text(text: str) -> List[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []

    activity_rules = [
        ("小组讨论", ["小组讨论", "分组讨论", "讨论"]),
        ("实验", ["实验", "动手操作"]),
        ("角色扮演", ["角色扮演", "情景扮演"]),
        ("游戏辩论", ["游戏辩论", "辩论", "游戏"]),
        ("演讲", ["演讲", "展示汇报", "上台展示"]),
        ("练习测验", ["练习", "测验", "随堂练", "随堂测", "习题"]),
    ]
    extracted: List[str] = []
    for label, keywords in activity_rules:
        if any(keyword in normalized for keyword in keywords):
            extracted.append(label)
    return _dedupe_non_empty_str_list(extracted)

def _extract_difficult_points_from_text(text: str) -> List[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []
    points = _extract_list_after_keyword(normalized, ["难点", "重点难点", "教学难点", "学生易错点"])
    points = [
        item for item in points
        if not any(marker in item for marker in ["学生基础", "学情", "采用", "小组讨论", "练习测验"])
    ]
    return points[:6]

def _extract_knowledge_points_from_text(text: str) -> List[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []

    for keywords in [
        ["知识点", "核心知识", "重点", "教学重点", "讲解重点"],
        ["内容包括", "主要内容", "围绕", "讲到"],
    ]:
        points = _extract_list_after_keyword(normalized, keywords)
        filtered = [
            item for item in points
            if len(item) <= 30 and not any(marker in item for marker in ["难点", "学生基础", "学情", "采用", "探究式", "讲授型", "项目式", "合作学习", "翻转课堂", "讨论", "练习", "测验", "展示", "实验"])
        ]
        if filtered:
            return filtered[:6]
    return []

def _extract_requirement_hints_from_text(text: str) -> Dict[str, Any]:
    normalized = str(text or "").strip()
    return {
        "duration": _extract_duration_from_text(normalized),
        "teaching_goals": _extract_teaching_goals_from_text(normalized),
        "knowledge_points": _extract_knowledge_points_from_text(normalized),
        "difficult_points": _extract_difficult_points_from_text(normalized),
        "teaching_style": _extract_teaching_style_from_text(normalized),
        "student_foundation": _extract_student_foundation_from_text(normalized),
        "activities": _extract_activity_options_from_text(normalized),
    }

def _dedupe_non_empty_str_list(items: List[str]) -> List[str]:
    """Deduplicate while keeping order and dropping empty strings."""
    result: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result

def _normalize_text_list(value: Any) -> List[str]:
    """Normalize array-like or delimited string into string list."""
    if isinstance(value, list):
        return _dedupe_non_empty_str_list([str(x) for x in value])
    if isinstance(value, str):
        parts = re.split(r"[，,；;、\n]+", value)
        return _dedupe_non_empty_str_list(parts)
    return []

def normalize_structured_requirement(raw: Dict[str, Any], form_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize structured teaching requirement schema with rule-based fallback."""
    grade_subject = str(form_snapshot.get("gradeSubject", "") or "").strip()
    learning_objectives = str(form_snapshot.get("learningObjectives", "") or "").strip()
    key_points_text = str(form_snapshot.get("keyPoints", "") or "").strip()
    student_level = str(form_snapshot.get("studentLevel", "") or "").strip()
    teaching_style = str(form_snapshot.get("teachingStyle", "") or "").strip()
    outline_type = str(form_snapshot.get("outlineType", "") or "").strip().lower()
    activities = form_snapshot.get("activities", []) if isinstance(form_snapshot.get("activities"), list) else []
    free_teaching_idea = str(form_snapshot.get("freeTeachingIdea", "") or "").strip()
    hints = _extract_requirement_hints_from_text(free_teaching_idea)
    inferred_key_points = hints.get("knowledge_points", [])
    inferred_difficult_points = hints.get("difficult_points", [])
    inferred_activities = hints.get("activities", [])

    topic = str(raw.get("topic") or "").strip()
    if not topic:
        topic = learning_objectives or key_points_text or grade_subject or "未命名主题"

    knowledge_points = _normalize_text_list(raw.get("knowledge_points"))
    if not knowledge_points and key_points_text:
        knowledge_points = _normalize_text_list(key_points_text)
    if not knowledge_points and inferred_key_points:
        knowledge_points = inferred_key_points

    key_points = _normalize_text_list(raw.get("key_points"))
    if not key_points and key_points_text:
        key_points = _normalize_text_list(key_points_text)
    if not key_points and inferred_key_points:
        key_points = inferred_key_points

    difficult_points = _normalize_text_list(raw.get("difficult_points"))
    if not difficult_points and key_points_text:
        difficult_points = [item for item in _normalize_text_list(key_points_text) if "难" in item]
    if not difficult_points and inferred_difficult_points:
        difficult_points = inferred_difficult_points

    raw_flow = raw.get("teaching_flow")
    teaching_flow: List[Dict[str, Any]] = []
    if isinstance(raw_flow, list):
        for idx, item in enumerate(raw_flow):
            step = idx + 1
            title = ""
            goal = ""
            if isinstance(item, dict):
                try:
                    raw_step = item.get("step")
                    if isinstance(raw_step, (int, float)):
                        step = int(raw_step)
                    elif isinstance(raw_step, str) and raw_step.strip().isdigit():
                        step = int(raw_step.strip())
                except Exception:
                    step = idx + 1
                title = str(item.get("title") or "").strip()
                goal = str(item.get("goal") or "").strip()
            else:
                title = str(item or "").strip()
            if title or goal:
                teaching_flow.append({
                    "step": max(step, 1),
                    "title": title or f"步骤{idx + 1}",
                    "goal": goal
                })

    if not teaching_flow:
        default_titles = [
            ("导入与目标说明", "激活先验知识并明确学习目标"),
            ("核心知识讲解与示例", "建立关键概念与解题路径"),
            ("练习反馈与总结", "巩固知识点并完成迁移应用")
        ]
        if activities or inferred_activities:
            default_titles[2] = ("课堂活动与总结", "通过活动完成应用并总结反思")
        for idx, (title, goal) in enumerate(default_titles):
            teaching_flow.append({"step": idx + 1, "title": title, "goal": goal})

    raw_profile = raw.get("student_profile") if isinstance(raw.get("student_profile"), dict) else {}
    student_profile = {
        "grade": str(raw_profile.get("grade") or grade_subject or "").strip(),
        "foundation": str(raw_profile.get("foundation") or student_level or hints.get("student_foundation") or "").strip(),
        "learning_preference": str(raw_profile.get("learning_preference") or "").strip()
    }
    if not student_profile["learning_preference"]:
        student_profile["learning_preference"] = "案例驱动" if (activities or inferred_activities) else "讲练结合"

    raw_style = raw.get("style")
    if isinstance(raw_style, dict):
        style_obj = {
            "teaching_style": str(raw_style.get("teaching_style") or teaching_style or hints.get("teaching_style") or "").strip(),
            "interaction_level": str(raw_style.get("interaction_level") or "").strip(),
            "output_preference": str(raw_style.get("output_preference") or "").strip()
        }
    else:
        style_obj = {
            "teaching_style": str(raw_style or teaching_style or hints.get("teaching_style") or "").strip(),
            "interaction_level": "",
            "output_preference": ""
        }

    if not style_obj["interaction_level"]:
        style_obj["interaction_level"] = "高互动" if len(inferred_activities) >= 2 else ("中互动" if inferred_activities else "低互动")
    if not style_obj["output_preference"]:
        style_obj["output_preference"] = "课程总纲" if outline_type == "course" else "课堂教案"

    normalized = {
        "topic": topic,
        "knowledge_points": knowledge_points,
        "teaching_flow": teaching_flow,
        "key_points": key_points,
        "difficult_points": difficult_points,
        "student_profile": student_profile,
        "style": style_obj
    }
    return normalized

def _normalize_source_refs(value: Any) -> List[str]:
    """Normalize source refs into a stable string list."""
    if isinstance(value, list):
        return _dedupe_non_empty_str_list([str(item) for item in value])
    if isinstance(value, str):
        return _dedupe_non_empty_str_list(re.split(r"[，,；;、\n]+", value))
    return []

def _slugify_identifier(value: Any, prefix: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    text = text.strip("_")
    if not text:
        return prefix
    return text

def _default_game_theme(theme_name: str = "clean") -> Dict[str, str]:
    theme = str(theme_name or "clean").strip().lower() or "clean"
    if theme == "tech":
        return {
            "name": "tech",
            "font_family": "'Microsoft YaHei', 'PingFang SC', sans-serif",
            "bg": "#0f172a",
            "bg_accent": "#1d4ed8",
            "surface": "#f8fbff",
            "surface_strong": "#dbeafe",
            "primary": "#2563eb",
            "primary_strong": "#1d4ed8",
            "accent": "#22d3ee",
            "success": "#16a34a",
            "danger": "#dc2626",
            "text": "#0f172a",
            "muted": "#475569",
            "border": "#93c5fd",
        }
    if theme == "vivid":
        return {
            "name": "vivid",
            "font_family": "'Microsoft YaHei', 'PingFang SC', sans-serif",
            "bg": "#fff7ed",
            "bg_accent": "#fde68a",
            "surface": "#ffffff",
            "surface_strong": "#ffedd5",
            "primary": "#ea580c",
            "primary_strong": "#c2410c",
            "accent": "#0284c7",
            "success": "#16a34a",
            "danger": "#dc2626",
            "text": "#431407",
            "muted": "#7c2d12",
            "border": "#fdba74",
        }
    return {
        "name": "clean",
        "font_family": "'Microsoft YaHei', 'PingFang SC', sans-serif",
        "bg": "#eff6ff",
        "bg_accent": "#dbeafe",
        "surface": "#ffffff",
        "surface_strong": "#eff6ff",
        "primary": "#2563eb",
        "primary_strong": "#1d4ed8",
        "accent": "#f59e0b",
        "success": "#16a34a",
        "danger": "#dc2626",
        "text": "#0f172a",
        "muted": "#475569",
        "border": "#bfdbfe",
    }

def _build_default_game_plan(
    requirement_summary: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    topic = str(
        requirement_summary.get("topic")
        or requirement_summary.get("chapter_title")
        or requirement_summary.get("grade_subject")
        or "当前主题"
    ).strip()
    knowledge_points = _normalize_text_list(requirement_summary.get("knowledge_points"))
    source_refs = _dedupe_non_empty_str_list([
        str(item.get("source_title") or "").strip()
        for item in source_notes[:4]
        if isinstance(item, dict)
    ])
    stage_templates = [
        ("stage_1", "基础识别", "快速识别核心概念，建立信心", 3, 2),
        ("stage_2", "应用判断", "在情境中应用概念做出判断", 3, 2),
        ("stage_3", "综合挑战", "综合多个知识点完成收尾挑战", 2, 1),
    ]
    stages: List[Dict[str, Any]] = []
    for index, (stage_id, name, goal, question_count, min_correct) in enumerate(stage_templates):
        start = index * 2
        tags = knowledge_points[start:start + 2] or knowledge_points[:2] or [topic]
        stages.append({
            "id": stage_id,
            "name": name,
            "goal": goal,
            "knowledge_tags": tags,
            "question_count": question_count,
            "pass_rule": {
                "min_correct": min_correct,
                "description": f"至少答对 {min_correct} 题即可通关"
            },
            "review_refs": source_refs[:2] or ["对应课件讲解页"],
            "teacher_tip": f"本关聚焦：{'、'.join(tags)}",
        })

    return {
        "mode": "level_challenge",
        "title": f"{topic}轻量闯关",
        "objective": f"围绕“{topic}”完成三关互动练习与即时反馈",
        "theme": "clean",
        "mechanic": "三关闯关 + 即时反馈 + 通关总结",
        "estimated_minutes": 8,
        "stages": stages,
        "score_rule": {
            "base_score": 10,
            "combo_bonus": 2,
            "stage_clear_bonus": 5,
            "time_bonus_enabled": False,
        },
        "feedback_style": {
            "success_tone": "鼓励式",
            "retry_tone": "纠错式",
            "summary_tone": "诊断式",
        },
        "steps": [
            "第1关侧重基础识别，帮助学生快速进入状态",
            "第2关侧重应用判断，突出知识点迁移",
            "第3关侧重综合挑战，形成完整闯关收束",
        ],
        "materials": ["课件讲解页", "课堂板书", "随堂练习"],
        "source_refs": source_refs[:3],
    }

def _normalize_game_plan(
    raw_game_plan: Any,
    requirement_summary: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    defaults = _build_default_game_plan(requirement_summary, source_notes)
    raw = raw_game_plan if isinstance(raw_game_plan, dict) else {}
    raw_stages = raw.get("stages") if isinstance(raw.get("stages"), list) else []
    stages: List[Dict[str, Any]] = []

    for index, item in enumerate(raw_stages):
        if not isinstance(item, dict):
            continue
        fallback_stage = defaults["stages"][min(index, len(defaults["stages"]) - 1)]
        pass_rule_raw = item.get("pass_rule") if isinstance(item.get("pass_rule"), dict) else {}
        stage_id = str(item.get("id") or fallback_stage["id"]).strip()
        question_count = item.get("question_count", fallback_stage["question_count"])
        try:
            question_count = max(int(question_count), 1)
        except Exception:
            question_count = fallback_stage["question_count"]
        min_correct = pass_rule_raw.get("min_correct", fallback_stage["pass_rule"]["min_correct"])
        try:
            min_correct = max(int(min_correct), 1)
        except Exception:
            min_correct = fallback_stage["pass_rule"]["min_correct"]

        stages.append({
            "id": _slugify_identifier(stage_id, fallback_stage["id"]),
            "name": str(item.get("name") or fallback_stage["name"]).strip() or fallback_stage["name"],
            "goal": str(item.get("goal") or fallback_stage["goal"]).strip() or fallback_stage["goal"],
            "knowledge_tags": _normalize_text_list(item.get("knowledge_tags")) or fallback_stage["knowledge_tags"],
            "question_count": question_count,
            "pass_rule": {
                "min_correct": min_correct,
                "description": str(pass_rule_raw.get("description") or fallback_stage["pass_rule"]["description"]).strip()
                or fallback_stage["pass_rule"]["description"],
            },
            "review_refs": _normalize_source_refs(item.get("review_refs")) or fallback_stage["review_refs"],
            "teacher_tip": str(item.get("teacher_tip") or fallback_stage["teacher_tip"]).strip() or fallback_stage["teacher_tip"],
        })

    if not stages:
        stages = defaults["stages"]

    raw_score_rule = raw.get("score_rule") if isinstance(raw.get("score_rule"), dict) else {}
    raw_feedback_style = raw.get("feedback_style") if isinstance(raw.get("feedback_style"), dict) else {}
    estimated_minutes = raw.get("estimated_minutes", defaults["estimated_minutes"])
    try:
        estimated_minutes = max(int(estimated_minutes), 1)
    except Exception:
        estimated_minutes = defaults["estimated_minutes"]

    normalized = {
        "mode": str(raw.get("mode") or defaults["mode"]).strip() or defaults["mode"],
        "title": str(raw.get("title") or defaults["title"]).strip() or defaults["title"],
        "objective": str(raw.get("objective") or defaults["objective"]).strip() or defaults["objective"],
        "theme": str(raw.get("theme") or defaults["theme"]).strip() or defaults["theme"],
        "mechanic": str(raw.get("mechanic") or defaults["mechanic"]).strip() or defaults["mechanic"],
        "estimated_minutes": estimated_minutes,
        "stages": stages,
        "score_rule": {
            "base_score": int(raw_score_rule.get("base_score", defaults["score_rule"]["base_score"]) or defaults["score_rule"]["base_score"]),
            "combo_bonus": int(raw_score_rule.get("combo_bonus", defaults["score_rule"]["combo_bonus"]) or defaults["score_rule"]["combo_bonus"]),
            "stage_clear_bonus": int(raw_score_rule.get("stage_clear_bonus", defaults["score_rule"]["stage_clear_bonus"]) or defaults["score_rule"]["stage_clear_bonus"]),
            "time_bonus_enabled": bool(raw_score_rule.get("time_bonus_enabled", defaults["score_rule"]["time_bonus_enabled"])),
        },
        "feedback_style": {
            "success_tone": str(raw_feedback_style.get("success_tone") or defaults["feedback_style"]["success_tone"]).strip() or defaults["feedback_style"]["success_tone"],
            "retry_tone": str(raw_feedback_style.get("retry_tone") or defaults["feedback_style"]["retry_tone"]).strip() or defaults["feedback_style"]["retry_tone"],
            "summary_tone": str(raw_feedback_style.get("summary_tone") or defaults["feedback_style"]["summary_tone"]).strip() or defaults["feedback_style"]["summary_tone"],
        },
        "steps": _normalize_text_list(raw.get("steps")),
        "materials": _normalize_text_list(raw.get("materials")) or defaults["materials"],
        "source_refs": _normalize_source_refs(raw.get("source_refs")) or defaults["source_refs"],
    }
    if not normalized["steps"]:
        normalized["steps"] = [f"{stage['name']}：{stage['goal']}" for stage in stages]
    return normalized

def _trim_text(value: Any, limit: int = 240) -> str:
    """Trim arbitrary content into a concise single string."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def _contains_semantic_phrase(text: Any, phrase: Any) -> bool:
    haystack = str(text or "").strip()
    needle = str(phrase or "").strip()
    if not needle:
        return True
    if needle in haystack:
        return True
    tokens = [token for token in re.split(r"[，,；;、/\s]+", needle) if token]
    if not tokens:
        return False
    matched = sum(1 for token in tokens[:4] if token in haystack)
    return matched >= min(len(tokens[:4]), 2)


def _score_source_alignment(text: str, note: Dict[str, Any]) -> int:
    score = 0
    knowledge_point = str(note.get("knowledge_point") or "").strip()
    source_title = str(note.get("source_title") or "").strip()
    usage = str(note.get("usage") or "").strip()
    haystack = str(text or "").strip()
    if not haystack:
        return score
    if _contains_semantic_phrase(haystack, knowledge_point):
        score += 8
    if _contains_semantic_phrase(haystack, source_title):
        score += 4
    usage_keywords = {
        "content": ["概念", "讲解", "知识", "要点"],
        "case": ["案例", "情境", "迁移", "分析"],
        "format": ["结构", "层次", "呈现", "板书"],
        "image_asset": ["图片", "图示", "素材", "配图"],
    }.get(usage, [])
    score += sum(1 for keyword in usage_keywords if keyword in haystack)
    return score


def _pick_best_docx_section_index(docx_outline: List[Dict[str, Any]], note: Dict[str, Any]) -> int:
    if not docx_outline:
        return 0
    best_index = 0
    best_score = -1
    for index, item in enumerate(docx_outline):
        if not isinstance(item, dict):
            continue
        section_text = " ".join([
            str(item.get("section_title") or "").strip(),
            str(item.get("section_goal") or "").strip(),
            " ".join(_normalize_text_list(item.get("bullets"))),
        ]).strip()
        score = _score_source_alignment(section_text, note)
        title = str(item.get("section_title") or "").strip()
        usage = str(note.get("usage") or "").strip()
        if usage in {"content", "case"} and any(keyword in title for keyword in ["流程", "活动", "重点", "难点"]):
            score += 2
        if usage == "format" and any(keyword in title for keyword in ["流程", "活动", "目标"]):
            score += 1
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def _pick_best_ppt_slide_index(ppt_outline: List[Dict[str, Any]], note: Dict[str, Any]) -> int:
    if not ppt_outline:
        return 0
    candidate_indexes = [
        index for index, item in enumerate(ppt_outline)
        if isinstance(item, dict) and str(item.get("slide_type") or "").strip() != "cover"
    ] or list(range(len(ppt_outline)))
    best_index = candidate_indexes[0] if candidate_indexes else 0
    best_score = -1
    for index in candidate_indexes:
        item = ppt_outline[index]
        slide_text = " ".join([
            str(item.get("title") or "").strip(),
            str(item.get("goal") or "").strip(),
            str(item.get("visual_suggestion") or "").strip(),
            " ".join(_normalize_text_list(item.get("bullets"))),
        ]).strip()
        score = _score_source_alignment(slide_text, note)
        if str(note.get("usage") or "").strip() == "image_asset" and "图" in slide_text:
            score += 2
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def _append_unique_text(items: Any, text: str) -> List[str]:
    normalized = [str(item).strip() for item in items if str(item).strip()] if isinstance(items, list) else []
    candidate = str(text or "").strip()
    if candidate and candidate not in normalized:
        normalized.append(candidate)
    return normalized


def _build_source_binding_copy(note: Dict[str, Any], target: str) -> str:
    source_title = str(note.get("source_title") or "参考资料").strip()
    knowledge_point = str(note.get("knowledge_point") or "").strip()
    usage = str(note.get("usage") or "content").strip()
    if usage == "case":
        return f"结合《{source_title}》中的案例，围绕“{knowledge_point or '本课主题'}”组织情境分析与迁移练习。"
    if usage == "format":
        if target == "ppt":
            return f"参考《{source_title}》的呈现结构安排本页信息层级，突出“{knowledge_point or '核心内容'}”。"
        return f"参考《{source_title}》的结构组织本节内容层次，突出“{knowledge_point or '核心内容'}”。"
    if usage == "image_asset":
        return f"展示《{source_title}》中与“{knowledge_point or '本课主题'}”相关的图像素材，辅助学生形成直观理解。"
    return f"结合《{source_title}》提炼“{knowledge_point or '本课主题'}”的讲解要点，并落实到本环节。"


def _enforce_source_intent_on_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(spec, dict):
        return spec

    requirement_summary = spec.get("requirement_summary") if isinstance(spec.get("requirement_summary"), dict) else {}
    source_notes = spec.get("source_notes") if isinstance(spec.get("source_notes"), list) else []
    docx_outline = spec.get("docx_outline") if isinstance(spec.get("docx_outline"), list) else []
    ppt_outline = spec.get("ppt_outline") if isinstance(spec.get("ppt_outline"), list) else []
    game_plan = spec.get("game_plan") if isinstance(spec.get("game_plan"), dict) else {}

    merged_knowledge_points = _normalize_text_list(requirement_summary.get("knowledge_points"))
    for note in source_notes:
        if not isinstance(note, dict):
            continue
        knowledge_point = str(note.get("knowledge_point") or "").strip()
        if knowledge_point and not any(_contains_semantic_phrase(existing, knowledge_point) for existing in merged_knowledge_points):
            merged_knowledge_points.append(knowledge_point)
    if merged_knowledge_points:
        requirement_summary["knowledge_points"] = _dedupe_non_empty_str_list(merged_knowledge_points)
        spec["requirement_summary"] = requirement_summary

    for note in source_notes:
        if not isinstance(note, dict):
            continue
        source_title = str(note.get("source_title") or "").strip()
        if not source_title:
            continue
        knowledge_point = str(note.get("knowledge_point") or "").strip()

        if docx_outline:
            section_index = _pick_best_docx_section_index(docx_outline, note)
            section = docx_outline[section_index]
            section["source_refs"] = _append_unique_text(section.get("source_refs"), source_title)
            section_text = " ".join([
                str(section.get("section_title") or "").strip(),
                str(section.get("section_goal") or "").strip(),
                " ".join(_normalize_text_list(section.get("bullets"))),
            ]).strip()
            if knowledge_point and not _contains_semantic_phrase(section_text, knowledge_point):
                section["bullets"] = _append_unique_text(section.get("bullets"), _build_source_binding_copy(note, "docx"))

        if ppt_outline:
            slide_index = _pick_best_ppt_slide_index(ppt_outline, note)
            slide = ppt_outline[slide_index]
            slide["source_refs"] = _append_unique_text(slide.get("source_refs"), source_title)
            slide_text = " ".join([
                str(slide.get("title") or "").strip(),
                str(slide.get("goal") or "").strip(),
                str(slide.get("visual_suggestion") or "").strip(),
                " ".join(_normalize_text_list(slide.get("bullets"))),
            ]).strip()
            if str(note.get("usage") or "").strip() == "image_asset":
                visual_suggestion = str(slide.get("visual_suggestion") or "").strip()
                binding_copy = _build_source_binding_copy(note, "ppt")
                if binding_copy not in visual_suggestion:
                    slide["visual_suggestion"] = f"{visual_suggestion}；{binding_copy}".strip("；")
            elif knowledge_point and not _contains_semantic_phrase(slide_text, knowledge_point):
                slide["bullets"] = _append_unique_text(slide.get("bullets"), _build_source_binding_copy(note, "ppt"))

        if isinstance(game_plan, dict):
            game_plan["source_refs"] = _append_unique_text(game_plan.get("source_refs"), source_title)
            for stage in game_plan.get("stages") if isinstance(game_plan.get("stages"), list) else []:
                if not isinstance(stage, dict):
                    continue
                review_refs = stage.get("review_refs")
                stage["review_refs"] = _append_unique_text(review_refs, source_title) if bool(note.get("required")) else _normalize_source_refs(review_refs)

    spec["docx_outline"] = docx_outline
    spec["ppt_outline"] = ppt_outline
    if isinstance(game_plan, dict):
        spec["game_plan"] = game_plan
    return spec

def _format_ms(ms: Any) -> str:
    """Format milliseconds as MM:SS or HH:MM:SS."""
    try:
        total_seconds = max(int(ms or 0) // 1000, 0)
    except Exception:
        total_seconds = 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def _build_requirement_summary_payload(
    form_snapshot: Dict[str, Any],
    clarified_requirement: Any,
    structured_requirement: Any,
    chapter_title: str
) -> Dict[str, Any]:
    """Build deterministic requirement summary for lesson_plan_spec."""
    clarified = normalize_requirement_summary(
        clarified_requirement if isinstance(clarified_requirement, dict) else {},
        form_snapshot
    )
    structured = normalize_structured_requirement(
        structured_requirement if isinstance(structured_requirement, dict) else {},
        form_snapshot
    )
    outline_type = str(form_snapshot.get("outlineType", "") or "course").strip().lower() or "course"
    grade_subject = str(form_snapshot.get("gradeSubject", "") or "").strip()
    duration = str(
        clarified.get("duration")
        or form_snapshot.get("duration")
        or ""
    ).strip()
    topic = str(
        structured.get("topic")
        or chapter_title
        or form_snapshot.get("learningObjectives")
        or form_snapshot.get("keyPoints")
        or grade_subject
        or ""
    ).strip()

    return {
        "topic": topic,
        "grade_subject": grade_subject,
        "outline_type": outline_type,
        "chapter_title": str(chapter_title or "").strip(),
        "duration": duration,
        "teaching_goals": _normalize_text_list(clarified.get("teaching_goals")),
        "knowledge_points": _normalize_text_list(
            structured.get("knowledge_points") or clarified.get("knowledge_points")
        ),
        "key_points": _normalize_text_list(structured.get("key_points")),
        "difficult_points": _normalize_text_list(structured.get("difficult_points")),
        "student_profile": {
            "grade": str(structured.get("student_profile", {}).get("grade") or "").strip(),
            "foundation": str(structured.get("student_profile", {}).get("foundation") or "").strip(),
            "learning_preference": str(structured.get("student_profile", {}).get("learning_preference") or "").strip(),
        },
        "style": {
            "teaching_style": str(structured.get("style", {}).get("teaching_style") or clarified.get("style") or "").strip(),
            "interaction_level": str(structured.get("style", {}).get("interaction_level") or "").strip(),
            "output_preference": str(structured.get("style", {}).get("output_preference") or "").strip(),
        },
        "output_targets": _normalize_text_list(clarified.get("output_targets")),
    }

def _build_temp_source_note(source: Dict[str, Any]) -> Dict[str, Any]:
    """Build normalized source note from processed temporary source."""
    kind = str(source.get("kind") or "document").strip() or "document"
    mapping = source.get("mapping") if isinstance(source.get("mapping"), dict) else {}
    source_title = str(mapping.get("file_name") or source.get("title") or "未命名资料").strip()
    usage = str(mapping.get("usage") or "content").strip() or "content"
    knowledge_point = str(mapping.get("knowledge_point") or "").strip()
    required = bool(mapping.get("is_required"))
    summary = _trim_text(source.get("summary"), 320)
    raw_text = _trim_text(source.get("raw_text"), 240)
    chunks = source.get("chunks") if isinstance(source.get("chunks"), list) else []
    assets = source.get("assets") if isinstance(source.get("assets"), dict) else {}

    snippets: List[str] = []
    if kind == "document":
        for item in chunks[:3]:
            if not isinstance(item, dict):
                continue
            snippet = _trim_text(item.get("text") or item.get("summary"), 220)
            if snippet:
                snippets.append(snippet)
    elif kind == "ppt":
        for item in chunks[:3]:
            if not isinstance(item, dict):
                continue
            slide_index = item.get("slide_index")
            title = str(item.get("title") or "").strip()
            slide_label = f"第{slide_index}页" if slide_index else "幻灯片"
            snippet = _trim_text(item.get("text") or item.get("summary"), 200)
            if snippet:
                snippets.append(f"{slide_label} {title}".strip() + f": {snippet}")
    elif kind == "image":
        if raw_text:
            snippets.append(raw_text)
        tags = assets.get("tags") if isinstance(assets.get("tags"), list) else []
        if tags:
            snippets.append(f"标签: {', '.join([str(tag).strip() for tag in tags if str(tag).strip()])}")
    elif kind == "video":
        ranked_chunks = [
            item for item in chunks
            if isinstance(item, dict)
        ]
        ranked_chunks.sort(key=lambda item: float(item.get("importance_score", 0) or 0), reverse=True)
        for item in ranked_chunks[:3]:
            start_label = _format_ms(item.get("start_ms"))
            end_label = _format_ms(item.get("end_ms"))
            snippet = _trim_text(item.get("summary") or item.get("text"), 180)
            if snippet:
                snippets.append(f"{start_label}-{end_label}: {snippet}")
        keyframes = assets.get("keyframes") if isinstance(assets.get("keyframes"), list) else []
        for frame in keyframes[:2]:
            if not isinstance(frame, dict):
                continue
            frame_summary = _trim_text(frame.get("summary") or frame.get("ocr_text"), 160)
            if frame_summary:
                snippets.append(f"关键帧 {_format_ms(frame.get('timestamp_ms'))}: {frame_summary}")

    if not snippets and summary:
        snippets.append(summary)

    return {
        "source_kind": kind,
        "source_title": source_title,
        "usage": usage,
        "knowledge_point": knowledge_point,
        "required": required,
        "note": summary or raw_text,
        "snippets": _dedupe_non_empty_str_list(snippets),
    }

def _build_knowledge_source_notes(retrieved_docs: List[Any]) -> List[Dict[str, Any]]:
    """Build deterministic knowledge-base source notes from retrieved docs."""
    notes_by_source: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for doc in retrieved_docs:
        metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
        source_url = str(metadata.get("source") or metadata.get("file_path") or "").strip()
        if not source_url:
            continue
        if source_url not in notes_by_source:
            source_title = str(metadata.get("title") or os.path.basename(source_url) or source_url).strip()
            notes_by_source[source_url] = {
                "source_kind": "knowledge_base",
                "source_title": source_title,
                "usage": "content",
                "knowledge_point": str(metadata.get("knowledge_point") or "").strip(),
                "required": False,
                "note": "",
                "snippets": [],
                "_purpose": str(metadata.get("purpose") or "general").strip() or "general",
                "_url": source_url,
            }
            order.append(source_url)

        note = notes_by_source[source_url]
        snippet = _trim_text(getattr(doc, "page_content", ""), 220)
        if snippet and len(note["snippets"]) < 3:
            note["snippets"].append(snippet)
        if not note["note"]:
            note["note"] = _trim_text(getattr(doc, "page_content", ""), 320)
        if not note["knowledge_point"]:
            note["knowledge_point"] = str(metadata.get("knowledge_point") or "").strip()
        if note["_purpose"] != "lesson_plan" and str(metadata.get("purpose") or "").strip() == "lesson_plan":
            note["_purpose"] = "lesson_plan"

    result: List[Dict[str, Any]] = []
    for source_url in order[:6]:
        note = notes_by_source[source_url]
        result.append({
            "source_kind": note["source_kind"],
            "source_title": note["source_title"],
            "usage": note["usage"],
            "knowledge_point": note["knowledge_point"],
            "required": note["required"],
            "note": note["note"],
            "snippets": _dedupe_non_empty_str_list(note["snippets"]),
        })
    return result

def _normalize_source_note_list(raw_value: Any, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize source notes while preserving fallback notes when output is unusable."""
    if not isinstance(raw_value, list):
        raw_value = []

    normalized: List[Dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "source_kind": str(item.get("source_kind") or "document").strip() or "document",
            "source_title": str(item.get("source_title") or "").strip(),
            "usage": str(item.get("usage") or "content").strip() or "content",
            "knowledge_point": str(item.get("knowledge_point") or "").strip(),
            "required": bool(item.get("required")),
            "note": str(item.get("note") or "").strip(),
            "snippets": _normalize_text_list(item.get("snippets")),
        })

    return normalized or fallback

def _match_docx_section_title(title: Any) -> Optional[str]:
    normalized = str(title or "").strip()
    if not normalized:
        return None

    for rule in DOCX_SECTION_RULES:
        if normalized == rule["title"]:
            return rule["title"]

    for rule in DOCX_SECTION_RULES:
        if any(keyword in normalized for keyword in rule["keywords"]):
            return rule["title"]
    return None

def _build_default_docx_sections(
    requirement_summary: Dict[str, Any],
    ppt_outline: List[Dict[str, Any]],
    game_plan: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    topic = str(
        requirement_summary.get("topic")
        or requirement_summary.get("chapter_title")
        or requirement_summary.get("grade_subject")
        or "本课主题"
    ).strip()
    teaching_goals = _normalize_text_list(requirement_summary.get("teaching_goals"))
    knowledge_points = _normalize_text_list(requirement_summary.get("knowledge_points"))
    key_points = _normalize_text_list(requirement_summary.get("key_points"))
    difficult_points = _normalize_text_list(requirement_summary.get("difficult_points"))
    student_profile = requirement_summary.get("student_profile") if isinstance(requirement_summary.get("student_profile"), dict) else {}
    style = requirement_summary.get("style") if isinstance(requirement_summary.get("style"), dict) else {}

    ppt_steps: List[str] = []
    for index, item in enumerate(ppt_outline[:4]):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip() or f"教学环节 {index + 1}"
        goal = str(item.get("goal") or "").strip()
        bullets = _normalize_text_list(item.get("bullets"))
        detail = goal or (bullets[0] if bullets else "围绕核心知识组织讲授与互动")
        ppt_steps.append(f"{title}：{detail}")

    game_steps = _normalize_text_list(game_plan.get("steps"))
    game_materials = _normalize_text_list(game_plan.get("materials"))
    source_titles = _dedupe_non_empty_str_list([
        str(item.get("source_title") or "").strip()
        for item in source_notes[:4]
        if isinstance(item, dict)
    ])

    sections: Dict[str, Dict[str, Any]] = {
        "教学目标": {
            "section_goal": "明确本课的知识、能力与素养目标",
            "bullets": teaching_goals or [
                f"知识与技能：围绕“{topic}”完成核心概念、关键术语与基本规律的建构。",
                "过程与方法：通过示例讲解、问题拆解和课堂练习形成分析路径。",
                "情感态度与价值观：引导学生建立主动探究、规范表达与迁移应用意识。",
                "能够结合课堂任务复述本课核心内容，并完成基础层面的当堂应用。",
            ],
            "source_refs": source_titles[:2],
        },
        "学情分析": {
            "section_goal": "分析学生基础、认知特点与学习偏好",
            "bullets": _dedupe_non_empty_str_list([
                f"学习对象：{str(student_profile.get('grade') or requirement_summary.get('grade_subject') or '待补充').strip()}",
                f"基础情况：{str(student_profile.get('foundation') or '基础水平待进一步确认').strip()}",
                f"学习偏好：{str(student_profile.get('learning_preference') or style.get('teaching_style') or '建议采用讲练结合与适度互动').strip()}",
                "可能误区：容易停留在表层记忆，缺少对概念之间联系和应用场景的系统理解。",
                "支持策略：通过分层提问、案例类比、板书结构化提示帮助学生逐步建立认知框架。",
            ]),
            "source_refs": source_titles[:1],
        },
        "教学重点难点": {
            "section_goal": "聚焦本课重点与难点，明确突破策略",
            "bullets": _dedupe_non_empty_str_list(
                [f"教学重点：{item}" for item in key_points]
                + [f"教学难点：{item}" for item in difficult_points]
                + ["突破策略：借助典型案例、对比讲解和板书框架帮助学生形成整体认识。"] 
                + ["评价关注：重点观察学生能否用自己的语言解释核心概念并完成简单迁移。"] 
            ) or [
                f"教学重点：围绕“{topic}”梳理关键知识点、核心关系与典型应用场景。",
                "教学难点：帮助学生把抽象概念转化为可理解、可表达、可应用的知识结构。",
                "突破策略：通过典型案例、对比分析和分层练习逐步突破理解难点。",
                "评价关注：根据课堂回应和练习结果判断学生对重点难点的真实掌握情况。",
            ],
            "source_refs": source_titles[:2],
        },
        "教学流程": {
            "section_goal": "组织课堂教学环节与时间推进",
            "bullets": ppt_steps or [
                "导入与目标说明（约5分钟）：通过生活化问题或案例激活旧知，明确本课主题、学习目标与评价任务。",
                f"核心讲解与示例分析（约15分钟）：围绕“{topic}”展开关键概念讲解，结合示例帮助学生建立整体框架。",
                "师生互动与追问（约8分钟）：通过层层追问、同伴讨论或举例说明，检查学生对核心概念的理解深度。",
                "当堂练习与反馈（约10分钟）：安排基础练习或小任务，教师依据学生表现进行即时纠偏和点拨。",
                "课堂总结与迁移（约5分钟）：回顾知识主线、方法要点和易错点，连接后续学习任务。",
            ],
            "source_refs": source_titles[:3],
        },
        "课堂活动": {
            "section_goal": "设计可执行的互动任务与实践活动",
            "bullets": _dedupe_non_empty_str_list(
                ([f"活动目标：{str(game_plan.get('objective') or '').strip()}"] if str(game_plan.get("objective") or "").strip() else [])
                + ([f"活动机制：{str(game_plan.get('mechanic') or '').strip()}"] if str(game_plan.get("mechanic") or "").strip() else [])
                + game_steps
                + ([f"活动材料：{'、'.join(game_materials)}"] if game_materials else [])
                + ["组织方式：可采用个人思考 + 同伴交流 + 全班反馈的方式，提高参与度。"] 
                + ["反馈方式：通过口头展示、板演记录或即时点评帮助学生修正理解。"] 
            ) or [
                "设置分组讨论或课堂问答，围绕重点知识进行即时反馈与思路比较。",
                "安排一项迁移应用任务，要求学生说明解题思路、依据和结论。",
                "教师根据学生回答进行追问与点拨，帮助学生暴露误区并完成修正。",
                "活动产出可以是口头表达、板演结果、结构图或任务单记录。",
            ],
            "source_refs": _normalize_source_refs(game_plan.get("source_refs")) or source_titles[:2],
        },
        "作业布置": {
            "section_goal": "安排课后巩固、迁移与拓展任务",
            "bullets": [
                f"基础巩固：完成围绕“{topic}”的课后练习，梳理课堂核心概念与关键术语。",
                "迁移应用：结合课堂重点难点完成一项案例分析、情境解释或综合应用任务。",
                "反思整理：记录课堂中最易混淆的知识点和自己的理解障碍，形成错因清单。",
                "预习准备：围绕下一课主题提出1-2个问题，带着问题进入后续学习。",
            ],
            "source_refs": source_titles[:1],
        },
        "板书建议": {
            "section_goal": "沉淀课堂核心结构与板书呈现方式",
            "bullets": _dedupe_non_empty_str_list(
                [f"板书主线：{topic}"]
                + [f"板书关键词：{item}" for item in knowledge_points[:4]]
                + ["板书结构：建议按“主题导入 - 核心概念 - 关键方法 - 典型示例 - 课堂总结”分区呈现"]
                + ["呈现重点：用箭头、层级缩进或编号标清概念之间关系，帮助学生形成结构化理解"]
            ),
            "source_refs": [],
        },
        "教学反思": {
            "section_goal": "复盘教学效果并为后续优化提供依据",
            "bullets": [
                "记录学生对重点与难点的掌握情况，尤其关注课堂回应中暴露出的共性误区。",
                "复盘课堂活动参与度、时间分配、提问层次和互动效果，评估设计是否贴合学情。",
                "根据课堂练习和课后作业反馈调整后续讲解节奏、例题难度和练习层次。",
                "反思本节课中最有效的教学支架和最需要优化的环节，为下次备课提供依据。",
            ],
            "source_refs": [],
        },
    }

    for rule in DOCX_SECTION_RULES:
        title = rule["title"]
        section = sections.get(title, {})
        section["section_title"] = title
        section["section_goal"] = str(section.get("section_goal") or rule["goal"]).strip()
        section["bullets"] = _dedupe_non_empty_str_list(_normalize_text_list(section.get("bullets")))
        section["source_refs"] = _normalize_source_refs(section.get("source_refs"))
        sections[title] = section

    return sections


def _expand_docx_bullet_text(section_title: str, bullet: str, topic: str, section_goal: str) -> str:
    text = str(bullet or "").strip().lstrip("•").strip()
    if not text:
        return ""
    if len(text) >= 42:
        return text

    suffix_map = {
        "教学目标": f"建议在课堂中结合“{topic}”设计可观察的达成标准，并通过提问或练习及时确认学生是否真正掌握。",
        "学情分析": "教师可根据学生已有经验与常见误区调整讲解节奏，必要时加入类比说明和分层支持。",
        "教学重点难点": "课堂实施时需要配合案例拆解和即时反馈，帮助学生把抽象内容转成可理解的学习任务。",
        "教学流程": "建议同步明确该环节的时间安排、师生活动和预期产出，避免流程只有标题没有执行细节。",
        "课堂活动": "可进一步补充分组方式、任务要求、展示形式和评价标准，保证活动落地而不是停留在口头设计。",
        "作业布置": "作业设计应兼顾基础巩固与迁移应用，并提示学生如何复盘课堂中的关键知识点。",
        "板书建议": "板书时建议突出关键词之间的关系与层次，帮助学生课后回看时仍能快速抓住主线。",
        "教学反思": "建议课后结合学生表现和作业反馈记录可优化点，为下一次授课提供明确修订依据。",
    }
    suffix = suffix_map.get(section_title) or f"建议围绕“{topic}”进一步补充课堂执行细节，使内容更贴近{section_goal or '教学实施'}。"
    return f"{text}，{suffix}"


def _enrich_docx_outline_detail(
    sections: Dict[str, Dict[str, Any]],
    requirement_summary: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    topic = str(
        requirement_summary.get("topic")
        or requirement_summary.get("chapter_title")
        or requirement_summary.get("grade_subject")
        or "本课主题"
    ).strip()
    for title, section in sections.items():
        bullets = _normalize_text_list(section.get("bullets"))
        section_goal = str(section.get("section_goal") or "").strip()
        enriched = [
            _expand_docx_bullet_text(title, bullet, topic, section_goal)
            for bullet in bullets
            if str(bullet or "").strip()
        ]
        section["bullets"] = _dedupe_non_empty_str_list(enriched)
    return sections

def _normalize_docx_outline(
    raw_outline: Any,
    requirement_summary: Dict[str, Any],
    ppt_outline: List[Dict[str, Any]],
    game_plan: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    sections = _build_default_docx_sections(
        requirement_summary=requirement_summary,
        ppt_outline=ppt_outline,
        game_plan=game_plan,
        source_notes=source_notes,
    )
    unmatched_bullets: List[str] = []
    unmatched_refs: List[str] = []

    for item in raw_outline if isinstance(raw_outline, list) else []:
        if not isinstance(item, dict):
            continue
        matched_title = _match_docx_section_title(item.get("section_title"))
        incoming_goal = str(item.get("section_goal") or "").strip()
        incoming_bullets = _normalize_text_list(item.get("bullets"))
        incoming_refs = _normalize_source_refs(item.get("source_refs"))
        if matched_title and matched_title in sections:
            section = sections[matched_title]
            if incoming_goal:
                section["section_goal"] = incoming_goal
            section["bullets"] = _dedupe_non_empty_str_list(section.get("bullets", []) + incoming_bullets)
            section["source_refs"] = _dedupe_non_empty_str_list(section.get("source_refs", []) + incoming_refs)
            continue

        title_text = str(item.get("section_title") or "").strip()
        if title_text:
            unmatched_bullets.append(title_text)
        unmatched_bullets.extend(incoming_bullets)
        unmatched_refs.extend(incoming_refs)

    if unmatched_bullets:
        sections["教学流程"]["bullets"] = _dedupe_non_empty_str_list(
            sections["教学流程"].get("bullets", []) + unmatched_bullets
        )
    if unmatched_refs:
        sections["教学流程"]["source_refs"] = _dedupe_non_empty_str_list(
            sections["教学流程"].get("source_refs", []) + unmatched_refs
        )

    sections = _enrich_docx_outline_detail(sections, requirement_summary)

    return [
        {
            "section_title": rule["title"],
            "section_goal": sections[rule["title"]]["section_goal"],
            "bullets": sections[rule["title"]]["bullets"],
            "source_refs": sections[rule["title"]]["source_refs"],
        }
        for rule in DOCX_SECTION_RULES
    ]

def _normalize_lesson_plan_spec(
    raw_spec: Any,
    requirement_summary_fallback: Dict[str, Any],
    source_notes_fallback: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Normalize lesson_plan_spec schema and fill required sections."""
    spec = raw_spec if isinstance(raw_spec, dict) else {}
    raw_requirement = spec.get("requirement_summary") if isinstance(spec.get("requirement_summary"), dict) else {}
    fallback_student_profile = requirement_summary_fallback.get("student_profile", {})
    fallback_style = requirement_summary_fallback.get("style", {})

    requirement_summary = {
        "topic": str(raw_requirement.get("topic") or requirement_summary_fallback.get("topic") or "").strip(),
        "grade_subject": str(raw_requirement.get("grade_subject") or requirement_summary_fallback.get("grade_subject") or "").strip(),
        "outline_type": str(raw_requirement.get("outline_type") or requirement_summary_fallback.get("outline_type") or "").strip(),
        "chapter_title": str(raw_requirement.get("chapter_title") or requirement_summary_fallback.get("chapter_title") or "").strip(),
        "duration": str(raw_requirement.get("duration") or requirement_summary_fallback.get("duration") or "").strip(),
        "teaching_goals": _normalize_text_list(raw_requirement.get("teaching_goals") or requirement_summary_fallback.get("teaching_goals")),
        "knowledge_points": _normalize_text_list(raw_requirement.get("knowledge_points") or requirement_summary_fallback.get("knowledge_points")),
        "key_points": _normalize_text_list(raw_requirement.get("key_points") or requirement_summary_fallback.get("key_points")),
        "difficult_points": _normalize_text_list(raw_requirement.get("difficult_points") or requirement_summary_fallback.get("difficult_points")),
        "student_profile": {
            "grade": str(
                (raw_requirement.get("student_profile") if isinstance(raw_requirement.get("student_profile"), dict) else {}).get("grade")
                or fallback_student_profile.get("grade")
                or ""
            ).strip(),
            "foundation": str(
                (raw_requirement.get("student_profile") if isinstance(raw_requirement.get("student_profile"), dict) else {}).get("foundation")
                or fallback_student_profile.get("foundation")
                or ""
            ).strip(),
            "learning_preference": str(
                (raw_requirement.get("student_profile") if isinstance(raw_requirement.get("student_profile"), dict) else {}).get("learning_preference")
                or fallback_student_profile.get("learning_preference")
                or ""
            ).strip(),
        },
        "style": {
            "teaching_style": str(
                (raw_requirement.get("style") if isinstance(raw_requirement.get("style"), dict) else {}).get("teaching_style")
                or fallback_style.get("teaching_style")
                or ""
            ).strip(),
            "interaction_level": str(
                (raw_requirement.get("style") if isinstance(raw_requirement.get("style"), dict) else {}).get("interaction_level")
                or fallback_style.get("interaction_level")
                or ""
            ).strip(),
            "output_preference": str(
                (raw_requirement.get("style") if isinstance(raw_requirement.get("style"), dict) else {}).get("output_preference")
                or fallback_style.get("output_preference")
                or ""
            ).strip(),
        },
        "output_targets": _normalize_text_list(raw_requirement.get("output_targets") or requirement_summary_fallback.get("output_targets")),
    }

    ppt_outline: List[Dict[str, Any]] = []
    for item in spec.get("ppt_outline", []) if isinstance(spec.get("ppt_outline"), list) else []:
        if not isinstance(item, dict):
            continue
        ppt_outline.append({
            "slide_type": str(item.get("slide_type") or "").strip(),
            "title": str(item.get("title") or "").strip(),
            "goal": str(item.get("goal") or "").strip(),
            "bullets": _normalize_text_list(item.get("bullets")),
            "visual_suggestion": str(item.get("visual_suggestion") or "").strip(),
            "source_refs": _normalize_source_refs(item.get("source_refs")),
        })

    normalized_source_notes = _normalize_source_note_list(spec.get("source_notes"), source_notes_fallback)
    raw_game_plan = spec.get("game_plan") if isinstance(spec.get("game_plan"), dict) else {}
    game_plan = _normalize_game_plan(
        raw_game_plan=raw_game_plan,
        requirement_summary=requirement_summary,
        source_notes=normalized_source_notes,
    )
    docx_outline = _normalize_docx_outline(
        raw_outline=spec.get("docx_outline"),
        requirement_summary=requirement_summary,
        ppt_outline=ppt_outline,
        game_plan=game_plan,
        source_notes=normalized_source_notes,
    )

    return {
        "requirement_summary": requirement_summary,
        "source_notes": normalized_source_notes,
        "ppt_outline": ppt_outline,
        "docx_outline": docx_outline,
        "game_plan": game_plan,
    }

def _normalize_lesson_plan_sources(raw_sources: Any) -> List[Dict[str, Any]]:
    normalized_sources: List[Dict[str, Any]] = []
    if not isinstance(raw_sources, list):
        return normalized_sources

    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        title = str(item.get('title') or '').strip()
        url = str(item.get('url') or '').strip()
        purpose = str(item.get('purpose') or '').strip()
        mapping_raw = item.get('mapping') if isinstance(item.get('mapping'), dict) else {}
        mapping: Optional[Dict[str, Any]] = None
        if mapping_raw:
            mapping = {
                'usage': str(mapping_raw.get('usage') or '').strip(),
                'knowledge_point': str(mapping_raw.get('knowledge_point') or '').strip(),
                'is_required': bool(mapping_raw.get('is_required')),
            }
        if not title and not url:
            continue
        normalized_sources.append({
            'title': title or url or '未命名资料',
            'url': url,
            'purpose': purpose or None,
            'mapping': mapping,
        })
    return normalized_sources

def _normalize_revision_meta(
    raw_meta: Any,
    fallback_version_index: int,
    fallback_created_at: Optional[int] = None,
) -> Dict[str, Any]:
    meta = raw_meta if isinstance(raw_meta, dict) else {}

    try:
        version_index = int(meta.get('version_index', fallback_version_index))
    except Exception:
        version_index = fallback_version_index
    if version_index < 1:
        version_index = fallback_version_index

    based_on_raw = meta.get('based_on_version_index')
    try:
        based_on_version_index = int(based_on_raw) if based_on_raw is not None else None
    except Exception:
        based_on_version_index = None
    if based_on_version_index is not None and based_on_version_index < 1:
        based_on_version_index = None

    try:
        created_at = int(meta.get('created_at', fallback_created_at or int(time.time())))
    except Exception:
        created_at = fallback_created_at or int(time.time())

    revision_request = str(meta.get('revision_request') or '').strip()
    if not revision_request:
        revision_request = '初始生成' if version_index == 1 else '版本修订'

    return {
        'version_index': version_index,
        'based_on_version_index': based_on_version_index,
        'revision_request': revision_request,
        'created_at': created_at,
    }

def _build_lesson_plan_payload(
    normalized_spec: Dict[str, Any],
    sources: List[Dict[str, Any]],
    revision_meta: Optional[Dict[str, Any]] = None,
    core_spec: Optional[Dict[str, Any]] = None,
    outline_generation_meta: Optional[Dict[str, Any]] = None,
    source_evidence_meta: Optional[Dict[str, Any]] = None,
    generated_assets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        'format': 'lesson_plan_spec_v1',
        'lesson_plan_spec': normalized_spec,
        'sources': _normalize_lesson_plan_sources(sources),
    }
    if revision_meta:
        payload['revision_meta'] = revision_meta
    if isinstance(core_spec, dict) and core_spec:
        payload['core_spec'] = core_spec
    if isinstance(outline_generation_meta, dict) and outline_generation_meta:
        payload['outline_generation_meta'] = outline_generation_meta
    if isinstance(source_evidence_meta, dict) and source_evidence_meta:
        payload['source_evidence_meta'] = source_evidence_meta
    normalized_assets = _normalize_generated_assets(generated_assets)
    if normalized_assets:
        payload['generated_assets'] = normalized_assets
    return payload

def _normalize_generated_assets(raw_assets: Any) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    if not isinstance(raw_assets, dict):
        return normalized
    for key in ('word', 'ppt', 'game'):
        raw_value = raw_assets.get(key)
        try:
            material_id = int(raw_value)
        except (TypeError, ValueError):
            continue
        if material_id > 0:
            normalized[key] = material_id
    return normalized

def _parse_lesson_plan_payload_message(
    content: Any,
    fallback_version_index: int = 1,
    fallback_created_at: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(str(content or ''))
    except Exception:
        return None

    if parsed.get('format') != 'lesson_plan_spec_v1' or not isinstance(parsed.get('lesson_plan_spec'), dict):
        return None

    normalized_spec = _normalize_lesson_plan_spec(
        raw_spec=parsed.get('lesson_plan_spec'),
        requirement_summary_fallback=parsed.get('lesson_plan_spec', {}).get('requirement_summary', {}),
        source_notes_fallback=parsed.get('lesson_plan_spec', {}).get('source_notes', []),
    )
    normalized_sources = _normalize_lesson_plan_sources(parsed.get('sources'))
    revision_meta = _normalize_revision_meta(
        raw_meta=parsed.get('revision_meta'),
        fallback_version_index=fallback_version_index,
        fallback_created_at=fallback_created_at,
    )
    generated_assets = _normalize_generated_assets(parsed.get('generated_assets'))
    core_spec = parsed.get('core_spec') if isinstance(parsed.get('core_spec'), dict) else None
    outline_generation_meta = parsed.get('outline_generation_meta') if isinstance(parsed.get('outline_generation_meta'), dict) else None
    source_evidence_meta = parsed.get('source_evidence_meta') if isinstance(parsed.get('source_evidence_meta'), dict) else None
    return {
        'format': 'lesson_plan_spec_v1',
        'lesson_plan_spec': normalized_spec,
        'sources': normalized_sources,
        'revision_meta': revision_meta,
        'generated_assets': generated_assets,
        'core_spec': core_spec,
        'outline_generation_meta': outline_generation_meta,
        'source_evidence_meta': source_evidence_meta,
    }

def _extract_lesson_plan_versions_from_history(chat_history: List[ChatHistory]) -> List[Dict[str, Any]]:
    versions: List[Dict[str, Any]] = []
    next_version_index = 1
    for chat in chat_history:
        if getattr(chat, 'role', None) != 'assistant':
            continue
        payload = _parse_lesson_plan_payload_message(
            content=getattr(chat, 'message', ''),
            fallback_version_index=next_version_index,
            fallback_created_at=getattr(chat, 'timestamp', None),
        )
        if not payload:
            continue
        payload['timestamp'] = getattr(chat, 'timestamp', None)
        versions.append(payload)
        next_version_index = max(next_version_index + 1, payload['revision_meta']['version_index'] + 1)

    versions.sort(key=lambda item: item.get('revision_meta', {}).get('version_index', 0))
    return versions

def _material_relative_path_to_abs(path_value: Any) -> Optional[str]:
    normalized = normalize_relative_upload_path(path_value)
    if not normalized:
        return None
    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/"):]
    upload_root = str(current_app.config.get('UPLOAD_FOLDER') or '').strip()
    if not upload_root:
        return None
    absolute_path = os.path.normpath(os.path.join(upload_root, normalized))
    upload_root_abs = os.path.abspath(upload_root)
    if os.path.commonpath([upload_root_abs, os.path.abspath(absolute_path)]) != upload_root_abs:
        return None
    return absolute_path

def _safe_remove_file(path_value: Any) -> bool:
    absolute_path = _material_relative_path_to_abs(path_value)
    if not absolute_path or not os.path.isfile(absolute_path):
        return False
    try:
        os.remove(absolute_path)
        return True
    except Exception as exc:
        current_app.logger.warning(f"failed to remove file %s: %s", absolute_path, str(exc))
        return False

def _cleanup_material_processed_cache(file_hash: Optional[str]) -> int:
    normalized_hash = str(file_hash or '').strip()
    if not normalized_hash:
        return 0

    upload_root = str(current_app.config.get('UPLOAD_FOLDER') or '').strip()
    if not upload_root:
        return 0

    deleted_count = 0
    patterns = [
        os.path.join(upload_root, 'temp', '*', 'processed', f'{normalized_hash}.json'),
        os.path.join(upload_root, 'temp', '*', 'derived', normalized_hash),
        os.path.join(upload_root, 'temp', '*', 'parser', normalized_hash),
        os.path.join(upload_root, 'temp', '*', 'pdf', normalized_hash),
        os.path.join(upload_root, 'temp', '*', 'ppt', normalized_hash),
        os.path.join(upload_root, 'temp', '*', 'docx', normalized_hash),
        os.path.join(upload_root, 'processed', f'{normalized_hash}.json'),
        os.path.join(upload_root, 'processed_cache', f'{normalized_hash}.json'),
        os.path.join(upload_root, 'processed_cache', f'{normalized_hash}_*.json'),
    ]
    for pattern in patterns:
        for cache_path in glob.glob(pattern):
            try:
                if os.path.isfile(cache_path):
                    os.remove(cache_path)
                    deleted_count += 1
                elif os.path.isdir(cache_path):
                    shutil.rmtree(cache_path)
                    deleted_count += 1
            except Exception as exc:
                current_app.logger.warning(f"failed to remove processed cache %s: %s", cache_path, str(exc))
    return deleted_count

def _normalize_material_storage_path(path_value: Any) -> Optional[str]:
    normalized = normalize_knowledge_file_path(path_value)
    if normalized:
        return normalized
    return normalize_relative_upload_path(path_value)

def _collect_related_queue_items(
    course_id: Any,
    file_hash: Optional[str],
    normalized_paths: List[str],
) -> List[KnowledgeBaseQueue]:
    if course_id is None:
        return []

    target_hash = str(file_hash or '').strip()
    path_set = {path for path in normalized_paths if path}
    related: List[KnowledgeBaseQueue] = []
    seen_ids = set()

    for queue_item in KnowledgeBaseQueue.query.filter_by(course_id=course_id).all():
        queue_hash = str(queue_item.file_hash or '').strip()
        queue_path = _normalize_material_storage_path(queue_item.file_path)
        same_hash = bool(target_hash and queue_hash and queue_hash == target_hash)
        same_path = bool(queue_path and queue_path in path_set)
        if not same_hash and not same_path:
            continue
        if queue_item.id in seen_ids:
            continue
        related.append(queue_item)
        seen_ids.add(queue_item.id)
        if queue_path:
            path_set.add(queue_path)

    return related

def _collect_related_materials(
    course_id: Any,
    file_hash: Optional[str],
    normalized_paths: List[str],
) -> List[Material]:
    if course_id is None:
        return []

    target_hash = str(file_hash or '').strip()
    path_set = {path for path in normalized_paths if path}
    related: List[Material] = []
    seen_ids = set()

    for material in Material.query.filter_by(course_id=course_id).all():
        material_hash = str(material.file_hash or '').strip()
        material_path = _normalize_material_storage_path(material.file_path)
        same_hash = bool(target_hash and material_hash and material_hash == target_hash)
        same_path = bool(material_path and material_path in path_set)
        if not same_hash and not same_path:
            continue
        if material.id in seen_ids:
            continue
        related.append(material)
        seen_ids.add(material.id)
        if material_path:
            path_set.add(material_path)

    return related

def _remove_file_from_vector_indexes(course_id: Any, normalized_path: str) -> int:
    cleaned = 0
    if not normalized_path:
        return cleaned

    try:
        from backend.rag.create_db import remove_document_from_knowledge_base
    except Exception as exc:
        current_app.logger.warning("failed to import vector cleanup helper for %s: %s", normalized_path, str(exc))
        return cleaned

    namespaces = [GLOBAL_KNOWLEDGE_BASE_NAMESPACE]
    if course_id is not None:
        namespaces.append(str(course_id))

    seen_namespaces = set()
    for namespace in namespaces:
        if not namespace or namespace in seen_namespaces:
            continue
        seen_namespaces.add(namespace)
        try:
            if remove_document_from_knowledge_base(namespace, normalized_path):
                cleaned += 1
        except Exception as exc:
            current_app.logger.warning(
                "failed to remove %s from knowledge namespace %s: %s",
                normalized_path,
                namespace,
                str(exc),
            )

    return cleaned

def _purge_knowledge_assets(
    *,
    course_id: Any,
    file_hash: Optional[str],
    normalized_paths: List[str],
) -> Dict[str, Any]:
    path_set = {path for path in normalized_paths if path}
    related_queue_items = _collect_related_queue_items(course_id, file_hash, list(path_set))
    for queue_item in related_queue_items:
        queue_path = _normalize_material_storage_path(queue_item.file_path)
        if queue_path:
            path_set.add(queue_path)

    related_materials = _collect_related_materials(course_id, file_hash, list(path_set))
    for material in related_materials:
        material_path = _normalize_material_storage_path(material.file_path)
        if material_path:
            path_set.add(material_path)

    deleted_queue_ids: List[int] = []
    deleted_material_ids: List[int] = []
    deleted_files = 0
    deleted_cache_files = 0
    vector_cleanup_count = 0

    for normalized_path in sorted(path_set):
        vector_cleanup_count += _remove_file_from_vector_indexes(course_id, normalized_path)

    processed_hashes = set()
    for material in related_materials:
        deleted_files += int(_safe_remove_file(material.file_path))
        deleted_files += int(_safe_remove_file(material.preview_file_path))

        normalized_hash = str(material.file_hash or '').strip()
        if normalized_hash and normalized_hash not in processed_hashes:
            deleted_cache_files += _cleanup_material_processed_cache(normalized_hash)
            processed_hashes.add(normalized_hash)

        db.session.delete(material)
        deleted_material_ids.append(material.id)

    for normalized_path in sorted(path_set):
        deleted_files += int(_safe_remove_file(normalized_path))

    normalized_target_hash = str(file_hash or '').strip()
    if normalized_target_hash and normalized_target_hash not in processed_hashes:
        deleted_cache_files += _cleanup_material_processed_cache(normalized_target_hash)

    for queue_item in related_queue_items:
        db.session.delete(queue_item)
        deleted_queue_ids.append(queue_item.id)

    return {
        'deleted_queue_ids': deleted_queue_ids,
        'deleted_material_ids': deleted_material_ids,
        'deleted_files': deleted_files,
        'deleted_cache_files': deleted_cache_files,
        'vector_cleanup_count': vector_cleanup_count,
    }

def purge_knowledge_assets_for_queue_item(queue_item: KnowledgeBaseQueue) -> Dict[str, Any]:
    normalized_path = _normalize_material_storage_path(getattr(queue_item, 'file_path', None))
    return _purge_knowledge_assets(
        course_id=getattr(queue_item, 'course_id', None),
        file_hash=getattr(queue_item, 'file_hash', None),
        normalized_paths=[normalized_path] if normalized_path else [],
    )

def purge_knowledge_assets_for_material(material: Material) -> Dict[str, Any]:
    normalized_path = _normalize_material_storage_path(getattr(material, 'file_path', None))
    return _purge_knowledge_assets(
        course_id=getattr(material, 'course_id', None),
        file_hash=getattr(material, 'file_hash', None),
        normalized_paths=[normalized_path] if normalized_path else [],
    )


def cleanup_stale_material_and_queue_records(course_id: Optional[Any] = None) -> Dict[str, Any]:
    material_query = Material.query
    queue_query = KnowledgeBaseQueue.query
    if course_id not in (None, ""):
        material_query = material_query.filter_by(course_id=course_id)
        queue_query = queue_query.filter_by(course_id=course_id)

    stale_materials = [
        material for material in material_query.all()
        if material.file_path and not resolve_upload_path(material.file_path)
    ]
    stale_queue_items = [
        queue_item for queue_item in queue_query.all()
        if queue_item.file_path and not resolve_upload_path(queue_item.file_path)
    ]

    deleted_material_ids = set()
    deleted_queue_ids = set()

    for material in stale_materials:
        if material.id in deleted_material_ids:
            continue
        cleanup_summary = purge_knowledge_assets_for_material(material)
        deleted_material_ids.update(cleanup_summary.get("deleted_material_ids", []))
        deleted_queue_ids.update(cleanup_summary.get("deleted_queue_ids", []))

    for queue_item in stale_queue_items:
        if queue_item.id in deleted_queue_ids:
            continue
        cleanup_summary = purge_knowledge_assets_for_queue_item(queue_item)
        deleted_material_ids.update(cleanup_summary.get("deleted_material_ids", []))
        deleted_queue_ids.update(cleanup_summary.get("deleted_queue_ids", []))

    if deleted_material_ids or deleted_queue_ids:
        db.session.commit()

    return {
        "deleted_material_ids": sorted(deleted_material_ids),
        "deleted_queue_ids": sorted(deleted_queue_ids),
    }

def _collect_generated_material_ids_from_payloads(payloads: List[Dict[str, Any]]) -> List[int]:
    material_ids = set()
    for payload in payloads:
        for material_id in _normalize_generated_assets(payload.get('generated_assets')).values():
            material_ids.add(material_id)
    return sorted(material_ids)

def _find_lesson_plan_payload_message(
    conversation_id: str,
    user_id: int,
    version_index: Optional[int] = None,
) -> Optional[Tuple[ChatHistory, Dict[str, Any]]]:
    assistant_messages = ChatHistory.query.filter_by(
        conversation_id=conversation_id,
        user_id=user_id,
        role='assistant',
    ).order_by(ChatHistory.timestamp.desc(), ChatHistory.id.desc()).all()

    fallback_match: Optional[Tuple[ChatHistory, Dict[str, Any]]] = None
    for chat in assistant_messages:
        payload = _parse_lesson_plan_payload_message(
            content=getattr(chat, 'message', ''),
            fallback_created_at=getattr(chat, 'timestamp', None),
        )
        if not payload:
            continue
        if fallback_match is None:
            fallback_match = (chat, payload)
        if version_index is None or payload.get('revision_meta', {}).get('version_index') == version_index:
            return chat, payload
    return fallback_match

def _link_generated_material_to_conversation(
    conversation_id: Optional[str],
    user_id: int,
    asset_key: str,
    material_id: int,
    version_index: Optional[int] = None,
) -> bool:
    normalized_conversation_id = str(conversation_id or '').strip()
    if asset_key not in {'word', 'ppt', 'game'} or not normalized_conversation_id:
        return False

    payload_message = _find_lesson_plan_payload_message(
        conversation_id=normalized_conversation_id,
        user_id=user_id,
        version_index=version_index,
    )
    if not payload_message:
        return False

    chat_message, payload = payload_message
    generated_assets = _normalize_generated_assets(payload.get('generated_assets'))
    generated_assets[asset_key] = int(material_id)
    payload['generated_assets'] = generated_assets
    chat_message.message = json.dumps(payload, ensure_ascii=False)
    db.session.flush()
    return True

def _infer_outline_type_from_conversation(
    first_user_message: Optional[ChatHistory],
    versions: List[Dict[str, Any]],
) -> str:
    if versions:
        latest_requirement = versions[-1].get('lesson_plan_spec', {}).get('requirement_summary', {})
        outline_type = str(latest_requirement.get('outline_type') or '').strip()
        if outline_type in {'course', 'class'}:
            return outline_type

    first_message_text = str(getattr(first_user_message, 'message', '') or '')
    if '课程总纲' in first_message_text:
        return 'course'
    if '课堂教案' in first_message_text:
        return 'class'
    return 'course'


def _parse_grade_subject_parts(grade_subject: Any) -> Dict[str, str]:
    normalized = str(grade_subject or '').strip()
    if not normalized:
        return {'stage': '', 'grade': '', 'subject': ''}
    parts = [part.strip() for part in re.split(r'[/|｜]+', normalized) if str(part).strip()]
    if len(parts) >= 3:
        return {'stage': parts[0], 'grade': parts[1], 'subject': parts[2]}
    if len(parts) == 2:
        return {'stage': '', 'grade': parts[0], 'subject': parts[1]}
    return {'stage': '', 'grade': '', 'subject': parts[0]}


def _build_history_display_title(
    requirement_summary: Dict[str, Any],
    last_time: Optional[int],
    fallback_title: str,
) -> str:
    summary = requirement_summary if isinstance(requirement_summary, dict) else {}
    grade_parts = _parse_grade_subject_parts(summary.get('grade_subject'))
    subject = grade_parts.get('subject') or ''
    grade = grade_parts.get('grade') or str(
        (summary.get('student_profile') or {}).get('grade') if isinstance(summary.get('student_profile'), dict) else ''
    ).strip()
    chapter_title = str(summary.get('chapter_title') or summary.get('topic') or fallback_title or '').strip()
    time_label = ''
    try:
        if last_time:
            time_label = time.strftime('%y/%m/%d %H.%M', time.localtime(int(last_time)))
    except Exception:
        time_label = ''
    title_parts = [part for part in [subject, grade, chapter_title, time_label] if part]
    return ' '.join(title_parts) if title_parts else fallback_title

def _build_fallback_game_pack(
    normalized_spec: Dict[str, Any],
    requested_theme: Optional[str] = None,
) -> Dict[str, Any]:
    requirement = normalized_spec.get("requirement_summary") if isinstance(normalized_spec.get("requirement_summary"), dict) else {}
    game_plan = normalized_spec.get("game_plan") if isinstance(normalized_spec.get("game_plan"), dict) else {}
    topic = str(requirement.get("topic") or requirement.get("chapter_title") or requirement.get("grade_subject") or "当前主题").strip()
    stage_items = game_plan.get("stages") if isinstance(game_plan.get("stages"), list) else []
    summary_rules = {
        "weak_point_rules": [
            "统计错误最多的知识标签，归纳为本次薄弱点",
            "如果出现重复错误，优先提示回看对应课件页或知识点讲解",
        ],
        "encouragement_copy": [
            "先保住基础题正确率，再逐步提高应用题稳定性。",
            "闯关时保持节奏，连续答对能快速拉高总体表现。",
        ],
        "retry_suggestion_copy": [
            "重试前先回看错题对应讲解页，再重新挑战本关。",
            "优先复习错误最多的知识标签，再做一轮巩固练习。",
        ],
    }

    stages: List[Dict[str, Any]] = []
    question_seed = 1
    for stage_index, stage in enumerate(stage_items):
        if not isinstance(stage, dict):
            continue
        knowledge_tags = _normalize_text_list(stage.get("knowledge_tags")) or [topic]
        review_refs = _normalize_source_refs(stage.get("review_refs")) or ["对应知识点讲解页"]
        question_count = stage.get("question_count", 2)
        try:
            question_count = max(int(question_count), 1)
        except Exception:
            question_count = 2

        questions: List[Dict[str, Any]] = []
        interactive_types = ["matching", "ordering", "error_spotting"]
        for question_index in range(question_count):
            tag = knowledge_tags[question_index % len(knowledge_tags)]
            question_type = interactive_types[question_index % len(interactive_types)]
            base_question = {
                "id": f"q_{question_seed}",
                "stage_id": str(stage.get("id") or f"stage_{stage_index + 1}"),
                "type": question_type,
                "stem": f"围绕“{tag}”完成本题交互任务。",
                "answer": [],
                "score": int(game_plan.get("score_rule", {}).get("base_score", 10) or 10),
                "knowledge_tag": tag,
                "correct_feedback": f"你抓住了“{tag}”的关键要点。",
                "wrong_feedback": f"建议先回看“{tag}”相关讲解再作答。",
                "review_ref": review_refs[question_index % len(review_refs)],
            }
            questions.append(
                _apply_interactive_question_payload(
                    base_question,
                    stage=stage,
                    question_type=question_type,
                )
            )
            question_seed += 1

        pass_rule = stage.get("pass_rule") if isinstance(stage.get("pass_rule"), dict) else {}
        stages.append({
            "id": str(stage.get("id") or f"stage_{stage_index + 1}"),
            "title": str(stage.get("name") or f"第{stage_index + 1}关").strip() or f"第{stage_index + 1}关",
            "goal": str(stage.get("goal") or "完成本关练习").strip() or "完成本关练习",
            "knowledge_tags": knowledge_tags,
            "pass_rule": {
                "min_correct": int(pass_rule.get("min_correct", max(1, len(questions) - 1)) or max(1, len(questions) - 1)),
                "description": str(pass_rule.get("description") or f"至少答对 {max(1, len(questions) - 1)} 题").strip(),
            },
            "questions": questions,
        })

    theme_name = str(requested_theme or game_plan.get("theme") or "clean").strip().lower() or "clean"
    return {
        "meta": {
            "title": str(game_plan.get("title") or f"{topic}轻量闯关").strip() or f"{topic}轻量闯关",
            "topic": topic,
            "grade_subject": str(requirement.get("grade_subject") or "").strip(),
            "duration": str(requirement.get("duration") or "").strip(),
            "generated_at": int(time.time()),
        },
        "theme_config": _default_game_theme(theme_name),
        "score_rule": game_plan.get("score_rule") if isinstance(game_plan.get("score_rule"), dict) else _build_default_game_plan(requirement, normalized_spec.get("source_notes", [])).get("score_rule"),
        "render_config": {
            "show_timer": False,
            "show_combo": True,
            "show_progress": True,
            "allow_retry_stage": True,
        },
        "summary_rules": summary_rules,
        "stages": stages,
    }


def _build_default_matching_pairs(stage: Dict[str, Any]) -> List[Dict[str, str]]:
    tags = _normalize_text_list(stage.get("knowledge_tags"))
    pairs: List[Dict[str, str]] = []
    for index, tag in enumerate(tags[:3]):
        text = str(tag or "").strip()
        if not text:
            continue
        left = f"核心概念{index + 1}"
        right = text
        if "：" in text:
            left_part, right_part = text.split("：", 1)
            left = left_part.strip() or left
            right = right_part.strip() or right
        elif ":" in text:
            left_part, right_part = text.split(":", 1)
            left = left_part.strip() or left
            right = right_part.strip() or right
        pairs.append({
            "left": left[:20],
            "right": right[:36],
        })

    fallback_pairs = [
        {"left": "放热反应", "right": "反应后体系向外释放热量"},
        {"left": "吸热反应", "right": "反应过程中需要从外界吸收热量"},
        {"left": "热效应判断", "right": "结合温度变化或能量转移进行分析"},
    ]
    while len(pairs) < 3:
        pairs.append(fallback_pairs[len(pairs)])
    return pairs[:3]


def _is_low_quality_matching_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True

    normalized = re.sub(r"\s+", "", text).lower()
    placeholder_patterns = [
        r"^知识点\d+$",
        r"^核心概念\d+$",
        r"^要点\d+$",
        r"^内容\d+$",
        r"^项目\d+$",
        r"^步骤\d+$",
    ]
    if any(re.match(pattern, normalized) for pattern in placeholder_patterns):
        return True

    banned_fragments = {
        "学习价值",
        "知识点",
        "对应内容",
        "相关内容",
        "主要内容",
        "具体内容",
        "顺序",
        "先后",
    }
    return any(fragment in text for fragment in banned_fragments)


def _contains_subject_term(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False

    subject_terms = {
        "化学", "反应", "热效应", "放热", "吸热", "能量", "温度", "热量", "焓", "燃烧",
        "溶解", "中和", "催化", "氧化", "还原", "离子", "分子", "原子", "元素", "化合物",
        "酸", "碱", "盐", "溶液", "浓度", "守恒", "方程式", "实验", "现象", "条件",
        "pressure", "temperature", "energy", "reaction"
    }
    return any(term in text for term in subject_terms)


def _is_generic_slogan_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True

    slogan_fragments = {
        "解释生活现象",
        "解决问题",
        "提升能力",
        "提高素养",
        "学会思考",
        "培养兴趣",
        "理解世界",
        "联系实际",
        "掌握方法",
        "形成观念",
        "综合提升",
        "核心素养",
    }
    if any(fragment in text for fragment in slogan_fragments):
        return True

    return not _contains_subject_term(text)


def _is_matching_length_unbalanced(left: Any, right: Any) -> bool:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if not left_text or not right_text:
        return True

    left_len = len(re.sub(r"\s+", "", left_text))
    right_len = len(re.sub(r"\s+", "", right_text))
    shorter = max(min(left_len, right_len), 1)
    longer = max(left_len, right_len)
    return longer / shorter > 3.0


def _has_low_quality_matching_pairs(pairs: Any) -> bool:
    if not isinstance(pairs, list) or len(pairs) < 2:
        return True

    for pair in pairs:
        if not isinstance(pair, dict):
            return True
        left = pair.get("left")
        right = pair.get("right")
        if _is_low_quality_matching_text(left) or _is_low_quality_matching_text(right):
            return True
        if _is_generic_slogan_text(left) or _is_generic_slogan_text(right):
            return True
        if _is_matching_length_unbalanced(left, right):
            return True
    return False


def _build_default_ordering_sequence(stage: Dict[str, Any]) -> List[str]:
    goal = str(stage.get("goal") or "").strip()
    ordered = [
        "阅读题干并圈出关键词",
        "结合知识点分析条件",
        "给出结论并完成自检",
    ]
    if goal:
        ordered[0] = f"明确任务目标：{goal[:18]}"
    return ordered


def _build_default_error_spotting_payload(stage: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    goal = str(stage.get("goal") or "本关目标").strip()
    text = f"{goal}只需要死记硬背，不必关注变化过程；化学反应通常与能量变化没有关系。"
    answers = [
        {
            "wrong": "只需要死记硬背",
            "correct": ["需要理解条件、过程与证据", "不能只靠死记硬背", "需要结合过程理解"],
        },
        {
            "wrong": "通常与能量变化没有关系",
            "correct": ["通常伴随能量变化", "往往伴随能量变化", "一般会发生能量变化"],
        },
    ]
    return text, answers


def _build_question_interaction_tip(question_type: str, question: Dict[str, Any]) -> str:
    if question_type == "matching":
        return "操作提示：从左侧条目按住拖向右侧目标，靠近时会自动吸附高亮；连错可用“撤销最近连线”。"
    if question_type == "ordering":
        return "操作提示：直接拖拽卡片调整顺序；拖到目标位置时会出现动画过渡。"
    if question_type == "error_spotting":
        return "操作提示：点击标红的错误词片段，输入修正内容后保存，再继续检查下一处。"
    return "操作提示：按照题目要求完成交互后再提交答案。"


def _build_question_example(question_type: str, question: Dict[str, Any]) -> str:
    if question_type == "matching":
        pairs = question.get("pairs") if isinstance(question.get("pairs"), list) else []
        if pairs and isinstance(pairs[0], dict):
            left = str(pairs[0].get("left") or "").strip()
            right = str(pairs[0].get("right") or "").strip()
            if left and right:
                return f"示例：把“{left}”连到“{right}”。"
        return "示例：先观察概念，再把最容易判断的一对先连起来。"
    if question_type == "ordering":
        answer = question.get("answer") if isinstance(question.get("answer"), list) else []
        if len(answer) >= 2:
            first = str(answer[0]).strip()
            second = str(answer[1]).strip()
            if first and second:
                return f"示例：先把“{first}”放在最前，再接“{second}”。"
        return "示例：先确定起始步骤，再确定收尾步骤，中间步骤最后调整。"
    if question_type == "error_spotting":
        answers = question.get("answer") if isinstance(question.get("answer"), list) else []
        if answers and isinstance(answers[0], dict):
            wrong = str(answers[0].get("wrong") or "").strip()
            raw_correct = answers[0].get("correct")
            if isinstance(raw_correct, list):
                correct = str(raw_correct[0] or "").strip() if raw_correct else ""
            else:
                correct = str(raw_correct or "").strip()
            if wrong and correct:
                return f"示例：点击“{wrong}”，改成“{correct}”。"
        return "示例：点击明显错误的词语，再输入更准确的表述。"
    return "示例：先阅读题干，再完成对应的交互动作。"


def _normalize_error_spotting_answers(text: str, answers: Any) -> List[Dict[str, Any]]:
    normalized_answers: List[Dict[str, Any]] = []
    if not isinstance(answers, list):
        return normalized_answers

    search_cursor = 0
    source_text = str(text or "")
    for item in answers:
        if not isinstance(item, dict):
            continue
        wrong = str(item.get("wrong") or "").strip()
        raw_correct = item.get("correct")
        accepted_answers: List[str] = []
        if isinstance(raw_correct, list):
            for candidate in raw_correct:
                candidate_text = str(candidate or "").strip()
                if candidate_text and candidate_text not in accepted_answers:
                    accepted_answers.append(candidate_text)
        else:
            candidate_text = str(raw_correct or "").strip()
            if candidate_text:
                accepted_answers.append(candidate_text)

        if not wrong or not accepted_answers:
            continue

        start = item.get("start")
        end = item.get("end")
        try:
            start = int(start)
            end = int(end)
        except Exception:
            start = -1
            end = -1

        if start < 0 or end <= start or source_text[start:end] != wrong:
            start = source_text.find(wrong, search_cursor)
            if start < 0:
                start = source_text.find(wrong)
            end = start + len(wrong) if start >= 0 else -1

        if start < 0 or end <= start:
            continue

        normalized_answers.append({
            "wrong": wrong,
            "correct": accepted_answers[0],
            "acceptable_answers": accepted_answers,
            "start": start,
            "end": end,
        })
        search_cursor = end

    normalized_answers.sort(key=lambda item: (int(item.get("start") or 0), int(item.get("end") or 0)))
    return normalized_answers


def _apply_question_quality_defaults(
    question: Dict[str, Any],
    *,
    stage: Dict[str, Any],
    question_type: str,
) -> Dict[str, Any]:
    normalized = dict(question)
    normalized["interaction_tip"] = str(
        normalized.get("interaction_tip") or _build_question_interaction_tip(question_type, normalized)
    ).strip()
    normalized["example"] = str(
        normalized.get("example") or _build_question_example(question_type, normalized)
    ).strip()
    normalized["wrong_feedback"] = str(
        normalized.get("wrong_feedback") or f"建议回看“{str(stage.get('goal') or normalized.get('knowledge_tag') or '本题知识点').strip()}”后再尝试。"
    ).strip()
    return normalized


def _apply_interactive_question_payload(
    question: Dict[str, Any],
    *,
    stage: Dict[str, Any],
    question_type: str,
) -> Dict[str, Any]:
    normalized = dict(question)
    normalized["type"] = question_type
    if question_type == "matching":
        pairs = _build_default_matching_pairs(stage)
        normalized["stem"] = str(normalized.get("stem") or "请将左侧概念与右侧解释进行正确匹配。").strip()
        normalized["pairs"] = pairs
        normalized["answer"] = pairs
        normalized.pop("options", None)
        normalized.pop("items", None)
        normalized.pop("text", None)
    elif question_type == "ordering":
        ordered = _build_default_ordering_sequence(stage)
        shuffled = ordered[1:] + ordered[:1] if len(ordered) > 1 else ordered[:]
        normalized["stem"] = str(normalized.get("stem") or "请将下列步骤按合理顺序排列。").strip()
        normalized["items"] = shuffled
        normalized["answer"] = ordered
        normalized.pop("options", None)
        normalized.pop("pairs", None)
        normalized.pop("text", None)
    elif question_type == "error_spotting":
        text, answers = _build_default_error_spotting_payload(stage)
        normalized["stem"] = str(normalized.get("stem") or "请找出并修正下列陈述中的错误。").strip()
        normalized["text"] = str(normalized.get("text") or text)
        normalized["answer"] = _normalize_error_spotting_answers(
            normalized["text"],
            normalized.get("answer") if isinstance(normalized.get("answer"), list) and normalized.get("answer") else answers,
        )
        normalized.pop("options", None)
        normalized.pop("pairs", None)
        normalized.pop("items", None)
    return _apply_question_quality_defaults(normalized, stage=stage, question_type=question_type)


def _validate_and_enrich_game_questions(stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        questions = stage.get("questions") if isinstance(stage.get("questions"), list) else []
        validated_questions: List[Dict[str, Any]] = []
        for question in questions:
            if not isinstance(question, dict):
                continue
            question_type = str(question.get("type") or "").strip()
            normalized = dict(question)
            if question_type == "matching":
                pairs = normalized.get("pairs") if isinstance(normalized.get("pairs"), list) else []
                normalized["pairs"] = [
                    {"left": str(item.get("left") or "").strip(), "right": str(item.get("right") or "").strip()}
                    for item in pairs
                    if isinstance(item, dict) and str(item.get("left") or "").strip() and str(item.get("right") or "").strip()
                ]
                if not normalized["pairs"] or _has_low_quality_matching_pairs(normalized["pairs"]):
                    normalized = _apply_interactive_question_payload(normalized, stage=stage, question_type="matching")
            elif question_type == "ordering":
                items = normalized.get("items") if isinstance(normalized.get("items"), list) else []
                answer = normalized.get("answer") if isinstance(normalized.get("answer"), list) else []
                normalized["items"] = [str(item).strip() for item in items if str(item).strip()]
                normalized["answer"] = [str(item).strip() for item in answer if str(item).strip()]
                if len(normalized["items"]) < 2 or len(normalized["answer"]) < 2:
                    normalized = _apply_interactive_question_payload(normalized, stage=stage, question_type="ordering")
            elif question_type == "error_spotting":
                normalized["text"] = str(normalized.get("text") or "").strip()
                normalized["answer"] = _normalize_error_spotting_answers(normalized["text"], normalized.get("answer"))
                if not normalized["text"] or not normalized["answer"]:
                    normalized = _apply_interactive_question_payload(normalized, stage=stage, question_type="error_spotting")

            normalized = _apply_question_quality_defaults(normalized, stage=stage, question_type=question_type)
            validated_questions.append(normalized)
        stage["questions"] = validated_questions
    return stages


def _enforce_game_pack_question_variety(stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not stages:
        return stages

    required_types = ["matching", "ordering", "error_spotting"]
    question_slots: List[Tuple[int, int]] = []
    for stage_index, stage in enumerate(stages):
        questions = stage.get("questions") if isinstance(stage.get("questions"), list) else []
        for question_index, question in enumerate(questions):
            if isinstance(question, dict):
                question_slots.append((stage_index, question_index))

    if not question_slots:
        return stages

    # 先把所有非目标题型统一替换掉，确保最终只保留三种交互题。
    for slot_index, (stage_index, question_index) in enumerate(question_slots):
        stage = stages[stage_index]
        questions = stage.get("questions") if isinstance(stage.get("questions"), list) else []
        if question_index >= len(questions) or not isinstance(questions[question_index], dict):
            continue
        base_question = questions[question_index]
        current_type = str(base_question.get("type") or "").strip()
        if current_type not in required_types:
            questions[question_index] = _apply_interactive_question_payload(
                base_question,
                stage=stage,
                question_type=required_types[slot_index % len(required_types)],
            )
        stage["questions"] = questions

    present_types = {
        str(question.get("type") or "").strip()
        for stage in stages
        for question in (stage.get("questions") if isinstance(stage.get("questions"), list) else [])
        if isinstance(question, dict)
    }
    missing_types = [item for item in required_types if item not in present_types]
    for offset, target_type in enumerate(missing_types):
        stage_index, question_index = question_slots[offset % len(question_slots)]
        stage = stages[stage_index]
        questions = stage.get("questions") if isinstance(stage.get("questions"), list) else []
        if question_index >= len(questions) or not isinstance(questions[question_index], dict):
            continue
        questions[question_index] = _apply_interactive_question_payload(
            questions[question_index],
            stage=stage,
            question_type=target_type,
        )
        stage["questions"] = questions

    return stages


def _normalize_game_pack(
    raw_pack: Any,
    normalized_spec: Dict[str, Any],
    requested_theme: Optional[str] = None,
) -> Dict[str, Any]:
    allowed_types = {"matching", "ordering", "error_spotting"}
    fallback = _build_fallback_game_pack(normalized_spec, requested_theme)
    pack = raw_pack if isinstance(raw_pack, dict) else {}
    raw_stages = pack.get("stages") if isinstance(pack.get("stages"), list) else []
    stages: List[Dict[str, Any]] = []

    for stage_index, stage in enumerate(raw_stages):
        if not isinstance(stage, dict):
            continue
        fallback_stage = fallback["stages"][min(stage_index, len(fallback["stages"]) - 1)]
        stage_questions_raw = stage.get("questions") if isinstance(stage.get("questions"), list) else []
        questions: List[Dict[str, Any]] = []
        for question_index, question in enumerate(stage_questions_raw):
            if not isinstance(question, dict):
                continue
            fallback_question = fallback_stage["questions"][min(question_index, len(fallback_stage["questions"]) - 1)]
            question_type = str(question.get("type") or fallback_question["type"]).strip() or fallback_question["type"]
            if question_type not in allowed_types:
                question_type = fallback_question["type"]
            score_value = question.get("score", fallback_question["score"])
            try:
                score_value = max(int(score_value), 1)
            except Exception:
                score_value = fallback_question["score"]
            normalized_question = {
                "id": str(question.get("id") or fallback_question["id"]).strip() or fallback_question["id"],
                "stage_id": str(question.get("stage_id") or stage.get("id") or fallback_stage["id"]).strip() or fallback_stage["id"],
                "type": question_type,
                "stem": str(question.get("stem") or fallback_question["stem"]).strip() or fallback_question["stem"],
                "answer": question.get("answer", fallback_question["answer"]),
                "score": score_value,
                "knowledge_tag": str(question.get("knowledge_tag") or fallback_question["knowledge_tag"]).strip() or fallback_question["knowledge_tag"],
                "correct_feedback": str(question.get("correct_feedback") or fallback_question["correct_feedback"]).strip() or fallback_question["correct_feedback"],
                "wrong_feedback": str(question.get("wrong_feedback") or fallback_question["wrong_feedback"]).strip() or fallback_question["wrong_feedback"],
                "review_ref": str(question.get("review_ref") or fallback_question["review_ref"]).strip() or fallback_question["review_ref"],
                "interaction_tip": str(question.get("interaction_tip") or fallback_question.get("interaction_tip") or "").strip(),
                "example": str(question.get("example") or fallback_question.get("example") or "").strip(),
            }
            if question_type == "matching":
                pairs_raw = question.get("pairs") if isinstance(question.get("pairs"), list) else []
                pairs: List[Dict[str, str]] = []
                for pair in pairs_raw:
                    if not isinstance(pair, dict):
                        continue
                    left = str(pair.get("left") or "").strip()
                    right = str(pair.get("right") or "").strip()
                    if left and right:
                        pairs.append({"left": left, "right": right})
                normalized_question["pairs"] = pairs
                if len(normalized_question["pairs"]) < 2 or _has_low_quality_matching_pairs(normalized_question["pairs"]):
                    normalized_question = _apply_interactive_question_payload(
                        normalized_question,
                        stage=stage,
                        question_type="matching",
                    )
                elif not isinstance(normalized_question["answer"], list) or not normalized_question["answer"]:
                    normalized_question["answer"] = normalized_question["pairs"]
            elif question_type == "ordering":
                items = question.get("items") if isinstance(question.get("items"), list) else []
                normalized_question["items"] = [str(item).strip() for item in items if str(item).strip()]
                answer_items = normalized_question["answer"] if isinstance(normalized_question["answer"], list) else []
                normalized_question["answer"] = [str(item).strip() for item in answer_items if str(item).strip()]
                if len(normalized_question["items"]) < 2 or len(normalized_question["answer"]) < 2:
                    normalized_question = _apply_interactive_question_payload(
                        normalized_question,
                        stage=stage,
                        question_type="ordering",
                    )
            elif question_type == "error_spotting":
                normalized_question["text"] = str(question.get("text") or "").strip()
                answer_items = normalized_question["answer"] if isinstance(normalized_question["answer"], list) else []
                normalized_question["answer"] = _normalize_error_spotting_answers(
                    normalized_question["text"],
                    answer_items,
                )
                if not normalized_question["text"] or not normalized_question["answer"]:
                    normalized_question = _apply_interactive_question_payload(
                        normalized_question,
                        stage=stage,
                        question_type="error_spotting",
                    )
            else:
                normalized_question = _apply_interactive_question_payload(
                    normalized_question,
                    stage=stage,
                    question_type=fallback_question["type"],
                )
            questions.append(normalized_question)

        if not questions:
            questions = fallback_stage["questions"]
        pass_rule_raw = stage.get("pass_rule") if isinstance(stage.get("pass_rule"), dict) else {}
        min_correct = pass_rule_raw.get("min_correct", fallback_stage["pass_rule"]["min_correct"])
        try:
            min_correct = max(int(min_correct), 1)
        except Exception:
            min_correct = fallback_stage["pass_rule"]["min_correct"]
        stages.append({
            "id": str(stage.get("id") or fallback_stage["id"]).strip() or fallback_stage["id"],
            "title": str(stage.get("title") or stage.get("name") or fallback_stage["title"]).strip() or fallback_stage["title"],
            "goal": str(stage.get("goal") or fallback_stage["goal"]).strip() or fallback_stage["goal"],
            "knowledge_tags": _normalize_text_list(stage.get("knowledge_tags")) or fallback_stage["knowledge_tags"],
            "pass_rule": {
                "min_correct": min_correct,
                "description": str(pass_rule_raw.get("description") or fallback_stage["pass_rule"]["description"]).strip() or fallback_stage["pass_rule"]["description"],
            },
            "questions": questions,
        })

    if not stages:
        stages = fallback["stages"]
    stages = _enforce_game_pack_question_variety(stages)
    stages = _validate_and_enrich_game_questions(stages)

    theme_config = pack.get("theme_config") if isinstance(pack.get("theme_config"), dict) else {}
    theme_name = str(requested_theme or theme_config.get("name") or fallback["theme_config"]["name"]).strip().lower() or fallback["theme_config"]["name"]
    return {
        "meta": {
            "title": str((pack.get("meta") or {}).get("title") or fallback["meta"]["title"]).strip() or fallback["meta"]["title"],
            "topic": str((pack.get("meta") or {}).get("topic") or fallback["meta"]["topic"]).strip() or fallback["meta"]["topic"],
            "grade_subject": str((pack.get("meta") or {}).get("grade_subject") or fallback["meta"]["grade_subject"]).strip(),
            "duration": str((pack.get("meta") or {}).get("duration") or fallback["meta"]["duration"]).strip(),
            "generated_at": int((pack.get("meta") or {}).get("generated_at") or fallback["meta"]["generated_at"] or int(time.time())),
        },
        "theme_config": {**_default_game_theme(theme_name), **theme_config, "name": theme_name},
        "score_rule": {
            "base_score": int((pack.get("score_rule") or {}).get("base_score") or fallback["score_rule"]["base_score"]),
            "combo_bonus": int((pack.get("score_rule") or {}).get("combo_bonus") or fallback["score_rule"]["combo_bonus"]),
            "stage_clear_bonus": int((pack.get("score_rule") or {}).get("stage_clear_bonus") or fallback["score_rule"]["stage_clear_bonus"]),
            "time_bonus_enabled": bool((pack.get("score_rule") or {}).get("time_bonus_enabled", fallback["score_rule"]["time_bonus_enabled"])),
        },
        "render_config": {
            "show_timer": bool((pack.get("render_config") or {}).get("show_timer", fallback["render_config"]["show_timer"])),
            "show_combo": bool((pack.get("render_config") or {}).get("show_combo", fallback["render_config"]["show_combo"])),
            "show_progress": bool((pack.get("render_config") or {}).get("show_progress", fallback["render_config"]["show_progress"])),
            "allow_retry_stage": bool((pack.get("render_config") or {}).get("allow_retry_stage", fallback["render_config"]["allow_retry_stage"])),
        },
        "summary_rules": {
            "weak_point_rules": _normalize_text_list((pack.get("summary_rules") or {}).get("weak_point_rules")) or fallback["summary_rules"]["weak_point_rules"],
            "encouragement_copy": _normalize_text_list((pack.get("summary_rules") or {}).get("encouragement_copy")) or fallback["summary_rules"]["encouragement_copy"],
            "retry_suggestion_copy": _normalize_text_list((pack.get("summary_rules") or {}).get("retry_suggestion_copy")) or fallback["summary_rules"]["retry_suggestion_copy"],
        },
        "stages": stages,
    }

# 文件哈希计算函数
def calculate_file_hash(file_path):
    """Calculate SHA-256 hash for a file."""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # 读取文件块并更新哈希
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希值时出错: {str(e)}")
        return None

def check_file_exists_by_hash(file_hash, course_id=None):
    """妫€鏌ュ叿鏈夌浉鍚屽搱甯屽€肩殑鏂囦欢鏄惁宸插瓨鍦ㄤ簬鐭ヨ瘑搴撻槦鍒椾腑"""
    try:
        query = KnowledgeBaseQueue.query.filter_by(file_hash=file_hash)
        if course_id is not None:
            query = query.filter_by(course_id=course_id)
        existing_file = query.order_by(KnowledgeBaseQueue.id.desc()).first()
        return existing_file
    except Exception as e:
        logger.error(f"妫€鏌ユ枃浠跺搱甯屽€兼椂鍑洪敊: {str(e)}")
        return None

def _request_game_pack_from_model(
    normalized_spec: Dict[str, Any],
    course: Course,
    api_key: str,
    api_base: str,
    model_name: Optional[str],
    requested_theme: Optional[str],
    app_logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    requirement = normalized_spec.get("requirement_summary") if isinstance(normalized_spec.get("requirement_summary"), dict) else {}
    game_plan = normalized_spec.get("game_plan") if isinstance(normalized_spec.get("game_plan"), dict) else {}
    source_notes = normalized_spec.get("source_notes") if isinstance(normalized_spec.get("source_notes"), list) else []

    system_prompt = """You are 易度新星 EduNova game content designer.
Generate exactly one JSON object for an offline single-file classroom game.
Do not output markdown fences or explanations.

The JSON must contain these top-level keys:
- meta
- theme_config
- score_rule
- render_config
- summary_rules
- stages

Rules:
1. The game must be playable offline in a single HTML file.
2. Question types are restricted to: matching, ordering, error_spotting.
3. Each stage must include id, title, goal, knowledge_tags, pass_rule, questions.
4. Each question must include id, stage_id, type, stem, answer, score, knowledge_tag, correct_feedback, wrong_feedback, review_ref, interaction_tip, example.
5. VERY IMPORTANT: The `stem` must be a short, natural language instruction to the user. It MUST NOT contain JSON dictionaries, Python strings, or raw code. Example of good stems: "请将下列概念与它们对应的解释正确连线", "请将下面的步骤拖拽为正确的顺序", "请找出下面这段话中的错误部分，并给出修正后的内容".
6. For matching: provide "pairs" which is a list of objects { "left": "...", "right": "..." }. The "answer" should be the correctly matched pairs list. Use real, content-rich concept-to-definition / phenomenon-to-judgment / method-to-purpose matches. Every pair must contain clear subject terminology, must not use generic slogans or value statements, and the text length on the two sides should stay reasonably balanced. Do not use placeholders such as “知识点1”, “知识点2”, “学习价值”, “对应内容”, and do not turn ordering/sequencing into a fake matching question.
7. For ordering: provide "items" which is a list of strings in random order. "answer" is the list of items in correct order. Do not use JSON in items.
8. For error_spotting: provide "text" which is the original natural language text containing errors. "answer" is a list of objects { "wrong": "substring", "correct": "replacement or a list of acceptable replacements", "start": number, "end": number }. Prefer 2-4 acceptable phrasings when the correction can be expressed flexibly. start/end are zero-based indexes of the wrong substring in text. Do not use JSON in text.
9. review_ref should point to a lesson source, knowledge point, or slide/page style hint.
10. interaction_tip must tell the student how to operate this interaction in one short sentence.
11. example must provide one short concrete example of how to answer.
12. Keep language concise, teacher-facing and student-friendly. All outputs MUST be clean natural language, NO stringified JSON or code in the generated content.
13. Across all stages, include all three types at least once: matching, ordering, error_spotting.
14. Output must be valid JSON."""

    user_prompt = f"""请根据以下备课规格，生成一套可离线导出为单文件 HTML 的课堂闯关题包。

课程信息:
{json.dumps({'name': course.name, 'description': course.description or ''}, ensure_ascii=False)}

需求摘要:
{json.dumps(requirement, ensure_ascii=False)}

小游戏蓝图:
{json.dumps(game_plan, ensure_ascii=False)}

来源笔记:
{json.dumps(source_notes, ensure_ascii=False)}

附加要求:
- 游戏固定为 3 关轻量闯关
- 每关都要体现不同节奏：基础识别、应用判断、综合挑战
- 必须包含错题回看提示
- 输出适合课堂展示与课后练习
- 题型仅允许三种，且至少各出现 1 次：matching、ordering、error_spotting
- 每题都必须给出操作提示和一个简短示例
- 找错题请尽量把错误定位到词语或短语，不要整句都当成错误片段
- 主题风格优先使用: {requested_theme or str(game_plan.get('theme') or 'clean')}

请直接返回 JSON。"""

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    payload = {
        'model': model_name or get_model_primary("text"),
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 3500,
        'stream': False
    }

    app_logger.info(f'calling game-pack API: base={api_base}, model={payload["model"]}')
    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=120
    )
    if response.status_code != 200:
        raise ValueError(f'game-pack API request failed: {response.status_code}, {response.text}')

    response_json = response.json()
    content = ''
    choices = response_json.get('choices') if isinstance(response_json, dict) else []
    if isinstance(choices, list) and choices:
        message = choices[0].get('message', {}) if isinstance(choices[0], dict) else {}
        raw_content = message.get('content')
        if isinstance(raw_content, list):
            parts: List[str] = []
            for item in raw_content:
                if isinstance(item, dict) and item.get('text'):
                    parts.append(str(item.get('text')))
                elif isinstance(item, str):
                    parts.append(item)
            content = ''.join(parts).strip()
        else:
            content = str(raw_content or '').strip()
    if not content:
        return None
    return _extract_first_json_object(content)

# 鍔犺浇鐜鍙橀噺
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
backend_env_path = os.path.join(project_root, 'backend', '.env')
root_env_path = os.path.join(project_root, '.env')
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path)
if os.path.exists(root_env_path):
    load_dotenv(root_env_path)
rag_env_path = os.path.join(project_root, 'RAG', '.env')
if os.path.exists(rag_env_path):
    load_dotenv(rag_env_path)  # 如果存在，加载RAG/.env

# 灏濊瘯鑾峰彇API瀵嗛挜锛屼紭鍏堜娇鐢↙LM閰嶇疆锛屽鏋滀笉瀛樺湪鍒欎娇鐢―EEPSEEK閰嶇疆
def get_api_config():
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE") or get_chat_base_url()
    model_name = os.getenv("LLM_MODEL") or get_model_primary("text")
    
    # 濡傛灉LLM閰嶇疆涓嶅瓨鍦紝灏濊瘯浣跨敤DEEPSEEK閰嶇疆
    if not api_key:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        model_name = os.getenv("DEEPSEEK_MODEL")
    
    return api_key, api_base, model_name


def _compact_outline_evidence_context(category: str, evidence_context: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(evidence_context, dict):
        return {}

    query_terms = evidence_context.get('query_terms') if isinstance(evidence_context.get('query_terms'), list) else []
    source_notes = evidence_context.get('source_notes') if isinstance(evidence_context.get('source_notes'), list) else []
    source_evidence = evidence_context.get('source_evidence') if isinstance(evidence_context.get('source_evidence'), list) else []

    note_limit = 6 if category == 'docx_outline' else 8
    evidence_limit = 7 if category == 'docx_outline' else 10
    snippet_limit = 2 if category == 'docx_outline' else 3

    compact_notes: List[Dict[str, Any]] = []
    for item in source_notes[:note_limit]:
        if not isinstance(item, dict):
            continue
        compact_notes.append({
            'source_title': str(item.get('source_title') or '').strip(),
            'usage': str(item.get('usage') or '').strip(),
            'knowledge_point': str(item.get('knowledge_point') or '').strip(),
            'required': bool(item.get('required')),
            'note': str(item.get('note') or '').strip(),
        })

    compact_evidence: List[Dict[str, Any]] = []
    for item in source_evidence[:evidence_limit]:
        if not isinstance(item, dict):
            continue
        snippets = item.get('snippets') if isinstance(item.get('snippets'), list) else []
        compact_evidence.append({
            'source_title': str(item.get('source_title') or '').strip(),
            'source_kind': str(item.get('source_kind') or '').strip(),
            'knowledge_point': str(item.get('knowledge_point') or '').strip(),
            'required': bool(item.get('required')),
            'summary': str(item.get('summary') or '').strip(),
            'snippets': [str(snippet).strip() for snippet in snippets[:snippet_limit] if str(snippet).strip()],
        })

    return {
        'query_terms': [str(item).strip() for item in query_terms[:8] if str(item).strip()],
        'source_notes': compact_notes,
        'source_evidence': compact_evidence,
        'source_contract': evidence_context.get('source_contract') if isinstance(evidence_context.get('source_contract'), list) else [],
    }


def _generate_core_teaching_spec_via_model(
    *,
    api_key: str,
    api_base: str,
    model_name: str,
    course_info: Dict[str, Any],
    requirement_summary_payload: Dict[str, Any],
    structured_requirement: Dict[str, Any],
    form_context: Dict[str, Any],
    evidence_context: Dict[str, Any],
) -> Dict[str, Any]:
    system_prompt, user_prompt_template = load_prompt_bundle(
        category='core_spec',
        fallback_system=LESSON_PLAN_CORE_FALLBACK_SYSTEM_PROMPT,
        fallback_user=LESSON_PLAN_CORE_FALLBACK_USER_PROMPT,
    )
    user_prompt = render_prompt_template(user_prompt_template, {
        'course_info_json': json.dumps(course_info, ensure_ascii=False),
        'requirement_summary_json': json.dumps(requirement_summary_payload, ensure_ascii=False),
        'structured_requirement_json': json.dumps(structured_requirement or {}, ensure_ascii=False),
        'form_context_json': json.dumps(form_context or {}, ensure_ascii=False),
        'source_evidence_json': json.dumps(evidence_context or {}, ensure_ascii=False),
    })
    parsed: Dict[str, Any] | None = None
    last_error: Exception | None = None
    for max_tokens in [5200, 4400, 3600]:
        try:
            parsed = _request_chat_completion_json(
                api_key=api_key,
                api_base=api_base,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            )
            break
        except RuntimeError as exc:
            last_error = exc
            logger.warning(f'core_spec generation retry with lower token budget ({max_tokens}): {exc}')
            continue
    if parsed is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError('core_spec generation failed with unknown error')
    return normalize_core_teaching_spec(parsed, requirement_summary_payload, evidence_context.get('source_notes', []) if isinstance(evidence_context, dict) else [])


def _generate_outline_from_core_spec_via_model(
    *,
    category: str,
    fallback_system: str,
    fallback_user: str,
    target_key: str,
    api_key: str,
    api_base: str,
    model_name: str,
    core_spec: Dict[str, Any],
    requirement_summary_payload: Dict[str, Any],
    evidence_context: Dict[str, Any],
) -> Any:
    system_prompt, user_prompt_template = load_prompt_bundle(
        category=category,
        fallback_system=fallback_system,
        fallback_user=fallback_user,
    )
    compact_evidence_context = _compact_outline_evidence_context(category, evidence_context)
    user_prompt = render_prompt_template(user_prompt_template, {
        'core_spec_json': json.dumps(core_spec, ensure_ascii=False),
        'requirement_summary_json': json.dumps(requirement_summary_payload, ensure_ascii=False),
        'source_evidence_json': json.dumps(compact_evidence_context, ensure_ascii=False),
    })
    max_token_candidates = [5200, 4200, 3200] if category == 'docx_outline' else [4200, 3200]
    parsed: Dict[str, Any] | None = None
    last_error: Exception | None = None
    for max_tokens in max_token_candidates:
        try:
            parsed = _request_chat_completion_json(
                api_key=api_key,
                api_base=api_base,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            )
            break
        except RuntimeError as exc:
            last_error = exc
            if category != 'docx_outline':
                raise
            logger.warning(f'{category} generation retry with lower token budget ({max_tokens}): {exc}')
            continue
    if parsed is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError(f'{category} generation failed with unknown error')
    outline = parsed.get(target_key)
    return outline if isinstance(outline, list) else []


def _revise_core_teaching_spec_via_model(
    *,
    api_key: str,
    api_base: str,
    model_name: str,
    core_spec: Dict[str, Any],
    lesson_plan_spec: Dict[str, Any],
    revision_request: str,
    evidence_context: Dict[str, Any],
) -> Dict[str, Any]:
    system_prompt, user_prompt_template = load_prompt_bundle(
        category='revision',
        fallback_system=LESSON_PLAN_REVISION_FALLBACK_SYSTEM_PROMPT,
        fallback_user=LESSON_PLAN_REVISION_FALLBACK_USER_PROMPT,
    )
    user_prompt = render_prompt_template(user_prompt_template, {
        'core_spec_json': json.dumps(core_spec, ensure_ascii=False),
        'lesson_plan_spec_json': json.dumps(lesson_plan_spec, ensure_ascii=False),
        'revision_request': revision_request,
        'source_evidence_json': json.dumps(evidence_context or {}, ensure_ascii=False),
    })
    return _request_chat_completion_json(
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=4000,
    )


def _build_lesson_plan_generation_artifacts(
    *,
    api_key: str,
    api_base: str,
    model_name: str,
    course_info: Dict[str, Any],
    requirement_summary_payload: Dict[str, Any],
    structured_requirement: Dict[str, Any],
    form_context: Dict[str, Any],
    source_bundle: Dict[str, Any],
    course_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
) -> Dict[str, Any]:
    core_spec = _generate_core_teaching_spec_via_model(
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
        course_info=course_info,
        requirement_summary_payload=requirement_summary_payload,
        structured_requirement=structured_requirement,
        form_context=form_context,
        evidence_context=source_bundle,
    )
    chapter_assessment_questions = _generate_chapter_assessment_questions(
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
        course_info=course_info,
        requirement_summary=requirement_summary_payload,
        course_id=course_id,
        chapter_id=chapter_id,
    )
    if chapter_assessment_questions:
        assessment_plan = core_spec.get('assessment_plan') if isinstance(core_spec.get('assessment_plan'), dict) else {}
        assessment_plan['questions'] = chapter_assessment_questions
        core_spec['assessment_plan'] = assessment_plan
    requirement_summary = core_spec_to_requirement_summary(core_spec, requirement_summary_payload)
    source_notes = source_bundle.get('source_notes') if isinstance(source_bundle.get('source_notes'), list) else []
    docx_outline = _generate_outline_from_core_spec_via_model(
        category='docx_outline',
        fallback_system=LESSON_PLAN_DOCX_FALLBACK_SYSTEM_PROMPT,
        fallback_user=LESSON_PLAN_DOCX_FALLBACK_USER_PROMPT,
        target_key='docx_outline',
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
        core_spec=core_spec,
        requirement_summary_payload=requirement_summary,
        evidence_context=source_bundle,
    )
    ppt_outline = _generate_outline_from_core_spec_via_model(
        category='ppt_outline',
        fallback_system=LESSON_PLAN_PPT_FALLBACK_SYSTEM_PROMPT,
        fallback_user=LESSON_PLAN_PPT_FALLBACK_USER_PROMPT,
        target_key='ppt_outline',
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
        core_spec=core_spec,
        requirement_summary_payload=requirement_summary,
        evidence_context=source_bundle,
    )
    game_plan = build_game_plan_seed_from_core_spec(core_spec, requirement_summary, source_notes)
    normalized_spec = _normalize_lesson_plan_spec(
        raw_spec={
            'requirement_summary': requirement_summary,
            'source_notes': source_notes,
            'docx_outline': docx_outline,
            'ppt_outline': ppt_outline,
            'game_plan': game_plan,
        },
        requirement_summary_fallback=requirement_summary,
        source_notes_fallback=source_notes,
    )
    normalized_spec = _enforce_source_intent_on_spec(normalized_spec)
    return {
        'core_spec': core_spec,
        'normalized_spec': normalized_spec,
        'outline_generation_meta': {
            'pipeline': 'core_spec_v2',
            'docx_sections': len(normalized_spec.get('docx_outline') or []),
            'ppt_slides': len(normalized_spec.get('ppt_outline') or []),
            'source_note_count': len(source_notes),
        },
    }


def _generate_chapter_assessment_questions(
    *,
    api_key: str,
    api_base: str,
    model_name: str,
    course_info: Dict[str, Any],
    requirement_summary: Dict[str, Any],
    course_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
) -> List[str]:
    chapter_title = str(requirement_summary.get('chapter_title') or '').strip()
    if not chapter_title and not chapter_id:
        return []

    course_name = str(course_info.get('name') or requirement_summary.get('grade_subject') or '课程').strip()
    course_description = str(course_info.get('description') or '').strip()
    extra_info = '请围绕选定章节生成课堂检测题，题干尽量短、明确、可直接用于Word教案中的课堂检测部分。'

    try:
        from backend.api.learning import generate_assessment_with_ai as _generate_assessment_with_ai

        assessment_data = _generate_assessment_with_ai(
            course_name=course_name,
            course_description=course_description,
            extra_info=extra_info,
            assessment_type='quiz',
            difficulty='medium',
            course_id=course_id,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            status_callback=None,
        )
    except Exception as exc:
        current_app.logger.warning('章节检测题生成失败，回退到常规教案题目: %s', exc)
        return []

    sections = assessment_data.get('sections') if isinstance(assessment_data, dict) else []
    question_texts: List[str] = []
    for section in sections if isinstance(sections, list) else []:
        if not isinstance(section, dict):
            continue
        questions = section.get('questions') if isinstance(section.get('questions'), list) else []
        for question in questions:
            if not isinstance(question, dict):
                continue
            stem = str(question.get('stem') or question.get('content') or '').strip()
            if not stem:
                continue
            q_type = str(question.get('type') or '').strip()
            if q_type == 'multiple_choice':
                options = _normalize_text_list(question.get('options'))
                if options:
                    stem = f"{stem}（{' / '.join(options[:4])}）"
            question_texts.append(_compress_assessment_question_text(stem))
            if len(question_texts) >= 7:
                return question_texts

    if not question_texts:
        description = str(assessment_data.get('description') or '').strip()
        if description:
            question_texts.append(_compress_assessment_question_text(description))
    while len(question_texts) < 7:
        question_texts.append(f"请结合本节课内容完成第{len(question_texts) + 1}道课堂检测题。")
    return question_texts[:7]


def _compress_assessment_question_text(text: str, max_chars: int = 48) -> str:
    return re.sub(r'\s+', '', str(text or '').strip())


rag_api = Blueprint('rag_api', __name__)

def initialize_rag():
    """鍦ㄥ簲鐢ㄤ笂涓嬫枃涓垵濮嬪寲RAG妯″潡"""
    global RAG_AVAILABLE, hybrid_retriever, format_docs
    
    try:
        # 妫€鏌ヨ矾寰?
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 妫€鏌ュ彲鑳界殑鐭ヨ瘑搴撹矾寰?
        possible_paths = [
            os.path.join(project_root, "uploads", "knowledge_base"),
            os.path.join(project_root, "backend", "uploads", "knowledge_base")
        ]
        
        vectordb_path = None
        for path in possible_paths:
            if os.path.exists(path):
                vectordb_path = path
                logger.info(f"鎵惧埌鐭ヨ瘑搴撹矾寰? {path}")
                
                # 妫€鏌ュ悜閲忔暟鎹簱
                vdb_path = os.path.join(path, "vectordb")
                if os.path.exists(vdb_path):
                    logger.info(f"鎵惧埌鍚戦噺鏁版嵁搴? {vdb_path}")
                    vectordb_path = vdb_path
                    break
        
        if not vectordb_path:
            logger.warning("鏃犳硶鎵惧埌鏈夋晥鐨勭煡璇嗗簱璺緞")
        
        # 导入RAG模块
        try:
            from backend.rag.rag_query import hybrid_retriever, format_docs
            RAG_AVAILABLE = True
            logger.info("RAG module imported successfully")
            return True
        except ImportError as e:
            logger.error(f"无法导入RAG模块: {str(e)}")
            
            # 灏濊瘯浠庡叾浠栧彲鑳界殑璺緞瀵煎叆
            try:
                import sys
                sys.path.append(project_root)
                from backend.rag.rag_query import hybrid_retriever, format_docs
                RAG_AVAILABLE = True
                logger.info("閫氳繃璋冩暣璺緞鎴愬姛瀵煎叆RAG妯″潡")
                return True
            except ImportError as e2:
                logger.error(f"灏濊瘯璋冩暣璺緞鍚庝粛鏃犳硶瀵煎叆RAG妯″潡: {str(e2)}")
                RAG_AVAILABLE = False
                return False
    except Exception as e:
        logger.error(f"鍒濆鍖朢AG妯″潡鏃跺嚭閿? {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        RAG_AVAILABLE = False
        return False

@rag_api.route('/status', methods=['GET'])
def get_module_status_api():
    """Get status of RAG and AI modules."""
    global RAG_AVAILABLE

    if not RAG_AVAILABLE:
        initialize_rag()

    api_key, api_base, _ = get_api_config()
    rag_status = "available" if RAG_AVAILABLE else "unavailable"
    logger.info(f"RAG module status: {rag_status}")

    ai_status = "available" if (api_key and api_base) else "not_configured"
    logger.info(f"AI API status: {ai_status}")

    return jsonify({
        'status': 'success',
        'rag_enabled': RAG_AVAILABLE,
        'ai_enabled': bool(api_key and api_base),
        'message': 'module status fetched'
    })
@rag_api.route('/transcribe-audio', methods=['POST'])
@jwt_required()
def transcribe_audio_api():
    """Transcribe uploaded audio file and return plain text + segments."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'audio file is required'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'status': 'error', 'message': 'invalid audio file'}), 400

    source_kind = (request.form.get('source_kind') or 'mic').strip().lower()
    if source_kind not in ('mic', 'video'):
        return jsonify({'status': 'error', 'message': 'source_kind must be mic or video'}), 400

    raw_hints = request.form.get('language_hints')
    language_hints: List[str] = ['zh', 'en']
    if raw_hints:
        try:
            parsed = json.loads(raw_hints)
            if isinstance(parsed, list):
                language_hints = [str(x).strip() for x in parsed if str(x).strip()]
            elif isinstance(parsed, str) and parsed.strip():
                language_hints = [parsed.strip()]
        except json.JSONDecodeError:
            language_hints = [x.strip() for x in raw_hints.split(',') if x.strip()] or language_hints

    temp_root = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', str(user_id), 'audio')
    os.makedirs(temp_root, exist_ok=True)
    safe_name = secure_filename(file.filename or f'{uuid.uuid4().hex}.webm')
    original_path = os.path.join(temp_root, f"{uuid.uuid4().hex}_{safe_name}")
    try:
        # Lazy import to avoid circular dependency during app bootstrap
        from backend.rag.create_db import transcribe_audio_dashscope

        file.save(original_path)
        result = transcribe_audio_dashscope(
            original_path,
            language_hints=language_hints,
            with_segments=True,
            mime_type=file.mimetype,
        )
        return jsonify({
            'status': 'success',
            'text': result.get('text', ''),
            'segments': result.get('segments', []),
            'duration_ms': result.get('duration_ms', 0),
            'provider': 'dashscope',
            'model': result.get('model', get_model_primary("asr"))
        })
    except FileNotFoundError as e:
        app_logger.error(f'transcribe failed (file missing): {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except requests.RequestException as e:
        app_logger.error(f'transcribe request failed: {str(e)}')
        return jsonify({'status': 'error', 'message': f'transcribe service call failed: {str(e)}'}), 502
    except Exception as e:
        app_logger.error(f'transcribe failed: {str(e)}')
        return jsonify({'status': 'error', 'message': f'transcribe failed: {str(e)}'}), 500
    finally:
        for p in [original_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

@rag_api.route('/summarize-lesson-requirement', methods=['POST'])
@jwt_required()
def summarize_lesson_requirement():
    """Summarize requirement into a fixed JSON schema."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()
    data = request.json or {}
    form_snapshot = data.get('form_snapshot') or {}
    if not isinstance(form_snapshot, dict):
        return jsonify({'status': 'error', 'message': 'form_snapshot must be an object'}), 400

    conversation_id = data.get('conversation_id')
    course_id = data.get('course_id')

    history_lines: List[str] = []
    if conversation_id:
        chats = ChatHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id
        ).order_by(ChatHistory.timestamp.asc()).all()
        for chat in chats[-20:]:
            role = 'teacher' if chat.role == 'user' else 'assistant'
            history_lines.append(f"{role}: {chat.message}")

    api_key, api_base, model_name = get_api_config()
    if not api_key or not api_base:
        return jsonify({'status': 'error', 'message': 'API key or base URL is not configured'}), 500
    model_name = model_name or get_model_primary("text")

    system_prompt = (
        'You are a lesson requirement structuring assistant. '
        'Return exactly one JSON object with keys: '
        'teaching_goals(array), knowledge_points(array), duration(string), '
        'style(string), output_targets(array).'
    )
    user_prompt = (
        "Extract final confirmed requirements from form snapshot and conversation history.\n"
        f"Form snapshot:\n{json.dumps(form_snapshot, ensure_ascii=False)}\n"
        f"Course ID: {course_id}\n"
        "Conversation history:\n"
        f"{chr(10).join(history_lines) if history_lines else '(none)'}"
    )

    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.1,
        'max_tokens': 800,
        'stream': False
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    try:
        resp = requests.post(
            f"{api_base.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )
        resp.raise_for_status()
        body = resp.json()
        content = (
            body.get('choices', [{}])[0]
            .get('message', {})
            .get('content', '')
        )
        parsed = _extract_first_json_object(content) or {}
        normalized = normalize_requirement_summary(parsed, form_snapshot)
        return jsonify({
            'status': 'success',
            'summary': normalized
        })
    except requests.RequestException as e:
        app_logger.error(f'summary request failed: {str(e)}')
        fallback = normalize_requirement_summary({}, form_snapshot)
        return jsonify({
            'status': 'success',
            'summary': fallback,
            'message': 'summary model failed; fallback summary returned'
        })
    except Exception as e:
        app_logger.error(f'summary generation failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'summary generation failed: {str(e)}'
        }), 500

@rag_api.route('/structure-teaching-elements', methods=['POST'])
@jwt_required()
def structure_teaching_elements():
    """Structure teaching elements into a fixed JSON schema."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()
    data = request.json or {}
    form_snapshot = data.get('form_snapshot') or {}
    if not isinstance(form_snapshot, dict):
        return jsonify({'status': 'error', 'message': 'form_snapshot must be an object'}), 400

    conversation_id = data.get('conversation_id')
    course_id = data.get('course_id')
    requirement_summary = data.get('requirement_summary') if isinstance(data.get('requirement_summary'), dict) else {}
    source_mappings = data.get('source_mappings') if isinstance(data.get('source_mappings'), list) else []

    history_lines: List[str] = []
    if conversation_id:
        chats = ChatHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id
        ).order_by(ChatHistory.timestamp.asc()).all()
        for chat in chats[-20:]:
            role = 'teacher' if chat.role == 'user' else 'assistant'
            history_lines.append(f"{role}: {chat.message}")

    rule_fallback = normalize_structured_requirement({}, form_snapshot)
    free_description = str(form_snapshot.get('freeTeachingIdea', '') or '').strip()
    has_rule_core = bool(
        rule_fallback.get('topic')
        and rule_fallback.get('knowledge_points')
        and rule_fallback.get('teaching_flow')
    )
    if has_rule_core and not free_description and not history_lines:
        return jsonify({
            'status': 'success',
            'structured': rule_fallback,
            'message': 'rule-based structured result returned (model call skipped)',
            'fallback': True
        })

    source_mapping_summary = []
    for item in source_mappings:
        if not isinstance(item, dict):
            continue
        file_path = str(item.get('filePath') or '').strip()
        usage = str(item.get('usage') or '').strip()
        kp = str(item.get('knowledgePoint') or '').strip()
        is_required = item.get('isRequired')
        if not file_path:
            continue
        source_mapping_summary.append({
            'file_path': file_path,
            'usage': usage,
            'knowledge_point': kp,
            'is_required': bool(is_required) if isinstance(is_required, bool) else None
        })

    api_key, api_base, model_name = get_api_config()
    if not api_key or not api_base:
        return jsonify({
            'status': 'success',
            'structured': rule_fallback,
            'message': 'model config missing; rule-based structured result returned',
            'fallback': True
        })
    model_name = model_name or get_model_primary("text")

    system_prompt = (
        "You are a lesson requirement structuring assistant.\n"
        "Return exactly one JSON object with keys:\n"
        "topic(string), knowledge_points(array), teaching_flow(array of objects),\n"
        "key_points(array), difficult_points(array), student_profile(object), style(object).\n"
        "teaching_flow item schema: {step(number), title(string), goal(string)}.\n"
        "student_profile keys: grade, foundation, learning_preference.\n"
        "style keys: teaching_style, interaction_level, output_preference.\n"
        "Do not output markdown or explanation."
    )
    user_prompt = (
        "Please structure teaching elements from the following inputs.\n"
        f"Rule-based extraction seed:\n{json.dumps(rule_fallback, ensure_ascii=False)}\n"
        f"Form snapshot:\n{json.dumps(form_snapshot, ensure_ascii=False)}\n"
        f"Requirement summary (optional):\n{json.dumps(requirement_summary, ensure_ascii=False)}\n"
        f"Source mapping summary (optional):\n{json.dumps(source_mapping_summary, ensure_ascii=False)}\n"
        f"Course ID: {course_id}\n"
        "Conversation history:\n"
        f"{chr(10).join(history_lines) if history_lines else '(none)'}"
    )

    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.1,
        'max_tokens': 1200,
        'stream': False
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    try:
        resp = requests.post(
            f"{api_base.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )
        resp.raise_for_status()
        body = resp.json()
        content = (
            body.get('choices', [{}])[0]
            .get('message', {})
            .get('content', '')
        )
        parsed = _extract_first_json_object(content) or {}
        normalized = normalize_structured_requirement(parsed, form_snapshot)
        return jsonify({
            'status': 'success',
            'structured': normalized,
            'fallback': False
        })
    except requests.RequestException as e:
        app_logger.error(f'structure teaching elements request failed: {str(e)}')
        return jsonify({
            'status': 'success',
            'structured': rule_fallback,
            'message': 'structure model failed; fallback structured result returned',
            'fallback': True
        })
    except Exception as e:
        app_logger.error(f'structure teaching elements failed: {str(e)}')
        return jsonify({
            'status': 'success',
            'structured': rule_fallback,
            'message': f'structure failed; fallback structured result returned: {str(e)}',
            'fallback': True
        })

@rag_api.route('/knowledge/import-examples', methods=['POST'])
@jwt_required()
def import_example_files():
    """Import local example files into course materials and queue them to knowledge base."""
    app_logger = current_app.logger
    current_user = get_authenticated_user()
    data = request.json or {}
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({'status': 'error', 'message': 'course_id 不能为空'}), 400
    try:
        course_id = int(course_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'course_id 蹇呴』鏄暟瀛?'}), 400

    purpose = normalize_purpose(data.get('purpose', 'lesson_plan'), default='lesson_plan')
    if not purpose:
        return jsonify({'status': 'error', 'message': 'purpose 浠呮敮鎸?general 鎴?lesson_plan'}), 400

    course = Course.query.get(course_id)
    access_error = ensure_course_teacher_access(course, current_user)
    if access_error:
        return access_error

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    example_dir = os.path.join(project_root, 'example')
    if not os.path.isdir(example_dir):
        return jsonify({'status': 'error', 'message': 'example 鐩綍涓嶅瓨鍦?'}), 404

    files_to_import: List[str] = []
    for root, _, files in os.walk(example_dir):
        for name in files:
            src = os.path.join(root, name)
            if os.path.isfile(src):
                files_to_import.append(src)

    if not files_to_import:
        return jsonify({'status': 'success', 'imported_count': 0, 'queued_count': 0, 'skipped_count': 0, 'items': []})

    from backend.tasks.rag_processor import start_processing_queue_item

    materials_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'materials', str(course_id))
    os.makedirs(materials_dir, exist_ok=True)

    def detect_material_type(filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        mapping = {
            '.pdf': 'PDF', '.doc': 'Word', '.docx': 'Word',
            '.ppt': 'PowerPoint', '.pptx': 'PowerPoint',
            '.txt': 'Text', '.md': 'Markdown', '.markdown': 'Markdown',
            '.jpg': 'Image', '.jpeg': 'Image', '.png': 'Image', '.webp': 'Image',
            '.mp4': 'Video', '.mov': 'Video', '.avi': 'Video', '.mkv': 'Video', '.webm': 'Video'
        }
        return mapping.get(ext, 'Other')

    imported_count = 0
    queued_count = 0
    skipped_count = 0
    items: List[Dict[str, Any]] = []

    for src_path in files_to_import:
        filename = os.path.basename(src_path)
        src_hash = calculate_file_hash(src_path)
        if not src_hash:
            skipped_count += 1
            items.append({'file': filename, 'status': 'skipped', 'reason': 'hash_failed'})
            continue

        # 1) Ensure material exists (dedup by hash in same course)
        material = Material.query.filter_by(course_id=course_id, file_hash=src_hash).first()
        if not material:
            safe_name = secure_filename(filename) or f"example_{uuid.uuid4().hex}{os.path.splitext(filename)[1]}"
            target_path = os.path.join(materials_dir, safe_name)
            if os.path.exists(target_path):
                stem, ext = os.path.splitext(safe_name)
                target_path = os.path.join(materials_dir, f"{stem}_{uuid.uuid4().hex[:8]}{ext}")
            shutil.copy2(src_path, target_path)

            relative_upload_path = f"/uploads/materials/{course_id}/{os.path.basename(target_path)}"
            material = Material(
                title=os.path.basename(target_path),
                material_type=detect_material_type(target_path),
                file_path=relative_upload_path,
                file_hash=src_hash,
                content=f"Imported from example: {filename}",
                course_id=course_id
            )
            db.session.add(material)
            db.session.commit()
            imported_count += 1

        queue_file_path = str(material.file_path or "").replace('/uploads/', '').lstrip('/')
        existing_queue = check_file_exists_by_hash(src_hash, course_id=course_id)
        if existing_queue:
            if existing_queue.purpose == 'general' and purpose == 'lesson_plan':
                existing_queue.purpose = purpose
                db.session.commit()
            skipped_count += 1
            items.append({
                'file': filename,
                'status': 'skipped',
                'reason': 'already_queued',
                'queue_id': existing_queue.id
            })
            continue

        queue_item = KnowledgeBaseQueue(
            course_id=course_id,
            file_path=queue_file_path,
            file_hash=src_hash,
            purpose=purpose
        )
        db.session.add(queue_item)
        db.session.commit()
        start_processing_queue_item(queue_item.id)
        queued_count += 1
        items.append({
            'file': filename,
            'status': 'queued',
            'queue_id': queue_item.id,
            'purpose': purpose
        })

    return jsonify({
        'status': 'success',
        'imported_count': imported_count,
        'queued_count': queued_count,
        'skipped_count': skipped_count,
        'items': items
    })

@rag_api.route('/chat', methods=['GET', 'POST'])
@jwt_required()
def chat_with_ai():
    """AI chat endpoint with optional RAG enhancement."""
    global RAG_AVAILABLE
    
    # 鍦ㄥ簲鐢ㄤ笂涓嬫枃涓皾璇曞垵濮嬪寲RAG妯″潡
    if not RAG_AVAILABLE:
        initialize_rag()
    
    # 鍦ㄥ簲鐢ㄤ笂涓嬫枃涓褰曟棩蹇?
    app_logger = current_app.logger
    
    # 根据请求方法获取数据
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '鏃犳晥鐨勮姹傛暟鎹?'}), 400
    else:  # GET请求
        data = request.args
    
    user_id = get_jwt_identity()
    message = data.get('message')
    course_id = data.get('course_id')  # 鍙€夊弬鏁?
    conversation_id = data.get('conversation_id')  # 鍙€夊弬鏁?
    stream = data.get('stream', False)  # 鏄惁浣跨敤娴佸紡杈撳嚭锛岄粯璁や负False
    use_rag = data.get('use_rag', True)  # 鏄惁浣跨敤RAG锛岄粯璁や负True
    selected_knowledge_items = parse_selected_knowledge_items(data.get('selectedKnowledgeItems', []))
    
    # 瀵逛簬GET璇锋眰锛屽皢stream鍜寀se_rag鍙傛暟杞崲涓哄竷灏斿€?
    if request.method == 'GET':
        if stream == 'true':
            stream = True
        if use_rag == 'false':
            use_rag = False
    
    if not message:
        return jsonify({'status': 'error', 'message': '消息不能为空'}), 400
    
    try:
        # 鑾峰彇API瀵嗛挜鍜屽熀纭€URL
        api_key, api_base, model_name = get_api_config()
        
        if not api_key or not api_base:
            return jsonify({
                'status': 'error',
                'message': 'API瀵嗛挜鎴栧熀纭€URL鏈厤缃?'
            }), 500
        
        if not model_name:
            model_name = "deepseek-chat"  # 榛樿妯″瀷
        
        # 获取历史对话记录
        history = []
        if conversation_id:
            chat_history = ChatHistory.query.filter_by(
                conversation_id=conversation_id,
                user_id=user_id
            ).order_by(ChatHistory.timestamp.asc()).all()
            
            for chat in chat_history:
                if chat.role == 'user':
                    history.append({"role": "user", "content": chat.message})
                else:
                    history.append({"role": "assistant", "content": chat.message})
        
        # 添加当前消息
        history.append({"role": "user", "content": message})
        
        # 生成或使用现有的对话ID
        if not conversation_id:
            conversation_id = f"conv_{user_id}_{int(time.time())}"
        
        # 淇濆瓨鐢ㄦ埛娑堟伅鍒版暟鎹簱
        user_chat = ChatHistory(
            user_id=user_id,
            course_id=course_id,  # 鍙兘涓篘one
            conversation_id=conversation_id,
            role='user',
            message=message,
            timestamp=int(time.time())
        )
        db.session.add(user_chat)
        db.session.commit()
        
        resolved_course = Course.query.get(course_id) if course_id else None
        course_info = ""
        course_context_prompt = ""
        selected_knowledge_prompt = ""
        if resolved_course:
            course_info = f"""
                        课程名称: {resolved_course.name}
                        课程简介: {resolved_course.description or '无简介'}
                        课程类别: {resolved_course.category or '未分类'}
                        难度级别: {resolved_course.difficulty or '未指定'}
                        课程时长: {resolved_course.duration or 0} 小时
                        """
            course_context_prompt = (
                f"当前用户已经在界面中明确选择了课程“{resolved_course.name}”。"
                "如果用户提到“这门课程”“当前课程”“本课程”等指代，默认都指这门课，"
                "不要反问用户是哪门课程，除非用户随后明确切换了课程主题。"
            )
            app_logger.info(f"chat request resolved course context: {resolved_course.name}")
        elif course_id:
            app_logger.warning(f"chat request course not found, course_id={course_id}")
        if selected_knowledge_items:
            selected_file_names = []
            for item in selected_knowledge_items[:5]:
                file_name = str(item.get('file_name') or os.path.basename(str(item.get('file_path') or '')) or '').strip()
                if file_name:
                    selected_file_names.append(file_name)
            if selected_file_names:
                selected_knowledge_prompt = (
                    "当前用户已经在界面中明确指定只围绕以下知识库文件检索和回答："
                    f"{'、'.join(selected_file_names)}。"
                    "除非用户主动要求扩展范围，否则不要引用其他知识库文件。"
                )

        # 鍑嗗API璇锋眰澶?
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        if use_rag and course_id and get_chapter_query_type(message):
            assistant_reply = build_chapter_query_reply(
                course_id=course_id,
                course_name=resolved_course.name if resolved_course else "",
                message=message,
            )
            if assistant_reply:
                return build_direct_assistant_response(
                    assistant_reply=assistant_reply,
                    user_id=user_id,
                    course_id=course_id,
                    conversation_id=conversation_id,
                    sources=[],
                    stream=stream,
                )

        if use_rag and course_id and is_knowledge_file_list_request(message):
            assistant_reply = build_knowledge_file_listing_reply(
                course_id=course_id,
                course_name=resolved_course.name if resolved_course else ""
            )
            return build_direct_assistant_response(
                assistant_reply=assistant_reply,
                user_id=user_id,
                course_id=course_id,
                conversation_id=conversation_id,
                sources=[],
                stream=stream,
            )
        
        # 鍒ゆ柇鏄惁浣跨敤RAG
        retrieved_docs = []
        context = ""
        sources = []
        fallback_instruction = ""
        context_mode = "vector"
        
        if use_rag and (course_id or selected_knowledge_items):
            # 纭繚RAG妯″潡宸插垵濮嬪寲
            if not RAG_AVAILABLE:
                initialize_rag()
            
            if RAG_AVAILABLE:
                try:
                    if resolved_course:
                        app_logger.info(f"鑾峰彇鍒拌绋嬩俊鎭? {resolved_course.name}")
                    else:
                        app_logger.warning(f"鏈壘鍒拌绋嬩俊鎭紝璇剧▼ID: {course_id}")
                    
                    # 浣跨敤RAG妫€绱㈢浉鍏虫枃妗?
                    app_logger.info(
                        f"浣跨敤RAG妫€绱紝璇剧▼ID: {course_id}, selected_items={len(selected_knowledge_items)}"
                    )
                    
                    # 纭繚hybrid_retriever涓嶆槸None
                    if hybrid_retriever is None:
                        app_logger.error("hybrid_retriever鏈垵濮嬪寲")
                        structured_context, structured_sources, structured_mode = build_structured_index_context(
                            course_id=course_id,
                            message=message,
                            course_name=resolved_course.name if resolved_course else "",
                        )
                        if structured_context:
                            context = structured_context
                            sources = structured_sources
                            context_mode = structured_mode or "structured_index"
                        else:
                            fallback_instruction = build_natural_fallback_instruction(
                                course_id=course_id,
                                course_name=resolved_course.name if resolved_course else "",
                                reason="rag_unavailable",
                            )
                            use_rag = False
                    else:
                        if selected_knowledge_items:
                            query_parts = [message]
                            for item in selected_knowledge_items[:8]:
                                file_name = str(item.get('file_name') or '').strip()
                                knowledge_point = str(item.get('knowledge_point') or '').strip()
                                if file_name:
                                    query_parts.append(f"selected material {file_name}")
                                if knowledge_point:
                                    query_parts.append(f"focus knowledge point {knowledge_point}")

                            search_query = ' '.join(part for part in query_parts if part)
                            namespaces = build_knowledge_retrieval_namespaces(course_id, selected_knowledge_items)
                            merged_docs = []
                            for namespace in namespaces:
                                namespace_docs = hybrid_retriever(search_query, namespace) or []
                                if namespace_docs:
                                    merged_docs.extend(namespace_docs)
                            retrieved_docs = dedupe_retrieved_docs(merged_docs)
                            retrieved_docs = filter_retrieved_docs_by_selected_items(
                                retrieved_docs,
                                selected_knowledge_items
                            )
                        else:
                            retrieved_docs = hybrid_retriever(message, str(course_id))
                    
                    # 添加调试日志，查看文档元数据
                    app_logger.info(f"retrieved docs: {len(retrieved_docs) if retrieved_docs else 0}")
                    for i, doc in enumerate(retrieved_docs[:3]):  # 鍙褰曞墠3涓枃妗ｇ殑鍏冩暟鎹紝閬垮厤鏃ュ織杩囬暱
                        app_logger.info(f"鏂囨。 {i+1} 鍏冩暟鎹? {doc.metadata}")
                    
                    # 鏍煎紡鍖栨绱㈠埌鐨勬枃妗?
                    if retrieved_docs:
                        # 纭繚format_docs涓嶆槸None
                        if format_docs is None:
                            app_logger.error("format_docs鏈垵濮嬪寲")
                            context = "\n".join([doc.page_content for doc in retrieved_docs])
                        else:
                            context = format_docs(retrieved_docs)
                        
                        # 鎻愬彇鏂囨。婧愪俊鎭?- 鏀硅繘鐨勭増鏈?
                        selected_knowledge_lookup = _build_selected_knowledge_lookup(selected_knowledge_items)
                        for doc in retrieved_docs:
                            # 妫€鏌ュ绉嶅彲鑳界殑鍏冩暟鎹瓧娈?
                            source_url = None
                            source_title = None
                            
                            # 灏濊瘯浠庝笉鍚岀殑鍏冩暟鎹瓧娈佃幏鍙栨簮URL
                            if 'source' in doc.metadata:
                                source_url = doc.metadata['source']
                            elif 'file_path' in doc.metadata:
                                source_url = doc.metadata['file_path']
                            elif 'path' in doc.metadata:
                                source_url = doc.metadata['path']
                            
                            # 如果找到了源URL
                            if source_url:
                                selected_mapping = _match_selected_knowledge_item(
                                    source_url,
                                    source_title,
                                    selected_knowledge_lookup
                                )
                                # 灏濊瘯浠庝笉鍚岀殑鍏冩暟鎹瓧娈佃幏鍙栨爣棰?
                                if selected_mapping.get('file_name'):
                                    source_title = str(selected_mapping.get('file_name')).strip()
                                elif 'title' in doc.metadata and doc.metadata['title']:
                                    source_title = doc.metadata['title']
                                elif 'file_name' in doc.metadata and doc.metadata['file_name']:
                                    source_title = doc.metadata['file_name']
                                else:
                                    # 濡傛灉娌℃湁鏍囬锛屼娇鐢ㄦ枃浠跺悕
                                    source_title = os.path.basename(source_url)
                                    # 绉婚櫎鏂囦欢鎵╁睍鍚?
                                    source_title = os.path.splitext(source_title)[0]
                                    # 缇庡寲鏍囬鏍煎紡
                                    source_title = source_title.replace('-', ' ').replace('_', ' ')
                                
                                # 娣诲姞椤电爜鎴栫珷鑺備俊鎭紙濡傛灉鏈夛級
                                source_info = ""
                                if 'page' in doc.metadata and doc.metadata['page'] is not None:
                                    page_num = doc.metadata['page']
                                    source_info += f"第{page_num + 1}页" if isinstance(page_num, int) else f"第{page_num}页"
                                
                                if 'chunk_id' in doc.metadata and doc.metadata['chunk_id']:
                                    chunk_id = doc.metadata['chunk_id']
                                    if chunk_id.startswith('chunk_'):
                                        chunk_num = chunk_id[6:]
                                        if source_info:
                                            source_info += f", 鐗囨{chunk_num}"
                                        else:
                                            source_info += f"鐗囨{chunk_num}"
                                
                                # 濡傛灉鏈夐澶栦俊鎭紝娣诲姞鍒版爣棰樹腑
                                if source_info:
                                    full_title = f"{source_title} ({source_info})"
                                else:
                                    full_title = source_title
                                
                                # 妫€鏌ユ槸鍚﹀凡缁忔坊鍔犺繃杩欎釜婧?
                                if source_url not in [s.get('url') for s in sources]:
                                    sources.append({
                                        'title': full_title,
                                        'url': source_url
                                    })
                        
                        # 记录提取的源信息
                        app_logger.info(f"提取的源信息: {sources}")
                    else:
                        structured_context, structured_sources, structured_mode = build_structured_index_context(
                            course_id=course_id,
                            message=message,
                            course_name=resolved_course.name if resolved_course else "",
                        )
                        if structured_context:
                            context = structured_context
                            sources = structured_sources
                            context_mode = structured_mode or "structured_index"
                        else:
                            fallback_instruction = build_natural_fallback_instruction(
                                course_id=course_id,
                                course_name=resolved_course.name if resolved_course else "",
                                reason="no_relevant_docs",
                            )
                            use_rag = False
                    
                    if use_rag and context:
                        reference_mode_instruction = (
                            "以下参考资料是教材的结构化索引摘要与目录，不是逐字原文。请优先依据这些结构化线索回答，并清楚区分“教材目录/摘要可确认的信息”与“你补充的通用解释”。"
                            if context_mode == "structured_index"
                            else "请优先直接引用参考资料中的内容，尽可能保留原始表述的关键细节。"
                        )

                        # 构建带有上下文的系统提示
                        system_prompt = f"""浣犳槸涓€涓櫤鑳芥暀鑲插姪鎵嬶紝鍚嶄负易度新星 EduNova銆備綘鐨勪换鍔℃槸甯姪瀛︾敓瑙ｇ瓟闂銆佹彁渚涘涔犲缓璁拰瑙ｉ噴澶嶆潅姒傚康銆?
浣犳鍦ㄨ緟鍔╀互涓嬭绋嬬殑瀛︿範锛?
{course_info}
{course_context_prompt}
{selected_knowledge_prompt}

璇峰熀浜庝互涓嬪弬鑰冭祫鏂欏洖绛旂敤鎴风殑闂銆傝閬靛惊浠ヤ笅鎸囧鍘熷垯锛?

1. {reference_mode_instruction}
2. 涓嶈杩囧害姒傛嫭鎴栫畝鍖栧弬鑰冭祫鏂欎腑鐨勬妧鏈粏鑺傘€佷唬鐮佺ず渚嬫垨姝ラ璇存槑
3. 濡傛灉鍙傝€冭祫鏂欎腑鍖呭惈瀹屾暣鐨勬暀绋嬫垨姝ラ锛岃瀹屾暣淇濈暀杩欎簺姝ラ鐨勯『搴忓拰缁嗚妭
4. 瀵逛簬浠ｇ爜绀轰緥锛屼繚鎸佸師鏍峰紩鐢紝涓嶈绠€鍖栨垨淇敼
5. 鍙湁鍦ㄥ弬鑰冭祫鏂欎腑淇℃伅鏈夐檺鎴栨病鏈夌浉鍏充俊鎭椂锛屾墠浣跨敤浣犺嚜韬殑鐭ヨ瘑杩涜琛ュ厖
6.  鍦ㄥ洖绛旂粨鏉熸椂锛屽繀椤绘坊鍔犱竴琛?鍙傝€冩潵婧?"锛岀劧鍚庡垪鍑轰綘浣跨敤鐨勬墍鏈夊弬鑰冭祫鏂?"

浣犵殑鍥炵瓟搴旇灏藉彲鑳藉湴蹇犱簬鍙傝€冭祫鏂欎腑鐨勫師濮嬪唴瀹癸紝鍚屾椂淇濇寔鍙嬪ソ銆佷笓涓氫笖鏄撲簬鐞嗚В锛屽綋鍙傝€冭祫鏂欏畬鍏ㄦ棤娉曟弧瓒宠姹傛椂锛屼綘鍐嶅紑濮嬭€冭檻鐢ㄨ嚜宸辩殑鐭ヨ瘑杩涜鍥炵瓟銆?

鍙傝€冭祫鏂?
{context}"""
                        
                        # 鍑嗗API璇锋眰浣?
                        payload = {
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                *history[-5:]  # 鍙娇鐢ㄦ渶杩?鏉″璇濆巻鍙诧紝閬垮厤token杩囧
                            ],
                            "temperature": 0.7,
                            "max_tokens": 4000,
                            "stream": stream
                        }
                        
                        app_logger.info("built RAG-enhanced request successfully")
                except Exception as e:
                    app_logger.error(f"RAG妫€绱㈠け璐? {str(e)}")
                    structured_context, structured_sources, structured_mode = build_structured_index_context(
                        course_id=course_id,
                        message=message,
                        course_name=resolved_course.name if resolved_course else "",
                    )
                    if structured_context:
                        context = structured_context
                        sources = structured_sources
                        context_mode = structured_mode or "structured_index"
                        system_prompt = f"""浣犳槸涓€涓櫤鑳芥暀鑲插姪鎵嬶紝鍚嶄负易度新星 EduNova銆備綘鐨勪换鍔℃槸甯姪瀛︾敓瑙ｇ瓟闂銆佹彁渚涘涔犲缓璁拰瑙ｉ噴澶嶆潅姒傚康銆?
浣犳鍦ㄨ緟鍔╀互涓嬭绋嬬殑瀛︿範锛?
{course_info}
{course_context_prompt}
{selected_knowledge_prompt}

当前没有直接拿到教材原文片段，但拿到了教材的结构化索引摘要、目录和关键词。请先基于这些结构化线索回答，并明确哪些结论来自教材摘要，哪些是你补充的通用解释。不要提及内部检索失败。

参考资料：
{context}"""
                        payload = {
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                *history[-5:]
                            ],
                            "temperature": 0.7,
                            "max_tokens": 4000,
                            "stream": stream
                        }
                    else:
                        fallback_instruction = build_natural_fallback_instruction(
                            course_id=course_id,
                            course_name=resolved_course.name if resolved_course else "",
                            reason="retrieval_error",
                        )
                        use_rag = False
            else:
                app_logger.warning("RAG unavailable in strict knowledge mode")
                fallback_instruction = build_natural_fallback_instruction(
                    course_id=course_id,
                    course_name=resolved_course.name if resolved_course else "",
                    reason="rag_unavailable",
                )
                use_rag = False
        
        # 濡傛灉涓嶄娇鐢≧AG鎴朢AG妫€绱㈠け璐?
        if not use_rag or (not course_id and not selected_knowledge_items) or not context:
            # 鍑嗗鏅€氬璇濈殑API璇锋眰浣?
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是 易度新星 EduNova 智能学习助手，回答时优先结合当前会话中的课程上下文。"
                            f"{course_context_prompt}"
                            f"{selected_knowledge_prompt}"
                            + (
                                f"\n当前课程信息：\n{course_info}\n"
                                if course_info
                                else "\n当前未选择具体课程时，再按通用学习助手方式回答。\n"
                            )
                            + (f"\n{fallback_instruction}\n" if fallback_instruction else "")
                        )
                    },
                    *history
                ],
                "temperature": 0.7,
                "max_tokens": 4000,
                "stream": stream
            }
        
        # 如果请求流式输出
        if stream:
            def generate():
                # 流式请求
                with requests.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=120  # 澧炲姞瓒呮椂鏃堕棿鍒?20绉?
                ) as response:
                    
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'status': 'error', 'message': f'API调用失败: {response.text}'})}\n\n"
                        return
                    
                    # 鍒濆鍖栧彉閲忥紝鐢ㄤ簬鏀堕泦瀹屾暣鐨勫洖澶?
                    full_response = ""
                    
                    # 处理流式响应
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode('utf-8')
                            if line_text.startswith('data: '):
                                line_json = line_text[6:]  # 移除 'data: ' 前缀
                                if line_json.strip() == '[DONE]':
                                    break
                                
                                try:
                                    chunk = json.loads(line_json)
                                    if 'choices' in chunk and len(chunk['choices']) > 0:
                                        if 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                                            content = chunk['choices'][0]['delta']['content']
                                            if content:
                                                full_response += content
                                                # 鍙戦€佹暟鎹埌瀹㈡埛绔?
                                                yield f"data: {json.dumps({'content': content})}\n\n"
                                except json.JSONDecodeError:
                                    continue
                
                # 娴佸紡鍝嶅簲缁撴潫鍚庯紝淇濆瓨瀹屾暣鍥炲鍒版暟鎹簱
                ai_response = full_response.lstrip()
                ai_chat = ChatHistory(
                    user_id=user_id,
                    course_id=course_id,
                    conversation_id=conversation_id,
                    role='assistant',
                    message=ai_response,
                    timestamp=int(time.time())
                )
                db.session.add(ai_chat)
                db.session.commit()
                
                # 鍙戦€佺粨鏉熶俊鍙凤紝鍖呭惈寮曠敤婧?
                yield f"data: {json.dumps({'status': 'done', 'conversation_id': conversation_id, 'sources': sources})}\n\n"
            
            return Response(stream_with_context(generate()), content_type='text/event-stream')
        
        # 闈炴祦寮忚姹?
        else:
            # 鍙戦€佽姹?
            response = requests.post(
                f"{api_base}/chat/completions", 
                headers=headers, 
                json=payload,
                timeout=60  # 设置超时时间
            )
            
            # 妫€鏌ュ搷搴?
            if response.status_code != 200:
                return jsonify({
                    'status': 'error',
                    'message': f'API调用失败: {response.text}'
                }), 500
                
            # 解析响应
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            # 鍘婚櫎寮€澶寸殑绌鸿
            ai_response = ai_response.lstrip()
            
            # 淇濆瓨AI鍥炲鍒版暟鎹簱
            ai_chat = ChatHistory(
                user_id=user_id,
                course_id=course_id,  # 鍙兘涓篘one
                conversation_id=conversation_id,
                role='assistant',
                message=ai_response,
                timestamp=int(time.time())
            )
            db.session.add(ai_chat)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'response': {
                    'content': ai_response,
                    'sources': sources,  # 包含引用来源
                    'conversation_id': conversation_id
                }
            })
        
    except Exception as e:
        app_logger.error(f"AI chat error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'澶勭悊璇锋眰鏃跺嚭閿? {str(e)}'
        }), 500

@rag_api.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """获取聊天历史"""
    app_logger = current_app.logger
    user_id = get_jwt_identity()
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '对话ID不能为空'}), 400
    
    try:
        # 获取历史对话记录
        chat_history = ChatHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id
        ).order_by(ChatHistory.timestamp.asc()).all()
        
        # 鏍煎紡鍖栧巻鍙茶褰?
        history = []
        for chat in chat_history:
            history.append({
                'role': chat.role,
                'content': chat.message,
                'timestamp': chat.timestamp
            })

        versions = _extract_lesson_plan_versions_from_history(chat_history)
        
        return jsonify({
            'status': 'success',
            'history': history,
            'versions': versions,
        })
        
    except Exception as e:
        app_logger.error(f"Get chat history error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取聊天历史失败: {str(e)}'
        }), 500

@rag_api.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get all conversations for current user."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()
    course_id = request.args.get('course_id')
    
    try:
        # 鏋勫缓鏌ヨ
        query = db.session.query(
            ChatHistory.conversation_id,
            db.func.min(ChatHistory.timestamp).label('start_time'),
            db.func.max(ChatHistory.timestamp).label('last_time')
        ).filter(ChatHistory.user_id == user_id)
        
        # 濡傛灉鎸囧畾浜嗚绋婭D锛屽垯杩囨护
        if course_id:
            query = query.filter(ChatHistory.course_id == course_id)
        
        # 鎸夊璇滻D鍒嗙粍骞舵寜鏈€鍚庢椂闂存帓搴?
        conversations = query.group_by(
            ChatHistory.conversation_id
        ).order_by(db.desc('last_time')).all()
        
        # 鑾峰彇姣忎釜瀵硅瘽鐨勭涓€鏉℃秷鎭綔涓烘爣棰?
        result = []
        for conv_id, start_time, last_time in conversations:
            # 鑾峰彇绗竴鏉＄敤鎴锋秷鎭綔涓烘爣棰?
            first_message = ChatHistory.query.filter_by(
                conversation_id=conv_id,
                user_id=user_id,
                role='user'
            ).order_by(ChatHistory.timestamp.asc()).first()
            
            # 获取消息数量
            message_count = ChatHistory.query.filter_by(
                conversation_id=conv_id,
                user_id=user_id,
            ).count()

            conversation_messages = ChatHistory.query.filter_by(
                conversation_id=conv_id,
                user_id=user_id,
            ).order_by(ChatHistory.timestamp.asc()).all()
            conversation_course_id = next(
                (getattr(message, 'course_id', None) for message in reversed(conversation_messages) if getattr(message, 'course_id', None)),
                None,
            )
            versions = _extract_lesson_plan_versions_from_history(conversation_messages)
            outline_type = _infer_outline_type_from_conversation(first_message, versions)
            latest_requirement = {}
            if versions:
                latest_requirement = versions[-1].get('lesson_plan_spec', {}).get('requirement_summary', {})
            
            # 澶勭悊鏍囬锛屽鏋渇irst_message涓篘one锛屼娇鐢ㄩ粯璁ゆ爣棰?
            title = '鏂板璇?'
            if first_message and first_message.message:
                title = str(first_message.message).strip()
            display_title = _build_history_display_title(latest_requirement, last_time, title)
            grade_parts = _parse_grade_subject_parts(latest_requirement.get('grade_subject'))
            
            result.append({
                'conversation_id': conv_id,
                'title': title,
                'display_title': display_title,
                'course_id': int(conversation_course_id) if conversation_course_id else None,
                'start_time': start_time,
                'last_time': last_time,
                'message_count': message_count,
                'outline_type': outline_type,
                'subject': grade_parts.get('subject') or '',
                'grade': grade_parts.get('grade') or '',
                'chapter_title': str(latest_requirement.get('chapter_title') or '').strip(),
                'topic': str(latest_requirement.get('topic') or '').strip(),
            })
        
        return jsonify({
            'status': 'success',
            'conversations': result
        })
        
    except Exception as e:
        app_logger.error(f"Get conversations error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取对话列表失败: {str(e)}'
        }), 500

@rag_api.route('/conversations/<conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Delete a lesson-plan conversation and its generated artifacts."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()
    normalized_conversation_id = str(conversation_id or '').strip()

    if not normalized_conversation_id:
        return jsonify({'status': 'error', 'message': 'conversation_id is required'}), 400

    try:
        chat_history = ChatHistory.query.filter_by(
            conversation_id=normalized_conversation_id,
            user_id=user_id,
        ).order_by(ChatHistory.timestamp.asc(), ChatHistory.id.asc()).all()
        if not chat_history:
            return jsonify({'status': 'error', 'message': 'Conversation not found'}), 404

        payloads = _extract_lesson_plan_versions_from_history(chat_history)
        generated_material_ids = _collect_generated_material_ids_from_payloads(payloads)

        referenced_material_ids = set()
        if generated_material_ids:
            other_assistant_messages = ChatHistory.query.filter(
                ChatHistory.conversation_id != normalized_conversation_id,
                ChatHistory.role == 'assistant',
            ).all()
            for chat in other_assistant_messages:
                payload = _parse_lesson_plan_payload_message(
                    content=getattr(chat, 'message', ''),
                    fallback_created_at=getattr(chat, 'timestamp', None),
                )
                if not payload:
                    continue
                referenced_material_ids.update(_normalize_generated_assets(payload.get('generated_assets')).values())

        deleted_material_ids: List[int] = []
        skipped_material_ids: List[int] = []
        deleted_cache_files = 0
        deleted_files = 0

        for material_id in generated_material_ids:
            if material_id in referenced_material_ids:
                skipped_material_ids.append(material_id)
                continue

            material = Material.query.get(material_id)
            if not material:
                continue

            deleted_files += int(_safe_remove_file(material.file_path))
            deleted_files += int(_safe_remove_file(material.preview_file_path))
            deleted_cache_files += _cleanup_material_processed_cache(material.file_hash)
            db.session.delete(material)
            deleted_material_ids.append(material_id)

        deleted_message_count = ChatHistory.query.filter_by(
            conversation_id=normalized_conversation_id,
            user_id=user_id,
        ).delete(synchronize_session=False)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'conversation_id': normalized_conversation_id,
            'deleted_message_count': deleted_message_count,
            'deleted_material_ids': deleted_material_ids,
            'skipped_material_ids': skipped_material_ids,
            'deleted_files': deleted_files,
            'deleted_cache_files': deleted_cache_files,
        })
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"delete conversation failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'删除备课历史失败: {str(e)}'
        }), 500

@rag_api.route('/recommendations', methods=['GET'])
@jwt_required()
def get_learning_recommendations():
    """??????"""
    app_logger = current_app.logger
    user_id = get_jwt_identity()
    course_id = request.args.get('course_id')

    try:
        if course_id:
            recommendations = [
                {
                    'title': '??????',
                    'description': '?????????????????????????',
                    'link': f'/course/{course_id}/materials'
                },
                {
                    'title': '????',
                    'description': '???????????????????????????',
                    'link': f'/course/{course_id}/assessments'
                },
                {
                    'title': '????',
                    'description': '???????????????????????????',
                    'link': f'/course/{course_id}/discussions'
                }
            ]
        else:
            recommendations = [
                {
                    'title': '????',
                    'description': '????????????????????????',
                    'link': '/courses'
                },
                {
                    'title': '??????',
                    'description': '????????????????????????',
                    'link': '/dashboard'
                },
                {
                    'title': '??????',
                    'description': '????????????????????',
                    'link': '/resources'
                }
            ]

        return jsonify({
            'status': 'success',
            'recommendations': recommendations
        })

    except Exception as e:
        app_logger.error(f"AI recommendations error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'????????: {str(e)}'
        }), 500

@rag_api.route('/knowledge/add', methods=['POST'])
@jwt_required()
def add_to_knowledge_base():
    """Add a file to the knowledge base processing queue"""
    # 鏈湴瀵煎叆浠ラ伩鍏嶅惊鐜鍏?
    from backend.tasks.rag_processor import start_processing_queue_item
    current_user = get_authenticated_user()
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': '鏃犳晥鐨勮姹傛暟鎹?'}), 400
        
    course_id = data.get('course_id')
    file_path = data.get('file_path')
    purpose = normalize_purpose(data.get('purpose', 'general'), default='general')
    
    if not course_id or not file_path:
        return jsonify({'status': 'error', 'message': '鍙傛暟涓嶅畬鏁?'}), 400
    if not purpose:
        return jsonify({'status': 'error', 'message': 'purpose 浠呮敮鎸?general 鎴?lesson_plan'}), 400

    course = Course.query.get(course_id)
    access_error = ensure_course_knowledge_access(course, current_user)
    if access_error:
        return access_error

    normalized_file_path = normalize_knowledge_file_path(file_path)
    if not normalized_file_path:
        return jsonify({'status': 'error', 'message': '文件路径无效'}), 400
    
    # Validate file exists
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], normalized_file_path)
    if not os.path.exists(full_path):
        return jsonify({'status': 'error', 'message': '鏂囦欢涓嶅瓨鍦?'}), 404
    
    # 璁＄畻鏂囦欢鍝堝笇鍊?
    file_hash = calculate_file_hash(full_path)
    if not file_hash:
        return jsonify({'status': 'error', 'message': '鏃犳硶璁＄畻鏂囦欢鍝堝笇鍊?'}), 500
    
    # 妫€鏌ユ槸鍚﹀凡瀛樺湪鐩稿悓鍝堝笇鍊肩殑鏂囦欢
    existing_items = (
        KnowledgeBaseQueue.query
        .filter_by(file_hash=file_hash, course_id=course_id)
        .order_by(KnowledgeBaseQueue.id.desc())
        .all()
    )
    if existing_items:
        active_item = next((item for item in existing_items if item.status in ['pending', 'processing']), None)
        completed_item = next((item for item in existing_items if item.status == 'completed'), None)
        failed_item = next((item for item in existing_items if item.status == 'failed'), None)
        existing_file = active_item or completed_item or failed_item or existing_items[0]

        # 濡傛灉鏂囦欢宸插湪闃熷垪涓鐞?
        if active_item:
            return jsonify({
                'status': 'error',
                'message': '鏂囦欢宸插湪澶勭悊闃熷垪涓?,',
                'queue_id': active_item.id,
                'progress': active_item.progress,
                'file_hash': file_hash
            }), 409

        # 濡傛灉鏂囦欢宸插瓨鍦ㄤ絾鐢ㄩ€斾笉鍚岋紝鏇存柊鐢ㄩ€?
        if existing_file.purpose != purpose and existing_file.purpose == 'general':
            existing_file.purpose = purpose

        # 濡傛灉鏂囦欢宸插畬鎴愬鐞嗘垨澶辫触锛岄兘鍙互閲嶆柊澶勭悊
        if completed_item or failed_item:
            retry_item = failed_item or completed_item or existing_file
            retry_item.file_path = normalized_file_path
            retry_item.status = 'pending'
            retry_item.progress = 0.0
            retry_item.error_message = None
            retry_item.completed_at = None
            retry_item.progress_detail = None
            retry_item.last_updated = int(time.time())
            retry_item.purpose = purpose
            db.session.commit()

            # Start processing in background
            start_processing_queue_item(retry_item.id)

            return jsonify({
                'status': 'success',
                'message': '鏂囦欢宸查噸鏂版坊鍔犲埌鐭ヨ瘑搴撳鐞嗛槦鍒?,',
                'queue_id': retry_item.id,
                'file_hash': file_hash
            })
    
    # Add to queue
    queue_item = KnowledgeBaseQueue(
        course_id=course_id,
        file_path=normalized_file_path,
        file_hash=file_hash,
        purpose=purpose
    )
    db.session.add(queue_item)
    db.session.commit()
    
    # Start processing in background
    start_processing_queue_item(queue_item.id)
    
    return jsonify({
        'status': 'success',
        'message': '鏂囦欢宸叉坊鍔犲埌鐭ヨ瘑搴撳鐞嗛槦鍒?,',
        'queue_id': queue_item.id,
        'file_hash': file_hash
    })

@rag_api.route('/knowledge/status', methods=['GET'])
@jwt_required()
def get_knowledge_base_status():
    """Get the status of the knowledge base processing queue"""
    current_user = get_authenticated_user()
    course_id = request.args.get('course_id')
    cleanup_stale_material_and_queue_records(course_id=course_id)

    query = KnowledgeBaseQueue.query
    if course_id:
        course = Course.query.get(course_id)
        access_error = ensure_course_knowledge_access(course, current_user)
        if access_error:
            return access_error
        query = query.filter_by(course_id=course_id)
    elif current_user and current_user.role != 'admin':
        query = query.join(Course, KnowledgeBaseQueue.course_id == Course.id)
        if current_user.role == 'teacher':
            query = query.filter(Course.teacher_id == current_user.id)
        elif current_user.role == 'student':
            query = query.filter(Course.students.any(User.id == current_user.id))
        else:
            query = query.filter(Course.id == -1)

    queue_items = query.order_by(
        KnowledgeBaseQueue.created_at.desc(),
        KnowledgeBaseQueue.id.desc()
    ).all()
    
    result = []
    for item in queue_items:
        result.append(item.to_dict())
    
    return jsonify({
        'status': 'success',
        'items': result
    })

@rag_api.route('/knowledge/supported-types', methods=['GET'])
def get_supported_file_types():
    """Get the list of file types supported for knowledge base processing"""
    supported_types = [
        {'extension': '.pdf', 'description': 'PDF文档'},
        {'extension': '.docx', 'description': 'Word文档'},
        {'extension': '.doc', 'description': 'Word文档'},
        {'extension': '.ppt', 'description': 'PowerPoint文档'},
        {'extension': '.pptx', 'description': 'PowerPoint文档'},
        {'extension': '.txt', 'description': '文本文件'},
        {'extension': '.md', 'description': 'Markdown文件'},
    ]
    
    return jsonify({
        'status': 'success',
        'supported_types': supported_types
    })

@rag_api.route('/knowledge/process_now', methods=['POST'])
@jwt_required()
def process_knowledge_now():
    """Process a file immediately and add it to the knowledge base."""
    try:
        current_user = get_authenticated_user()
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '鏃犳晥鐨勮姹傛暟鎹?'}), 400
            
        course_id = data.get('course_id')
        file_path = data.get('file_path')
        
        if not course_id or not file_path:
            return jsonify({'status': 'error', 'message': '缂哄皯蹇呰鍙傛暟'}), 400

        course = Course.query.get(course_id)
        access_error = ensure_course_teacher_access(course, current_user)
        if access_error:
            return access_error

        normalized_file_path = normalize_knowledge_file_path(file_path)
        if not normalized_file_path:
            return jsonify({'status': 'error', 'message': '文件路径无效'}), 400
        
        # 纭繚鏂囦欢瀛樺湪
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], normalized_file_path)
        if not os.path.exists(full_path):
            return jsonify({'status': 'error', 'message': f'鏂囦欢涓嶅瓨鍦? {normalized_file_path}'}), 404
        
        # 获取当前用户
        # current_user_id = get_jwt_identity()
        
        try:
            # 直接处理文件
            from backend.rag.create_db import process_document_with_progress
            
            # 鍒涘缓涓€涓畝鍗曠殑杩涘害鍥炶皟鍑芥暟
            def progress_callback(progress):
                print(f"处理进度: {progress}%")
            
            # 直接处理文件
            success = process_document_with_progress(
                str(course_id), 
                full_path, 
                progress_callback=progress_callback
            )
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': '鏂囦欢宸叉垚鍔熷鐞嗗苟娣诲姞鍒扮煡璇嗗簱'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '文件处理失败'
                }), 500
                
        except Exception as e:
            current_app.logger.error(f"澶勭悊鏂囦欢鏃跺嚭閿? {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'澶勭悊鏂囦欢鏃跺嚭閿? {str(e)}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"澶勭悊璇锋眰鏃跺嚭閿? {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'澶勭悊璇锋眰鏃跺嚭閿? {str(e)}'
        }), 500

@rag_api.route('/knowledge/remove', methods=['DELETE'])
@jwt_required()
def remove_from_knowledge_base():
    """Remove a file from the knowledge base"""
    try:
        current_user = get_authenticated_user()
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '鏃犳晥鐨勮姹傛暟鎹?'}), 400
            
        queue_id = data.get('queue_id')
        
        if not queue_id:
            return jsonify({'status': 'error', 'message': '缺少队列ID'}), 400
        
        # 鏌ユ壘闃熷垪椤?
        queue_item = db.session.get(KnowledgeBaseQueue, queue_id)
        access_error = ensure_queue_item_teacher_access(queue_item, current_user)
        if access_error:
            return access_error

        cleanup_summary = purge_knowledge_assets_for_queue_item(queue_item)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '文件及其知识库缓存已彻底删除',
            'cleanup': cleanup_summary,
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"鍒犻櫎鏂囦欢鏃跺嚭閿? {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'鍒犻櫎鏂囦欢鏃跺嚭閿? {str(e)}'
        }), 500

@rag_api.route('/knowledge/clear-queue', methods=['DELETE'])
@jwt_required()
def clear_knowledge_base_queue():
    """Clear the knowledge base processing queue for a course"""
    try:
        current_user = get_authenticated_user()
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '鏃犳晥鐨勮姹傛暟鎹?'}), 400
            
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'status': 'error', 'message': '缺少课程ID'}), 400

        course = Course.query.get(course_id)
        access_error = ensure_course_teacher_access(course, current_user)
        if access_error:
            return access_error

        # 鏌ユ壘鎵€鏈夊緟澶勭悊鍜屽鐞嗕腑鐨勯槦鍒楅」
        queue_items = KnowledgeBaseQueue.query.filter_by(course_id=course_id).filter(
            KnowledgeBaseQueue.status.in_(['pending', 'processing'])
        ).all()
        
        if not queue_items:
            return jsonify({
                'status': 'success',
                'message': '娌℃湁寰呭鐞嗙殑闃熷垪椤?,',
                'count': 0
            })
        
        # 鍒犻櫎鎵€鏈夐槦鍒楅」
        count = 0
        for item in queue_items:
            db.session.delete(item)
            count += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'鎴愬姛娓呯┖{count}涓槦鍒楅」',
            'count': count
        })
        
    except Exception as e:
        current_app.logger.error(f"娓呯┖闃熷垪鏃跺嚭閿? {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'娓呯┖闃熷垪鏃跺嚭閿? {str(e)}'
        }), 500

@rag_api.route('/knowledge/batch-remove', methods=['DELETE'])
@jwt_required()
def batch_remove_from_knowledge_base():
    """Batch remove files from the knowledge base"""
    try:
        current_user = get_authenticated_user()
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '鏃犳晥鐨勮姹傛暟鎹?'}), 400
            
        queue_ids = data.get('queue_ids', [])
        
        if not queue_ids:
            return jsonify({'status': 'error', 'message': '缺少队列ID列表'}), 400
        
        deleted_count = 0
        failed_count = 0
        deleted_queue_ids = set()
        deleted_material_ids = set()
        deleted_files = 0
        deleted_cache_files = 0

        queue_items = KnowledgeBaseQueue.query.filter(KnowledgeBaseQueue.id.in_(queue_ids)).all()
        queue_item_map = {item.id: item for item in queue_items}

        for queue_id in queue_ids:
            try:
                queue_item = queue_item_map.get(queue_id)
                if not queue_item:
                    failed_count += 1
                    continue
                access_error = ensure_queue_item_teacher_access(queue_item, current_user)
                if access_error:
                    failed_count += 1
                    continue

                if queue_item.id in deleted_queue_ids:
                    continue

                cleanup_summary = purge_knowledge_assets_for_queue_item(queue_item)
                deleted_queue_ids.update(cleanup_summary.get('deleted_queue_ids', []))
                deleted_material_ids.update(cleanup_summary.get('deleted_material_ids', []))
                deleted_files += int(cleanup_summary.get('deleted_files', 0) or 0)
                deleted_cache_files += int(cleanup_summary.get('deleted_cache_files', 0) or 0)
                deleted_count += 1
            except Exception as e:
                current_app.logger.error(f"鍒犻櫎闃熷垪椤?{queue_id} 鏃跺嚭閿? {str(e)}")
                failed_count += 1
        
        db.session.commit()
        
        message = f'鎵归噺鍒犻櫎瀹屾垚锛屾垚鍔熷垹闄?{deleted_count} 涓」鐩?'
        if failed_count > 0:
            message += f'锛屽け璐?{failed_count} 涓」鐩?'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'deleted_queue_ids': sorted(deleted_queue_ids),
            'deleted_material_ids': sorted(deleted_material_ids),
            'deleted_files': deleted_files,
            'deleted_cache_files': deleted_cache_files,
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量删除知识库文件时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'批量删除失败: {str(e)}'
        }), 500

@rag_api.route('/generate-lesson-plan', methods=['POST'])
@jwt_required()
def generate_lesson_plan():
    """Generate lesson_plan_spec and persist it as structured history."""
    app_logger = current_app.logger
    app_logger.info('received generate lesson plan request')

    data = request.json
    if not data:
        app_logger.error('invalid request payload')
        return jsonify({'status': 'error', 'message': 'invalid request payload'}), 400

    user_id = get_jwt_identity()
    app_logger.info(f'user_id: {user_id}')

    outline_type = data.get('outlineType', 'course')
    course_id = data.get('courseId')
    chapter_id = data.get('chapterId')
    grade_subject = data.get('gradeSubject')
    duration = data.get('duration', '')
    learning_objectives = data.get('learningObjectives', '')
    key_points = data.get('keyPoints', '')
    student_level = data.get('studentLevel', '')
    custom_student_level = data.get('customStudentLevel', '')
    activities = data.get('activities', [])
    teaching_style = data.get('teachingStyle', '')
    assessment_methods = data.get('assessmentMethods', [])
    detail_level = data.get('detailLevel', 2)
    free_teaching_idea = data.get('freeTeachingIdea', '')
    clarified_requirement = data.get('clarifiedRequirement')
    structured_requirement = data.get('structuredRequirement')

    use_knowledge_base = data.get('useKnowledgeBase', False)
    temp_files = data.get('tempFiles', [])
    source_mappings_raw = data.get('sourceMappings', [])
    selected_knowledge_items = parse_selected_knowledge_items(data.get('selectedKnowledgeItems', []))
    if selected_knowledge_items:
        selected_knowledge_validation = validate_selected_knowledge_items(selected_knowledge_items)
        if not selected_knowledge_validation.get('ok'):
            return jsonify({
                'status': 'error',
                'message': selected_knowledge_validation.get('message', 'selectedKnowledgeItems validation failed')
            }), 400

    temp_file_result = normalize_temp_file_list(temp_files)
    if not temp_file_result.get('ok'):
        return jsonify({'status': 'error', 'message': temp_file_result.get('message', 'tempFiles validation failed')}), 400
    normalized_temp_files: List[str] = temp_file_result.get('files', [])

    temp_source_mappings: List[Dict[str, Any]] = []
    if normalized_temp_files:
        source_mapping_result = parse_source_mappings(
            raw_mappings=source_mappings_raw,
            normalized_temp_files=normalized_temp_files,
            user_id=user_id,
            upload_root=current_app.config['UPLOAD_FOLDER']
        )
        if not source_mapping_result.get('ok'):
            return jsonify({
                'status': 'error',
                'message': source_mapping_result.get('message', 'sourceMappings validation failed')
            }), 400
        temp_source_mappings = source_mapping_result.get('ordered_mappings', [])

    if not grade_subject:
        app_logger.error('missing required field: gradeSubject')
        return jsonify({'status': 'error', 'message': 'Missing required field: gradeSubject'}), 400

    app_logger.info(f'lesson-plan params: outlineType={outline_type}, gradeSubject={grade_subject}')

    try:
        api_key, api_base, model_name = get_api_config()
        if not api_key or not api_base:
            app_logger.error('API key or base URL is not configured')
            return jsonify({'status': 'error', 'message': 'API key or base URL is not configured'}), 500

        model_name = model_name or 'deepseek-ai/DeepSeek-R1'
        app_logger.info(f'lesson-plan model: {model_name}')

        course_info: Dict[str, Any] = {}
        selected_chapter_title = ''

        if course_id:
            course = Course.query.get(course_id)
            if course:
                course_info = {
                    'name': course.name,
                    'description': course.description or ''
                }

                if outline_type == 'class' and chapter_id:
                    try:
                        chapters_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chapters')
                        course_chapters_folder = os.path.join(chapters_folder, str(course_id))
                        chapters_file_path = os.path.join(course_chapters_folder, 'chapters.json')

                        if os.path.exists(chapters_file_path):
                            with open(chapters_file_path, 'r', encoding='utf-8') as f:
                                chapters_data = json.load(f)

                            try:
                                idx = int(chapter_id) - 1
                                if 0 <= idx < len(chapters_data):
                                    chapter = chapters_data[idx]
                                    selected_chapter_title = chapter.get('title', '')
                            except (ValueError, IndexError):
                                app_logger.warning(f'failed to locate chapter by index, chapter_id={chapter_id}')
                    except Exception as e:
                        app_logger.error(f'load chapter info failed: {str(e)}')

        student_level_text = student_level or custom_student_level
        activities_text = ', '.join([str(x) for x in activities]) if isinstance(activities, list) and activities else ''
        assessment_text = ', '.join([str(x) for x in assessment_methods]) if isinstance(assessment_methods, list) and assessment_methods else ''

        clarified_context = ''
        if isinstance(clarified_requirement, dict) and clarified_requirement:
            try:
                clarified_context = json.dumps(clarified_requirement, ensure_ascii=False)
            except Exception:
                clarified_context = ''

        structured_context = ''
        if isinstance(structured_requirement, dict) and structured_requirement:
            try:
                structured_context = json.dumps(structured_requirement, ensure_ascii=False)
            except Exception:
                structured_context = ''

        form_snapshot = {
            'outlineType': outline_type,
            'courseId': course_id,
            'chapterId': chapter_id,
            'gradeSubject': grade_subject,
            'duration': duration,
            'learningObjectives': learning_objectives,
            'keyPoints': key_points,
            'studentLevel': student_level,
            'customStudentLevel': custom_student_level,
            'activities': activities,
            'teachingStyle': teaching_style,
            'assessmentMethods': assessment_methods,
            'detailLevel': detail_level,
            'freeTeachingIdea': free_teaching_idea,
        }
        requirement_summary_payload = _build_requirement_summary_payload(
            form_snapshot=form_snapshot,
            clarified_requirement=clarified_requirement,
            structured_requirement=structured_requirement,
            chapter_title=selected_chapter_title
        )

        processed_temp_sources: List[Dict[str, Any]] = []
        if normalized_temp_files:
            from backend.rag.source_processing import process_temp_sources

            processed_temp_sources = process_temp_sources(
                file_paths=normalized_temp_files,
                source_mappings=temp_source_mappings,
                upload_root=current_app.config['UPLOAD_FOLDER'],
                user_id=user_id,
                api_key=api_key,
                api_base=api_base,
                model_name=model_name or get_model_primary("text")
            )

        sources: List[Dict[str, Any]] = []
        for source in processed_temp_sources:
            mapping = source.get('mapping') if isinstance(source.get('mapping'), dict) else {}
            sources.append({
                'title': str(mapping.get('file_name') or source.get('title') or '未命名资料').strip(),
                'url': mapping.get('file_path'),
                'purpose': 'temp',
                'mapping': {
                    'usage': mapping.get('usage'),
                    'knowledge_point': mapping.get('knowledge_point'),
                    'is_required': bool(mapping.get('is_required'))
                }
            })

        retrieved_docs: List[Any] = []
        selected_knowledge_lookup = _build_selected_knowledge_lookup(selected_knowledge_items)
        selected_knowledge_identities = set()
        source_urls = {str(source.get('url') or '').strip() for source in sources if str(source.get('url') or '').strip()}
        for item in selected_knowledge_items:
            if not isinstance(item, dict):
                continue
            item_identity = _build_selected_knowledge_identity(item)
            if item_identity and item_identity in selected_knowledge_identities:
                continue
            if item_identity:
                selected_knowledge_identities.add(item_identity)
            source_url = normalize_knowledge_file_path(item.get('file_path')) or str(item.get('file_path') or '').strip()
            if source_url:
                source_urls.add(source_url)
            sources.append({
                'title': str(item.get('file_name') or os.path.basename(source_url) or '知识库资料').strip(),
                'url': source_url,
                'purpose': str(item.get('purpose') or 'general').strip() or 'general',
                'mapping': {
                    'usage': str(item.get('usage') or 'content').strip() or 'content',
                    'knowledge_point': str(item.get('knowledge_point') or '').strip(),
                    'is_required': bool(item.get('is_required'))
                }
            })
        query_terms = build_query_terms(
            requirement_summary=requirement_summary_payload,
            structured_requirement=structured_requirement if isinstance(structured_requirement, dict) else {},
            free_teaching_idea=free_teaching_idea,
        )
        if selected_knowledge_items:
            app_logger.info('knowledge base enhancement enabled')
            try:
                global RAG_AVAILABLE
                if not RAG_AVAILABLE:
                    initialize_rag()

                if RAG_AVAILABLE:
                    from backend.rag.rag_query import hybrid_retriever

                    query_parts = [f'grade_subject {grade_subject}']
                    if outline_type == 'course':
                        query_parts.append('course outline teaching objectives teaching arrangement')
                    else:
                        query_parts.append('class lesson plan teaching flow classroom activity')
                        if selected_chapter_title:
                            query_parts.append(f'chapter {selected_chapter_title}')

                    if learning_objectives:
                        query_parts.append(f'learning objectives {learning_objectives}')
                    if key_points:
                        query_parts.append(f'key points {key_points}')
                    if requirement_summary_payload.get('teaching_goals'):
                        query_parts.append(f"teaching goals {', '.join(requirement_summary_payload['teaching_goals'])}")
                    if requirement_summary_payload.get('knowledge_points'):
                        query_parts.append(f"knowledge points {', '.join(requirement_summary_payload['knowledge_points'])}")
                    if requirement_summary_payload.get('key_points'):
                        query_parts.append(f"key teaching points {', '.join(requirement_summary_payload['key_points'])}")
                    if requirement_summary_payload.get('difficult_points'):
                        query_parts.append(f"teaching difficult points {', '.join(requirement_summary_payload['difficult_points'])}")
                    if requirement_summary_payload.get('style', {}).get('teaching_style'):
                        query_parts.append(f"teaching style {requirement_summary_payload['style']['teaching_style']}")
                    if free_teaching_idea:
                        query_parts.append(f'free teaching idea {free_teaching_idea}')
                    for item in selected_knowledge_items[:8]:
                        file_name = str(item.get('file_name') or '').strip()
                        knowledge_point = str(item.get('knowledge_point') or '').strip()
                        if file_name:
                            query_parts.append(f'selected material {file_name}')
                        if knowledge_point:
                            query_parts.append(f'must cover knowledge point {knowledge_point}')
                    query_parts.extend(query_terms[:8])

                    search_query = ' '.join(query_parts)
                    app_logger.info(f'knowledge query: {search_query}')
                    namespaces = build_knowledge_retrieval_namespaces(course_id, selected_knowledge_items)
                    merged_docs: List[Any] = []
                    for namespace in namespaces:
                        namespace_docs = hybrid_retriever(search_query, namespace) or []
                        if namespace_docs:
                            merged_docs.extend(namespace_docs)

                    retrieved_docs = dedupe_retrieved_docs(merged_docs)
                    retrieved_docs = filter_retrieved_docs_by_selected_items(retrieved_docs, selected_knowledge_items)
                    retrieved_docs.sort(key=lambda doc: 0 if doc.metadata.get('purpose') == 'lesson_plan' else 1)

                    for doc in retrieved_docs:
                        metadata = doc.metadata if isinstance(getattr(doc, 'metadata', None), dict) else {}
                        source_url = str(metadata.get('source') or metadata.get('file_path') or '').strip()
                        normalized_source_url = normalize_knowledge_file_path(source_url) or source_url
                        source_title = str(metadata.get('title') or os.path.basename(normalized_source_url) or normalized_source_url).strip()
                        selected_mapping = _match_selected_knowledge_item(
                            normalized_source_url,
                            source_title,
                            selected_knowledge_lookup,
                        )
                        selected_identity = _build_selected_knowledge_identity(selected_mapping) if selected_mapping else ""
                        if (
                            not normalized_source_url
                            or normalized_source_url in source_urls
                            or (selected_identity and selected_identity in selected_knowledge_identities)
                        ):
                            continue
                        source_urls.add(normalized_source_url)
                        if selected_identity:
                            selected_knowledge_identities.add(selected_identity)
                        sources.append({
                            'title': source_title,
                            'url': normalized_source_url,
                            'purpose': str(metadata.get('purpose') or 'general').strip() or 'general',
                            'mapping': {
                                'usage': str(selected_mapping.get('usage') or 'content').strip() or 'content',
                                'knowledge_point': str(selected_mapping.get('knowledge_point') or metadata.get('knowledge_point') or '').strip(),
                                'is_required': bool(selected_mapping.get('is_required'))
                            } if selected_mapping else None
                        })

                    app_logger.info(
                        f'knowledge docs retrieved: {len(retrieved_docs)}, '
                        f'selected_items={len(selected_knowledge_items)}, namespaces={namespaces}'
                    )
            except Exception as e:
                app_logger.error(f'knowledge retrieval failed: {str(e)}')

        form_context = {
            'student_level': student_level_text,
            'activities': activities if isinstance(activities, list) else [],
            'activities_text': activities_text,
            'teaching_style': teaching_style,
            'assessment_methods': assessment_methods if isinstance(assessment_methods, list) else [],
            'assessment_text': assessment_text,
            'detail_level': detail_level,
            'free_teaching_idea': free_teaching_idea,
            'outline_type': outline_type,
            'chapter_title': selected_chapter_title,
            'clarified_requirement': clarified_requirement if isinstance(clarified_requirement, dict) else {},
            'structured_requirement': structured_requirement if isinstance(structured_requirement, dict) else {},
        }
        source_bundle = build_source_evidence_bundle(
            processed_sources=processed_temp_sources,
            retrieved_docs=retrieved_docs,
            query_terms=query_terms,
            selected_knowledge_items=selected_knowledge_items,
        )
        generation_artifacts = _build_lesson_plan_generation_artifacts(
            api_key=api_key,
            api_base=api_base,
            model_name=model_name,
            course_info=course_info,
            requirement_summary_payload=requirement_summary_payload,
            structured_requirement=structured_requirement if isinstance(structured_requirement, dict) else {},
            form_context=form_context,
            source_bundle=source_bundle,
            course_id=course_id,
            chapter_id=chapter_id,
        )
        normalized_spec = generation_artifacts['normalized_spec']
        core_spec = generation_artifacts['core_spec']
        outline_generation_meta = generation_artifacts['outline_generation_meta']
        source_evidence_meta = {
            'query_terms': source_bundle.get('query_terms', []),
            'source_count': len(source_bundle.get('source_notes', []) or []),
            'evidence_sources': source_bundle.get('source_evidence', []),
            'source_contract': source_bundle.get('source_contract', []),
        }

        created_at = int(time.time())
        conversation_id = f'lesson_plan_{user_id}_{created_at}'
        revision_meta = {
            'version_index': 1,
            'based_on_version_index': None,
            'revision_request': '初始生成',
            'created_at': created_at,
        }
        user_message_lines = [
            "备课生成请求",
            f"大纲类型：{'课程总纲' if outline_type == 'course' else '课堂教案'}",
            f"学段/年级/学科：{grade_subject}",
        ]
        if duration:
            user_message_lines.append(f"课时长度：{duration}")
        user_message_lines.append(f"知识库增强：{'是' if use_knowledge_base else '否'}")
        if selected_chapter_title:
            user_message_lines.append(f"章节：{selected_chapter_title}")
        if learning_objectives:
            user_message_lines.append(f"教学目标：{learning_objectives}")
        if key_points:
            user_message_lines.append(f"教学重点难点：{key_points}")
        user_message_text = "\n".join(user_message_lines)
        assistant_message_payload = json.dumps(
            _build_lesson_plan_payload(
                normalized_spec=normalized_spec,
                sources=sources,
                revision_meta=revision_meta,
                core_spec=core_spec,
                outline_generation_meta=outline_generation_meta,
                source_evidence_meta=source_evidence_meta,
            ),
            ensure_ascii=False
        )

        user_message = ChatHistory(
            user_id=user_id,
            course_id=course_id,
            conversation_id=conversation_id,
            role='user',
            message=user_message_text,
            timestamp=created_at
        )
        db.session.add(user_message)

        ai_message = ChatHistory(
            user_id=user_id,
            course_id=course_id,
            conversation_id=conversation_id,
            role='assistant',
            message=assistant_message_payload,
            timestamp=created_at
        )
        db.session.add(ai_message)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'conversation_id': conversation_id,
            'outline_type': outline_type,
            'selected_chapter': selected_chapter_title,
            'lesson_plan_spec': normalized_spec,
            'sources': sources,
            'revision_meta': revision_meta,
            'core_spec': core_spec,
            'outline_generation_meta': outline_generation_meta,
            'source_evidence_meta': source_evidence_meta,
        })

    except Exception as e:
        db.session.rollback()
        app_logger.error(f'generate lesson plan failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'generate lesson plan failed: {str(e)}'
        }), 500

@rag_api.route('/revise-lesson-plan', methods=['POST'])
@jwt_required()
def revise_lesson_plan():
    """Revise an existing lesson_plan_spec within the same conversation."""
    app_logger = current_app.logger
    data = request.json or {}
    user_id = get_jwt_identity()

    conversation_id = str(data.get('conversation_id') or '').strip()
    revision_request = str(data.get('revision_request') or '').strip()
    raw_spec = data.get('lesson_plan_spec')

    if not conversation_id:
        return jsonify({'status': 'error', 'message': 'conversation_id is required'}), 400
    if not isinstance(raw_spec, dict) or not raw_spec:
        return jsonify({'status': 'error', 'message': 'lesson_plan_spec is required'}), 400
    if not revision_request:
        return jsonify({'status': 'error', 'message': 'revision_request is required'}), 400

    try:
        chat_history = ChatHistory.query.filter_by(
            conversation_id=conversation_id,
            user_id=user_id,
        ).order_by(ChatHistory.timestamp.asc()).all()
        if not chat_history:
            return jsonify({'status': 'error', 'message': 'Conversation not found'}), 404

        versions = _extract_lesson_plan_versions_from_history(chat_history)
        latest_version_index = versions[-1]['revision_meta']['version_index'] if versions else 0
        course_id = next((chat.course_id for chat in reversed(chat_history) if getattr(chat, 'course_id', None)), None)
        course = Course.query.get(course_id) if course_id else None

        requirement_fallback = raw_spec.get('requirement_summary') if isinstance(raw_spec.get('requirement_summary'), dict) else {}
        source_notes_fallback = raw_spec.get('source_notes') if isinstance(raw_spec.get('source_notes'), list) else []
        base_spec = _normalize_lesson_plan_spec(
            raw_spec=raw_spec,
            requirement_summary_fallback=requirement_fallback,
            source_notes_fallback=source_notes_fallback,
        )

        based_on_version_index = latest_version_index or 1
        if versions:
            base_spec_signature = json.dumps(base_spec, ensure_ascii=False, sort_keys=True)
            for version in versions:
                version_signature = json.dumps(version.get('lesson_plan_spec') or {}, ensure_ascii=False, sort_keys=True)
                if version_signature == base_spec_signature:
                    based_on_version_index = version['revision_meta']['version_index']
                    break

        sources = versions[-1].get('sources', []) if versions else []
        latest_core_spec = versions[-1].get('core_spec') if versions and isinstance(versions[-1].get('core_spec'), dict) else {}
        latest_source_evidence_meta = versions[-1].get('source_evidence_meta') if versions and isinstance(versions[-1].get('source_evidence_meta'), dict) else {}
        api_key, api_base, model_name = get_api_config()
        if not api_key or not api_base:
            return jsonify({'status': 'error', 'message': 'API key or base URL is not configured'}), 500

        base_core_spec = normalize_core_teaching_spec(
            latest_core_spec,
            base_spec.get('requirement_summary', {}),
            base_spec.get('source_notes', []),
        )
        revision_source_bundle = {
            'source_notes': base_spec.get('source_notes', []),
            'source_evidence': latest_source_evidence_meta.get('evidence_sources', []) if isinstance(latest_source_evidence_meta.get('evidence_sources'), list) else [],
            'query_terms': latest_source_evidence_meta.get('query_terms', []) if isinstance(latest_source_evidence_meta.get('query_terms'), list) else [],
            'source_contract': latest_source_evidence_meta.get('source_contract', []) if isinstance(latest_source_evidence_meta.get('source_contract'), list) else base_spec.get('source_notes', []),
        }
        revised_core_spec_raw = _revise_core_teaching_spec_via_model(
            api_key=api_key,
            api_base=api_base,
            model_name=model_name or get_model_primary("text"),
            core_spec=base_core_spec,
            lesson_plan_spec=base_spec,
            revision_request=revision_request,
            evidence_context=revision_source_bundle,
        )
        revised_core_spec = normalize_core_teaching_spec(
            revised_core_spec_raw,
            base_spec.get('requirement_summary', {}),
            base_spec.get('source_notes', []),
        )
        revised_requirement_summary = core_spec_to_requirement_summary(
            revised_core_spec,
            base_spec.get('requirement_summary', {}),
        )
        chapter_assessment_questions = _generate_chapter_assessment_questions(
            api_key=api_key,
            api_base=api_base,
            model_name=model_name or get_model_primary("text"),
            course_info={'name': course.name or '', 'description': course.description or ''} if course else {},
            requirement_summary=revised_requirement_summary,
            course_id=course_id,
            chapter_id=None,
        )
        if chapter_assessment_questions:
            assessment_plan = revised_core_spec.get('assessment_plan') if isinstance(revised_core_spec.get('assessment_plan'), dict) else {}
            assessment_plan['questions'] = chapter_assessment_questions
            revised_core_spec['assessment_plan'] = assessment_plan
        docx_outline = _generate_outline_from_core_spec_via_model(
            category='docx_outline',
            fallback_system=LESSON_PLAN_DOCX_FALLBACK_SYSTEM_PROMPT,
            fallback_user=LESSON_PLAN_DOCX_FALLBACK_USER_PROMPT,
            target_key='docx_outline',
            api_key=api_key,
            api_base=api_base,
            model_name=model_name or get_model_primary("text"),
            core_spec=revised_core_spec,
            requirement_summary_payload=revised_requirement_summary,
            evidence_context=revision_source_bundle,
        )
        ppt_outline = _generate_outline_from_core_spec_via_model(
            category='ppt_outline',
            fallback_system=LESSON_PLAN_PPT_FALLBACK_SYSTEM_PROMPT,
            fallback_user=LESSON_PLAN_PPT_FALLBACK_USER_PROMPT,
            target_key='ppt_outline',
            api_key=api_key,
            api_base=api_base,
            model_name=model_name or get_model_primary("text"),
            core_spec=revised_core_spec,
            requirement_summary_payload=revised_requirement_summary,
            evidence_context=revision_source_bundle,
        )
        normalized_spec = _normalize_lesson_plan_spec(
            raw_spec={
                'requirement_summary': revised_requirement_summary,
                'source_notes': base_spec.get('source_notes', []),
                'docx_outline': docx_outline,
                'ppt_outline': ppt_outline,
                'game_plan': build_game_plan_seed_from_core_spec(revised_core_spec, revised_requirement_summary, base_spec.get('source_notes', [])),
            },
            requirement_summary_fallback=revised_requirement_summary,
            source_notes_fallback=base_spec.get('source_notes', []),
        )
        normalized_spec = _enforce_source_intent_on_spec(normalized_spec)
        outline_generation_meta = {
            'pipeline': 'core_spec_v2',
            'docx_sections': len(normalized_spec.get('docx_outline') or []),
            'ppt_slides': len(normalized_spec.get('ppt_outline') or []),
            'source_note_count': len(base_spec.get('source_notes', []) or []),
            'revision_mode': True,
        }

        created_at = int(time.time())
        revision_meta = {
            'version_index': latest_version_index + 1 if latest_version_index > 0 else 1,
            'based_on_version_index': based_on_version_index,
            'revision_request': revision_request,
            'created_at': created_at,
        }

        user_message = ChatHistory(
            user_id=user_id,
            course_id=course_id,
            conversation_id=conversation_id,
            role='user',
            message=revision_request,
            timestamp=created_at,
        )
        db.session.add(user_message)

        assistant_message = ChatHistory(
            user_id=user_id,
            course_id=course_id,
            conversation_id=conversation_id,
            role='assistant',
            message=json.dumps(
                _build_lesson_plan_payload(
                    normalized_spec=normalized_spec,
                    sources=sources,
                    revision_meta=revision_meta,
                    core_spec=revised_core_spec,
                    outline_generation_meta=outline_generation_meta,
                    source_evidence_meta=latest_source_evidence_meta,
                ),
                ensure_ascii=False
            ),
            timestamp=created_at,
        )
        db.session.add(assistant_message)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'conversation_id': conversation_id,
            'lesson_plan_spec': normalized_spec,
            'sources': sources,
            'revision_meta': revision_meta,
            'core_spec': revised_core_spec,
            'outline_generation_meta': outline_generation_meta,
            'source_evidence_meta': latest_source_evidence_meta,
        })
    except Exception as e:
        db.session.rollback()
        app_logger.error(f'revise lesson plan failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'revise lesson plan failed: {str(e)}'
        }), 500

@rag_api.route('/generate-lesson-ppt', methods=['POST'])
@jwt_required()
def generate_lesson_ppt():
    """Render lesson_plan_spec into a local PPTX and persist it as course material."""
    app_logger = current_app.logger
    data = request.json or {}
    user_id = get_jwt_identity()

    course_id = data.get('courseId', data.get('course_id'))
    raw_spec = data.get('lessonPlanSpec', data.get('lesson_plan_spec'))
    core_spec = data.get('coreSpec', data.get('core_spec'))
    processed_sources = data.get('processedSources', data.get('processed_sources', []))
    game_html_material_id = data.get('gameHtmlMaterialId', data.get('game_html_material_id'))
    conversation_id = str(data.get('conversation_id') or '').strip() or None
    raw_version_index = data.get('version_index')
    requested_theme = str(data.get('theme') or '').strip().lower() or None
    template_profile = str(data.get('templateProfile', data.get('template_profile')) or '').strip() or None
    use_gallery = data.get('useGallery', data.get('use_gallery', True))

    if not course_id:
        return jsonify({'status': 'error', 'message': 'courseId is required'}), 400
    try:
        course_id = int(course_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'courseId must be an integer'}), 400

    if not isinstance(raw_spec, dict) or not raw_spec:
        return jsonify({'status': 'error', 'message': 'lessonPlanSpec is required'}), 400

    if not isinstance(processed_sources, list):
        processed_sources = []
    if not isinstance(use_gallery, bool):
        use_gallery = True
    version_index = None
    if raw_version_index is not None and raw_version_index != '':
        try:
            version_index = int(raw_version_index)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'version_index must be an integer'}), 400
    if game_html_material_id is not None:
        try:
            game_html_material_id = int(game_html_material_id)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'gameHtmlMaterialId must be an integer'}), 400

    if requested_theme and requested_theme not in {'clean', 'tech', 'vivid'}:
        return jsonify({'status': 'error', 'message': 'theme must be clean, tech or vivid'}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'status': 'error', 'message': 'Course not found'}), 404

    requirement_fallback = raw_spec.get('requirement_summary') if isinstance(raw_spec.get('requirement_summary'), dict) else {}
    source_notes_fallback = raw_spec.get('source_notes') if isinstance(raw_spec.get('source_notes'), list) else []
    normalized_spec = _normalize_lesson_plan_spec(
        raw_spec=raw_spec,
        requirement_summary_fallback=requirement_fallback,
        source_notes_fallback=source_notes_fallback,
    )
    output_targets = normalized_spec.get('requirement_summary', {}).get('output_targets')
    if not isinstance(output_targets, list):
        output_targets = []
    requires_game_html_for_ppt = any(
        re.search(r'(游戏|html|闯关)', str(item or ''), flags=re.IGNORECASE)
        for item in output_targets
    )
    if requires_game_html_for_ppt and game_html_material_id is None:
        return jsonify({
            'status': 'error',
            'message': '检测到已选择互动小游戏产出，请先生成 HTML 小游戏，再生成 PPT。'
        }), 400

    try:
        from backend.rag.ppt_generation import (
            build_output_path,
            build_theme_config,
            build_game_entry,
            collect_image_candidates,
            normalize_ppt_outline_to_12_slides,
            persist_generated_material,
            render_pptx,
            resolve_ppt_template,
            search_gallery_images,
        )

        template_meta = resolve_ppt_template(template_profile)
        normalized_plan = normalize_ppt_outline_to_12_slides(normalized_spec, template_meta.get('target_slide_count', 12))
        theme_config = build_theme_config(normalized_spec, requested_theme)
        game_entry = None
        if game_html_material_id is not None:
            game_html_material = Material.query.get(game_html_material_id)
            if not game_html_material:
                return jsonify({'status': 'error', 'message': 'Game HTML material not found'}), 404
            if int(game_html_material.course_id) != int(course_id):
                return jsonify({'status': 'error', 'message': 'Game HTML material does not belong to this course'}), 400
            material_type = str(game_html_material.material_type or '').strip().lower()
            title_text = str(game_html_material.title or '').strip().lower()
            if material_type != 'html' and not title_text.endswith('.html'):
                return jsonify({'status': 'error', 'message': 'Game HTML material must be an HTML file'}), 400

            download_url = f"{request.host_url.rstrip('/')}/api/materials/{game_html_material.id}/download"
            game_entry = build_game_entry(
                upload_root=current_app.config['UPLOAD_FOLDER'],
                course_id=course_id,
                title='小游戏入口页',
                material_title=str(game_html_material.title or 'lesson-game.html').strip(),
                download_url=download_url,
            )

        used_candidates = set()
        slide_images: List[Optional[Dict[str, Any]]] = []
        warnings: List[str] = []

        for slide in normalized_plan.get('content_slides', []):
            selected_image = None
            local_candidates = collect_image_candidates(
                slide=slide,
                processed_sources=processed_sources,
                upload_root=current_app.config['UPLOAD_FOLDER'],
                used_candidates=used_candidates,
            )
            if local_candidates:
                selected_image = local_candidates[0]
            elif use_gallery:
                gallery_candidates, gallery_warnings = search_gallery_images(
                    slide=slide,
                    spec=normalized_spec,
                    course_id=course_id,
                    upload_root=current_app.config['UPLOAD_FOLDER'],
                    used_candidates=used_candidates,
                )
                warnings.extend(gallery_warnings)
                if gallery_candidates:
                    selected_image = gallery_candidates[0]

            if selected_image:
                used_candidates.add(str(selected_image.get('path_or_url') or '').strip())
            slide_images.append(selected_image)

        topic = str(
            normalized_spec.get('requirement_summary', {}).get('topic')
            or normalized_spec.get('requirement_summary', {}).get('chapter_title')
            or course.name
            or 'lesson_ppt'
        ).strip()
        output_path = build_output_path(current_app.config['UPLOAD_FOLDER'], course_id, topic)
        image_stats = render_pptx(
            normalized_plan=normalized_plan,
            spec=normalized_spec,
            theme_config=theme_config,
            slide_images=slide_images,
            output_path=output_path,
            game_entry=game_entry,
            template_profile=template_profile,
        )
        material = persist_generated_material(
            course_id=course_id,
            course_name=course.name or '',
            topic=topic,
            theme_name=theme_config['name'],
            output_path=output_path,
            image_stats=image_stats,
        )
        _link_generated_material_to_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            asset_key='ppt',
            material_id=material.id,
            version_index=version_index,
        )
        db.session.commit()

        deduped_warnings: List[str] = []
        seen_warnings = set()
        for item in warnings:
            normalized = str(item or '').strip()
            if not normalized or normalized in seen_warnings:
                continue
            seen_warnings.add(normalized)
            deduped_warnings.append(normalized)

        return jsonify({
            'status': 'success',
            'message': 'PPT generated successfully',
            'material_id': material.id,
            'file_path': material.file_path,
            'download_url': f'/materials/{material.id}/download',
            'slide_count': 4 + len(normalized_plan.get('content_slides', [])),
            'theme': theme_config['name'],
            'template_profile': template_meta.get('profile'),
            'template_used': bool(template_meta.get('template_path')),
            'image_stats': image_stats,
            'warnings': deduped_warnings,
            'material': material.to_dict(),
        })
    except Exception as e:
        db.session.rollback()
        app_logger.error(f'generate lesson ppt failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'generate lesson ppt failed: {str(e)}'
        }), 500

@rag_api.route('/generate-lesson-docx', methods=['POST'])
@jwt_required()
def generate_lesson_docx():
    """Render lesson_plan_spec into a local DOCX lesson plan and persist it as course material."""
    app_logger = current_app.logger
    data = request.json or {}
    user_id = get_jwt_identity()

    course_id = data.get('courseId', data.get('course_id'))
    raw_spec = data.get('lessonPlanSpec', data.get('lesson_plan_spec'))
    core_spec = data.get('coreSpec', data.get('core_spec'))
    conversation_id = str(data.get('conversation_id') or '').strip() or None
    raw_version_index = data.get('version_index')
    template_profile = str(data.get('templateProfile', data.get('template_profile')) or '').strip() or None

    if not course_id:
        return jsonify({'status': 'error', 'message': 'courseId is required'}), 400
    try:
        course_id = int(course_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'courseId must be an integer'}), 400

    if not isinstance(raw_spec, dict) or not raw_spec:
        return jsonify({'status': 'error', 'message': 'lessonPlanSpec is required'}), 400
    version_index = None
    if raw_version_index is not None and raw_version_index != '':
        try:
            version_index = int(raw_version_index)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'version_index must be an integer'}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'status': 'error', 'message': 'Course not found'}), 404

    requirement_fallback = raw_spec.get('requirement_summary') if isinstance(raw_spec.get('requirement_summary'), dict) else {}
    source_notes_fallback = raw_spec.get('source_notes') if isinstance(raw_spec.get('source_notes'), list) else []
    normalized_spec = _normalize_lesson_plan_spec(
        raw_spec=raw_spec,
        requirement_summary_fallback=requirement_fallback,
        source_notes_fallback=source_notes_fallback,
    )
    if (not isinstance(core_spec, dict) or not core_spec) and conversation_id:
        payload_message = _find_lesson_plan_payload_message(
            conversation_id=conversation_id,
            user_id=user_id,
            version_index=version_index,
        )
        if payload_message:
            _, payload = payload_message
            payload_core_spec = payload.get('core_spec') if isinstance(payload.get('core_spec'), dict) else None
            if isinstance(payload_core_spec, dict) and payload_core_spec:
                core_spec = payload_core_spec

    try:
        from backend.rag.docx_generation import (
            build_output_path,
            persist_generated_material,
            render_docx,
        )

        topic = str(
            normalized_spec.get('requirement_summary', {}).get('topic')
            or normalized_spec.get('requirement_summary', {}).get('chapter_title')
            or course.name
            or 'lesson_docx'
        ).strip()
        output_path = build_output_path(current_app.config['UPLOAD_FOLDER'], course_id, topic)
        try:
            render_stats = render_docx(
                spec=normalized_spec,
                output_path=output_path,
                core_spec=core_spec,
                template_profile=template_profile,
            )
        except TypeError as exc:
            if "unexpected keyword argument 'core_spec'" not in str(exc):
                raise
            render_stats = render_docx(spec=normalized_spec, output_path=output_path)
        material = persist_generated_material(
            course_id=course_id,
            course_name=course.name or '',
            topic=topic,
            output_path=output_path,
            section_count=int(render_stats.get('section_count') or 0),
        )
        _link_generated_material_to_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            asset_key='word',
            material_id=material.id,
            version_index=version_index,
        )
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'DOCX generated successfully',
            'material_id': material.id,
            'file_path': material.file_path,
            'download_url': f'/materials/{material.id}/download',
            'section_count': render_stats.get('section_count', 0),
            'template_profile': render_stats.get('template_profile'),
            'template_used': bool(render_stats.get('template_used')),
            'material': material.to_dict(),
        })
    except Exception as e:
        db.session.rollback()
        app_logger.error(f'generate lesson docx failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'generate lesson docx failed: {str(e)}'
        }), 500

@rag_api.route('/generate-lesson-game-html', methods=['POST'])
@jwt_required()
def generate_lesson_game_html():
    """Render lesson_plan_spec into a standalone offline HTML game and persist it as course material."""
    app_logger = current_app.logger
    data = request.json or {}
    user_id = get_jwt_identity()

    course_id = data.get('courseId', data.get('course_id'))
    raw_spec = data.get('lessonPlanSpec', data.get('lesson_plan_spec'))
    raw_game_plan = data.get('gamePlan', data.get('game_plan'))
    conversation_id = str(data.get('conversation_id') or '').strip() or None
    raw_version_index = data.get('version_index')
    requested_theme = str(data.get('theme') or '').strip().lower() or None

    if not course_id:
        return jsonify({'status': 'error', 'message': 'courseId is required'}), 400
    try:
        course_id = int(course_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'courseId must be an integer'}), 400

    if not isinstance(raw_spec, dict) or not raw_spec:
        return jsonify({'status': 'error', 'message': 'lessonPlanSpec is required'}), 400
    version_index = None
    if raw_version_index is not None and raw_version_index != '':
        try:
            version_index = int(raw_version_index)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'version_index must be an integer'}), 400

    if requested_theme and requested_theme not in {'clean', 'tech', 'vivid'}:
        return jsonify({'status': 'error', 'message': 'theme must be clean, tech or vivid'}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'status': 'error', 'message': 'Course not found'}), 404

    spec_for_export = dict(raw_spec)
    if isinstance(raw_game_plan, dict):
        spec_for_export['game_plan'] = raw_game_plan

    requirement_fallback = spec_for_export.get('requirement_summary') if isinstance(spec_for_export.get('requirement_summary'), dict) else {}
    source_notes_fallback = spec_for_export.get('source_notes') if isinstance(spec_for_export.get('source_notes'), list) else []
    normalized_spec = _normalize_lesson_plan_spec(
        raw_spec=spec_for_export,
        requirement_summary_fallback=requirement_fallback,
        source_notes_fallback=source_notes_fallback,
    )

    raw_game_pack = None
    api_key, api_base, model_name = get_api_config()
    if api_key and api_base:
        try:
            raw_game_pack = _request_game_pack_from_model(
                normalized_spec=normalized_spec,
                course=course,
                api_key=api_key,
                api_base=api_base,
                model_name=model_name or get_model_primary("text"),
                requested_theme=requested_theme,
                app_logger=app_logger,
            )
        except Exception as e:
            app_logger.warning(f'game-pack model failed, fallback pack will be used: {str(e)}')

    game_pack = _normalize_game_pack(
        raw_pack=raw_game_pack,
        normalized_spec=normalized_spec,
        requested_theme=requested_theme,
    )

    try:
        from backend.rag.game_html_generation import (
            build_output_path,
            persist_generated_material,
            render_game_html,
        )

        topic = str(
            game_pack.get('meta', {}).get('title')
            or normalized_spec.get('requirement_summary', {}).get('topic')
            or normalized_spec.get('requirement_summary', {}).get('chapter_title')
            or course.name
            or 'lesson_game'
        ).strip()
        output_path = build_output_path(current_app.config['UPLOAD_FOLDER'], course_id, topic)
        stats = render_game_html(game_pack=game_pack, output_path=output_path)
        material = persist_generated_material(
            course_id=course_id,
            course_name=course.name or '',
            topic=topic,
            output_path=output_path,
            stats=stats,
        )
        _link_generated_material_to_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            asset_key='game',
            material_id=material.id,
            version_index=version_index,
        )
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Lesson game HTML generated successfully',
            'material_id': material.id,
            'file_path': material.file_path,
            'download_url': f'/materials/{material.id}/download',
            'stage_count': stats.get('stage_count', 0),
            'question_count': stats.get('question_count', 0),
            'material': material.to_dict(),
        })
    except Exception as e:
        db.session.rollback()
        app_logger.error(f'generate lesson game html failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'generate lesson game html failed: {str(e)}'
        }), 500

@rag_api.route('/knowledge/upload-temp', methods=['POST'])
@jwt_required()
def upload_temp_file():
    """Upload temporary files for lesson planning without importing to KB."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400

    if file.filename is None:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400

    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()

    supported_exts = [
        '.pdf', '.docx', '.doc', '.txt', '.md',
        '.ppt', '.pptx',
        '.jpg', '.jpeg', '.png', '.webp',
        '.mp4', '.mov', '.avi', '.mkv', '.webm'
    ]
    if ext not in supported_exts:
        return jsonify({
            'status': 'error',
            'message': f'Unsupported file type, only supports: {", ".join(supported_exts)}'
        }), 400

    try:
        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', str(user_id))
        os.makedirs(temp_dir, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(temp_dir, safe_filename)
        file.save(file_path)

        file_hash = calculate_file_hash(file_path)

        return jsonify({
            'status': 'success',
            'message': 'upload success',
            'file_info': {
                'original_name': file.filename,
                'saved_name': safe_filename,
                'file_path': f'temp/{user_id}/{safe_filename}',
                'file_hash': file_hash,
                'file_size': os.path.getsize(file_path)
            }
        })
    except Exception as e:
        app_logger.error(f'upload temp file failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'upload failed: {str(e)}'
        }), 500

@rag_api.route('/process-temp-sources', methods=['POST'])
@jwt_required()
def process_temp_sources_api():
    """Process temporary sources into normalized preview payloads."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()

    data = request.json or {}
    raw_file_paths = data.get('file_paths', data.get('filePaths', []))
    raw_source_mappings = data.get('source_mappings', data.get('sourceMappings', []))

    temp_file_result = normalize_temp_file_list(raw_file_paths)
    if not temp_file_result.get('ok'):
        return jsonify({'status': 'error', 'message': temp_file_result.get('message', 'file_paths validation failed')}), 400
    normalized_temp_files: List[str] = temp_file_result.get('files', [])
    if not normalized_temp_files:
        return jsonify({'status': 'error', 'message': 'file_paths is required'}), 400

    source_mapping_result = parse_source_mappings(
        raw_mappings=convert_snake_to_legacy_source_mappings(raw_source_mappings),
        normalized_temp_files=normalized_temp_files,
        user_id=user_id,
        upload_root=current_app.config['UPLOAD_FOLDER']
    )
    if not source_mapping_result.get('ok'):
        return jsonify({
            'status': 'error',
            'message': source_mapping_result.get('message', 'sourceMappings validation failed')
        }), 400

    try:
        from backend.rag.source_processing import process_temp_sources

        api_key, api_base, model_name = get_api_config()
        processed_sources = process_temp_sources(
            file_paths=normalized_temp_files,
            source_mappings=source_mapping_result.get('ordered_mappings', []),
            upload_root=current_app.config['UPLOAD_FOLDER'],
            user_id=user_id,
            api_key=api_key,
            api_base=api_base,
            model_name=model_name or get_model_primary("text")
        )
        return jsonify({
            'status': 'success',
            'sources': processed_sources
        })
    except Exception as e:
        app_logger.error(f'process temp sources failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'process temp sources failed: {str(e)}'
        }), 500

@rag_api.route('/knowledge/process-temp', methods=['POST'])
@jwt_required()
def process_temp_files():
    """Legacy wrapper around normalized temp source processing."""
    app_logger = current_app.logger
    user_id = get_jwt_identity()

    data = request.json or {}
    raw_file_paths = data.get('file_paths', data.get('filePaths', []))

    temp_file_result = normalize_temp_file_list(raw_file_paths)
    if not temp_file_result.get('ok'):
        return jsonify({'status': 'error', 'message': temp_file_result.get('message', 'file_paths validation failed')}), 400
    normalized_temp_files: List[str] = temp_file_result.get('files', [])
    if not normalized_temp_files:
        return jsonify({'status': 'error', 'message': 'file_paths is required'}), 400

    source_mappings_payload = data.get('source_mappings', data.get('sourceMappings'))
    if source_mappings_payload:
        source_mapping_result = parse_source_mappings(
            raw_mappings=convert_snake_to_legacy_source_mappings(source_mappings_payload),
            normalized_temp_files=normalized_temp_files,
            user_id=user_id,
            upload_root=current_app.config['UPLOAD_FOLDER']
        )
    else:
        source_mapping_result = build_default_source_mappings(
            normalized_temp_files=normalized_temp_files,
            user_id=user_id,
            upload_root=current_app.config['UPLOAD_FOLDER']
        )

    if not source_mapping_result.get('ok'):
        return jsonify({
            'status': 'error',
            'message': source_mapping_result.get('message', 'sourceMappings validation failed')
        }), 400

    try:
        from backend.rag.source_processing import build_legacy_context, process_temp_sources

        api_key, api_base, model_name = get_api_config()
        processed_sources = process_temp_sources(
            file_paths=normalized_temp_files,
            source_mappings=source_mapping_result.get('ordered_mappings', []),
            upload_root=current_app.config['UPLOAD_FOLDER'],
            user_id=user_id,
            api_key=api_key,
            api_base=api_base,
            model_name=model_name or get_model_primary("text")
        )
        context = build_legacy_context(processed_sources)

        return jsonify({
            'status': 'success',
            'message': f'successfully processed {len(processed_sources)} files',
            'context': context,
            'sources': processed_sources
        })
    except Exception as e:
        app_logger.error(f'process temp files failed: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'process temp files failed: {str(e)}'
        }), 500


