from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Avg, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.models import Document
from .models import (
    PlayerProfile,
    Quiz,
    QuizQuestion,
    GameSession,
    PlayerAnswer,
    Achievement,
    PlayerAchievement,
    DailyChallenge,
)
from .serializers import (
    PlayerProfileSerializer,
    QuizSerializer,
    QuizQuestionStudentSerializer,
    QuizQuestionDetailSerializer,
    GameSessionSerializer,
    AchievementSerializer,
    LeaderboardEntrySerializer,
)
from .services.generator import generate_quiz_with_ai


def get_or_create_profile(user):
    profile, _ = PlayerProfile.objects.get_or_create(user=user)
    return profile


class PlayerProfileView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        serializer = PlayerProfileSerializer(profile)
        return Response(serializer.data)


class GenerateQuizView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        document_id = request.data.get("document_id")
        topic = request.data.get("topic", "Core Concepts")
        difficulty = request.data.get("difficulty", "medium")
        game_mode = request.data.get("game_mode", "quiz_battle")
        try:
            count = int(request.data.get("count", 5))
            count = max(3, min(count, 20))
        except (ValueError, TypeError):
            count = 5

        # Verify document belongs to student
        document = get_object_or_404(Document, id=document_id, user=request.user)

        try:
            questions_data = generate_quiz_with_ai(
                document=document,
                user_id=request.user.id,
                topic=topic,
                count=count,
                difficulty=difficulty,
                game_mode=game_mode,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Create Quiz in database
        quiz = Quiz.objects.create(
            user=request.user,
            document=document,
            title=f"{document.title} — {topic.title()}",
            topic=topic,
            difficulty=difficulty,
            game_mode=game_mode,
            total_questions=len(questions_data),
        )

        # Save generated questions
        for idx, q_data in enumerate(questions_data):
            QuizQuestion.objects.create(
                quiz=quiz,
                question_text=q_data.get("question", "Question"),
                option_a=q_data.get("option_a", "Option A"),
                option_b=q_data.get("option_b", "Option B"),
                option_c=q_data.get("option_c", ""),
                option_d=q_data.get("option_d", ""),
                correct_option=q_data.get("correct_option", "A").upper().strip(),
                explanation=q_data.get("explanation", ""),
                source_page=q_data.get("page", 1),
                order=idx,
            )

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quizzes = Quiz.objects.filter(user=request.user).order_by("-created_at")[:25]
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data)


class StartGameSessionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user)
        profile = get_or_create_profile(request.user)

        session = GameSession.objects.create(
            user=request.user,
            profile=profile,
            quiz=quiz,
            total_possible=quiz.questions.count(),
        )

        return Response({
            "session_id": session.id,
            "quiz": QuizSerializer(quiz).data,
            "questions": QuizQuestionStudentSerializer(quiz.questions.all(), many=True).data
        }, status=status.HTTP_201_CREATED)


class SubmitAnswerView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(GameSession, id=session_id, user=request.user, completed=False)
        question_id = request.data.get("question_id")
        selected_option = request.data.get("selected_option", "").strip().upper()
        time_taken = float(request.data.get("time_taken", 0))

        question = get_object_or_404(QuizQuestion, id=question_id, quiz=session.quiz)

        # Check if already answered in this session
        if PlayerAnswer.objects.filter(session=session, question=question).exists():
            return Response({"error": "Question already answered in this session."}, status=status.HTTP_400_BAD_REQUEST)

        # Evaluate answer on backend
        is_correct = (selected_option == question.correct_option.strip().upper())

        # Difficulty XP base
        xp_map = {"easy": 10, "medium": 20, "hard": 30}
        base_xp = xp_map.get(session.quiz.difficulty, 20)

        # Time challenge bonus (if answered in < 5 seconds and correct)
        time_bonus = 5 if (is_correct and time_taken > 0 and time_taken < 5 and session.quiz.game_mode == "time_challenge") else 0
        awarded_xp = (base_xp + time_bonus) if is_correct else 0

        PlayerAnswer.objects.create(
            session=session,
            question=question,
            selected_option=selected_option,
            is_correct=is_correct,
            time_taken=time_taken,
        )

        if is_correct:
            session.correct_count += 1
            session.score += (10 + time_bonus)
            session.xp_earned += awarded_xp
        else:
            session.incorrect_count += 1

        session.time_taken_seconds += int(time_taken)
        session.save()

        # Return answer result with explanation & document source citations
        return Response({
            "is_correct": is_correct,
            "correct_option": question.correct_option,
            "explanation": question.explanation,
            "source_page": question.source_page,
            "document_title": session.quiz.document.title if session.quiz.document else "Document",
            "xp_awarded": awarded_xp,
            "current_score": session.score,
        })


class CompleteGameSessionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(GameSession, id=session_id, user=request.user, completed=False)
        profile = get_or_create_profile(request.user)

        session.completed = True
        session.completed_at = timezone.now()

        # Perfect quiz bonus
        perfect_bonus = 0
        if session.correct_count == session.total_possible and session.total_possible > 0:
            perfect_bonus = 50
            session.xp_earned += perfect_bonus
            session.score += 50

        session.save()

        # Update profile XP and streaks
        if session.xp_earned > 0:
            profile.add_xp(session.xp_earned, reason=f"Quiz Completion: {session.quiz.title}")
        profile.update_streak()

        return Response({
            "session_id": session.id,
            "total_questions": session.total_possible,
            "correct_count": session.correct_count,
            "incorrect_count": session.incorrect_count,
            "accuracy_percentage": round((session.correct_count / max(1, session.total_possible)) * 100, 1),
            "score": session.score,
            "xp_earned": session.xp_earned,
            "perfect_bonus": perfect_bonus,
            "total_profile_xp": profile.total_xp,
            "level": profile.level,
            "streak": profile.current_streak,
        })


class LeaderboardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get("period", "all_time")
        profiles = PlayerProfile.objects.select_related("user").order_by("-total_xp", "-level")[:50]

        leaderboard = []
        for rank, prof in enumerate(profiles, 1):
            answers = PlayerAnswer.objects.filter(session__profile=prof)
            tot = answers.count()
            acc = round((answers.filter(is_correct=True).count() / tot) * 100, 1) if tot > 0 else 0.0

            leaderboard.append({
                "rank": rank,
                "username": prof.user.username,
                "level": prof.level,
                "total_xp": prof.total_xp,
                "games_played": prof.sessions.filter(completed=True).count(),
                "accuracy_percentage": acc,
            })

        return Response(leaderboard)


class AchievementsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        profile.check_achievements()

        all_achievements = Achievement.objects.all()
        user_ach_ids = set(profile.achievements.values_list("achievement_id", flat=True))

        data = []
        for ach in all_achievements:
            unlocked = ach.id in user_ach_ids
            unlocked_at = None
            if unlocked:
                pa = PlayerAchievement.objects.filter(profile=profile, achievement=ach).first()
                unlocked_at = pa.unlocked_at if pa else None

            data.append({
                "code": ach.code,
                "title": ach.title,
                "description": ach.description,
                "icon": ach.icon,
                "xp_bonus": ach.xp_bonus,
                "unlocked": unlocked,
                "unlocked_at": unlocked_at,
            })

        return Response(data)


class LearningAnalyticsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        sessions = GameSession.objects.filter(user=request.user, completed=True)

        total_games = sessions.count()
        total_answers = PlayerAnswer.objects.filter(session__user=request.user)
        total_ans_count = total_answers.count()
        correct_ans_count = total_answers.filter(is_correct=True).count()

        overall_accuracy = round((correct_ans_count / total_ans_count) * 100, 1) if total_ans_count > 0 else 0

        # Difficulty performance
        diff_stats = {}
        for diff in ["easy", "medium", "hard"]:
            diff_ans = total_answers.filter(session__quiz__difficulty=diff)
            d_tot = diff_ans.count()
            d_cor = diff_ans.filter(is_correct=True).count()
            diff_stats[diff] = {
                "total": d_tot,
                "accuracy": round((d_cor / d_tot) * 100, 1) if d_tot > 0 else 0
            }

        # Game modes breakdown
        mode_counts = {}
        for sess in sessions:
            m = sess.quiz.game_mode
            mode_counts[m] = mode_counts.get(m, 0) + 1

        # Recent learning activity (last 7 days)
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        daily_activity = []
        for d in range(7):
            day = seven_days_ago + timedelta(days=d)
            xp_sum = profile.transactions.filter(created_at__date=day).aggregate(Sum("amount"))["amount__sum"] or 0
            daily_activity.append({
                "date": day.strftime("%b %d"),
                "xp": xp_sum,
            })

        return Response({
            "total_games": total_games,
            "overall_accuracy": overall_accuracy,
            "total_xp": profile.total_xp,
            "level": profile.level,
            "streak": profile.current_streak,
            "difficulty_stats": diff_stats,
            "mode_breakdown": mode_counts,
            "weekly_activity": daily_activity,
            "recent_sessions": GameSessionSerializer(sessions.order_by("-completed_at")[:6], many=True).data,
        })
