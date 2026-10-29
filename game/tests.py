from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document, DocumentChunk
from game.models import PlayerProfile, Quiz, QuizQuestion, GameSession, PlayerAnswer, Achievement


class NeuralQuestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testplayer", password="password123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.doc = Document.objects.create(
            user=self.user,
            title="Sample Course Material",
            status="processed"
        )
        DocumentChunk.objects.create(
            document=self.doc,
            content="Retrieval-Augmented Generation (RAG) grounds language models on private knowledge bases.",
            chunk_index=0
        )

    def test_player_profile_auto_created(self):
        response = self.client.get("/api/game/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testplayer")
        self.assertEqual(response.data["level"], 1)
        self.assertEqual(response.data["total_xp"], 0)

    def test_quiz_generation_and_play_flow(self):
        # 1. Generate Quiz
        gen_res = self.client.post("/api/game/generate/", {
            "document_id": self.doc.id,
            "topic": "RAG Concepts",
            "count": 3,
            "difficulty": "medium",
            "game_mode": "quiz_battle"
        })
        self.assertEqual(gen_res.status_code, status.HTTP_201_CREATED)
        quiz_id = gen_res.data["id"]

        # 2. Start Session
        sess_res = self.client.post(f"/api/game/session/start/{quiz_id}/")
        self.assertEqual(sess_res.status_code, status.HTTP_201_CREATED)
        session_id = sess_res.data["session_id"]
        questions = sess_res.data["questions"]
        self.assertTrue(len(questions) > 0)

        # 3. Submit Answer
        q_id = questions[0]["id"]
        ans_res = self.client.post(f"/api/game/session/{session_id}/submit/", {
            "question_id": q_id,
            "selected_option": "A",
            "time_taken": 2.5
        })
        self.assertEqual(ans_res.status_code, status.HTTP_200_OK)
        self.assertIn("is_correct", ans_res.data)
        self.assertIn("explanation", ans_res.data)
        self.assertIn("source_page", ans_res.data)

        # 4. Complete Session
        comp_res = self.client.post(f"/api/game/session/{session_id}/complete/")
        self.assertEqual(comp_res.status_code, status.HTTP_200_OK)
        self.assertIn("xp_earned", comp_res.data)

    def test_leaderboard_and_achievements(self):
        lb_res = self.client.get("/api/game/leaderboard/")
        self.assertEqual(lb_res.status_code, status.HTTP_200_OK)

        ach_res = self.client.get("/api/game/achievements/")
        self.assertEqual(ach_res.status_code, status.HTTP_200_OK)
