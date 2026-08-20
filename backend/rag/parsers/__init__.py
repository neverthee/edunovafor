import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, TypedDict


PARSER_VERSION = "2026-04-10-v1"


class ChunkItem(TypedDict, total=False):
    index: int
    text: str
    kind: str
    page: int
    slide_index: int
    block_id: str
    summary: str
    title: str


class PdfPageStructure(TypedDict, total=False):
    page_number: int
    text: str
    blocks: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    ocr_text: str


class DocxBlock(TypedDict, total=False):
    block_id: str
    type: str
    text: str
    level: int
    rows: List[List[str]]
    image_path: str
    ocr_text: str
    source: str


class PptSlideStructure(TypedDict, total=False):
    slide_index: int
    title: str
    text: str
    notes: str
    tables: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    ocr_text: str
    speaker_notes_weighted_text: str


class ParseResult(TypedDict):
    raw_text: str
    summary: str
    chunks: List[ChunkItem]
    structure: Dict[str, Any]
    assets: Dict[str, Any]
    meta: Dict[str, Any]


def calculate_file_hash(file_path: str) -> str:
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_processed_cache_dir(upload_root: str) -> str:
    cache_dir = os.path.join(upload_root, "processed_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def build_cache_path(upload_root: str, file_hash: str, parse_mode: str, parser_version: str = PARSER_VERSION) -> str:
    safe_mode = "".join(ch for ch in str(parse_mode or "default").lower() if ch.isalnum() or ch in {"_", "-"})
    return os.path.join(get_processed_cache_dir(upload_root), f"{file_hash}_{parser_version}_{safe_mode}.json")


def load_cached_parse_result(
    upload_root: Optional[str],
    file_hash: str,
    parse_mode: str,
    parser_version: str = PARSER_VERSION,
) -> Optional[ParseResult]:
    if not upload_root or not file_hash:
        return None
    cache_path = build_cache_path(upload_root, file_hash, parse_mode, parser_version)
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        if isinstance(payload, dict):
            return payload  # type: ignore[return-value]
    except Exception:
        return None
    return None


def write_cached_parse_result(
    upload_root: Optional[str],
    file_hash: str,
    parse_mode: str,
    result: ParseResult,
    parser_version: str = PARSER_VERSION,
) -> None:
    if not upload_root or not file_hash:
        return
    cache_path = build_cache_path(upload_root, file_hash, parse_mode, parser_version)
    with open(cache_path, "w", encoding="utf-8") as file_obj:
        json.dump(result, file_obj, ensure_ascii=False, indent=2)


def ensure_derived_dir(upload_root: str, owner_id: Any, file_hash: str, namespace: str = "parser") -> str:
    safe_owner = str(owner_id if owner_id is not None else "system")
    safe_hash = str(file_hash or "adhoc")
    derived_dir = os.path.join(upload_root, "temp", safe_owner, namespace, safe_hash)
    os.makedirs(derived_dir, exist_ok=True)
    return derived_dir


def to_rel_upload_path(abs_path: str, upload_root: Optional[str]) -> str:
    if not upload_root:
        return abs_path.replace("\\", "/")
    rel_path = os.path.relpath(abs_path, upload_root)
    return rel_path.replace("\\", "/")


def clip_text(text: str, limit: int) -> str:
    clean_text = " ".join(str(text or "").split()).strip()
    if len(clean_text) <= limit:
        return clean_text
    return clean_text[: max(0, limit - 1)].rstrip() + "…"


def summarize_chunks(chunks: List[Dict[str, Any]], empty_text: str) -> str:
    texts: List[str] = []
    for item in chunks[:5]:
        text = str(item.get("text") or item.get("summary") or "").strip()
        if text:
            texts.append(text)
    if not texts:
        return empty_text
    return clip_text("\n".join(texts), 360)


def segment_text(raw_text: str, chunk_size: int = 300) -> List[str]:
    try:
        from backend.rag.segmentor import segment_text as segment_with_model

        return segment_with_model(raw_text, chunk_size)
    except Exception:
        text = str(raw_text or "").strip()
        return [
            text[start:start + chunk_size].strip()
            for start in range(0, len(text), chunk_size)
            if text[start:start + chunk_size].strip()
        ]


def build_text_chunks(raw_text: str, *, kind: str, extra: Optional[Dict[str, Any]] = None) -> List[ChunkItem]:
    if not str(raw_text or "").strip():
        return []
    base_extra = dict(extra or {})
    chunks: List[ChunkItem] = []
    for index, segment in enumerate(segment_text(raw_text), start=1):
        if not segment.strip():
            continue
        chunk: ChunkItem = {
            "index": index,
            "text": segment.strip(),
            "kind": kind,
        }
        chunk.update(base_extra)
        chunks.append(chunk)
    return chunks


def guess_extension_from_content_type(content_type: str, fallback: str = ".bin") -> str:
    extension = mimetypes.guess_extension(content_type or "") or fallback
    if extension == ".jpe":
        return ".jpg"
    return extension


def resolve_windows_shortcut_path(candidate_path: str) -> str:
    normalized = str(candidate_path or "").strip().strip('"')
    if os.name != "nt" or not normalized.lower().endswith(".lnk") or not os.path.exists(normalized):
        return normalized

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$shell = New-Object -ComObject WScript.Shell; "
                "$shortcut = $shell.CreateShortcut($args[0]); "
                "[Console]::Out.Write($shortcut.TargetPath)",
                normalized,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        resolved = (result.stdout or "").strip().strip('"')
        if resolved:
            return resolved
    except Exception:
        pass

    return normalized


def get_soffice_command() -> Optional[str]:
    configured_paths = [
        os.getenv("SOFFICE_PATH", "").strip(),
        os.getenv("UNSTRUCTURED_SOFFICE_PATH", "").strip(),
    ]
    candidates = [path for path in configured_paths if path]
    for command_name in ("soffice", "libreoffice"):
        resolved = shutil.which(command_name)
        if resolved:
            candidates.append(resolved)
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env_name)
        if not root:
            continue
        candidates.append(os.path.join(root, "LibreOffice", "program", "soffice.exe"))
    for candidate in candidates:
        if not candidate:
            continue
        candidate = resolve_windows_shortcut_path(candidate)
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def run_soffice_convert(
    *,
    source_path: str,
    output_dir: str,
    convert_to: str,
    missing_message: str,
    timeout: int = 180,
) -> str:
    soffice = get_soffice_command()
    if not soffice:
        raise RuntimeError(missing_message)
    os.makedirs(output_dir, exist_ok=True)
    command = [
        soffice,
        "--headless",
        "--convert-to",
        convert_to,
        source_path,
        "--outdir",
        output_dir,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RuntimeError(stderr or stdout or "LibreOffice conversion failed")
    return output_dir
