import os
from typing import Dict, List, Optional, Union
from urllib.parse import urlsplit


DEFAULT_CHAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_ROUTING_DEFAULTS: Dict[str, Dict[str, Union[List[str], str]]] = {
    "text": {
        "primary": "qwen-flash",
        "fallbacks": ["qwen3.5-flash", "qwen3.6-plus"],
    },
    "ocr": {
        "primary": "qwen-vl-ocr-latest",
        "fallbacks": ["qwen-vl-ocr", "qwen3-vl-flash"],
    },
    "embedding": {
        "primary": "text-embedding-v4",
        "fallbacks": ["text-embedding-v3"],
    },
    "rerank": {
        "primary": "qwen3-rerank",
        "fallbacks": ["gte-rerank-v2"],
    },
    "asr": {
        "primary": "qwen3-asr-flash-realtime",
        "fallbacks": ["qwen3-asr-flash-filetrans", "fun-asr-realtime"],
    },
}

_ROLE_ENV_KEYS = {
    "text": ("MODEL_TEXT_PRIMARY", "MODEL_TEXT_FALLBACKS"),
    "ocr": ("MODEL_OCR_PRIMARY", "MODEL_OCR_FALLBACKS"),
    "embedding": ("MODEL_EMBEDDING_PRIMARY", "MODEL_EMBEDDING_FALLBACKS"),
    "rerank": ("MODEL_RERANK_PRIMARY", "MODEL_RERANK_FALLBACKS"),
    "asr": ("MODEL_ASR_PRIMARY", "MODEL_ASR_FALLBACKS"),
}


def _split_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _unique(seq: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def get_chat_base_url() -> str:
    return (os.getenv("LLM_API_BASE") or DEFAULT_CHAT_BASE).strip().rstrip("/")


def get_rerank_url(api_base: Optional[str]) -> str:
    base = (api_base or get_chat_base_url()).strip().rstrip("/")
    if "dashscope" in base.lower() or ".maas.aliyuncs.com" in base.lower():
        parsed = urlsplit(base)
        return f"{parsed.scheme}://{parsed.netloc}/compatible-api/v1/reranks"
    return f"{base}/rerank"


def get_model_primary(role: str, preferred: Optional[str] = None) -> str:
    if preferred and str(preferred).strip():
        return str(preferred).strip()

    if role not in _ROLE_ENV_KEYS:
        raise ValueError(f"unknown model role: {role}")

    primary_key, _ = _ROLE_ENV_KEYS[role]
    env_primary = os.getenv(primary_key, "").strip()
    if env_primary:
        return env_primary

    # Backward-compatible legacy envs.
    if role == "text":
        legacy = os.getenv("LLM_MODEL", "").strip()
        if legacy:
            return legacy
    if role == "rerank":
        legacy = os.getenv("RERANK_MODEL", "").strip()
        if legacy:
            return legacy

    return str(_ROUTING_DEFAULTS[role]["primary"])


def get_model_candidates(role: str, preferred: Optional[str] = None) -> List[str]:
    primary = get_model_primary(role, preferred=preferred)
    _, fallback_key = _ROLE_ENV_KEYS[role]

    fallback_env = _split_list(os.getenv(fallback_key, ""))
    fallback_default = list(_ROUTING_DEFAULTS[role]["fallbacks"])  # type: ignore[arg-type]

    if role == "text":
        # Avoid duplicated primary when legacy LLM_MODEL equals a fallback.
        fallback_default = [item for item in fallback_default if item != primary]

    return _unique([primary, *fallback_env, *fallback_default])
