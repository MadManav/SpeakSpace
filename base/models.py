from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import random
import string

# ----------------------
# Custom User Model
# ----------------------
class User(AbstractUser):
    ROLE_CHOICES = (
        ('moderator', 'Moderator'),
        ('participant', 'Participant'),
        ('evaluator', 'Evaluator'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    image = models.ImageField(upload_to='static/user_images/', null=True, blank=True, default='static/user_images/avatar.svg')

    def __str__(self):
        return f"{self.username} ({self.role})"

# ----------------------
# Topic Model (Chat Rooms)
# ----------------------
class Topic(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

# ----------------------
# Evaluator Availability
# ----------------------
class EvaluatorAvailability(models.Model):
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'evaluator'})
    available_from = models.DateTimeField()
    available_to = models.DateTimeField()

    def __str__(self):
        return f"{self.evaluator.username} | {self.available_from} - {self.available_to}"

# ----------------------
# Participant Interview Request
# ----------------------
class InterviewRequest(models.Model):
    participant = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'participant'})
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    preferred_date = models.DateTimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.participant.username} request on {self.topic.title} [{self.status}]"

# ----------------------
# Interview Session
# ----------------------
class Session(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    selector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluated_sessions', null=True, blank=True, limit_choices_to={'role': 'evaluator'})
    scheduled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='scheduled_sessions', limit_choices_to={'role': 'moderator'})
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    is_voice_enabled = models.BooleanField(default=False)
    meeting_link = models.URLField(max_length=500, blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.topic.title} - {self.start_time}"

    def generate_meeting_credentials(self):
        self.meeting_id = f"speakspace-{uuid.uuid4().hex[:8]}"
        password_chars = string.ascii_letters + string.digits
        self.meeting_password = ''.join(random.choice(password_chars) for _ in range(8))
        base_url = "https://meet.jit.si/"
        self.meeting_link = f"{base_url}{self.meeting_id}"
        self.save()
        return {
            'meeting_id': self.meeting_id,
            'password': self.meeting_password,
            'link': self.meeting_link
        }

    def notify_participants(self):
        meeting_info = {
            'session_id': self.id,
            'topic': self.topic.title,
            'start_time': self.start_time,
            'duration': self.duration_minutes,
            'meeting_credentials': {
                'link': self.meeting_link,
                'id': self.meeting_id,
                'password': self.meeting_password
            },
            'selector': self.selector.username if self.selector else None,
            'created_by': self.created_by.username
        }

        for participant in self.participants.all():
            participant.meeting_details = meeting_info
            participant.save()

        if self.selector:
            self.selector.evaluated_sessions.add(self)

        return meeting_info

# ----------------------
# Participants in Sessions
# ----------------------
class SessionParticipant(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    meeting_details = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('session', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.session.topic.title}"

# ----------------------
# Real-time Chat Messages
# ----------------------
class Message(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

# ----------------------
# Feedback from Evaluator
# ----------------------
class Feedback(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'evaluator'})
    participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback_received')
    rating = models.IntegerField()
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

# ----------------------
# Aggregated Performance Analytics
# ----------------------
class PerformanceAnalytics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    average_rating = models.FloatField(default=0)
    sessions_participated = models.PositiveIntegerField(default=0)
    last_feedback_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Avg Rating: {self.average_rating}"
