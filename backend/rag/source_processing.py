import base64
import copy
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

import requests
from PIL import Image
from backend.config.model_routing import get_model_candidates, get_model_primary
from backend.rag.parsers import PARSER_VERSION, build_text_chunks, run_soffice_convert
from backend.rag.parsers.docx_parser import parse_docx
from backend.rag.parsers.ocr import (
    extract_first_json_object,
    extract_message_content,
    post_chat_completion,
    post_chat_completion_with_model_fallback,
    run_remote_ocr,
)
from backend.rag.parsers.pdf_parser import parse_pdf
from backend.rag.parsers.ppt_parser import parse_ppt


logger = logging.getLogger(__name__)

DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".markdown"}
PPT_EXTENSIONS = {".ppt", ".pptx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def process_temp_sources(
    file_paths: List[str],
    source_mappings: List[Dict[str, Any]],
    upload_root: str,
    user_id: Any,
    api_key: Optional[str],
    api_base: Optional[str],
    model_name: Optional[str],
) -> List[Dict[str, Any]]:
    """Parse temporary sources and return normalized source payloads."""
    mapping_by_file = {item["file_path"]: item for item in source_mappings}
    processed_root = os.path.join(upload_root, "temp", str(user_id), "processed")
    os.makedirs(processed_root, exist_ok=True)

    sources: List[Dict[str, Any]] = []
    for rel_path in file_paths:
        mapping = mapping_by_file.get(rel_path) or {
            "file_path": rel_path,
            "file_name": os.path.basename(rel_path),
            "usage": "content",
            "knowledge_point": os.path.basename(rel_path),
            "is_required": False,
        }
        full_path = os.path.join(upload_root, rel_path)
        file_hash = _calculate_file_hash(full_path)
        cache_path = os.path.join(processed_root, f"{file_hash}.json") if file_hash else ""

        cached = _load_cached_source(cache_path)
        if cached:
            cached["mapping"] = _serialize_mapping(mapping)
            sources.append(cached)
            continue

        cacheable = True
        try:
            parsed_source = _process_single_source(
                full_path=full_path,
                rel_path=rel_path,
                mapping=mapping,
                upload_root=upload_root,
                user_id=user_id,
                file_hash=file_hash or "",
                api_key=api_key,
                api_base=api_base,
                model_name=get_model_primary("text", preferred=model_name),
            )
        except Exception as exc:
            logger.exception("failed to process temp source %s", rel_path)
            parsed_source = {
                "kind": _guess_source_kind(rel_path),
                "mapping": _serialize_mapping(mapping),
                "raw_text": "",
                "chunks": [],
                "summary": f"解析失败: {str(exc)}",
                "assets": {
                    "error": str(exc),
                    "file_path": rel_path,
                },
            }
            cacheable = False

        if cache_path and cacheable:
            _write_cached_source(cache_path, parsed_source)
        sources.append(parsed_source)

    return sources


def build_legacy_context(processed_sources: List[Dict[str, Any]]) -> str:
    """Build legacy flat text context from normalized sources."""
    parts: List[str] = []
    for source in processed_sources:
        raw_text = str(source.get("raw_text") or "").strip()
        if raw_text:
            parts.append(raw_text)
            continue

        chunks = source.get("chunks") or []
        if isinstance(chunks, list):
            chunk_texts = []
            for item in chunks:
                if isinstance(item, dict):
                    text = str(item.get("text") or item.get("summary") or "").strip()
                    if text:
                        chunk_texts.append(text)
            if chunk_texts:
                parts.append("\n".join(chunk_texts))
    return "\n\n".join([part for part in parts if part]).strip()


def _segment_text(raw_text: str) -> List[str]:
    try:
        from backend.rag.segmentor import segment_text

        return segment_text(raw_text)
    except Exception:
        chunk_size = 300
        text = raw_text.strip()
        return [
            text[start:start + chunk_size].strip()
            for start in range(0, len(text), chunk_size)
            if text[start:start + chunk_size].strip()
        ]


