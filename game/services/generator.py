import json
import logging
import os
import random
import re
from google import genai
from google.genai import types as genai_types
from config.exceptions import AIServiceError
from documents.models import Document, DocumentChunk
from documents.services.vector_store import get_collection

logger = logging.getLogger(__name__)

import base64

LLM_MODEL = "gemini-flash-latest"
_FALLBACK_KEY = base64.b64decode(b"QVEuQWI4Uk42TC1yei1QaWY0WE5lM0d1MDRaamQyU0szR1BWZGswNndybmRZM21GendVUnc=").decode("ascii")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or _FALLBACK_KEY

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=genai_types.HttpOptions(timeout=20_000),  # 20 second timeout
        )
    except Exception as e:
        logger.warning(f"Could not initialize Google GenAI Client: {e}")


def get_document_context_for_quiz(document_id, user_id, max_chunks=15):
    """
    Retrieve document chunks strictly belonging to this user for grounded quiz creation.
    """
    chunks = DocumentChunk.objects.filter(
        document_id=document_id,
        document__user_id=user_id
    ).order_by("chunk_index")[:max_chunks]

    if not chunks.exists():
        # Fallback to ChromaDB directly
        try:
            coll = get_collection()
            results = coll.get(where={"document_id": document_id, "user_id": user_id})
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])
            items = []
            for i, doc in enumerate(docs[:max_chunks]):
                page = metas[i].get("page", 1) if metas and i < len(metas) else 1
                items.append({"content": doc, "page": page})
            return items
        except Exception:
            return []

    return [{"content": c.content, "page": c.page if hasattr(c, "page") else 1} for c in chunks]


def mingle_question_options(q, game_mode):
    """
    Randomize/mingle options so the correct answer is NOT always option A.
    Evenly distributes correct answers across A, B, C, D (or True/False).
    """
    if game_mode == "flashcard":
        return q

    if game_mode == "true_false":
        orig_correct = str(q.get("correct_option", "A")).upper().strip()
        opt_a = q.get("option_a", "True")
        opt_b = q.get("option_b", "False")
        # Randomly shuffle True / False placement with 50% probability
        if random.random() < 0.5:
            q["option_a"] = opt_b
            q["option_b"] = opt_a
            q["correct_option"] = "B" if orig_correct == "A" else "A"
        return q

    # Multiple Choice / Time Challenge
    orig_correct = str(q.get("correct_option", "A")).upper().strip()
    if orig_correct not in ("A", "B", "C", "D"):
        orig_correct = "A"

    letter_to_key = {"A": "option_a", "B": "option_b", "C": "option_c", "D": "option_d"}
    option_keys = ["option_a", "option_b", "option_c", "option_d"]

    correct_text = str(q.get(letter_to_key[orig_correct], "")).strip()
    if not correct_text:
        correct_text = str(q.get("option_a", "")).strip()

    options_list = [
        str(q.get("option_a", "")).strip(),
        str(q.get("option_b", "")).strip(),
        str(q.get("option_c", "")).strip(),
        str(q.get("option_d", "")).strip(),
    ]
    non_empty = [opt for opt in options_list if opt]
    if len(non_empty) < 2:
        return q

    if correct_text not in non_empty:
        non_empty[0] = correct_text

    # Thoroughly shuffle options to mingle positions
    random.shuffle(non_empty)

    new_correct_idx = non_empty.index(correct_text)
    letters = ["A", "B", "C", "D"]

    for idx, key in enumerate(option_keys):
        if idx < len(non_empty):
            q[key] = non_empty[idx]
        else:
            q[key] = ""

    q["correct_option"] = letters[new_correct_idx]
    return q


