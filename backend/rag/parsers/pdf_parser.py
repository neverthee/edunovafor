import os
import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader

from . import (
    PARSER_VERSION,
    ParseResult,
    build_text_chunks,
    calculate_file_hash,
    ensure_derived_dir,
    load_cached_parse_result,
    summarize_chunks,
    to_rel_upload_path,
    write_cached_parse_result,
)
from .ocr import run_remote_ocr


def parse_pdf(
    file_path: str,
    *,
    upload_root: Optional[str] = None,
    owner_id: Any = "system",
    file_hash: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    parse_mode: str = "pdf",
) -> ParseResult:
    resolved_hash = file_hash or calculate_file_hash(file_path)
    cached = load_cached_parse_result(upload_root, resolved_hash, parse_mode)
    if cached and (cached.get("raw_text") or not (api_key and api_base)):
        return cached

    try:
        import fitz
    except ImportError:
        result = _parse_pdf_with_pypdf(
            file_path=file_path,
            upload_root=upload_root,
            resolved_hash=resolved_hash,
            parse_mode=parse_mode,
        )
        write_cached_parse_result(upload_root, resolved_hash, parse_mode, result)
        return result

    document = fitz.open(file_path)
    try:
        derived_dir = ensure_derived_dir(upload_root, owner_id, resolved_hash, namespace="pdf") if upload_root else None
        pages: List[Dict[str, Any]] = []
        scan_detected = False
        has_ocr = False

        for index, page in enumerate(document, start=1):
            blocks, text_lines = _extract_text_blocks(page)
            page_text = "\n".join(text_lines).strip()
            tables = _extract_tables(page)
            table_text = "\n".join(table["markdown"] for table in tables if table.get("markdown")).strip()
            combined_text = "\n\n".join(part for part in [page_text, table_text] if part).strip()

            scanned_page = _looks_like_scan(page_text, blocks)
            if scanned_page:
                scan_detected = True
            ocr_text = ""
            images: List[Dict[str, Any]] = []
            if scanned_page and derived_dir and api_key and api_base:
                image_abs_path = os.path.join(derived_dir, f"page_{index:03d}.png")
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pixmap.save(image_abs_path)
                try:
                    ocr_result = run_remote_ocr(image_abs_path, api_key, api_base)
                    ocr_text = str(ocr_result.get("raw_text") or "").strip()
                    if ocr_text:
                        has_ocr = True
                    images.append(
                        {
                            "image_path": to_rel_upload_path(image_abs_path, upload_root),
                            "ocr_text": ocr_text,
                            "summary": str(ocr_result.get("summary") or "").strip(),
                        }
                    )
                except Exception as exc:
                    logging.warning("PDF OCR failed for %s page %s: %s", file_path, index, exc)

            pages.append(
                {
                    "page_number": index,
                    "text": combined_text or ocr_text,
                    "blocks": blocks,
                    "tables": tables,
                    "images": images,
                    "ocr_text": ocr_text,
                    "scan_detected": scanned_page,
                }
            )

        _filter_repeated_headers_and_footers(pages)

        result = _build_pdf_parse_result(
            file_path=file_path,
            pages=pages,
            has_ocr=has_ocr,
            scan_detected=scan_detected,
            parser_backend="pymupdf",
        )
        write_cached_parse_result(upload_root, resolved_hash, parse_mode, result)
        return result
    finally:
        document.close()


def _parse_pdf_with_pypdf(
    *,
    file_path: str,
    upload_root: Optional[str],
    resolved_hash: str,
    parse_mode: str,
) -> ParseResult:
    reader = PdfReader(file_path)
    pages: List[Dict[str, Any]] = []
    scan_detected = False

    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = str(page.extract_text() or "").strip()
        except Exception:
            page_text = ""
        scanned_page = len("".join(page_text.split())) < 20
        if scanned_page:
            scan_detected = True
        pages.append(
            {
                "page_number": index,
                "text": page_text,
                "blocks": [],
                "tables": [],
                "images": [],
                "ocr_text": "",
                "scan_detected": scanned_page,
            }
        )

    return _build_pdf_parse_result(
        file_path=file_path,
        pages=pages,
        has_ocr=False,
        scan_detected=scan_detected,
        parser_backend="pypdf",
    )


