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

    def get_matching_evaluators(self):
        """
        Find evaluators available for this interview request with enhanced matching logic.
        Returns evaluators sorted by best match criteria.
        """
        from django.db.models import Q, Count, Avg, F
        from datetime import timedelta
        
        # Calculate the end time based on a standard session duration (e.g., 60 minutes)
        session_duration = timedelta(minutes=60)
        preferred_end_time = self.preferred_date + session_duration
        
        # First get exact matches (evaluators available during the whole session)
        exact_matches = EvaluatorAvailability.objects.filter(
            topic=self.topic,
            available_from__lte=self.preferred_date,
            available_to__gte=preferred_end_time
        ).select_related('evaluator')
        
        if exact_matches.exists():
            # If we have exact matches, prioritize by:
            # 1. Expertise (number of past sessions with this topic)
            # 2. Rating (average feedback score)
            # 3. Current workload (fewer assigned sessions is better)
            
            # Get evaluator IDs from the matches
            evaluator_ids = [match.evaluator.id for match in exact_matches]
            
            # Count existing sessions for these evaluators on this topic
            from .models import Session
            evaluator_experience = Session.objects.filter(
                selector_id__in=evaluator_ids,
                topic=self.topic
            ).values('selector').annotate(
                topic_sessions=Count('id')
            )
            
            # Create a dictionary for quick lookup
            experience_dict = {item['selector']: item['topic_sessions'] 
                            for item in evaluator_experience}
            
            # Get average ratings
            from .models import Feedback
            evaluator_ratings = Feedback.objects.filter(
                evaluator_id__in=evaluator_ids
            ).values('evaluator').annotate(
                avg_rating=Avg('rating')
            )
            
            # Create a dictionary for quick lookup
            ratings_dict = {item['evaluator']: item['avg_rating'] 
                        for item in evaluator_ratings}
            
            # Count current workload (upcoming sessions)
            upcoming_sessions = Session.objects.filter(
                selector_id__in=evaluator_ids,
                start_time__gte=timezone.now()
            ).values('selector').annotate(
                workload=Count('id')
            )
            
            # Create a dictionary for quick lookup
            workload_dict = {item['selector']: item['workload'] 
                            for item in upcoming_sessions}
            
            # Add scoring info to each match
            for match in exact_matches:
                evaluator_id = match.evaluator.id
                match.topic_experience = experience_dict.get(evaluator_id, 0)
                match.rating = ratings_dict.get(evaluator_id, 3.0)  # Default rating if none
                match.workload = workload_dict.get(evaluator_id, 0)
                
                # Calculate a score (higher is better)
                # Weight factors according to priority
                match.match_score = (
                    (match.topic_experience * 3) +  # Topic experience has highest weight
                    (match.rating * 2) -            # Rating has medium weight
                    (match.workload * 1)            # Lower workload is better (negative factor)
                )
            
            # Sort by the calculated score (descending)
            return sorted(exact_matches, key=lambda x: x.match_score, reverse=True)
        
        # If no exact matches, try to find partial matches
        # (available at the start time but maybe not for the whole session)
        partial_matches = EvaluatorAvailability.objects.filter(
            topic=self.topic,
            available_from__lte=self.preferred_date,
            available_to__gt=self.preferred_date  # At least some overlap
        ).select_related('evaluator')
        
        if partial_matches.exists():
            # Add an overlap duration attribute to each match
            for match in partial_matches:
                # Calculate overlap duration in minutes
                overlap_end = min(match.available_to, preferred_end_time)
                overlap_duration = (overlap_end - self.preferred_date).total_seconds() / 60
                match.overlap_minutes = int(overlap_duration)
                
                # Only include if overlap is substantial (e.g., at least 30 minutes)
                if match.overlap_minutes < 30:
                    partial_matches = partial_matches.exclude(id=match.id)
            
            return partial_matches
        
        # If still no matches, try to find alternative times from evaluators 
        # who can handle this topic
        alternative_slots = EvaluatorAvailability.objects.filter(
            topic=self.topic,
            available_from__gte=timezone.now()  # Only future slots
        ).order_by('available_from').select_related('evaluator')
        
        # Add a 'time_difference' attribute to show how far the slot is from the preferred time
        for slot in alternative_slots:
            if slot.available_from > self.preferred_date:
                # The slot is later than preferred
                time_diff = (slot.available_from - self.preferred_date).total_seconds() / 3600  # hours
                slot.time_difference = f"{time_diff:.1f} hours later"
            else:
                # The slot is earlier than preferred
                time_diff = (self.preferred_date - slot.available_from).total_seconds() / 3600  # hours
                slot.time_difference = f"{time_diff:.1f} hours earlier"
        
        return alternative_slots
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
