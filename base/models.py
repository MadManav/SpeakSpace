from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('moderator', 'Moderator'),
        ('participant', 'Participant'),
        ('evaluator', 'Evaluator'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)

    # The following fields are already included in AbstractUser:
    # - first_name
    # - last_name
    # - username
    # - password
    # - email

    def __str__(self):
        return f"{self.username} ({self.role})"

# Topics for discussion
class Topic(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.title

# Session Model
class Session(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    is_voice_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.topic.title} - {self.start_time}"

# Session Participants
class SessionParticipant(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'user')
    
# Real-time Messages (Text chat log)
class Message(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

# Feedback from Evaluator or Moderator
class Feedback(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'evaluator'})
    participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback_received')
    rating = models.IntegerField()
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

# Analytics model (if you want to store processed summary)
class PerformanceAnalytics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    average_rating = models.FloatField(default=0)
    sessions_participated = models.PositiveIntegerField(default=0)
    last_feedback_date = models.DateTimeField(null=True, blank=True)

    