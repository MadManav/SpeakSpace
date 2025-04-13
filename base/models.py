from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import random
import string
from django.utils import timezone
# ----------------------
# Custom User Model
# ----------------------
class User(AbstractUser):
    ROLE_CHOICES = (
        ('moderator', 'Moderator'),
        ('participant', 'Participant'),  # Add default role
        ('evaluator', 'Evaluator'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant')  # Added default
    phone = models.CharField(max_length=15, blank=True, null=True)  # Changed to null=True
    image = models.ImageField(
        upload_to='user_images/',  # Changed from static/
        null=True, 
        blank=True,
        default='user_images/avatar.svg'  # Changed path
    )
# ----------------------
# Topic Model (Chat Rooms)
# ----------------------
class Topic(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class ChatRoom(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')

    def __str__(self):
        return f"Chat Room - {self.topic.title}"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"
# ----------------------
# Evaluator Availability
# ----------------------
# ... existing code ...

class EvaluatorAvailability(models.Model):
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'evaluator'})
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, default=1)  # Modified line
    available_from = models.DateTimeField()
    available_to = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-available_from']

    def __str__(self):
        return f"{self.evaluator.username} | {self.topic.title} | {self.available_from.strftime('%Y-%m-%d %H:%M')} - {self.available_to.strftime('%H:%M')}"


# ... existing code ...

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
    # Add new fields below
    assignment_type = models.CharField(
        max_length=20,
        choices=[('perfect', 'Perfect Match'), ('alternative', 'Alternative Time')],
        default='perfect'
    )
    participant_approved = models.BooleanField(default=False)
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('proposed', 'Proposed'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    selector_availability = models.ForeignKey(
        'EvaluatorAvailability',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.topic.title} - {self.start_time}"

    # Keep existing methods and add:
    def save(self, *args, **kwargs):
        """Auto-generate meeting credentials for approved sessions"""
        if self.participant_approved and not self.meeting_id:
            self.generate_meeting_credentials()
        super().save(*args, **kwargs)
        # ... rest of existing Session class ...

    def generate_meeting_credentials(self):
        from .jitsi import JitsiMeetManager
        # Corrected method call
        meeting_details = JitsiMeetManager.generate_meeting_credentials(
            topic=self.topic.title,
            start_time=self.start_time,
            duration_minutes=self.duration_minutes
        )
        
        self.meeting_link = meeting_details.get('meeting_link')
        self.meeting_id = meeting_details.get('meeting_id')
        self.meeting_password = meeting_details.get('meeting_password', '')
        return meeting_details

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

# Keep only ONE InterviewRequest class - remove the duplicate at line 159
class InterviewRequest(models.Model):
    participant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'participant'},
        default=1  # Set to ID of an existing participant user
    )
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    preferred_date = models.DateTimeField(default=timezone.now)  # Add default
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.participant.username} request on {self.topic.title} [{self.status}]"  # Keep this line
    
    # ... rest of the methods ...

    
    def get_matching_evaluators(self):
        """Simplified matching logic focusing on perfect & alternative matches"""
        from django.db.models import Q
        from datetime import timedelta
        
        session_duration = timedelta(minutes=60)
        preferred_end_time = self.preferred_date + session_duration
        
        # Perfect matches (covers entire requested duration)
        exact_matches = EvaluatorAvailability.objects.filter(
            topic=self.topic,
            available_from__lte=self.preferred_date,
            available_to__gte=preferred_end_time
        ).select_related('evaluator')
        
        # Alternative matches (within 2 hours window)
        alternative_slots = EvaluatorAvailability.objects.filter(
            topic=self.topic,
            available_from__range=(
                self.preferred_date - timedelta(hours=2),
                self.preferred_date + timedelta(hours=2)
            )
        ).exclude(
            Q(available_from__lte=self.preferred_date) &
            Q(available_to__gte=preferred_end_time)
        ).order_by('available_from').select_related('evaluator')
        
        return {
            'exact_matches': exact_matches,
            'alternative_slots': alternative_slots
        }

    

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

    # ... existing fields ...
    
    def get_truncated_comment(self, length=50):
        if len(self.comments) > length:
            return self.comments[:length] + '...'
        return self.comments

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
