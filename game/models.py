from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from documents.models import Document


class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="player_profile")
    total_xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_played_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} (Lvl {self.level} - {self.total_xp} XP)"

    def add_xp(self, xp_amount, reason="game_reward"):
        if xp_amount <= 0:
            return 0
        self.total_xp += xp_amount
        # Level progression formula: Level = 1 + floor(XP / 100)
        self.level = 1 + (self.total_xp // 100)
        self.save(update_fields=["total_xp", "level", "updated_at"])

        XPTransaction.objects.create(
            profile=self,
            amount=xp_amount,
            reason=reason
        )
        self.check_achievements()
        return self.total_xp

    def update_streak(self):
        today = timezone.now().date()
        if not self.last_played_date:
            self.current_streak = 1
        elif self.last_played_date == today:
            pass  # Already counted today
        elif (today - self.last_played_date).days == 1:
            self.current_streak += 1
        else:
            self.current_streak = 1

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_played_date = today
        self.save(update_fields=["current_streak", "longest_streak", "last_played_date", "updated_at"])
        self.check_achievements()

    def check_achievements(self):
        # Auto-unlock badges based on milestones
        badges = [
            ("first_step", "First Step", "Played your first game!", lambda: self.sessions.filter(completed=True).count() >= 1),
            ("knowledge_seeker", "Knowledge Seeker", "Completed 5 games!", lambda: self.sessions.filter(completed=True).count() >= 5),
            ("quiz_master", "Quiz Master", "Completed 20 games!", lambda: self.sessions.filter(completed=True).count() >= 20),
            ("streak_starter", "On Fire", "Achieved a 3-day learning streak!", lambda: self.current_streak >= 3),
            ("streak_legend", "Consistency King", "Achieved a 7-day learning streak!", lambda: self.current_streak >= 7),
            ("level_five", "Scholar", "Reached Level 5!", lambda: self.level >= 5),
            ("level_ten", "Grandmaster", "Reached Level 10!", lambda: self.level >= 10),
            ("centurion", "XP Century", "Earned 500+ Total XP!", lambda: self.total_xp >= 500),
        ]
        for code, title, desc, condition in badges:
            try:
                if condition():
                    ach, _ = Achievement.objects.get_or_create(code=code, defaults={"title": title, "description": desc, "icon": "🏆"})
                    PlayerAchievement.objects.get_or_create(profile=self, achievement=ach)
            except Exception:
                pass


class XPTransaction(models.Model):
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="transactions")
    amount = models.IntegerField()
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class Quiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="quizzes", null=True, blank=True)
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=150, default="General")
    difficulty = models.CharField(max_length=20, choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")], default="medium")
    game_mode = models.CharField(
        max_length=30,
        choices=[
            ("quiz_battle", "AI Quiz Battle"),
            ("time_challenge", "Time Challenge"),
            ("true_false", "True or False"),
            ("flashcard", "Flashcard Challenge"),
            ("daily_challenge", "Daily Knowledge Challenge"),
        ],
        default="quiz_battle"
    )
    total_questions = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.game_mode} - {self.difficulty})"


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    option_a = models.CharField(max_length=400)
    option_b = models.CharField(max_length=400)
    option_c = models.CharField(max_length=400, blank=True, default="")
    option_d = models.CharField(max_length=400, blank=True, default="")
    correct_option = models.CharField(max_length=5)  # 'A', 'B', 'C', 'D' or 'True'/'False'
    explanation = models.TextField(blank=True, default="")
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_context = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order + 1}: {self.question_text[:50]}"


class GameSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="game_sessions")
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="sessions")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions")
    score = models.IntegerField(default=0)
    total_possible = models.IntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    incorrect_count = models.PositiveIntegerField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session #{self.id} - {self.user.username} - Score: {self.score}"


class PlayerAnswer(models.Model):
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=10)
    is_correct = models.BooleanField(default=False)
    time_taken = models.FloatField(default=0.0)
    answered_at = models.DateTimeField(auto_now_add=True)


class Achievement(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default="🏆")
    xp_bonus = models.PositiveIntegerField(default=50)

    def __str__(self):
        return self.title


class PlayerAchievement(models.Model):
    profile = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "achievement")


class DailyChallenge(models.Model):
    date = models.DateField(unique=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="daily_challenges")
    bonus_xp = models.PositiveIntegerField(default=25)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Daily Challenge for {self.date}"
