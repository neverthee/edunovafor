import os
import re
from typing import Any, Dict, List, Sequence


PROMPT_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "prompts",
    "lesson_plan",
)


def _dedupe_non_empty(items: Sequence[Any]) -> List[str]:
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
    if isinstance(value, list):
        return _dedupe_non_empty(value)
    if isinstance(value, str):
        return _dedupe_non_empty(re.split(r"[，,；;、\n]+", value))
    return []


def _trim_text(value: Any, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 0)].rstrip()}..."


def _slugify_identifier(value: Any, prefix: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return slug or prefix


def _normalize_source_refs(value: Any) -> List[str]:
    return _normalize_text_list(value)


def load_prompt_bundle(category: str, fallback_system: str, fallback_user: str):
    category_dir = os.path.join(PROMPT_ROOT, category)
    system_path = os.path.join(category_dir, "system.md")
    user_path = os.path.join(category_dir, "user.md")
    system_prompt = fallback_system
    user_prompt = fallback_user

    if os.path.exists(system_path):
        with open(system_path, "r", encoding="utf-8") as file_obj:
            system_prompt = file_obj.read().strip() or fallback_system

    if os.path.exists(user_path):
        with open(user_path, "r", encoding="utf-8") as file_obj:
            user_prompt = file_obj.read().strip() or fallback_user

    return system_prompt, user_prompt


def render_prompt_template(template_text: Any, context: Dict[str, Any]) -> str:
    rendered = str(template_text or "")
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def build_query_terms(
    requirement_summary: Dict[str, Any],
    structured_requirement: Dict[str, Any],
    free_teaching_idea: Any,
) -> List[str]:
    terms: List[str] = []
    requirement_style = (
        requirement_summary.get("style")
        if isinstance(requirement_summary.get("style"), dict)
        else {}
    )
    structured_style = (
        structured_requirement.get("style")
        if isinstance(structured_requirement.get("style"), dict)
        else {}
    )
    student_profile = (
        requirement_summary.get("student_profile")
        if isinstance(requirement_summary.get("student_profile"), dict)
        else {}
    )
    teaching_flow = (
        structured_requirement.get("teaching_flow")
        if isinstance(structured_requirement.get("teaching_flow"), list)
        else []
    )

    terms.extend(
        _normalize_text_list(
            [
                requirement_summary.get("topic"),
                requirement_summary.get("chapter_title"),
                requirement_summary.get("grade_subject"),
                requirement_summary.get("duration"),
                requirement_style.get("teaching_style"),
                requirement_style.get("output_preference"),
                student_profile.get("foundation"),
                structured_style.get("interaction_level"),
                free_teaching_idea,
            ]
        )
    )
    terms.extend(_normalize_text_list(requirement_summary.get("teaching_goals")))
    terms.extend(_normalize_text_list(requirement_summary.get("knowledge_points")))
    terms.extend(_normalize_text_list(requirement_summary.get("key_points")))
    terms.extend(_normalize_text_list(requirement_summary.get("difficult_points")))

    for step in teaching_flow[:6]:
        if not isinstance(step, dict):
            continue
        terms.extend(_normalize_text_list([step.get("title"), step.get("goal")]))

    return _dedupe_non_empty(terms)[:24]


def _extract_processed_source_snippets(source: Dict[str, Any]) -> List[str]:
    snippets: List[str] = []
    for item in source.get("chunks") if isinstance(source.get("chunks"), list) else []:
        if isinstance(item, dict):
            page = item.get("page")
            locator = f"第{page}页" if isinstance(page, (int, float)) else ""
            text = _trim_text(item.get("text"), 180)
            snippet = f"{locator}: {text}".strip(": ").strip()
        else:
            snippet = _trim_text(item, 180)
        if snippet:
            snippets.append(snippet)
        if len(snippets) >= 3:
            break
    return _dedupe_non_empty(snippets)


def _processed_source_note(source: Dict[str, Any]) -> Dict[str, Any]:
    mapping = source.get("mapping") if isinstance(source.get("mapping"), dict) else {}
    source_title = str(
        mapping.get("file_name") or source.get("title") or "未命名资料"
    ).strip()
    snippets = _extract_processed_source_snippets(source)
    raw_note = str(source.get("summary") or "").strip()
    return {
        "source_kind": str(source.get("kind") or "document").strip() or "document",
        "source_title": source_title,
        "usage": str(mapping.get("usage") or "content").strip() or "content",
        "knowledge_point": str(mapping.get("knowledge_point") or "").strip(),
        "required": bool(mapping.get("is_required")),
        "note": raw_note or (snippets[0] if snippets else source_title),
        "snippets": snippets,
        "_source_url": str(mapping.get("file_path") or "").strip(),
    }


def _selected_knowledge_item_key(item: Dict[str, Any]) -> str:
    file_path = str(item.get("file_path") or "").strip().lower()
    if file_path:
        return f"path:{file_path}"
    file_name = str(item.get("file_name") or "").strip().lower()
    if file_name:
        return f"name:{file_name}"
    return ""


def _build_selected_knowledge_lookup(selected_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_path: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    for item in selected_items:
        if not isinstance(item, dict):
            continue
        file_path = str(item.get("file_path") or "").strip()
        file_name = str(item.get("file_name") or os.path.basename(file_path) or "").strip()
        normalized = {
            "file_path": file_path,
            "file_name": file_name,
            "usage": str(item.get("usage") or "content").strip() or "content",
            "knowledge_point": str(item.get("knowledge_point") or "").strip(),
            "is_required": bool(item.get("is_required")),
        }
        if file_path:
            by_path[file_path.lower()] = normalized
        if file_name:
            by_name[file_name.lower()] = normalized
    return {"by_path": by_path, "by_name": by_name}


def _match_selected_knowledge_mapping(
    *,
    source_url: str,
    title: str,
    lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    by_path = lookup.get("by_path") if isinstance(lookup.get("by_path"), dict) else {}
    by_name = lookup.get("by_name") if isinstance(lookup.get("by_name"), dict) else {}
    source_path = str(source_url or "").strip().lower()
    if source_path and source_path in by_path:
        return by_path[source_path]
    source_name = os.path.basename(str(source_url or title or "")).strip().lower()
    if source_name and source_name in by_name:
        return by_name[source_name]
    title_name = str(title or "").strip().lower()
    if title_name and title_name in by_name:
        return by_name[title_name]
    return {}


def _build_missing_selected_knowledge_notes(
    selected_items: List[Dict[str, Any]],
    matched_keys: set[str],
) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    for item in selected_items:
        if not isinstance(item, dict):
            continue
        item_key = _selected_knowledge_item_key(item)
        if not item_key or item_key in matched_keys:
            continue
        source_title = str(item.get("file_name") or os.path.basename(str(item.get("file_path") or "")) or "知识库资料").strip()
        knowledge_point = str(item.get("knowledge_point") or "").strip()
        summary = f"按用户要求引用《{source_title}》"
        if knowledge_point:
            summary = f"{summary}，重点服务知识点“{knowledge_point}”"
        notes.append({
            "source_kind": "knowledge_base",
            "source_title": source_title,
            "usage": str(item.get("usage") or "content").strip() or "content",
            "knowledge_point": knowledge_point,
            "required": bool(item.get("is_required")),
            "note": summary,
            "snippets": [],
            "_source_url": str(item.get("file_path") or "").strip(),
        })
    return notes


def _retrieved_doc_note_group(
    retrieved_docs: List[Any],
    selected_items: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    selected_items = selected_items if isinstance(selected_items, list) else []
    lookup = _build_selected_knowledge_lookup(selected_items)
    matched_keys: set[str] = set()

    for doc in retrieved_docs:
        metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
        source_url = str(metadata.get("source") or metadata.get("file_path") or "").strip()
        if not source_url:
            continue
        title = str(metadata.get("title") or os.path.basename(source_url) or source_url).strip()
        selected_mapping = _match_selected_knowledge_mapping(
            source_url=source_url,
            title=title,
            lookup=lookup,
        )
        matched_key = _selected_knowledge_item_key(selected_mapping) if selected_mapping else ""
        if matched_key:
            matched_keys.add(matched_key)
        if source_url not in grouped:
            grouped[source_url] = {
                "source_kind": "knowledge_base",
                "source_title": title,
                "usage": str(selected_mapping.get("usage") or "content").strip() or "content",
                "knowledge_point": str(
                    selected_mapping.get("knowledge_point")
                    or metadata.get("knowledge_point")
                    or ""
                ).strip(),
                "required": bool(selected_mapping.get("is_required")),
                "note": "",
                "snippets": [],
                "_source_url": source_url,
            }
            order.append(source_url)

        note = grouped[source_url]
        page_content = _trim_text(getattr(doc, "page_content", ""), 220)
        if page_content:
            locator_parts: List[str] = []
            if metadata.get("page") not in (None, ""):
                locator_parts.append(f"第{metadata.get('page')}页")
            elif metadata.get("chunk_id"):
                locator_parts.append(f"chunk {metadata.get('chunk_id')}")
            snippet = f"{' | '.join(locator_parts)}: {page_content}".strip(": ").strip()
            if len(note["snippets"]) < 3:
                note["snippets"].append(snippet)
            if not note["note"]:
                note["note"] = page_content
        if not note["knowledge_point"]:
            note["knowledge_point"] = str(metadata.get("knowledge_point") or "").strip()

    result: List[Dict[str, Any]] = []
    for source_url in order:
        note = grouped[source_url]
        note["snippets"] = _dedupe_non_empty(note["snippets"])
        note["note"] = note["note"] or (note["snippets"][0] if note["snippets"] else note["source_title"])
        result.append(note)
    result.extend(_build_missing_selected_knowledge_notes(selected_items, matched_keys))
    return result


def build_source_evidence_bundle(
    processed_sources: List[Dict[str, Any]],
    retrieved_docs: List[Any],
    query_terms: List[str],
    selected_knowledge_items: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    source_notes: List[Dict[str, Any]] = []
    source_evidence: List[Dict[str, Any]] = []

    for source in processed_sources:
        if not isinstance(source, dict):
            continue
        note = _processed_source_note(source)
        source_notes.append(note)
        source_evidence.append(
            {
                "source_title": note["source_title"],
                "source_kind": note["source_kind"],
                "source_url": note.pop("_source_url", ""),
                "summary": note["note"],
                "snippets": note["snippets"],
                "required": note["required"],
                "knowledge_point": note["knowledge_point"],
            }
        )

    for note in _retrieved_doc_note_group(retrieved_docs, selected_knowledge_items):
        source_notes.append(note)
        source_evidence.append(
            {
                "source_title": note["source_title"],
                "source_kind": note["source_kind"],
                "source_url": note.pop("_source_url", ""),
                "summary": note["note"],
                "snippets": note["snippets"],
                "required": bool(note["required"]),
                "knowledge_point": note["knowledge_point"],
            }
        )

    ranked = sorted(
        source_notes,
        key=lambda item: (
            0 if item.get("required") else 1,
            0 if item.get("source_kind") != "knowledge_base" else 1,
            item.get("source_title") or "",
        ),
    )
    for item in ranked:
        item.pop("_source_url", None)

    return {
        "query_terms": _dedupe_non_empty(query_terms),
        "source_notes": ranked[:12],
        "source_evidence": source_evidence[:16],
        "source_contract": [
            {
                "source_title": str(item.get("source_title") or "").strip(),
                "source_kind": str(item.get("source_kind") or "").strip(),
                "usage": str(item.get("usage") or "").strip(),
                "knowledge_point": str(item.get("knowledge_point") or "").strip(),
                "required": bool(item.get("required")),
            }
            for item in ranked[:12]
            if isinstance(item, dict) and str(item.get("source_title") or "").strip()
        ],
    }


def _fallback_teaching_flow(
    requirement_summary: Dict[str, Any],
    source_titles: List[str],
) -> List[Dict[str, Any]]:
    topic = str(
        requirement_summary.get("topic")
        or requirement_summary.get("chapter_title")
        or requirement_summary.get("grade_subject")
        or "当前主题"
    ).strip()
    knowledge_points = _normalize_text_list(requirement_summary.get("knowledge_points"))
    key_points = _normalize_text_list(requirement_summary.get("key_points")) or knowledge_points
    difficult_points = _normalize_text_list(requirement_summary.get("difficult_points"))

    flow_templates = [
        (
            "stage_intro",
            "导入与目标说明",
            "激活先验知识并明确学习目标",
            [f"围绕“{topic}”提出导入问题，连接学生已有经验", "说明本课目标与学习路径"],
        ),
        (
            "stage_core",
            "核心知识讲解与示例",
            "建立关键概念与解题路径",
            [f"结合“{'、'.join(key_points[:2] or [topic])}”进行讲解", "用典型例题或案例帮助学生理解"],
        ),
        (
            "stage_practice",
            "练习反馈与总结",
            "巩固知识点并完成迁移应用",
            ["安排当堂练习并即时反馈", "归纳本节课核心结论并提示后续迁移应用"],
        ),
    ]
    if difficult_points:
        flow_templates[1][3].append(f"重点突破难点：{'、'.join(difficult_points[:2])}")

    flow: List[Dict[str, Any]] = []
    for index, (step_id, title, goal, activities) in enumerate(flow_templates, start=1):
        flow.append(
            {
                "id": step_id,
                "title": title,
                "goal": goal,
                "activities": activities,
                "teacher_actions": [f"组织{title}", "控制节奏并提供示范"],
                "student_actions": ["参与课堂互动", "记录关键结论"],
                "assessment": ["观察参与情况", "通过提问或练习检查理解"],
                "source_refs": source_titles[:1],
            }
        )
    return flow


def normalize_core_teaching_spec(
    raw_core_spec: Dict[str, Any],
    requirement_summary: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    raw = raw_core_spec if isinstance(raw_core_spec, dict) else {}
    source_titles = _dedupe_non_empty(
        [
            str(item.get("source_title") or "").strip()
            for item in source_notes[:4]
            if isinstance(item, dict)
        ]
    )

    lesson_identity_raw = raw.get("lesson_identity") if isinstance(raw.get("lesson_identity"), dict) else {}
    objectives_raw = raw.get("teaching_objectives") if isinstance(raw.get("teaching_objectives"), dict) else {}
    student_raw = raw.get("student_profile") if isinstance(raw.get("student_profile"), dict) else {}
    knowledge_raw = raw.get("knowledge_structure") if isinstance(raw.get("knowledge_structure"), dict) else {}
    assessment_raw = raw.get("assessment_plan") if isinstance(raw.get("assessment_plan"), dict) else {}
    style_raw = raw.get("style") if isinstance(raw.get("style"), dict) else {}
    requirement_student = (
        requirement_summary.get("student_profile")
        if isinstance(requirement_summary.get("student_profile"), dict)
        else {}
    )
    requirement_style = (
        requirement_summary.get("style")
        if isinstance(requirement_summary.get("style"), dict)
        else {}
    )

    lesson_identity = {
        "topic": str(lesson_identity_raw.get("topic") or requirement_summary.get("topic") or "").strip(),
        "grade_subject": str(
            lesson_identity_raw.get("grade_subject")
            or requirement_summary.get("grade_subject")
            or ""
        ).strip(),
        "outline_type": str(
            lesson_identity_raw.get("outline_type")
            or requirement_summary.get("outline_type")
            or ""
        ).strip(),
        "chapter_title": str(
            lesson_identity_raw.get("chapter_title")
            or requirement_summary.get("chapter_title")
            or ""
        ).strip(),
        "duration": str(
            lesson_identity_raw.get("duration")
            or requirement_summary.get("duration")
            or ""
        ).strip(),
    }

    teaching_objectives = {
        "goals": _normalize_text_list(
            objectives_raw.get("goals") or requirement_summary.get("teaching_goals")
        ),
        "key_points": _normalize_text_list(
            objectives_raw.get("key_points")
            or requirement_summary.get("key_points")
            or requirement_summary.get("knowledge_points")
        ),
        "difficult_points": _normalize_text_list(
            objectives_raw.get("difficult_points")
            or requirement_summary.get("difficult_points")
        ),
        "deliverables": _normalize_text_list(
            objectives_raw.get("deliverables") or requirement_summary.get("output_targets")
        ),
    }

    student_profile = {
        "grade": str(
            student_raw.get("grade")
            or requirement_student.get("grade")
            or requirement_summary.get("grade_subject")
            or ""
        ).strip(),
        "foundation": str(
            student_raw.get("foundation") or requirement_student.get("foundation") or ""
        ).strip(),
        "learning_preference": str(
            student_raw.get("learning_preference")
            or requirement_student.get("learning_preference")
            or ""
        ).strip(),
        "common_misconceptions": _normalize_text_list(student_raw.get("common_misconceptions")),
    }

    knowledge_structure = {
        "knowledge_points": _normalize_text_list(
            knowledge_raw.get("knowledge_points")
            or requirement_summary.get("knowledge_points")
            or teaching_objectives.get("key_points")
        ),
        "knowledge_relations": _normalize_text_list(knowledge_raw.get("knowledge_relations")),
        "examples_or_cases": _normalize_text_list(knowledge_raw.get("examples_or_cases")),
        "common_errors": _normalize_text_list(knowledge_raw.get("common_errors")),
    }

    normalized_flow: List[Dict[str, Any]] = []
    raw_flow = raw.get("teaching_flow") if isinstance(raw.get("teaching_flow"), list) else []
    for index, item in enumerate(raw_flow, start=1):
        if not isinstance(item, dict):
            continue
        normalized_flow.append(
            {
                "id": str(item.get("id") or _slugify_identifier(item.get("title"), f"flow_{index}")).strip()
                or f"flow_{index}",
                "title": str(item.get("title") or f"教学环节 {index}").strip(),
                "goal": str(item.get("goal") or "").strip(),
                "activities": _normalize_text_list(item.get("activities")),
                "teacher_actions": _normalize_text_list(item.get("teacher_actions")),
                "student_actions": _normalize_text_list(item.get("student_actions")),
                "assessment": _normalize_text_list(item.get("assessment")),
                "source_refs": _normalize_source_refs(item.get("source_refs")) or source_titles[:1],
            }
        )

    if not normalized_flow:
        normalized_flow = _fallback_teaching_flow(requirement_summary, source_titles)

    normalized_visual_hints: List[Dict[str, Any]] = []
    for item in raw.get("visual_asset_hints") if isinstance(raw.get("visual_asset_hints"), list) else []:
        if not isinstance(item, dict):
            continue
        normalized_visual_hints.append(
            {
                "topic": str(item.get("topic") or lesson_identity["topic"]).strip(),
                "visual_type": str(item.get("visual_type") or "示意图").strip(),
                "hint": str(item.get("hint") or "").strip(),
                "source_refs": _normalize_source_refs(item.get("source_refs")) or source_titles[:2],
            }
        )
    if not normalized_visual_hints and lesson_identity["topic"]:
        normalized_visual_hints.append(
            {
                "topic": lesson_identity["topic"],
                "visual_type": "流程图",
                "hint": f"围绕“{lesson_identity['topic']}”提炼一张课堂讲解流程图。",
                "source_refs": source_titles[:2],
            }
        )

    normalized_grounding: List[Dict[str, Any]] = []
    for item in raw.get("source_grounding") if isinstance(raw.get("source_grounding"), list) else []:
        if not isinstance(item, dict):
            continue
        normalized_grounding.append(
            {
                "claim": str(item.get("claim") or "").strip(),
                "source_refs": _normalize_source_refs(item.get("source_refs")) or source_titles[:2],
                "evidence": _normalize_text_list(item.get("evidence")),
            }
        )
    if not normalized_grounding and source_titles:
        normalized_grounding.append(
            {
                "claim": f"本课围绕“{lesson_identity['topic'] or '当前主题'}”组织教学设计。",
                "source_refs": source_titles[:2],
                "evidence": [f"优先参考资料：{title}" for title in source_titles[:2]],
            }
        )

    return {
        "lesson_identity": lesson_identity,
        "teaching_objectives": teaching_objectives,
        "student_profile": student_profile,
        "knowledge_structure": knowledge_structure,
        "teaching_flow": normalized_flow,
        "assessment_plan": {
            "in_class_checks": _normalize_text_list(assessment_raw.get("in_class_checks")),
            "questions": _normalize_text_list(assessment_raw.get("questions")),
            "homework": _normalize_text_list(assessment_raw.get("homework")),
            "extension_tasks": _normalize_text_list(assessment_raw.get("extension_tasks")),
        },
        "visual_asset_hints": normalized_visual_hints,
        "source_grounding": normalized_grounding,
        "style": {
            "teaching_style": str(
                style_raw.get("teaching_style")
                or requirement_style.get("teaching_style")
                or ""
            ).strip(),
            "interaction_level": str(
                style_raw.get("interaction_level")
                or requirement_style.get("interaction_level")
                or ""
            ).strip(),
            "output_preference": str(
                style_raw.get("output_preference")
                or requirement_style.get("output_preference")
                or ""
            ).strip(),
        },
    }


def core_spec_to_requirement_summary(
    core_spec: Dict[str, Any],
    fallback_requirement_summary: Dict[str, Any],
) -> Dict[str, Any]:
    lesson_identity = (
        core_spec.get("lesson_identity")
        if isinstance(core_spec.get("lesson_identity"), dict)
        else {}
    )
    teaching_objectives = (
        core_spec.get("teaching_objectives")
        if isinstance(core_spec.get("teaching_objectives"), dict)
        else {}
    )
    student_profile = (
        core_spec.get("student_profile")
        if isinstance(core_spec.get("student_profile"), dict)
        else {}
    )
    knowledge_structure = (
        core_spec.get("knowledge_structure")
        if isinstance(core_spec.get("knowledge_structure"), dict)
        else {}
    )
    style = core_spec.get("style") if isinstance(core_spec.get("style"), dict) else {}
    fallback_style = (
        fallback_requirement_summary.get("style")
        if isinstance(fallback_requirement_summary.get("style"), dict)
        else {}
    )
    fallback_student = (
        fallback_requirement_summary.get("student_profile")
        if isinstance(fallback_requirement_summary.get("student_profile"), dict)
        else {}
    )

    return {
        "topic": str(
            lesson_identity.get("topic") or fallback_requirement_summary.get("topic") or ""
        ).strip(),
        "grade_subject": str(
            lesson_identity.get("grade_subject")
            or fallback_requirement_summary.get("grade_subject")
            or ""
        ).strip(),
        "outline_type": str(
            lesson_identity.get("outline_type")
            or fallback_requirement_summary.get("outline_type")
            or ""
        ).strip(),
        "chapter_title": str(
            lesson_identity.get("chapter_title")
            or fallback_requirement_summary.get("chapter_title")
            or ""
        ).strip(),
        "duration": str(
            lesson_identity.get("duration")
            or fallback_requirement_summary.get("duration")
            or ""
        ).strip(),
        "teaching_goals": _normalize_text_list(
            teaching_objectives.get("goals")
            or fallback_requirement_summary.get("teaching_goals")
        ),
        "knowledge_points": _normalize_text_list(
            knowledge_structure.get("knowledge_points")
            or fallback_requirement_summary.get("knowledge_points")
        ),
        "key_points": _normalize_text_list(
            teaching_objectives.get("key_points")
            or fallback_requirement_summary.get("key_points")
        ),
        "difficult_points": _normalize_text_list(
            teaching_objectives.get("difficult_points")
            or fallback_requirement_summary.get("difficult_points")
        ),
        "student_profile": {
            "grade": str(
                student_profile.get("grade")
                or fallback_student.get("grade")
                or ""
            ).strip(),
            "foundation": str(
                student_profile.get("foundation")
                or fallback_student.get("foundation")
                or ""
            ).strip(),
            "learning_preference": str(
                student_profile.get("learning_preference")
                or fallback_student.get("learning_preference")
                or ""
            ).strip(),
        },
        "style": {
            "teaching_style": str(
                style.get("teaching_style")
                or fallback_style.get("teaching_style")
                or ""
            ).strip(),
            "interaction_level": str(
                style.get("interaction_level")
                or fallback_style.get("interaction_level")
                or ""
            ).strip(),
            "output_preference": str(
                style.get("output_preference")
                or fallback_style.get("output_preference")
                or ""
            ).strip(),
        },
        "output_targets": _normalize_text_list(
            teaching_objectives.get("deliverables")
            or fallback_requirement_summary.get("output_targets")
        ),
    }


def build_game_plan_seed_from_core_spec(
    core_spec: Dict[str, Any],
    requirement_summary: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    lesson_identity = (
        core_spec.get("lesson_identity")
        if isinstance(core_spec.get("lesson_identity"), dict)
        else {}
    )
    teaching_flow = (
        core_spec.get("teaching_flow")
        if isinstance(core_spec.get("teaching_flow"), list)
        else []
    )
    knowledge_structure = (
        core_spec.get("knowledge_structure")
        if isinstance(core_spec.get("knowledge_structure"), dict)
        else {}
    )
    style = core_spec.get("style") if isinstance(core_spec.get("style"), dict) else {}

    source_refs = _dedupe_non_empty(
        [
            str(item.get("source_title") or "").strip()
            for item in source_notes[:4]
            if isinstance(item, dict)
        ]
    )
    knowledge_points = _normalize_text_list(
        knowledge_structure.get("knowledge_points")
        or requirement_summary.get("knowledge_points")
    )
    topic = str(
        lesson_identity.get("topic")
        or requirement_summary.get("topic")
        or "当前主题"
    ).strip()

    stages = [
        {
            "id": "stage_1",
            "name": "基础识别",
            "goal": "快速识别核心概念，建立信心",
            "knowledge_tags": knowledge_points[:2] or [topic],
            "question_count": 3,
            "pass_rule": {
                "min_correct": 2,
                "description": "至少答对 2 题即可通关",
            },
            "review_refs": source_refs[:2],
            "teacher_tip": "先从定义、特征和基础判断入手。",
        },
        {
            "id": "stage_2",
            "name": "应用判断",
            "goal": "在情境中应用概念做出判断",
            "knowledge_tags": knowledge_points[1:3] or knowledge_points[:2] or [topic],
            "question_count": 3,
            "pass_rule": {
                "min_correct": 2,
                "description": "至少答对 2 题即可通关",
            },
            "review_refs": source_refs[:2],
            "teacher_tip": "突出方法迁移与条件判断。",
        },
        {
            "id": "stage_3",
            "name": "综合挑战",
            "goal": "综合多个知识点完成收尾挑战",
            "knowledge_tags": knowledge_points[:3] or [topic],
            "question_count": 2,
            "pass_rule": {
                "min_correct": 1,
                "description": "至少答对 1 题即可通关",
            },
            "review_refs": source_refs[:2],
            "teacher_tip": "通过综合任务完成课堂收束。",
        },
    ]

    steps: List[str] = []
    for item in teaching_flow[:3]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        goal = str(item.get("goal") or "").strip()
        if title or goal:
            steps.append(f"{title}：{goal}".strip("："))

    return {
        "mode": "level_challenge",
        "title": f"{topic}轻量闯关",
        "objective": f"围绕“{topic}”完成基础识别、应用判断与综合挑战三阶段练习",
        "theme": "clean",
        "mechanic": "三关闯关 + 即时反馈 + 课堂总结",
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
        "steps": steps,
        "materials": _normalize_text_list(knowledge_structure.get("examples_or_cases"))[:3]
        or ["课件讲解页", "课堂板书", "随堂练习"],
        "source_refs": source_refs[:3],
    }


__all__ = [
    "PROMPT_ROOT",
    "build_game_plan_seed_from_core_spec",
    "build_query_terms",
    "build_source_evidence_bundle",
    "core_spec_to_requirement_summary",
    "load_prompt_bundle",
    "normalize_core_teaching_spec",
    "render_prompt_template",
]
