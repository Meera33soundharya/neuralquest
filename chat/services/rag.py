import hashlib
import logging
import os
import time

from google import genai
from google.genai import types as genai_types

from config.exceptions import AIServiceError
from .prompts import build_rag_prompt
from .retrieval import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

LLM_MODEL = "gemini-flash-latest"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Fast in-memory cache: (cache_key) -> (timestamp, response_dict)
_QUERY_CACHE = {}
_CACHE_TTL = 300  # 5 minutes TTL

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=genai_types.HttpOptions(timeout=15_000),  # 15s timeout for snappy response
        )
    except Exception as e:
        logger.warning(f"Could not initialize GenAI client: {e}")


def _get_cache_key(question: str, user_id) -> str:
    norm = question.strip().lower()
    return f"{user_id}:{hashlib.md5(norm.encode('utf-8')).hexdigest()}"


def generate_answer(question, user_id, n_results=3):
    """
    Generate a rapid grounded answer using retrieved document context with caching and fallback.
    """
    cache_key = _get_cache_key(question, user_id)
    now = time.time()
    
    # 1. Instant Cache Check (< 1ms access)
    cached_entry = _QUERY_CACHE.get(cache_key)
    if cached_entry:
        ts, cached_result = cached_entry
        if now - ts < _CACHE_TTL:
            return cached_result

    # 2. Optimized Retrieval (top 3 chunks for high relevance + low token overhead)
    chunks = retrieve_relevant_chunks(
        question=question,
        user_id=user_id,
        n_results=n_results,
    )

    if not chunks:
        return {
            "answer": "I could not find relevant information in your documents.",
            "sources": [],
        }

    context_parts = []
    sources = []

    for chunk in chunks:
        context_parts.append(chunk["content"])
        metadata = chunk["metadata"]
        sources.append({
            "document_id": metadata.get("document_id"),
            "page": metadata.get("page"),
            "chunk_index": metadata.get("chunk_index"),
        })

    context = "\n\n".join(context_parts)
    prompt = build_rag_prompt(
        question=question,
        context=context,
    )

    if client is None:
        raise AIServiceError("Gemini API key is not configured.")

    try:
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
        )
        result = {
            "answer": response.text.strip(),
            "sources": sources,
        }
        # Save to fast cache
        _QUERY_CACHE[cache_key] = (now, result)
        return result

    except Exception as exc:
        logger.warning("Gemini LLM request failed or timed out, returning grounded document context fallback: %s", exc)
        summary_sentence = context_parts[0][:300] if context_parts else "Information retrieved from document."
        fallback_result = {
            "answer": f"According to your document: \"{summary_sentence}...\"",
            "sources": sources,
        }
        return fallback_result
