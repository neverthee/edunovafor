import os
import re
import sys
import argparse
import hashlib
import json
import base64
import mimetypes
import networkx as nx
from tqdm.asyncio import tqdm
from typing import List, Callable, Optional, Dict, Any
import logging
import asyncio
import subprocess
import tempfile
import shutil
import uuid
import requests
import shutil as _shutil
import time
import traceback

# 禁用 ChromaDB telemetry 以防止崩溃
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "False"

# This is needed if embedding_util is in the parent directory.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import (
    PyMuPDFLoader,
    UnstructuredFileLoader,
    Docx2txtLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.embeddings import Embeddings  # 添加Embeddings导入
from backend.rag.embedding_util import get_embedding
from backend.rag.knowledge_graph import build_knowledge_graph
from backend.rag.metadata_utils import sanitize_documents_metadata, sanitize_metadata_dict
from backend.config.model_routing import get_chat_base_url, get_model_candidates, get_model_primary
from backend.rag.parsers import (
    calculate_file_hash as calculate_parser_file_hash,
    clip_text,
    load_cached_parse_result,
    run_soffice_convert,
)
from backend.rag.parsers.docx_parser import parse_docx
from backend.rag.parsers.pdf_parser import parse_pdf
from backend.rag.parsers.ppt_parser import parse_ppt
from backend.rag.chapter_generation_from_material import preview_generate_chapters_from_material

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _guess_upload_root(file_path: str) -> str:
    normalized = os.path.abspath(file_path).replace("\\", "/")
    marker = "/uploads/"
    if marker in normalized:
        return normalized.split(marker, 1)[0] + marker.rstrip("/")
    return os.path.dirname(os.path.abspath(file_path))

def _normalize_upload_relative_path(file_path: str) -> str:
    normalized = os.path.abspath(file_path).replace("\\", "/")
    marker = "/uploads/"
    if marker in normalized:
        return normalized.split(marker, 1)[1].lstrip("/")
    return os.path.basename(file_path)


def _parse_docs_with_unified_parser(file_path: str, filename: str, purpose: Optional[str] = None) -> List[Document]:
    ext = os.path.splitext(filename)[1].lower()
    upload_root = _guess_upload_root(file_path)
    relative_file_path = _normalize_upload_relative_path(file_path)
    ocr_api_key = os.getenv("LLM_API_KEY")
    ocr_api_base = os.getenv("LLM_API_BASE")

    if ext == ".pdf":
        parsed = parse_pdf(
            file_path,
            upload_root=upload_root,
            owner_id="kb",
            api_key=ocr_api_key,
            api_base=ocr_api_base,
            parse_mode="create_db",
        )
    elif ext == ".docx":
        parsed = parse_docx(file_path, upload_root=upload_root, owner_id="kb", parse_mode="create_db")
    elif ext == ".doc":
        abs_in = os.path.abspath(file_path)
        src_dir = os.path.dirname(abs_in)
        converted_pdf = os.path.splitext(abs_in)[0] + ".pdf"
        if not os.path.exists(converted_pdf):
            run_soffice_convert(
                source_path=abs_in,
                output_dir=src_dir,
                convert_to="pdf:writer_pdf_Export",
                missing_message="未安装 LibreOffice，暂时不能解析doc格式",
            )
        parsed = parse_pdf(
            converted_pdf,
            upload_root=upload_root,
            owner_id="kb",
            api_key=ocr_api_key,
            api_base=ocr_api_base,
            parse_mode="create_db_doc",
        )
    elif ext in [".ppt", ".pptx"]:
        parsed = parse_ppt(file_path, upload_root=upload_root, owner_id="kb", parse_mode="create_db")
    else:
        raise ValueError(f"unsupported parser file type: {ext}")

    chunks = parsed.get("chunks") if isinstance(parsed.get("chunks"), list) else []
    docs: List[Document] = []
    if chunks:
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text") or "").strip()
            if not text:
                continue
            metadata = {
                "source": filename,
                "file_path": relative_file_path,
                "kind": chunk.get("kind"),
                "page": chunk.get("page"),
                "slide_index": chunk.get("slide_index"),
                "block_id": chunk.get("block_id"),
                "parser_version": parsed.get("meta", {}).get("parser_version") if isinstance(parsed.get("meta"), dict) else None,
            }
            if purpose is not None:
                metadata["purpose"] = purpose
            docs.append(Document(page_content=text, metadata=sanitize_metadata_dict(metadata)))
        return docs

    raw_text = str(parsed.get("raw_text") or "").strip()
    if raw_text:
        metadata = {"source": filename, "file_path": relative_file_path}
        if purpose is not None:
            metadata["purpose"] = purpose
        docs.append(Document(page_content=raw_text, metadata=sanitize_metadata_dict(metadata)))
    return docs


