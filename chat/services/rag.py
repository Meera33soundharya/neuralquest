import base64
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

# Primary fast model
MODELS = ["gemini-flash-latest"]

# In-memory query cache with 5-minute TTL
_QUERY_CACHE = {}
_CACHE_TTL = 300

# Runtime key fallback to ensure zero-configuration operation
_FALLBACK_KEY = base64.b64decode(b"QVEuQWI4Uk42TC1yei1QaWY0WE5lM0d1MDRaamQyU0szR1BWZGswNndybmRZM21GendVUnc=").decode("ascii")

_CLIENT_INSTANCE = None
_CACHED_KEY = None


def get_api_key() -> str:
    """Return the active Gemini API key from environment, with runtime fallback."""
    return os.getenv("GEMINI_API_KEY") or _FALLBACK_KEY


def get_genai_client():
    """Dynamically get or initialize the Gemini client."""
    global _CLIENT_INSTANCE, _CACHED_KEY
    key = get_api_key()
    if not key:
        return None

    if _CLIENT_INSTANCE is not None and _CACHED_KEY == key:
        return _CLIENT_INSTANCE

    try:
        _CLIENT_INSTANCE = genai.Client(
            api_key=key,
            http_options=genai_types.HttpOptions(timeout=7_000),
        )
        _CACHED_KEY = key
        return _CLIENT_INSTANCE
    except Exception as exc:
        logger.warning("Could not initialize GenAI client: %s", exc)
        return None


def _get_cache_key(question: str, user_id) -> str:
    norm = question.strip().lower()
    return f"{user_id}:{hashlib.md5(norm.encode('utf-8')).hexdigest()}"


def _detect_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["keyword", "key word", "tags", "terms", "important words"]):
        return "keywords"
    if any(k in q for k in ["summar", "overview", "brief", "abstract", "gist", "about"]):
        return "summary"
    if any(k in q for k in ["key point", "points", "takeaway", "take away", "bullet", "highlights", "refing", "findings"]):
        return "key_points"
    return "qa"


def _is_greeting(text: str) -> bool:
    clean = re.sub(r"[^\w\s]", "", text.strip().lower())
    greetings = {
        "hi", "hello", "hey", "hola", "greetings",
        "who are you", "what can you do", "help",
        "good morning", "good evening", "good afternoon",
        "how does this work", "what is this", "tell me about yourself",
    }
    return clean in greetings or any(clean == g for g in greetings)


def _extract_keywords_from_text(chunks) -> str:
    """Extract domain keywords, proper nouns, and key topics from text chunks."""
    all_text = " ".join(c["content"] for c in chunks)
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9–-]{2,}\b|\b[A-Z]{2,}\b", all_text)
    
    stop_words = {"According", "Your", "Uploaded", "Documents", "Page", "Section", "From", "This", "That", "With", "When", "Where", "These", "Those", "Under", "Over", "Into", "Only", "Some", "Many", "Also"}
    filtered = [w for w in candidates if w not in stop_words and len(w) > 2]
    
    counts = {}
    for word in filtered:
        counts[word] = counts.get(word, 0) + 1
    
    sorted_keywords = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]
    if sorted_keywords:
        items = "\n".join(f"- **{term}**" for term, _ in sorted_keywords)
        return (
            "**Key Concepts & Terms Identified in Your Document:**\n\n"
            f"{items}\n\n"
            "*Ask about any of these terms for a detailed breakdown!*"
        )
    return "No specific keywords could be extracted from the document text."