def _build_pdf_parse_result(
    *,
    file_path: str,
    pages: List[Dict[str, Any]],
    has_ocr: bool,
    scan_detected: bool,
    parser_backend: str,
) -> ParseResult:
    _filter_repeated_headers_and_footers(pages)
    raw_text = "\n\n".join(page["text"] for page in pages if str(page.get("text") or "").strip()).strip()
    chunks = _build_page_chunks(pages)
    return {
        "raw_text": raw_text,
        "summary": summarize_chunks(chunks, empty_text="PDF 中未提取到可用文本。"),
        "chunks": chunks,
        "structure": {"pages": pages},
        "assets": {"page_count": len(pages)},
        "meta": {
            "parser_version": PARSER_VERSION,
            "file_type": "pdf",
            "source_path": file_path,
            "has_ocr": has_ocr,
            "scan_detected": scan_detected,
            "parser_backend": parser_backend,
        },
    }


def _extract_text_blocks(page: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    text_dict = page.get_text("dict")
    blocks: List[Dict[str, Any]] = []
    text_lines: List[str] = []
    for block_index, block in enumerate(text_dict.get("blocks") or [], start=1):
        if int(block.get("type", 0)) != 0:
            continue
        block_lines: List[str] = []
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            line_text = "".join(str(span.get("text") or "") for span in spans).strip()
            if line_text:
                block_lines.append(line_text)
                text_lines.append(line_text)
        block_text = "\n".join(block_lines).strip()
        if block_text:
            blocks.append(
                {
                    "block_id": f"page{page.number + 1}_block{block_index}",
                    "text": block_text,
                    "bbox": block.get("bbox"),
                }
            )
    return blocks, text_lines


def _extract_tables(page: Any) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    try:
        finder = page.find_tables()
    except Exception:
        return tables

    for table_index, table in enumerate(getattr(finder, "tables", []) or [], start=1):
        try:
            rows = table.extract() or []
        except Exception:
            continue
        normalized_rows = [
            [str(cell or "").strip() for cell in row]
            for row in rows
            if any(str(cell or "").strip() for cell in row)
        ]
        if not normalized_rows:
            continue
        tables.append(
            {
                "table_id": f"page{page.number + 1}_table{table_index}",
                "rows": normalized_rows,
                "markdown": _table_to_markdown(normalized_rows),
            }
        )
    return tables


def _table_to_markdown(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:] or []
    markdown_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        padded = row + [""] * max(0, len(header) - len(row))
        markdown_lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    if not body and header:
        markdown_lines.append("| " + " | ".join("" for _ in header) + " |")
    return "\n".join(markdown_lines)


def _looks_like_scan(page_text: str, blocks: List[Dict[str, Any]]) -> bool:
    compact_text = "".join(str(page_text or "").split())
    if len(compact_text) >= 40 and blocks:
        return False
    return len(compact_text) < 20


def _filter_repeated_headers_and_footers(pages: List[Dict[str, Any]]) -> None:
    if len(pages) < 2:
        return
    first_line_counter: Counter[str] = Counter()
    last_line_counter: Counter[str] = Counter()
    line_pairs: List[Tuple[Optional[str], Optional[str]]] = []
    for page in pages:
        lines = [line.strip() for line in str(page.get("text") or "").splitlines() if line.strip()]
        first_line = lines[0] if lines else None
        last_line = lines[-1] if lines else None
        line_pairs.append((first_line, last_line))
        if first_line and len(first_line) <= 60:
            first_line_counter[first_line] += 1
        if last_line and len(last_line) <= 60:
            last_line_counter[last_line] += 1
    repeated_headers = {line for line, count in first_line_counter.items() if count >= 2}
    repeated_footers = {line for line, count in last_line_counter.items() if count >= 2}
    for page, (first_line, last_line) in zip(pages, line_pairs):
        lines = [line.strip() for line in str(page.get("text") or "").splitlines() if line.strip()]
        if lines and first_line in repeated_headers:
            lines = lines[1:]
        if lines and last_line in repeated_footers:
            lines = lines[:-1]
        page["text"] = "\n".join(lines).strip()


def _build_page_chunks(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for page in pages:
        page_text = str(page.get("text") or "").strip()
        if not page_text:
            continue
        page_chunks = build_text_chunks(page_text, kind="pdf_page", extra={"page": page["page_number"]})
        for offset, chunk in enumerate(page_chunks, start=1):
            chunk["index"] = len(chunks) + 1
            chunk["block_id"] = f"page{page['page_number']}_chunk{offset}"
            chunks.append(chunk)
    return chunks
