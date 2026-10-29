from rest_framework import serializers
from .models import (
    PlayerProfile,
    Quiz,
    QuizQuestion,
    GameSession,
    PlayerAnswer,
    Achievement,
    DailyChallenge,
)
from documents.serializers import DocumentSerializer


class PlayerProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    games_played = serializers.SerializerMethodField()
    accuracy_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PlayerProfile
        fields = [
            "id",
            "username",
            "email",
            "total_xp",
            "level",
            "current_streak",
            "longest_streak",
            "last_played_date",
            "games_played",
            "accuracy_percentage",
        ]

    def get_games_played(self, obj):
        return obj.sessions.filter(completed=True).count()

    def get_accuracy_percentage(self, obj):
        answers = PlayerAnswer.objects.filter(session__profile=obj)
        total = answers.count()
        if total == 0:
            return 0
        correct = answers.filter(is_correct=True).count()
        return round((correct / total) * 100, 1)


class QuizQuestionStudentSerializer(serializers.ModelSerializer):
    """Question serializer sent to the student DURING the quiz (HIDES correct_option and explanation)"""
    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "source_page",
            "order",
        ]


class QuizQuestionDetailSerializer(serializers.ModelSerializer):
    """Full question details shown AFTER question submission for explanation & source citations"""
    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "explanation",
            "source_page",
            "order",
        ]


class QuizSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True, default="Document")
    questions = QuizQuestionStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "topic",
            "difficulty",
            "game_mode",
            "total_questions",
            "document",
            "document_title",
            "questions",
            "created_at",
        ]


class GameSessionSerializer(serializers.ModelSerializer):
    quiz = QuizSerializer(read_only=True)

    class Meta:
        model = GameSession
        fields = [
            "id",
            "quiz",
            "score",
            "total_possible",
            "correct_count",
            "incorrect_count",
            "xp_earned",
            "time_taken_seconds",
            "completed",
            "created_at",
            "completed_at",
        ]


class AchievementSerializer(serializers.ModelSerializer):
    unlocked = serializers.BooleanField(default=False)
    unlocked_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = Achievement
        fields = ["code", "title", "description", "icon", "xp_bonus", "unlocked", "unlocked_at"]


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    username = serializers.CharField()
    level = serializers.IntegerField()
    total_xp = serializers.IntegerField()
    games_played = serializers.IntegerField()
    accuracy_percentage = serializers.FloatField()
