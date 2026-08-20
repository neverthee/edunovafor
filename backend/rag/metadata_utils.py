import json
from typing import Any, Dict, Iterable, List

from langchain.docstore.document import Document


def sanitize_metadata_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, set, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def sanitize_metadata_dict(metadata: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in metadata.items():
        cleaned_value = sanitize_metadata_value(value)
        if cleaned_value is None:
            continue
        sanitized[str(key)] = cleaned_value
    return sanitized


def sanitize_documents_metadata(documents: Iterable[Document]) -> List[Document]:
    sanitized_docs: List[Document] = []
    for doc in documents:
        if not isinstance(doc.metadata, dict):
            doc.metadata = {}
        doc.metadata = sanitize_metadata_dict(doc.metadata)
        sanitized_docs.append(doc)
    return sanitized_docs
