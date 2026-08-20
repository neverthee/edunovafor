import os
import requests
import json
import time
import logging
from typing import List, Union, Dict, Any
from dotenv import load_dotenv
from backend.config.model_routing import get_chat_base_url, get_model_candidates

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
backend_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path)  # Load from backend/.env
rag_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'RAG', '.env')
if os.path.exists(rag_env_path):
    load_dotenv(rag_env_path)  # If exists, load from RAG/.env

def get_embedding(texts: Union[str, List[str]], max_retries: int = 3) -> Dict[str, Any]:
    """
    Get embeddings for text or list of texts using the Silicon Flow API.
    
    Args:
        texts: A string or list of strings to get embeddings for
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary containing the embedding results
    """
    api_key = os.getenv("LLM_API_KEY")
    api_base = get_chat_base_url()
    model_candidates = get_model_candidates("embedding")
    embedding_model = model_candidates[0]
    
    # Ensure texts is a list
    if isinstance(texts, str):
        texts = [texts]
    
    # 过滤空文本
    texts = [text.strip() for text in texts if text and text.strip()]
    if not texts:
        logger.warning("没有有效的文本进行向量化")
        # 返回空的embedding结果
        return {
            "data": [{"embedding": [0.0] * 1024}],
            "model": embedding_model,
            "usage": {"prompt_tokens": 0, "total_tokens": 0}
        }
    
    if not api_key:
        logger.warning("未配置LLM_API_KEY，返回占位符embedding")
        return {
            "data": [{"embedding": [0.0] * 1024} for _ in texts],
            "model": embedding_model,
            "usage": {"prompt_tokens": 0, "total_tokens": 0}
        }

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    errors: List[str] = []

    for model_name in model_candidates:
        embedding_model = model_name
        data = {
            "model": model_name,
            "input": texts,
            "encoding_format": "float"
        }
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"向量化请求 model={model_name} (尝试 {attempt + 1}/{max_retries}): {len(texts)} 个文本"
                )
                response = requests.post(
                    f"{api_base}/embeddings",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                if response.status_code != 200:
                    error_msg = f"{model_name} HTTP {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        time.sleep(wait_time)
                        continue
                    errors.append(error_msg)
                    break

                result = response.json()
                if "data" not in result:
                    raise Exception("API响应格式错误：缺少 'data' 字段")

                for i, item in enumerate(result["data"]):
                    if "embedding" not in item:
                        raise Exception(f"API响应格式错误：第 {i} 个结果缺少 'embedding' 字段")
                    embedding = item["embedding"]
                    if not isinstance(embedding, list):
                        raise Exception(f"API响应格式错误：第 {i} 个embedding不是数组")

                    # 保持项目当前1024维假设，避免下游向量库维度不匹配。
                    if len(embedding) != 1024:
                        if len(embedding) > 1024:
                            item["embedding"] = embedding[:1024]
                        else:
                            item["embedding"] = embedding + [0.0] * (1024 - len(embedding))

                result["model"] = model_name
                logger.info(f"向量化成功: {len(result['data'])} 个embedding, model={model_name}")
                return result

            except requests.exceptions.Timeout:
                msg = f"{model_name} timeout on attempt {attempt + 1}"
                logger.error(msg)
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                errors.append(msg)
            except requests.exceptions.RequestException as e:
                msg = f"{model_name} request error on attempt {attempt + 1}: {e}"
                logger.error(msg)
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                errors.append(msg)
            except Exception as e:
                msg = f"{model_name} unknown error on attempt {attempt + 1}: {e}"
                logger.error(msg)
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                errors.append(msg)
    
    # 如果所有重试都失败了，返回占位符embedding
    logger.warning("所有embedding候选模型都失败，返回占位符embedding: %s", " | ".join(errors))
    return {
        "data": [{"embedding": [0.0] * 1024} for _ in texts],
        "model": embedding_model,
        "usage": {"prompt_tokens": 0, "total_tokens": 0}
    }