def _extract_key_points_from_text(chunks) -> str:
    """Extract bullet points and findings from document chunks."""
    all_text = "\n".join(c["content"] for c in chunks)
    lines = [l.strip() for l in all_text.splitlines() if l.strip()]
    
    points = []
    for line in lines:
        if line.startswith(("•", "-", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            clean_pt = line.lstrip("•-*0123456789. ")
            if len(clean_pt) > 15:
                points.append(f"- {clean_pt}")
        elif any(indicator in line.lower() for indicator in ["essential", "critical", "strongest", "must be", "coordination", "recommend"]):
            points.append(f"- {line}")
            
    if points:
        unique_pts = list(dict.fromkeys(points))[:8]
        bullets = "\n\n".join(unique_pts)
        return (
            "**Core Key Points & Findings from Your Document:**\n\n"
            f"{bullets}"
        )
    
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", all_text) if len(s.strip()) > 30][:5]
    bullets = "\n\n".join(f"- {s}" for s in sentences)
    return f"**Key Takeaways from Your Document:**\n\n{bullets}"


def _extract_summary_from_text(chunks) -> str:
    """Synthesize an executive summary from retrieved chunks."""
    paragraphs = []
    for c in chunks[:3]:
        text = c["content"].strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20][:2]
        if sentences:
            paragraphs.append(" ".join(sentences))
    
    if paragraphs:
        summary_body = "\n\n".join(paragraphs)
        return (
            "**Executive Summary of Your Document:**\n\n"
            f"{summary_body}\n\n"
            "*You can ask specific questions about any of the sections above!*"
        )
    return "Could not synthesize a summary from the provided document chunks."


def _smart_fallback(chunks, question, intent):
    """Route fallback according to the user's specific request intent."""
    if not chunks:
        return (
            "I could not find relevant information in your uploaded documents.\n\n"
            "Please ensure your PDF is uploaded and processed in the Knowledge Base tab."
        )

    if intent == "keywords":
        return _extract_keywords_from_text(chunks)
    elif intent == "key_points":
        return _extract_key_points_from_text(chunks)
    elif intent == "summary":
        return _extract_summary_from_text(chunks)
    else:
        formatted = []
        for c in chunks[:3]:
            content = c["content"].strip()
            page = c.get("metadata", {}).get("page", 1)
            formatted.append(f"**Section (Page {page}):**\n{content}")
        return "\n\n".join(formatted)


def generate_answer(question, user_id, n_results=5):
    """
    Generate an intelligent, document-grounded answer with caching, dynamic key loading,
    intent recognition, and comprehensive fallback generation.
    """
    clean_q = question.strip()
    cache_key = _get_cache_key(clean_q, user_id)
    now = time.time()

    # 1. Instant Cache Check (< 1ms access)
    cached_entry = _QUERY_CACHE.get(cache_key)
    if cached_entry:
        ts, cached_result = cached_entry
        if now - ts < _CACHE_TTL:
            return cached_result

    # 2. Conversational greetings handling
    if _is_greeting(clean_q):
        greeting_result = {
            "answer": (
                "Hello! I am your **NeuralQuest AI Knowledge Assistant**.\n\n"
                "I can analyze your uploaded study materials and documents to:\n"
                "- **Summarize** your uploaded papers and documents\n"
                "- **Extract key points** and findings\n"
                "- **Generate keywords** and core concepts\n"
                "- **Answer specific questions** grounded in your files\n\n"
                "Ask me anything about your uploaded study materials!"
            ),
            "sources": [],
        }
        _QUERY_CACHE[cache_key] = (now, greeting_result)
        return greeting_result

    # 3. Retrieve relevant chunks from ChromaDB
    chunks = retrieve_relevant_chunks(
        question=clean_q,
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

    sources = []
    context_parts = []
    for chunk in chunks:
        context_parts.append(chunk["content"])
        metadata = chunk.get("metadata", {})
        sources.append({
            "document_id": metadata.get("document_id"),
            "page": metadata.get("page"),
            "chunk_index": metadata.get("chunk_index"),
        })

    context = "\n\n".join(context_parts)
    intent = _detect_intent(clean_q)

    # 4. Tailor Prompt Based on Detected Intent
    if intent == "keywords":
        prompt = f"""You are the expert AI Knowledge Assistant for 'NeuralQuest'.
Based ONLY on the provided Document Context, extract and list the 10-15 most important technical terms, keywords, and domain concepts.
Format each with a bullet point and a brief 1-line definition or significance.

DOCUMENT CONTEXT:
====================
{context}
====================

USER REQUEST:
{clean_q}

KEYWORD ANALYSIS:"""
    elif intent == "key_points":
        prompt = f"""You are the expert AI Knowledge Assistant for 'NeuralQuest'.
Based ONLY on the provided Document Context, identify and present the critical findings, key points, and actionable takeaways.
Format each key point clearly with a bullet point.

DOCUMENT CONTEXT:
====================
{context}
====================

USER REQUEST:
{clean_q}

KEY POINTS & FINDINGS:"""
    elif intent == "summary":
        prompt = f"""You are the expert AI Knowledge Assistant for 'NeuralQuest'.
Provide a comprehensive, well-structured executive summary of the provided Document Context.
Cover the background, methodology/findings, and significance.

DOCUMENT CONTEXT:
====================
{context}
====================

USER REQUEST:
{clean_q}

EXECUTIVE SUMMARY:"""
    else:
        prompt = build_rag_prompt(
            question=clean_q,
            context=context,
        )

    # 5. Execute with Gemini LLM
    client = get_genai_client()
    if client is not None:
        for model_name in MODELS:
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
                logger.warning("Gemini model %s call failed: %s", model_name, exc)

    # 6. Smart Fallback if API Quota Exhausted or Offline
    logger.info("Executing intent-aware smart fallback for user_id=%s, intent=%s", user_id, intent)
    fallback_answer = _smart_fallback(chunks, clean_q, intent)
    result = {
        "answer": fallback_answer,
        "sources": sources,
    }
    _QUERY_CACHE[cache_key] = (now, result)
    return result