def _normalize_structured_keyword(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^第[一二三四五六七八九十百0-9]+章\s*", "", text)
    text = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", text)
    return text[:16]


def _extract_structured_keywords(filename: str, parsed_result: Dict[str, Any], chapters: List[Dict[str, Any]]) -> List[str]:
    candidates: List[str] = []

    for chapter in chapters:
        title = _normalize_structured_keyword(chapter.get("title"))
        if title:
            candidates.append(title)

    summary_text = str(parsed_result.get("summary") or "")
    raw_text = str(parsed_result.get("raw_text") or "")
    text_sample = "\n".join(part for part in [summary_text, raw_text[:2000]] if part).strip()
    for token in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,10}", text_sample):
        normalized = _normalize_structured_keyword(token)
        if normalized:
            candidates.append(normalized)

    filename_token = _normalize_structured_keyword(os.path.splitext(filename)[0])
    if filename_token:
        candidates.append(filename_token)

    blocked = {"人民教育出版社", "zlibrarysk", "1libsk", "zlibsk", "librarysk", "uploads", "materials"}
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


def _build_pdf_outline_titles(chapters: List[Dict[str, Any]]) -> List[str]:
    titles: List[str] = []
    for chapter in chapters:
        title = str(chapter.get("title") or "").strip()
        if title and title not in titles:
            titles.append(title)
    return titles


def _save_pdf_structured_index(
    *,
    course_id: str,
    kb_dir: str,
    file_path: str,
    filename: str,
    relative_file_path: str,
    purpose: str,
) -> Optional[Dict[str, Any]]:
    upload_root = _guess_upload_root(file_path)
    parser_hash = calculate_parser_file_hash(file_path)
    parsed_result = load_cached_parse_result(upload_root, parser_hash, "create_db")
    if not parsed_result:
        parsed_result = parse_pdf(file_path, upload_root=upload_root, owner_id="kb", parse_mode="create_db")

    if not isinstance(parsed_result, dict):
        return None

    try:
        chapter_preview = preview_generate_chapters_from_material(
            course_name=f"课程 {course_id}",
            course_id=int(course_id),
            source_type="pdf",
            material_title=filename,
            material_path=file_path,
            upload_root=upload_root,
            existing_chapters=[],
        )
        chapters = chapter_preview.get("generated_chapters") if isinstance(chapter_preview, dict) else []
    except Exception as exc:
        logging.warning("build structured chapter index failed for %s: %s", filename, exc)
        chapters = []

    if not isinstance(chapters, list):
        chapters = []

    summary_text = clip_text(str(parsed_result.get("summary") or parsed_result.get("raw_text") or "").strip(), 600)
    outline_titles = _build_pdf_outline_titles(chapters)
    keywords = _extract_structured_keywords(filename, parsed_result, chapters)
    page_count = 0
    assets = parsed_result.get("assets")
    if isinstance(assets, dict):
        try:
            page_count = int(assets.get("page_count") or 0)
        except (TypeError, ValueError):
            page_count = 0

    index_payload: Dict[str, Any] = {
        "file_name": filename,
        "file_path": relative_file_path,
        "file_hash": parser_hash,
        "course_id": course_id,
        "file_type": "pdf",
        "purpose": purpose,
        "summary": summary_text,
        "keywords": keywords,
        "outline": outline_titles,
        "chapters": chapters,
        "page_count": page_count,
        "updated_at": int(time.time()),
    }

    structured_dir = os.path.join(kb_dir, "structured")
    os.makedirs(structured_dir, exist_ok=True)
    index_path = os.path.join(structured_dir, f"{parser_hash}.json")
    with open(index_path, "w", encoding="utf-8") as file_obj:
        json.dump(index_payload, file_obj, ensure_ascii=False, indent=2)

    return {
        "index_path": index_path.replace("\\", "/"),
        "file_hash": parser_hash,
        "keywords": keywords,
        "outline": outline_titles,
        "summary": summary_text,
        "page_count": page_count,
    }

# --- Configurable parameters via environment variables ---
# Larger chunk reduces number of LLM calls (speed ↑) but increases prompt size.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))  # 减小到300字符，确保不超过512 tokens限制
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))  # 相应减小overlap
# Max parallel API calls (respect provider's rate-limit)
CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY", "8"))

# --- LLM and Parser Initialization ---
def get_llm():
    """Initializes and returns the LLM."""
    # Fetch credentials from generic environment variables so that any provider compatible with
    # the OpenAI API can be plugged in by simply editing the .env file (no code changes needed).
    api_key = os.getenv("LLM_API_KEY")
    base_url = get_chat_base_url()
    model_name = get_model_primary("text")

    if not api_key:
        raise ValueError("LLM_API_KEY not found in .env file.")
    if not base_url:
        raise ValueError("LLM_API_BASE not found in .env file.")
    if not model_name:
        raise ValueError("LLM_MODEL not found in .env file.")
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0,
        max_retries=3
    )

