from django.contrib import admin
from .models import User, Topic, Session, SessionParticipant, Message, Feedback, PerformanceAnalytics

# Register User model with custom admin view
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'first_name', 'last_name', 'phone']
    list_filter = ['role']
    search_fields = ['username', 'email', 'first_name', 'last_name']

# Register Topic model
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title']
    search_fields = ['title', 'description']

# Register Session model
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['topic', 'created_by', 'start_time', 'duration_minutes', 'is_voice_enabled']
    list_filter = ['is_voice_enabled', 'start_time']
    search_fields = ['topic__title', 'created_by__username']

# Register SessionParticipant model
@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ['session', 'user', 'joined_at']
    list_filter = ['joined_at']
    search_fields = ['session__topic__title', 'user__username']

# Register Message model
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'sender', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['content', 'sender__username']

# Register Feedback model
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['session', 'evaluator', 'participant', 'rating', 'submitted_at']
    list_filter = ['rating', 'submitted_at']
    search_fields = ['comments', 'evaluator__username', 'participant__username']

# Register PerformanceAnalytics model
@admin.register(PerformanceAnalytics)
class PerformanceAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'average_rating', 'sessions_participated', 'last_feedback_date']
    list_filter = ['last_feedback_date']
    search_fields = ['user__username']