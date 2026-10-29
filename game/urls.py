from django.urls import path
from .views import (
    PlayerProfileView,
    GenerateQuizView,
    QuizListView,
    StartGameSessionView,
    SubmitAnswerView,
    CompleteGameSessionView,
    LeaderboardView,
    AchievementsView,
    LearningAnalyticsView,
)

urlpatterns = [
    path("profile/", PlayerProfileView.as_view(), name="game-profile"),
    path("generate/", GenerateQuizView.as_view(), name="game-generate"),
    path("quizzes/", QuizListView.as_view(), name="game-quizzes"),
    path("session/start/<int:quiz_id>/", StartGameSessionView.as_view(), name="game-session-start"),
    path("session/<int:session_id>/submit/", SubmitAnswerView.as_view(), name="game-session-submit"),
    path("session/<int:session_id>/complete/", CompleteGameSessionView.as_view(), name="game-session-complete"),
    path("leaderboard/", LeaderboardView.as_view(), name="game-leaderboard"),
    path("achievements/", AchievementsView.as_view(), name="game-achievements"),
    path("analytics/", LearningAnalyticsView.as_view(), name="game-analytics"),
]