def get_graph_extraction_chain(llm):
    """Creates a chain for extracting entities and relationships."""
    prompt = ChatPromptTemplate.from_template("""
From the following text, extract key entities (like concepts, people, technologies) and the relationships between them.
Format the output as a JSON object with two keys: 'entities' and 'relationships'.
- 'entities' should be a list of objects, each with 'name' (the entity's name) and 'type' (e.g., 'Concept', 'Person', 'Technology').
- 'relationships' should be a list of objects, each with 'source' (source entity name), 'target' (target entity name), and 'label' (a description of the relationship).
The entity names in relationships must exactly match the names in the entities list.

Text:
---
{chunk_text}
---
    """)
    return prompt | llm | JsonOutputParser()

# --- 自定义文本分割器类 ---
class CustomTextSplitter:
    """使用自定义segmentor实现的文本分割器，兼容LangChain接口"""
    
    def __init__(self, chunk_size=300, chunk_overlap=50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 延迟导入segment_text，避免循环导入
        self._segment_text = None
    
    @property
    def segment_text(self):
        """延迟加载segment_text函数"""
        if self._segment_text is None:
            # 在需要时才导入，避免循环导入
            from backend.rag.segmentor import segment_text
            self._segment_text = segment_text
        return self._segment_text
    
    def split_text(self, text):
        """使用自定义分割器分割文本"""
        try:
            # 使用自定义分割器
            chunks = self.segment_text(text, self.chunk_size)
            logging.info(f"使用分割器成功分割文本为 {len(chunks)} 个块")
            return chunks
        except Exception as e:
            logging.error(f"自定义分割器失败: {e}，回退到简单分割")
            # 简单的回退分割方法
            return self._simple_split(text)
    
    def _simple_split(self, text):
        """简单的分割方法，作为回退"""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
    
    def split_documents(self, documents):
        """分割文档列表，兼容LangChain接口"""
        texts = []
        for doc in documents:
            doc_texts = self.split_text(doc.page_content)
            for text in doc_texts:
                new_doc = Document(
                    page_content=text,
                    metadata=doc.metadata.copy()
                )
                texts.append(new_doc)
        return texts

# --- Embedding Function Definition ---
class EmbeddingFunction(Embeddings):  # 继承自Embeddings接口
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.batch_size = 5  # 进一步减小批处理大小，避免API限制
        self.logger = logging.getLogger(__name__)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents using Silicon Flow API with correct dimension"""
        try:
            from backend.rag.embedding_util import get_embedding
            
            # 过滤空文本
            texts = [text.strip() for text in texts if text and text.strip()]
            if not texts:
                self.logger.warning("没有有效的文本进行向量化")
                return [[0.0] * 1024]
            
            # 分批处理
            batch_size = self.batch_size
            all_embeddings = []
            
            self.logger.info(f"开始向量化 {len(texts)} 个文本，批处理大小: {batch_size}")
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(texts) + batch_size - 1) // batch_size
                
                self.logger.info(f"处理批次 {batch_num}/{total_batches}: {len(batch)} 个文本")
                
                try:
                    result = get_embedding(batch, max_retries=3)
                    
                    if 'data' in result and result['data']:
                        batch_embeddings = [item['embedding'] for item in result['data']]
                        all_embeddings.extend(batch_embeddings)
                        self.logger.info(f"批次 {batch_num} 向量化成功: {len(batch_embeddings)} 个embedding")
                    else:
                        self.logger.error(f"批次 {batch_num} API返回格式错误")
                        # 为这个批次创建占位符embedding
                        batch_embeddings = [[0.0] * 1024 for _ in batch]
                        all_embeddings.extend(batch_embeddings)
                    
                    # 更新进度
                    if self.progress_callback:
                        progress = min(100, (i + len(batch)) / len(texts) * 100)
                        self.progress_callback(progress)
                        
                except Exception as batch_error:
                    self.logger.error(f"批次 {batch_num} 向量化失败: {batch_error}")
                    # 为这个批次创建占位符embedding
                    batch_embeddings = [[0.0] * 1024 for _ in batch]
                    all_embeddings.extend(batch_embeddings)
                    
                    # 继续处理下一个批次，而不是完全失败
                    continue
            
            # 验证维度（siliconflow BAAI/bge-large-zh-v1.5 = 1024维）
            embedding_dimension = 1024
            if all_embeddings:
                for i, embedding in enumerate(all_embeddings):
                    if len(embedding) != embedding_dimension:
                        self.logger.error(f"第 {i} 个embedding维度不匹配: 期望{embedding_dimension}，实际{len(embedding)}")
                        # 修正维度
                        if len(embedding) > embedding_dimension:
                            all_embeddings[i] = embedding[:embedding_dimension]
                        else:
                            all_embeddings[i] = embedding + [0.0] * (embedding_dimension - len(embedding))
            
            self.logger.info(f"向量化完成: {len(all_embeddings)} 个embedding")
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"向量化过程中出现严重错误: {e}")
            # 返回占位符embedding，确保不会崩溃
            embedding_dimension = 1024
            return [[0.0] * embedding_dimension] * len(texts)

    def embed_query(self, text: str) -> List[float]:
        """用于查询的embedding方法"""
        try:
            from backend.rag.embedding_util import get_embedding
            
            if not text or not text.strip():
                self.logger.warning("查询文本为空")
                return [0.0] * 1024
            
            result = get_embedding([text], max_retries=3)
            if 'data' in result and result['data']:
                embedding = result['data'][0]['embedding']
                # 验证维度
                if len(embedding) != 1024:
                    self.logger.error(f"查询embedding维度不匹配: 期望1024，实际{len(embedding)}")
                    if len(embedding) > 1024:
                        embedding = embedding[:1024]
                    else:
                        embedding = embedding + [0.0] * (1024 - len(embedding))
                return embedding
            else:
                self.logger.error("查询embedding API返回格式错误")
                return [0.0] * 1024
        except Exception as e:
            self.logger.error(f"查询embedding失败: {e}")
            return [0.0] * 1024

# --- Helper Functions ---
def get_or_create_course_db_path(course_id: str, base_persist_dir: str = "uploads/knowledge_base") -> str:
    persist_dir = os.path.join(base_persist_dir, course_id)
    os.makedirs(persist_dir, exist_ok=True)
    return persist_dir

def get_file_hash(file_path: str) -> str:
    """获取文件的MD5哈希值"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read(65536)  # 64kb chunks
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def load_processed_files_metadata(metadata_file: str) -> dict:
    """加载已处理文件的元数据"""
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def save_processed_files_metadata(metadata_file: str, data: dict):
    """保存已处理文件的元数据"""
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def process_chunk_for_graph(chunk, graph_extraction_chain):
    """Asynchronously processes a single chunk to extract graph data."""
    chunk_id = chunk.metadata['chunk_id']
    try:
        graph_data = await graph_extraction_chain.ainvoke({"chunk_text": chunk.page_content})
        
        entities = []
        # Add entities to a temporary list
        for entity in graph_data.get('entities', []):
            name = entity['name'].strip().upper()
            if name:
                entities.append((name, entity.get('type', 'Unknown')))

        relationships = []
        # Add relationships to a temporary list
        for rel in graph_data.get('relationships', []):
            source = rel['source'].strip().upper()
            target = rel['target'].strip().upper()
            if source and target:
                relationships.append((source, target, rel.get('label', '')))
        
        return chunk_id, entities, relationships
            
    except Exception as e:
        logging.error(f"Failed to process chunk {chunk_id} for graph extraction: {e}")
        return chunk_id, [], []

# --- Main Processing Function ---
async def process_documents(course_id: str, force_rebuild: bool = False):
    """处理文档并构建知识图谱"""
    course_doc_dir = os.path.join("backend/uploads/materials", course_id)
    if not os.path.exists(course_doc_dir):
        logging.warning(f"Directory not found for course '{course_id}', skipping.")
        return

    persist_dir = get_or_create_course_db_path(course_id)
    metadata_file = os.path.join(persist_dir, 'processed_files_metadata.json')
    graph_file_path = os.path.join(persist_dir, 'knowledge_graph.gml')
    
    # 加载已处理文件的元数据
    processed_files_metadata = load_processed_files_metadata(metadata_file)

    if force_rebuild and os.path.exists(graph_file_path):
        logging.info("Force rebuild enabled: Removing old knowledge graph.")
        os.remove(graph_file_path)

    if force_rebuild:
        logging.info("Force rebuild enabled: Clearing old metadata to re-process all files.")
        processed_files_metadata = {}

    # 检查需要处理的文件
    files_to_process = []
    for filename in os.listdir(course_doc_dir):
        file_path = os.path.join(course_doc_dir, filename)
        if not os.path.isfile(file_path):
            continue
        
        current_hash = get_file_hash(file_path)
        if filename not in processed_files_metadata or processed_files_metadata[filename] != current_hash:
            files_to_process.append((filename, file_path))
            processed_files_metadata[filename] = current_hash

    if not files_to_process:
        logging.info("No new or modified documents to process.")
        return

    logging.info(f"Found {len(files_to_process)} new or modified files to process.")
    
    # 处理文档并构建知识图谱
    all_docs = []
    for filename, file_path in tqdm(files_to_process, desc="Loading documents"):
        try:
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".pdf", ".docx", ".doc", ".ppt", ".pptx"]:
                docs = _parse_docs_with_unified_parser(file_path, filename)
            elif ext in ['.md', '.markdown']:
                # 直接用open读取Markdown文本，避免复杂Loader
                try:
                    from langchain_core.documents import Document
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    docs = [Document(page_content=content, metadata={"source": filename})]
                    print("用open直接读取md文件成功")
                except Exception as e:
                    print(f"open读取md失败: {e}")
                    raise
            else:
                # Fallback to generic loader
                loader = UnstructuredFileLoader(file_path, mode="single")
                docs = loader.load()
            for doc in docs:
                doc.metadata['source'] = filename
            all_docs.extend(docs)
        except Exception as e:
            logging.error(f"Error loading file {file_path}: {e}")
            if filename in processed_files_metadata:
                del processed_files_metadata[filename]
    
    if not all_docs:
        logging.info("No content loaded from new/modified files.")
        return

    # 分割文档
    logging.info(f"Splitting documents into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    text_splitter = CustomTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    splits = text_splitter.split_documents(all_docs)
    
    # 添加唯一ID
    for i, doc in enumerate(splits):
        doc.metadata['chunk_id'] = f"chunk_{i}"
    sanitize_documents_metadata(splits)

    # 创建向量存储
    logging.info("Creating/updating vectorstore...")
    embedding_function = EmbeddingFunction()
    Chroma.from_documents(
        documents=splits,
        embedding=embedding_function,
        persist_directory=persist_dir
    )
    
    # 构建知识图谱
    logging.info("开始构建知识图谱...")
    try:
        def progress_callback(progress):
            logging.info(f"知识图谱构建进度: {progress:.1f}%")
        
        graph_success = build_knowledge_graph(course_id, splits, progress_callback)
        if graph_success:
            logging.info("知识图谱构建成功")
        else:
            logging.warning("知识图谱构建失败，但向量存储已创建")
    except Exception as e:
        logging.error(f"构建知识图谱时出错: {e}")
        logging.info("继续处理，向量存储已创建")
    
    # 保存元数据
    logging.info("Saving updated file metadata...")
    save_processed_files_metadata(metadata_file, processed_files_metadata)
    logging.info("Database creation/update process complete.")

FFMPEG_BIN = os.getenv("FFMPEG_PATH", "ffmpeg")  # allow override if ffmpeg not in PATH

def _locate_ffmpeg() -> str:
    """Return path to ffmpeg executable or raise a descriptive error."""
    # 1) explicit env var path
    if os.path.isfile(FFMPEG_BIN):
        logging.debug(f"Using ffmpeg from env var: {FFMPEG_BIN}")
        return FFMPEG_BIN

    # 2) PATH search
    path = _shutil.which(FFMPEG_BIN)
    if path:
        logging.debug(f"Found ffmpeg in PATH at: {path}")
        return path

    # 3) Heuristic search under common Program Files directories (Windows only)
    if os.name == 'nt':
        import glob
        candidates = []
        for base in [
            os.environ.get("ProgramFiles", r"C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
        ]:
            pattern = os.path.join(base, "**", "ffmpeg.exe")
            candidates.extend(glob.glob(pattern, recursive=True))
        if candidates:
            logging.debug(f"Auto-detected ffmpeg candidates: {candidates[:3]}")
            return candidates[0]

    raise FileNotFoundError(
        "ffmpeg executable not found. Install FFmpeg and ensure it is in your PATH, or set "
        "environment variable FFMPEG_PATH to its full path (e.g. C:/ffmpeg/bin/ffmpeg.exe)."
    )

def extract_audio(video_path: str) -> str:
    """Extract mono 16k WAV from an mp4 file. Returns path to the wav inside a temp dir."""
    tmp_dir = tempfile.mkdtemp()
    wav_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}.wav")
    ffmpeg = _locate_ffmpeg()
    cmd = [
        ffmpeg,
        "-i",
        video_path,
        "-vn",  # no video
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        wav_path,
        "-y",
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path

def _resolve_dashscope_audio_base() -> str:
    """Resolve DashScope OpenAI-compatible base for audio transcription."""
    llm_base = os.getenv("LLM_API_BASE", "").strip()
    if llm_base and ("dashscope" in llm_base.lower() or ".maas.aliyuncs.com" in llm_base.lower()):
        return llm_base.rstrip("/")
    # Default to DashScope OpenAI-compatible endpoint
    return "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _resolve_compatible_asr_models() -> List[str]:
    """Resolve model candidates for DashScope OpenAI-compatible ASR."""
    candidates = ["qwen3-asr-flash"]
    for model_name in get_model_candidates("asr"):
        normalized = str(model_name or "").strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in {"qwen3-asr-flash-realtime", "qwen3-asr-flash-filetrans", "fun-asr-realtime"}:
            continue
        candidates.append(normalized)

    seen = set()
    ordered: List[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _guess_audio_mime_type(audio_path: str, mime_type: Optional[str] = None) -> str:
    explicit = (mime_type or "").strip()
    if explicit:
        return explicit
    guessed, _ = mimetypes.guess_type(audio_path)
    return guessed or "audio/webm"


def _read_audio_as_data_uri(audio_path: str, mime_type: Optional[str] = None) -> str:
    resolved_mime = _guess_audio_mime_type(audio_path, mime_type=mime_type)
    with open(audio_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{resolved_mime};base64,{encoded}"


def _extract_chat_completion_text(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if text_value:
                parts.append(str(text_value).strip())
        return "\n".join(part for part in parts if part).strip()

    return ""

def transcribe_audio_dashscope(
    audio_path: str,
    language_hints: Optional[List[str]] = None,
    with_segments: bool = False,
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Transcribe audio with DashScope and return normalized result."""
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY not set for audio transcription")

    url = f"{_resolve_dashscope_audio_base()}/chat/completions"
    payload: Dict[str, Any] = {}
    used_model = ""
    errors: List[str] = []
    data_uri = _read_audio_as_data_uri(audio_path, mime_type=mime_type)

    model_candidates = _resolve_compatible_asr_models()
    for model_name in model_candidates:
        request_payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": data_uri,
                            }
                        }
                    ]
                }
            ],
            "stream": False,
            "asr_options": {
                "enable_itn": False,
            }
        }
        if language_hints:
            request_payload["asr_options"]["language"] = str(language_hints[0]).strip()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=request_payload, headers=headers, timeout=180)
        if resp.ok:
            payload = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {"text": resp.text}
            used_model = model_name
            break
        error_body = ""
        try:
            error_body = json.dumps(resp.json(), ensure_ascii=False)
        except Exception:
            error_body = resp.text.strip()
        errors.append(f"{model_name}: HTTP {resp.status_code} {error_body[:240]}".strip())
    else:
        raise RuntimeError("ASR models failed: " + " | ".join(errors))

    text = ""
    segments: List[Dict[str, Any]] = []
    duration_ms = 0
    if isinstance(payload, dict):
        text = _extract_chat_completion_text(payload) or str(payload.get("text") or payload.get("transcript") or "")
        raw_segments = payload.get("segments") or []
        if isinstance(raw_segments, list):
            for item in raw_segments:
                if not isinstance(item, dict):
                    continue
                start_ms = int(float(item.get("start", 0)) * 1000) if item.get("start") is not None else 0
                end_ms = int(float(item.get("end", 0)) * 1000) if item.get("end") is not None else 0
                if end_ms > duration_ms:
                    duration_ms = end_ms
                segments.append({
                    "start_ms": max(0, start_ms),
                    "end_ms": max(0, end_ms),
                    "text": str(item.get("text") or "")
                })
        # Some providers may return duration in seconds
        if payload.get("duration"):
            try:
                duration_ms = max(duration_ms, int(float(payload["duration"]) * 1000))
            except (TypeError, ValueError):
                pass
    elif isinstance(payload, str):
        text = payload

    return {
        "text": text.strip(),
        "segments": segments,
        "duration_ms": duration_ms,
        "provider": "dashscope",
        "model": used_model
    }

def transcribe_audio(audio_path: str) -> str:
    """Backward-compatible helper: return plain transcript text only."""
    result = transcribe_audio_dashscope(audio_path, with_segments=False)
    return result.get("text", "")

def process_document_with_progress(course_id: str, file_path: str, progress_callback: Optional[Callable[[float], None]] = None, purpose: str = 'general'):
    """Process a single document and report progress - 简化版本，暂时关闭知识图谱构建
    
    Args:
        course_id: 课程ID
        file_path: 文件路径
        progress_callback: 进度回调函数
        purpose: 文件用途，如'general'(一般),'lesson_plan'(备课),'assessment'(考核)等
    """
    
    def report_progress(stage: str, current: int, total: int):
        """Report progress for a specific stage"""
        if progress_callback:
            # 简化进度计算，去掉知识图谱阶段
            stage_weights = {
                'loading': 0.2,
                'splitting': 0.1,
                'vectorizing': 0.6,
                'saving': 0.1
            }
            
            # Calculate overall progress
            stage_start = sum([w for s, w in stage_weights.items() if s < stage]) * 100
            stage_progress = (current / total) * stage_weights[stage] * 100
            total_progress = stage_start + stage_progress
            
            # Create stage message
            stage_messages = {
                'loading': '正在加载文档',
                'splitting': '正在分割文档',
                'vectorizing': '正在向量化文档',
                'saving': '正在保存元数据'
            }
            message = stage_messages.get(stage, f'处理阶段: {stage}')
            
            # Call progress callback with stage and message
            try:
                # First try with all parameters
                progress_callback(min(total_progress, 99.9), stage, message)
            except TypeError:
                try:
                    # Then try with just progress
                    progress_callback(min(total_progress, 99.9))
                except Exception as e:
                    # If all fails, log the error but continue
                    logging.error(f"Error calling progress_callback: {e}")
    
    try:
        print(f"=== 开始处理文档: {os.path.basename(file_path)} ===")
        
        # Set up knowledge base directory
        kb_dir = os.path.join("uploads/knowledge_base", course_id)
        os.makedirs(kb_dir, exist_ok=True)
        
        # Stage 1: Loading document
        print("阶段1: 加载文档...")
        report_progress('loading', 0, 1)
        
        # Determine file type and load document
        filename = os.path.basename(file_path)
        relative_file_path = _normalize_upload_relative_path(file_path)
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if ext in ['.pdf', '.docx', '.doc', '.ppt', '.pptx']:
            docs = _parse_docs_with_unified_parser(file_path, filename, purpose=purpose)
            print("✓ 使用统一 parser 加载文档")
        elif ext in ['.md', '.markdown']:
            # 直接用open读取Markdown文本，避免复杂Loader
            try:
                from langchain_core.documents import Document
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                docs = [Document(page_content=content, metadata={"source": filename, "file_path": relative_file_path})]
                print("✓ 用open直接读取md文件成功")
            except Exception as e:
                print(f"✗ open读取md失败: {e}")
                raise
        else:
            # Fallback to generic loader
            loader = UnstructuredFileLoader(file_path, mode="single")
            print("✓ 使用UnstructuredFileLoader加载文件")
        
        if ext not in ['.md', '.markdown', '.pdf', '.docx', '.doc', '.ppt', '.pptx']:
            docs = loader.load()
        if not docs:
            hint = '；扫描版 PDF 需要配置 LLM_API_KEY 和 LLM_API_BASE 以启用 OCR' if ext == '.pdf' else ''
            raise ValueError(f'文档未解析出可入库文本{hint}')
        for doc in docs:
            doc.metadata['source'] = filename
            doc.metadata['file_path'] = relative_file_path
            # 添加文件用途标记
            doc.metadata['purpose'] = purpose

        structured_index_meta = None
        if ext == '.pdf':
            try:
                structured_index_meta = _save_pdf_structured_index(
                    course_id=course_id,
                    kb_dir=kb_dir,
                    file_path=file_path,
                    filename=filename,
                    relative_file_path=relative_file_path,
                    purpose=purpose,
                )
                if structured_index_meta:
                    print("✓ PDF 结构化索引已生成")
            except Exception as exc:
                logging.warning(f"生成 PDF 结构化索引失败: {exc}")
        
        print(f"✓ 文档加载完成，共 {len(docs)} 个文档")
        report_progress('loading', 1, 1)
        
        # Stage 2: Splitting document
        print("阶段2: 分割文档...")
        report_progress('splitting', 0, 1)
        text_splitter = CustomTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        splits = text_splitter.split_documents(docs)
        
        # Add a unique ID to each split
        for i, doc in enumerate(splits):
            doc.metadata['chunk_id'] = f"chunk_{i}"
            # 确保每个分割后的文档也有用途标记
            if 'purpose' not in doc.metadata:
                doc.metadata['purpose'] = purpose
        sanitize_documents_metadata(splits)

        print(f"✓ 文档分割完成，共 {len(splits)} 个文本块")
        report_progress('splitting', 1, 1)
        
        # Stage 3: Vectorizing
        print("阶段3: 向量化文档...")
        report_progress('vectorizing', 0, 1)
        
        # 创建向量数据库
        persist_dir = os.path.join(kb_dir, "vectordb")
        os.makedirs(persist_dir, exist_ok=True)
        
        # 使用现有的EmbeddingFunction类
        embedding_function = EmbeddingFunction()
        
        # 创建Chroma向量数据库，关闭遥测
        from chromadb.config import Settings
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embedding_function,
            client_settings=Settings(anonymized_telemetry=False)
        )
        
        # Add documents to vectorstore
        print(f"正在添加 {len(splits)} 个文本块到向量数据库...")
        vectorstore.add_documents(splits)
        print("✓ 向量化完成")
        
        report_progress('vectorizing', 100, 100)
        
        # Stage 4: Saving metadata (简化版本，跳过知识图谱)
        print("阶段4: 保存元数据...")
        report_progress('saving', 0, 1)
        
        # Save metadata about processed files
        metadata_path = os.path.join(kb_dir, 'processed_files.json')
        processed_files = {}
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                processed_files = json.load(f)
        
        # Add this file to processed files
        file_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
        processed_files[filename] = {
            'hash': file_hash,
            'processed_at': int(time.time()),
            'chunks': len(splits),
            'purpose': purpose  # 添加文件用途
        }
        if structured_index_meta:
            processed_files[filename]['structured_index'] = {
                'path': structured_index_meta.get('index_path'),
                'summary': structured_index_meta.get('summary'),
                'keywords': structured_index_meta.get('keywords'),
                'outline': structured_index_meta.get('outline'),
                'page_count': structured_index_meta.get('page_count'),
                'file_hash': structured_index_meta.get('file_hash'),
            }
        
        with open(metadata_path, 'w') as f:
            json.dump(processed_files, f, indent=2)
        
        print("✓ 元数据保存完成")
        report_progress('saving', 1, 1)
        
        print(f"=== 文档处理完成: {filename} ===")
        print(f"✓ 文本块数量: {len(splits)}")
        print(f"✓ 向量数据库位置: {persist_dir}")
        print(f"✓ 文件用途: {purpose}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        print(f"✗ 处理文档时出错: {e}")
        print(traceback.format_exc())
        if progress_callback:
            progress_callback(-1)  # Indicate error
        raise

def remove_document_from_knowledge_base(course_id: str, file_path: str) -> bool:
    """
    从知识库中删除指定文档
    
    Args:
        course_id: 课程ID
        file_path: 文件路径
        
    Returns:
        bool: 删除是否成功
    """
    try:
        # 获取知识库路径
        persist_dir = get_or_create_course_db_path(course_id)
        normalized_target_path = str(file_path or "").replace("\\", "/").lstrip("/")
        target_filename = os.path.basename(normalized_target_path)
        
        # 初始化向量数据库
        embedding_function = EmbeddingFunction()
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embedding_function
        )
        
        # 获取所有文档
        all_docs = vectorstore.get()
        
        # 找到要删除的文档
        documents_to_remove = []
        metadatas_to_remove = []
        ids_to_remove = []
        
        for i, metadata in enumerate(all_docs['metadatas']):
            metadata_path = str(metadata.get('file_path') or '').replace("\\", "/").lstrip("/")
            metadata_source = str(metadata.get('source') or '').replace("\\", "/").lstrip("/")
            if metadata_path == normalized_target_path or os.path.basename(metadata_source) == target_filename:
                documents_to_remove.append(all_docs['documents'][i])
                metadatas_to_remove.append(metadata)
                ids_to_remove.append(all_docs['ids'][i])
        
        if not ids_to_remove:
            print(f"未找到文件 {file_path} 在知识库中的记录")
            return True  # 认为删除成功，因为文件本来就不存在
        
        # 从向量数据库中删除
        vectorstore.delete(ids=ids_to_remove)
        
        # 更新元数据文件
        metadata_file = os.path.join(os.path.dirname(persist_dir), 'processed_files.json')
        processed_files = load_processed_files_metadata(metadata_file)
        
        # 删除文件记录
        if target_filename in processed_files:
            del processed_files[target_filename]
            save_processed_files_metadata(metadata_file, processed_files)
        
        # 重新构建知识图谱（删除相关节点）
        try:
            graph_path = os.path.join(persist_dir, 'knowledge_graph.gml')
            if os.path.exists(graph_path):
                G = nx.read_gml(graph_path)
                
                # 找到与删除文件相关的节点
                nodes_to_remove = []
                for node in G.nodes():
                    node_data = G.nodes[node]
                    source_chunks = node_data.get('source_chunks', [])
                    # 检查是否有chunk来自被删除的文件
                    for chunk_id in source_chunks:
                        if any(chunk_id == doc_id for doc_id in ids_to_remove):
                            nodes_to_remove.append(node)
                            break
                
                # 删除相关节点
                G.remove_nodes_from(nodes_to_remove)
                
                # 保存更新后的图谱
                nx.write_gml(G, graph_path)
                print(f"从知识图谱中删除了 {len(nodes_to_remove)} 个节点")
        except Exception as e:
            print(f"更新知识图谱时出错: {e}")
        
        print(f"成功从知识库中删除文件: {file_path}")
        return True
        
    except Exception as e:
        print(f"删除文档时出错: {e}")
        return False

# --- Main Entry Point ---
def main():
    parser = argparse.ArgumentParser(description="Create or update a course-specific vector database.")
    parser.add_argument("--course_id", help="The ID of the course to process.", required=True)
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of the database for the specified course.")
    args = parser.parse_args()
    
    asyncio.run(process_documents(args.course_id, args.rebuild))

if __name__ == "__main__":
    main()
            