def _process_single_source(
    full_path: str,
    rel_path: str,
    mapping: Dict[str, Any],
    upload_root: str,
    user_id: Any,
    file_hash: str,
    api_key: Optional[str],
    api_base: Optional[str],
    model_name: str,
) -> Dict[str, Any]:
    payload = parse_source_file(
        full_path=full_path,
        rel_path=rel_path,
        upload_root=upload_root,
        user_id=user_id,
        file_hash=file_hash,
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
    )
    kind = _guess_source_kind(rel_path)
    payload["kind"] = kind
    payload["mapping"] = _serialize_mapping(mapping)
    return payload


def parse_source_file(
    *,
    full_path: str,
    rel_path: str,
    upload_root: str,
    user_id: Any,
    file_hash: str,
    api_key: Optional[str],
    api_base: Optional[str],
    model_name: str,
) -> Dict[str, Any]:
    ext = os.path.splitext(full_path)[1].lower()

    if ext in DOCUMENT_EXTENSIONS:
        payload = _process_document_file(
            full_path,
            rel_path,
            upload_root=upload_root,
            user_id=user_id,
            file_hash=file_hash,
            api_key=api_key,
            api_base=api_base,
        )
    elif ext in PPT_EXTENSIONS:
        payload = _process_ppt_file(full_path, upload_root, user_id, file_hash, api_key=api_key, api_base=api_base)
    elif ext in IMAGE_EXTENSIONS:
        payload = _process_image_file(full_path, api_key, api_base)
    elif ext in VIDEO_EXTENSIONS:
        payload = _process_video_file(full_path, upload_root, user_id, file_hash, api_key, api_base, model_name)
    else:
        raise ValueError(f"unsupported file type: {ext}")
    return payload