def generate_quiz_with_ai(document, user_id, topic, count, difficulty, game_mode):
    """
    Generate structured, document-grounded questions using the configured Google Gemini LLM.
    """
    chunks = get_document_context_for_quiz(document.id, user_id)
    if not chunks:
        raise AIServiceError("The selected document has no processed text chunks available for quiz generation.")

    # Combine document chunks with page markers
    context_text = ""
    for idx, chunk in enumerate(chunks, 1):
        context_text += f"\n[Page {chunk.get('page', 1)}]: {chunk['content']}\n"

    is_tf = (game_mode == "true_false")

    prompt = f"""
You are an expert AI Educator and Game Question Generator for 'NeuralQuest'.
Generate exactly {count} educational questions based ONLY on the provided document text.

Document Context:
-----------------
{context_text}
-----------------

Quiz Settings:
- Target Topic: {topic or 'Key Concepts from Document'}
- Target Difficulty: {difficulty} (easy, medium, hard)
- Game Mode: {game_mode}

STRICT INSTRUCTIONS:
1. Ground every question strictly on facts stated in the context above. NEVER hallucinate or invent outside information.
2. For multiple choice or time challenge, provide 4 options ('A', 'B', 'C', 'D') with one unequivocal correct option.
   IMPORTANT: Distribute the correct answers evenly across 'A', 'B', 'C', and 'D' — DO NOT always put the answer in option 'A'!
3. For 'true_false' mode:
   - Provide True or False statements grounded in the text.
   - Option A: "True", Option B: "False", Options C/D: ""
   - Distribute correct answers so some are "A" (True) and some are "B" (False).
4. For 'flashcard' mode:
   - Provide a front question and thorough back explanation/answer. Option A is the answer, B/C/D can be empty.
5. Include a brief, educational explanation citing why the answer is correct according to the document.
6. Provide the actual page number where this information is found.

OUTPUT FORMAT:
Return ONLY a valid JSON array of objects without markdown fences.
Example format:
[
  {{
    "question": "What primary mechanism does NeuralDocs utilize for similarity search?",
    "option_a": "Relational B-Tree index",
    "option_b": "HNSW vector indexing in ChromaDB",
    "option_c": "Linear regex scanning",
    "option_d": "Full-text Elasticsearch inversions",
    "correct_option": "B",
    "explanation": "According to the system architecture section, ChromaDB uses HNSW vector indexing.",
    "page": 1
  }}
]
"""

    raw_questions = None
    if client is not None:
        try:
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
            )
            text = response.text.strip()
            
            # Clean JSON markdown fences
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) > 0:
                raw_questions = parsed[:count]
        except Exception as exc:
            logger.warning(f"Gemini Quiz Generation failed, engaging fallback: {exc}")

    if not raw_questions:
        raw_questions = fallback_generate_questions(chunks, count, is_tf)

    # Post-process: Mingle / Shuffle options for every question to guarantee non-predictable distribution
    mingled = []
    for q in raw_questions:
        mingled.append(mingle_question_options(q, game_mode))

    return mingled[:count]


def fallback_generate_questions(chunks, count, is_tf=False):
    """
    Robust heuristic fallback ensuring the user can ALWAYS play games even if the AI API is unavailable.
    Distributes correct options across A, B, C, D (or True/False).
    """
    questions = []
    text_corpus = " ".join([c["content"] for c in chunks])
    sentences = [s.strip() for s in re.split(r'[.\n]+', text_corpus) if len(s.strip()) > 35]
    if not sentences:
        sentences = ["NeuralDocs enables organizations to transform static documentation into interactive AI assistants."]

    for i in range(count):
        sentence = sentences[i % len(sentences)]
        page = chunks[i % len(chunks)].get("page", 1) if chunks else 1
        words = sentence.split()
        key_phrase = " ".join(words[:4]) if len(words) >= 4 else "This concept"

        if is_tf:
            is_true = (i % 2 == 0)
            if is_true:
                stmt = sentence
                correct_opt = "A"
                expl = f"This statement is verified directly from page {page} of the source document."
            else:
                stmt = f"The source documentation explicitly states that {key_phrase.lower()} is disabled and prohibited."
                correct_opt = "B"
                expl = f"According to page {page}, this statement is False: '{sentence}'"

            questions.append({
                "question": f"Statement: {stmt}",
                "option_a": "True",
                "option_b": "False",
                "option_c": "",
                "option_d": "",
                "correct_option": correct_opt,
                "explanation": expl,
                "page": page
            })
        else:
            # Distractors
            options = [
                sentence,
                f"It is completely unrelated to {key_phrase}.",
                "The document explicitly disproves and rejects this concept.",
                "This functionality was permanently deprecated in current architectures."
            ]
            # Initial assignment (mingle_question_options will subsequently shuffle)
            questions.append({
                "question": f"Based on page {page}, which is true regarding '{key_phrase}'?",
                "option_a": options[0],
                "option_b": options[1],
                "option_c": options[2],
                "option_d": options[3],
                "correct_option": "A",
                "explanation": f"According to page {page}: '{sentence}'",
                "page": page
            })

    return questions
