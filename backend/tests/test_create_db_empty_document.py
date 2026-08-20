import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.rag.create_db import process_document_with_progress
from backend.rag.parsers import pdf_parser


class EmptyPdfDocument:
    def __iter__(self):
        return iter(())

    def close(self):
        pass


class ProcessDocumentTests(unittest.TestCase):
    def test_empty_cache_is_reparsed_when_ocr_is_available(self):
        cached = {"raw_text": "", "chunks": []}
        fake_document = EmptyPdfDocument()
        fake_fitz = SimpleNamespace(open=lambda _: fake_document)
        with (
            patch.object(pdf_parser, "calculate_file_hash", return_value="hash"),
            patch.object(pdf_parser, "load_cached_parse_result", return_value=cached),
            patch.object(pdf_parser, "write_cached_parse_result") as write_cache,
            patch.dict(sys.modules, {"fitz": fake_fitz}),
        ):
            pdf_parser.parse_pdf("scanned.pdf", api_key="key", api_base="https://example.test")
        write_cache.assert_called_once()

    def test_rejects_empty_parsed_document_before_vectorstore_write(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "empty.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")
            with patch("backend.rag.create_db._parse_docs_with_unified_parser", return_value=[]):
                with self.assertRaisesRegex(ValueError, "未解析出可入库文本"):
                    process_document_with_progress("test", str(pdf_path))


if __name__ == "__main__":
    unittest.main()