def _process_document_file(
    full_path: str,
    rel_path: str,
    *,
    upload_root: Optional[str] = None,
    user_id: Any = "system",
    file_hash: str = "",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> Dict[str, Any]:
    ext = os.path.splitext(full_path)[1].lower()
    if ext == ".pdf":
        result = parse_pdf(
            full_path,
            upload_root=upload_root,
            owner_id=user_id,
            file_hash=file_hash or None,
            api_key=api_key,
            api_base=api_base,
        )
    elif ext == ".docx":
        result = parse_docx(
            full_path,
            upload_root=upload_root,
            owner_id=user_id,
            file_hash=file_hash or None,
            api_key=api_key,
            api_base=api_base,
        )
    elif ext == ".doc":
        raw_text = _extract_doc_text(full_path)
        chunks = build_text_chunks(raw_text, kind="doc")
        result = {
            "raw_text": raw_text.strip(),
            "summary": _summarize_chunks(chunks, empty_text="文档中未提取到可用文本。"),
            "chunks": chunks,
            "structure": {},
            "assets": {"file_path": rel_path},
            "meta": {
                "parser_version": PARSER_VERSION,
                "file_type": "doc",
                "source_path": full_path,
                "has_ocr": False,
                "scan_detected": False,
            },
        }
    else:
        raw_text = _read_text_file(full_path)
        raw_text = raw_text.strip()
        chunks = _build_text_chunks(raw_text)
        result = {
            "raw_text": raw_text,
            "summary": _summarize_chunks(chunks, empty_text="文档中未提取到可用文本。"),
            "chunks": chunks,
            "structure": {},
            "assets": {"file_path": rel_path},
            "meta": {
                "parser_version": PARSER_VERSION,
                "file_type": ext.lstrip("."),
                "source_path": full_path,
                "has_ocr": False,
                "scan_detected": False,
            },
        }

    result.setdefault("assets", {})
    result["assets"]["file_path"] = rel_path
    return result


def _process_ppt_file(
    full_path: str,
    upload_root: str,
    user_id: Any,
    file_hash: str,
    *,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> Dict[str, Any]:
    return parse_ppt(
        full_path,
        upload_root=upload_root,
        owner_id=user_id,
        file_hash=file_hash,
        api_key=api_key,
        api_base=api_base,
    )


def _process_image_file(full_path: str, api_key: Optional[str], api_base: Optional[str]) -> Dict[str, Any]:
    if not api_key or not api_base:
        raise ValueError("OCR requires configured LLM_API_KEY and LLM_API_BASE")

    ocr_result = _run_ocr(full_path, api_key, api_base)
    raw_text = str(ocr_result.get("raw_text") or "").strip()
    summary = str(ocr_result.get("summary") or "").strip() or "图片中未识别到文字。"
    tags = ocr_result.get("tags") if isinstance(ocr_result.get("tags"), list) else []
    layout_blocks = ocr_result.get("layout_blocks") if isinstance(ocr_result.get("layout_blocks"), list) else []

    chunks = []
    if raw_text or summary:
        chunks.append(
            {
                "index": 1,
                "text": raw_text or summary,
                "summary": summary,
            }
        )

    return {
        "raw_text": raw_text,
        "chunks": chunks,
        "summary": summary,
        "structure": {"layout_blocks": layout_blocks},
        "assets": {
            "ocr_text": raw_text,
            "layout_blocks": layout_blocks,
            "tags": tags,
        },
        "meta": {
            "parser_version": PARSER_VERSION,
            "file_type": "image",
            "source_path": full_path,
            "has_ocr": bool(raw_text),
            "scan_detected": False,
        },
    }


def _process_video_file(
    full_path: str,
    upload_root: str,
    user_id: Any,
    file_hash: str,
    api_key: Optional[str],
    api_base: Optional[str],
    model_name: str,
) -> Dict[str, Any]:
    if not api_key or not api_base:
        raise ValueError("video parsing requires configured LLM_API_KEY and LLM_API_BASE")

    from backend.rag.create_db import transcribe_audio_dashscope

    derived_dir = _ensure_derived_dir(upload_root, user_id, file_hash)
    ffmpeg_bin = _locate_ffmpeg_binary()
    audio_path = _extract_audio_for_video(full_path, ffmpeg_bin, derived_dir)

    try:
        transcript_payload = transcribe_audio_dashscope(
            audio_path,
            language_hints=["zh", "en"],
            with_segments=True,
        )
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

    transcript = str(transcript_payload.get("text") or "").strip()
    transcript_segments = transcript_payload.get("segments") if isinstance(transcript_payload.get("segments"), list) else []

    summary_payload = _summarize_video_transcript(
        transcript=transcript,
        transcript_segments=transcript_segments,
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
    )

    summary = str(summary_payload.get("summary") or "").strip()
    ranked_segments = summary_payload.get("segments") if isinstance(summary_payload.get("segments"), list) else []
    ranked_segments = [
        {
            "start_ms": max(0, int(item.get("start_ms", 0))),
            "end_ms": max(0, int(item.get("end_ms", 0))),
            "summary": str(item.get("summary") or "").strip(),
            "importance_score": float(item.get("importance_score", 0) or 0),
        }
        for item in ranked_segments
        if isinstance(item, dict)
    ]
    ranked_segments.sort(key=lambda item: item.get("importance_score", 0), reverse=True)
    ranked_segments = ranked_segments[:5]
    ranked_segments.sort(key=lambda item: item.get("start_ms", 0))

    keyframes: List[Dict[str, Any]] = []
    for index, segment in enumerate(ranked_segments, start=1):
        timestamp_ms = _pick_segment_midpoint(segment["start_ms"], segment["end_ms"])
        frame_abs_path = os.path.join(derived_dir, f"keyframe_{index:02d}_{timestamp_ms}.jpg")
        _capture_video_frame(full_path, frame_abs_path, timestamp_ms, ffmpeg_bin)

        ocr_result = _run_ocr(frame_abs_path, api_key, api_base)
        keyframes.append(
            {
                "timestamp_ms": timestamp_ms,
                "image_path": _to_rel_upload_path(frame_abs_path, upload_root),
                "ocr_text": str(ocr_result.get("raw_text") or "").strip(),
                "summary": str(ocr_result.get("summary") or "").strip(),
                "tags": ocr_result.get("tags") if isinstance(ocr_result.get("tags"), list) else [],
            }
        )

    chunks = [
        {
            "index": index,
            "start_ms": item["start_ms"],
            "end_ms": item["end_ms"],
            "summary": item["summary"],
            "importance_score": item["importance_score"],
            "text": item["summary"],
        }
        for index, item in enumerate(ranked_segments, start=1)
    ]

    return {
        "raw_text": transcript,
        "chunks": chunks,
        "summary": summary or _summarize_chunks(chunks, empty_text="视频转写为空。"),
        "structure": {
            "segments": ranked_segments,
            "keyframes": keyframes,
        },
        "assets": {
            "transcript": transcript,
            "segments": ranked_segments,
            "keyframes": keyframes,
        },
        "meta": {
            "parser_version": PARSER_VERSION,
            "file_type": "video",
            "source_path": full_path,
            "has_ocr": any(str(item.get("ocr_text") or "").strip() for item in keyframes),
            "scan_detected": False,
        },
    }


def _extract_doc_text(full_path: str) -> str:
    abs_path = os.path.abspath(full_path)
    output_dir = os.path.dirname(abs_path)
    converted_pdf = os.path.splitext(abs_path)[0] + ".pdf"

    try:
        if not os.path.exists(converted_pdf):
            run_soffice_convert(
                source_path=abs_path,
                output_dir=output_dir,
                convert_to="pdf:writer_pdf_Export",
                missing_message="未安装 LibreOffice，暂时不能解析doc格式",
            )

        return parse_pdf(converted_pdf).get("raw_text", "")
    except Exception:
        try:
            from langchain_community.document_loaders import UnstructuredFileLoader
        except ImportError as exc:
            raise RuntimeError("DOC parsing requires soffice or UnstructuredFileLoader support") from exc

        loader = UnstructuredFileLoader(full_path, mode="single")
        docs = loader.load()
        return "\n".join([doc.page_content for doc in docs if doc.page_content]).strip()


def _extract_slide_notes(slide: Any) -> str:
    try:
        notes_slide = slide.notes_slide
    except Exception:
        return ""

    try:
        notes_frame = notes_slide.notes_text_frame
        if notes_frame:
            return "\n".join(
                paragraph.text.strip()
                for paragraph in notes_frame.paragraphs
                if paragraph.text and paragraph.text.strip()
            ).strip()
    except Exception:
        pass
    return ""


def _run_ocr(image_path: str, api_key: str, api_base: str) -> Dict[str, Any]:
    return run_remote_ocr(image_path, api_key, api_base)


def _summarize_video_transcript(
    transcript: str,
    transcript_segments: List[Dict[str, Any]],
    api_key: str,
    api_base: str,
    model_name: str,
) -> Dict[str, Any]:
    if not transcript.strip():
        return {"summary": "", "segments": []}

    compact_segments = []
    for item in transcript_segments:
        if not isinstance(item, dict):
            continue
        compact_segments.append(
            {
                "start_ms": int(item.get("start_ms", 0) or 0),
                "end_ms": int(item.get("end_ms", 0) or 0),
                "text": str(item.get("text") or "").strip(),
            }
        )

    system_prompt = (
        "You are a video transcript summarization assistant. "
        "Return exactly one JSON object with keys summary and segments. "
        "segments must contain 3 to 5 objects, each with start_ms, end_ms, summary, importance_score. "
        "importance_score must be a number between 0 and 1."
    )
    user_prompt = (
        "Summarize this teaching video transcript and identify the most useful key segments.\n"
        f"Transcript:\n{transcript}\n\n"
        f"Timestamped transcript segments:\n{json.dumps(compact_segments, ensure_ascii=False)}"
    )
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
        "stream": False,
    }

    response_json, _ = post_chat_completion_with_model_fallback(
        api_key=api_key,
        api_base=api_base,
        payload=payload,
        model_candidates=get_model_candidates("text", preferred=model_name),
    )
    content = extract_message_content(response_json)
    parsed = extract_first_json_object(content) or {}

    return {
        "summary": str(parsed.get("summary") or "").strip(),
        "segments": parsed.get("segments") if isinstance(parsed.get("segments"), list) else [],
    }


def _build_text_chunks(raw_text: str) -> List[Dict[str, Any]]:
    if not raw_text.strip():
        return []

    segments = _segment_text(raw_text)
    return [
        {
            "index": index,
            "text": segment.strip(),
        }
        for index, segment in enumerate(segments, start=1)
        if segment and segment.strip()
    ]


def _summarize_chunks(chunks: List[Dict[str, Any]], empty_text: str) -> str:
    texts = []
    for item in chunks[:5]:
        text = str(item.get("text") or item.get("summary") or "").strip()
        if text:
            texts.append(text)
    if not texts:
        return empty_text
    merged = "\n".join(texts)
    return _clip_text(merged, 360)


def _summarize_ppt_slides(slides: List[Dict[str, Any]]) -> str:
    preview_parts = []
    for slide in slides[:5]:
        title = str(slide.get("title") or "").strip() or f"第{slide.get('slide_index', '?')}页"
        text = str(slide.get("text") or "").strip()
        notes = str(slide.get("notes") or "").strip()
        body = text or notes
        preview_parts.append(f"{title}: {_clip_text(body, 80) if body else '无文本'}")
    if not preview_parts:
        return "PPT 中未提取到可用文本。"
    return "；".join(preview_parts)


def _pick_segment_midpoint(start_ms: int, end_ms: int) -> int:
    if end_ms <= start_ms:
        return max(0, start_ms)
    return start_ms + int((end_ms - start_ms) / 2)


def _capture_video_frame(video_path: str, output_path: str, timestamp_ms: int, ffmpeg_bin: str) -> None:
    timestamp_seconds = max(0, timestamp_ms) / 1000.0
    cmd = [
        ffmpeg_bin,
        "-ss",
        f"{timestamp_seconds:.3f}",
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "-y",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(output_path):
        raise RuntimeError("ffmpeg frame extraction did not produce an output image")

    with Image.open(output_path) as img:
        rgb_image = img.convert("RGB")
        rgb_image.save(output_path, format="JPEG", quality=90)


def _extract_audio_for_video(video_path: str, ffmpeg_bin: str, derived_dir: str) -> str:
    audio_path = os.path.join(derived_dir, "video_audio.wav")
    cmd = [
        ffmpeg_bin,
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        audio_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path


def _locate_ffmpeg_binary() -> str:
    ffmpeg_env = os.getenv("FFMPEG_PATH", "").strip()
    if ffmpeg_env and os.path.isfile(ffmpeg_env):
        return ffmpeg_env
    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg_bin:
        return ffmpeg_bin
    raise FileNotFoundError("ffmpeg not found. Install ffmpeg and add it to PATH, or set FFMPEG_PATH.")


def _ensure_derived_dir(upload_root: str, user_id: Any, file_hash: str) -> str:
    derived_dir = os.path.join(upload_root, "temp", str(user_id), "derived", file_hash)
    os.makedirs(derived_dir, exist_ok=True)
    return derived_dir


def _serialize_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file_path": mapping.get("file_path"),
        "file_name": mapping.get("file_name") or os.path.basename(str(mapping.get("file_path") or "")),
        "usage": mapping.get("usage"),
        "knowledge_point": mapping.get("knowledge_point"),
        "is_required": bool(mapping.get("is_required")),
    }


def _load_cached_source(cache_path: str) -> Optional[Dict[str, Any]]:
    if not cache_path or not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        logger.warning("failed to load cached processed source: %s", cache_path)
    return None


def _write_cached_source(cache_path: str, source_payload: Dict[str, Any]) -> None:
    if not cache_path:
        return
    cache_copy = copy.deepcopy(source_payload)
    cache_copy.pop("mapping", None)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_copy, f, ensure_ascii=False, indent=2)


def _calculate_file_hash(file_path: str) -> Optional[str]:
    import hashlib

    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None


def _guess_source_kind(path_value: str) -> str:
    ext = os.path.splitext(path_value)[1].lower()
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in PPT_EXTENSIONS:
        return "ppt"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "document"


def _read_text_file(full_path: str) -> str:
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb18030"]
    for encoding in encodings:
        try:
            with open(full_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _clip_text(text: str, limit: int) -> str:
    clean_text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean_text) <= limit:
        return clean_text
    return clean_text[: max(0, limit - 1)].rstrip() + "…"


def _to_rel_upload_path(abs_path: str, upload_root: str) -> str:
    rel_path = os.path.relpath(abs_path, upload_root)
    return rel_path.replace("\\", "/")
