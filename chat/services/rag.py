import hashlib
import logging
import os
import re
import time

from google import genai
from google.genai import types as genai_types

from config.exceptions import AIServiceError
from .prompts import build_rag_prompt
from .retrieval import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

# Primary and fallback model identifiers
PRIMARY_MODEL = "gemini-flash-latest"
FALLBACK_MODEL = "gemini-1.5-flash"

# In-memory query cache with 5-minute TTL
_QUERY_CACHE = {}
_CACHE_TTL = 300

# Cached client instance
_CLIENT_INSTANCE = None
_CACHED_KEY = None


def get_genai_client():
    """
    Dynamically initialize or refresh the Gemini client whenever
    the GEMINI_API_KEY environment variable is present or changes.
    """
    global _CLIENT_INSTANCE, _CACHED_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    if _CLIENT_INSTANCE is not None and _CACHED_KEY == api_key:
        return _CLIENT_INSTANCE

    try:
        _CLIENT_INSTANCE = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(timeout=20_000),
        )
        _CACHED_KEY = api_key
        return _CLIENT_INSTANCE
    except Exception as exc:
        logger.warning("Could not initialize GenAI client: %s", exc)
        return None


def _get_cache_key(question: str, user_id) -> str:
    norm = question.strip().lower()
    return f"{user_id}:{hashlib.md5(norm.encode('utf-8')).hexdigest()}"


def _is_greeting_or_meta(text: str) -> bool:
    clean = re.sub(r"[^\w\s]", "", text.strip().lower())
    greetings = {
        "hi", "hello", "hey", "hola", "greetings",
        "who are you", "what can you do", "help",
        "good morning", "good evening", "good afternoon",
        "how does this work", "what is this", "tell me about yourself",
    }
    return clean in greetings or any(clean == g for g in greetings)


def _format_smart_fallback(chunks, question):
    """
    Generate an intelligent, well-structured answer from retrieved document chunks
    when the generative LLM is temporarily unavailable or rate-limited.
    """
    if not chunks:
        return "I could not find relevant information in your uploaded documents. Please ensure your PDF is uploaded and processed in the Knowledge Base."

    formatted_sections = []
    for idx, c in enumerate(chunks[:3], 1):
        content = c["content"].strip()
        page = c.get("metadata", {}).get("page", 1)
        doc_name = c.get("metadata", {}).get("source", "Document")
        formatted_sections.append(f"**From {doc_name} (Page {page}):**\n{content}")

    body = "\n\n".join(formatted_sections)
    return (
        f"Based on your uploaded documents, here is the relevant information regarding **\"{question}\"**:\n\n"
        f"{body}"
    )


def generate_answer(question, user_id, n_results=5):
    """
    Generate an intelligent, document-grounded answer with caching, dynamic client loading,
    and conversational fallback.
    """
    cache_key = _get_cache_key(question, user_id)
    now = time.time()

    # 1. Instant Cache Check (< 1ms access)
    cached_entry = _QUERY_CACHE.get(cache_key)
    if cached_entry:
        ts, cached_result = cached_entry
        if now - ts < _CACHE_TTL:
            return cached_result

    # 2. Conversational greetings handling
    if _is_greeting_or_meta(question):
        greeting_result = {
            "answer": (
                "👋 Hello! I am your **NeuralQuest AI Knowledge Assistant**.\n\n"
                "I can analyze your uploaded study materials and documents to:\n"
                "- Answer detailed questions about any topic in your files\n"
                "- Summarize key concepts and architectural breakdowns\n"
                "- Help you prepare for interactive quizzes and quests\n\n"
                "💡 *Tip: Upload your PDF in the Knowledge Base tab, then ask me anything about it!*"
            ),
            "sources": [],
        }
        _QUERY_CACHE[cache_key] = (now, greeting_result)
        return greeting_result

    # 3. Retrieve relevant chunks (up to 5 for comprehensive coverage)
    chunks = retrieve_relevant_chunks(
        question=question,
        user_id=user_id,
        n_results=n_results,
    )

    if not chunks:
        return {
            "answer": (
                "I couldn't find information matching your question in your uploaded documents.\n\n"
                "Please make sure your study PDF is uploaded in the **Knowledge Base**, or try rephrasing your query."
            ),
            "sources": [],
        }

    context_parts = []
    sources = []

    for chunk in chunks:
        context_parts.append(chunk["content"])
        metadata = chunk.get("metadata", {})
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

    # 4. Check / initialize Gemini client dynamically
    client = get_genai_client()

    if client is not None:
        # Try primary model, fallback to secondary if needed
        for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    result = {
                        "answer": response.text.strip(),
                        "sources": sources,
                    }
                    _QUERY_CACHE[cache_key] = (now, result)
                    return result
            except Exception as exc:
                logger.warning("Gemini model %s failed: %s", model_name, exc)

    # 5. Smart Structured Fallback
    logger.info("Engaging structured document synthesis fallback for user_id=%s", user_id)
    fallback_text = _format_smart_fallback(chunks, question)
    fallback_result = {
        "answer": fallback_text,
        "sources": sources,
    }
    _QUERY_CACHE[cache_key] = (now, fallback_result)
    return fallback_result
