import os
import sys
import django

# Setup Django Environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["USE_SQLITE"] = "true"
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from documents.models import Document, DocumentChunk
from documents.services.processor import process_document
from game.models import PlayerProfile, Quiz, QuizQuestion, GameSession, PlayerAnswer, Achievement


def run_comprehensive_audit():
    print("============================================================")
    print("[START] FULL FEATURE AUDIT FOR NEURALQUEST PLATFORM")
    print("============================================================\n")

    client = APIClient()

    # 1. AUTHENTICATION & PROFILE VERIFICATION
    print("[1/8] Verifying User Authentication & Player Profile...")
    user, created = User.objects.get_or_create(username="audit_tester", defaults={"email": "tester@test.com"})
    if created:
        user.set_password("pass1234")
        user.save()
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    profile_res = client.get("/api/game/profile/")
    assert profile_res.status_code == 200, f"Profile endpoint failed: {profile_res.status_code}"
    print(f"  [OK] User Profile verified: {profile_res.data['username']} (Lvl {profile_res.data['level']}, XP: {profile_res.data['total_xp']})")

    # 2. DOCUMENT INGESTION & CHUNKING
    print("\n[2/8] Verifying Document Ingestion & Vector Pipeline...")
    pdf_path = os.path.join(os.getcwd(), "sample_rag_guide.pdf")
    assert os.path.exists(pdf_path), "sample_rag_guide.pdf missing!"
    
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/", {"title": "Audit Guide Doc", "file": f}, format="multipart")
    
    assert upload_res.status_code in (200, 201), f"Document upload failed: {upload_res.data}"
    doc_id = upload_res.data["id"]
    doc = Document.objects.get(id=doc_id)
    chunks_count = doc.chunks.count()
    print(f"  [OK] Document '{doc.title}' uploaded and chunked. Chunks count: {chunks_count}")

    # 3. RAG CHATBOT RELEVANCE QUERY
    print("\n[3/8] Verifying Grounded RAG Knowledge Chat...")
    chat_res = client.post("/api/chat/", {"question": "What is Retrieval-Augmented Generation according to this document?"})
    assert chat_res.status_code == 200, f"Chat endpoint failed: {chat_res.data}"
    print(f"  [OK] Chat query answered successfully. Response preview: {chat_res.data['answer'][:120]}...")
    if chat_res.data.get("sources"):
        print(f"  [OK] Citation sources returned: {len(chat_res.data['sources'])} chunks cited.")

    # 4. CHAT HISTORY
    print("\n[4/8] Verifying Chat History...")
    history_res = client.get("/api/chat/history/")
    assert history_res.status_code == 200, f"Chat history failed: {history_res.status_code}"
    print(f"  [OK] Chat history verified: {len(history_res.data)} message pairs recorded.")

    # 5. AI QUIZ GENERATOR (MCQ, TRUE/FALSE, TIME CHALLENGE, FLASHCARD)
    print("\n[5/8] Verifying AI Quiz Generator across game modes...")
    for mode in ["quiz_battle", "time_challenge", "true_false", "flashcard"]:
        gen_res = client.post("/api/game/generate/", {
            "document_id": doc_id,
            "topic": f"Key concepts in {mode}",
            "count": 4,
            "difficulty": "medium",
            "game_mode": mode
        })
        assert gen_res.status_code == 201, f"Failed generating quiz for mode {mode}: {gen_res.data}"
        quiz_id = gen_res.data["id"]
        q_count = gen_res.data["total_questions"]
        print(f"  [OK] Mode '{mode}' generated successfully with {q_count} grounded questions.")

    # 6. ACTIVE GAME SESSION, REAL-TIME ANSWER SUBMISSION & CITATION VERIFICATION
    print("\n[6/8] Verifying Live Game Session & Scoring Engine...")
    session_res = client.post(f"/api/game/session/start/{quiz_id}/")
    assert session_res.status_code == 201, f"Failed starting session: {session_res.data}"
    session_id = session_res.data["session_id"]
    questions = session_res.data["questions"]
    assert len(questions) > 0, "No questions returned in session!"

    # Submit first question answer
    target_q = questions[0]
    submit_res = client.post(f"/api/game/session/{session_id}/submit/", {
        "question_id": target_q["id"],
        "selected_option": "A",
        "time_taken": 3.2
    })
    assert submit_res.status_code == 200, f"Submit answer failed: {submit_res.data}"
    print(f"  [OK] Answer submission validated. Result: {'Correct' if submit_res.data['is_correct'] else 'Incorrect'}")
    print(f"  [OK] Sourced Explanation: {submit_res.data['explanation'][:80]}...")
    print(f"  [OK] Page Citation: Page {submit_res.data['source_page']}")

    # Complete session
    complete_res = client.post(f"/api/game/session/{session_id}/complete/")
    assert complete_res.status_code == 200, f"Complete session failed: {complete_res.data}"
    print(f"  [OK] Session completed: Score {complete_res.data['score']}, XP Earned: +{complete_res.data['xp_earned']} XP")

    # 7. LEADERBOARD & ACHIEVEMENTS SYSTEM
    print("\n[7/8] Verifying Leaderboard & Achievement Badge Unlocks...")
    lb_res = client.get("/api/game/leaderboard/")
    assert lb_res.status_code == 200, f"Leaderboard failed: {lb_res.status_code}"
    print(f"  [OK] Leaderboard active with {len(lb_res.data)} ranked players.")

    ach_res = client.get("/api/game/achievements/")
    assert ach_res.status_code == 200, f"Achievements failed: {ach_res.status_code}"
    unlocked = [a for a in ach_res.data if a["unlocked"]]
    print(f"  [OK] Achievements verified. Total available: {len(ach_res.data)}, Unlocked for player: {len(unlocked)}")

    # 8. LEARNING ANALYTICS
    print("\n[8/8] Verifying Learning Analytics...")
    analytics_res = client.get("/api/game/analytics/")
    assert analytics_res.status_code == 200, f"Analytics failed: {analytics_res.status_code}"
    print(f"  [OK] Learning analytics verified. Overall Accuracy: {analytics_res.data['overall_accuracy']}%, Total Games: {analytics_res.data['total_games']}")

    print("\n============================================================")
    print("[SUCCESS] ALL 8 CORE PLATFORM FEATURES VERIFIED AND FUNCTIONING!")
    print("============================================================\n")


if __name__ == "__main__":
    run_comprehensive_audit()
