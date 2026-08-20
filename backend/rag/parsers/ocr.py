import base64
import copy
import json
import mimetypes
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.config.model_routing import get_model_candidates


def build_image_data_url(image_path: str) -> str:
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    with open(image_path, "rb") as file_obj:
        encoded = base64.b64encode(file_obj.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def post_chat_completion(api_key: str, api_base: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def post_chat_completion_with_model_fallback(
    api_key: str,
    api_base: str,
    payload: Dict[str, Any],
    model_candidates: List[str],
) -> Tuple[Dict[str, Any], str]:
    errors: List[str] = []
    for model in model_candidates:
        try:
            req_payload = copy.deepcopy(payload)
            req_payload["model"] = model
            return post_chat_completion(api_key, api_base, req_payload), model
        except requests.RequestException as exc:
            errors.append(f"{model}: {exc}")
            continue
    raise RuntimeError("all candidate models failed: " + " | ".join(errors))


def extract_message_content(response_json: Dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return str(content or "")


def extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
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


def run_remote_ocr(image_path: str, api_key: str, api_base: str) -> Dict[str, Any]:
    data_url = build_image_data_url(image_path)
    system_prompt = (
        "You are an OCR extraction assistant. "
        "Return exactly one JSON object with keys raw_text, summary, tags, layout_blocks. "
        "layout_blocks must be an array of objects with optional keys label and text. "
        "Do not output markdown."
    )
    user_content = [
        {
            "type": "text",
            "text": "Extract text from this image and summarize its usable teaching content.",
        },
        {
            "type": "image_url",
            "image_url": {
                "url": data_url,
            },
        },
    ]
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
        "stream": False,
    }
    response_json, used_model = post_chat_completion_with_model_fallback(
        api_key=api_key,
        api_base=api_base,
        payload=payload,
        model_candidates=get_model_candidates("ocr"),
    )
    content = extract_message_content(response_json)
    parsed = extract_first_json_object(content) or {}
    return {
        "model": used_model,
        "raw_text": str(parsed.get("raw_text") or "").strip(),
        "summary": str(parsed.get("summary") or "").strip(),
        "tags": parsed.get("tags") if isinstance(parsed.get("tags"), list) else [],
        "layout_blocks": parsed.get("layout_blocks") if isinstance(parsed.get("layout_blocks"), list) else [],
    }
