from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Session, Topic, SessionParticipant, InterviewRequest, EvaluatorAvailability, ChatRoom, ChatMessage,Feedback
from django.utils import timezone
from django.db.models import Avg
from django.http import JsonResponse
from datetime import datetime
from .jitsi import JitsiMeetManager
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods  # Add this import
from django.shortcuts import render, redirect, get_object_or_404  # Add get_object_or_404
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db import models


def loginPage(request):
    # if request.user.is_authenticated:
    #     return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            print(f"DEBUG: User {user.username} logged in with role: {user.role}")  # Add debug line
            if user.role == 'moderator':
                print(f"DEBUG: Redirecting moderator to moderator view")  # Add debug line
                return redirect('moderator')
            elif user.role == 'evaluator':
                return redirect('evaluation-dashboard')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'base/login.html')

def registerPage(request):
    if request.method == 'POST':
        try:
            first_name = request.POST.get('firstName')
            last_name = request.POST.get('lastName')
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('userRole')

            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            
            login(request, user)
            # Redirect based on user role
            if user.role == 'moderator':
                return redirect('moderator')
            elif user.role == 'evaluator':
                return redirect('evaluation-dashboard')
            return redirect('home')
            
        except IntegrityError as e:
            messages.error(request, 'Username or email already exists')
        except ValidationError as e:
            messages.error(request, '\n'.join(e.messages))
        except Exception as e:
            messages.error(request, f'Registration error: {str(e)}')
            
    return render(request, 'base/register.html')
    
def logoutUser(request):
    logout(request)
    return redirect('login')

def landingPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'base/landingpage.html')

@login_required(login_url='login')
def homePage(request):
    topics = Topic.objects.all()
    
    # Get all session proposals that need user action
    proposed_sessions = Session.objects.filter(
        status='proposed',
        participants__user=request.user
    ).select_related('topic', 'selector')
    
    # Get confirmed sessions (both explicitly confirmed and perfect assignments)
    confirmed_sessions = Session.objects.filter(
        participants__user=request.user
    ).filter(
        # Either confirmed status OR perfect match type with scheduled status
        models.Q(status='confirmed') | 
        models.Q(status='scheduled', assignment_type='perfect')
    ).select_related('topic', 'selector')
    
    # Get other scheduled upcoming sessions that aren't perfect matches
    upcoming_sessions = Session.objects.filter(
        status='scheduled',
        assignment_type='alternative',  # Only alternative assignments
        participants__user=request.user,
        start_time__gte=timezone.now()
    ).order_by('start_time').select_related('topic', 'selector')
    
    # Get user's chat rooms for joined status
    user_chat_rooms = ChatRoom.objects.filter(participants=request.user)
    joined_topic_ids = user_chat_rooms.values_list('topic_id', flat=True)
    
    context = {
        'topics': topics,
        'proposed_sessions': proposed_sessions,
        'confirmed_sessions': confirmed_sessions,
        'upcoming_sessions': upcoming_sessions,
        'user': request.user,
        'joined_topic_ids': joined_topic_ids,
        'current_time': timezone.now(),
    }
    return render(request, 'base/home.html', context)


@login_required(login_url='login')
def analyticsPage(request):
    # Get all topics for the user
    user_topics = Topic.objects.filter(
        session__participants__user=request.user
    ).distinct()
    
    # Get selected topic or first one
    selected_topic_id = request.GET.get('topic')
    selected_topic = get_object_or_404(Topic, id=selected_topic_id) if selected_topic_id else user_topics.first()
    
    if not selected_topic:
        context = {
            'user_topics': [],
            'selected_topic': None,
            'average_rating': 0,
            'total_sessions': 0,
            'latest_feedback': [],
            'topic_averages': json.dumps({'labels': [], 'data': []}),
            'user': request.user
        }
        return render(request, 'base/analytics.html', context)

    # Get total sessions (including those without feedback)
    total_sessions = SessionParticipant.objects.filter(
        user=request.user,
        session__topic=selected_topic
    ).count()

    # Get all feedback for the user
    feedback_list = Feedback.objects.filter(
        participant=request.user,
        session__topic=selected_topic
    ).select_related('session').order_by('-submitted_at')

    # Calculate average rating
    average_rating = feedback_list.aggregate(Avg('rating'))['rating__avg'] or 0

    # Get latest feedback
    latest_feedback = feedback_list[:2]

    # Prepare topic averages for chart
    topic_averages = []
    for topic in user_topics:
        topic_feedback = Feedback.objects.filter(
            participant=request.user,
            session__topic=topic
        ).aggregate(avg_rating=Avg('rating'))
        
        topic_averages.append({
            'title': topic.title,
            'avg_rating': topic_feedback['avg_rating'] or 0
        })

    context = {
        'user_topics': user_topics,
        'selected_topic': selected_topic,
        'average_rating': round(average_rating, 1),
        'total_sessions': total_sessions,
        'latest_feedback': latest_feedback,
        'topic_averages': json.dumps({
            'labels': [t['title'] for t in topic_averages],
            'data': [t['avg_rating'] for t in topic_averages]
        }),
        'user': request.user
    }
    
    return render(request, 'base/analytics.html', context)

@login_required(login_url='login')
def applySession(request):
    if request.method == 'POST':
        topic_id = request.POST.get('topic_id')
        preferred_date = request.POST.get('preferred_date')
        
        if topic_id and preferred_date:
            InterviewRequest.objects.create(
                participant=request.user,
                topic_id=topic_id,
                preferred_date=preferred_date,
                status='pending'
            )
            return redirect('apply-sessions')
    
    # Get all topics and annotate with interview request status
    topics = Topic.objects.all()
    for topic in topics:
        try:
            interview_request = InterviewRequest.objects.filter(
                participant=request.user,
                topic=topic
            ).latest('created_at')
            topic.interview_status = interview_request.status
        except InterviewRequest.DoesNotExist:
            topic.interview_status = None
    
    context = {
        'user': request.user,
        'topics': topics
    }
    return render(request, 'base/apply_sessions.html', context)


# ... existing code ...

def moderator_view(request):
    # Get available evaluators with future availability slots
    available_evaluators = EvaluatorAvailability.objects.filter(
        available_from__gte=timezone.now(),
        topic__isnull=False
    ).select_related('evaluator', 'topic').order_by('available_from')
    
    # Create a list of evaluators with their details
    evaluator_data = []
    for availability in available_evaluators:
        evaluator_data.append({
            'id': availability.evaluator.id,
            'full_name': availability.evaluator.get_full_name(),
            'username': availability.evaluator.username,
            'topics': [availability.topic.title],
            'availability_slots': [f"{availability.available_from}|{availability.available_to}"]
        })

    context = {
        'available_evaluators': evaluator_data,
        'interview_requests': InterviewRequest.objects.filter(status='pending')  # Changed status -> request_status
    }
    return render(request, 'base/moderator.html', context)


@login_required(login_url='login')
def update_user_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # Delete old image if it exists and is not the default avatar
            if request.user.image and 'avatar.svg' not in request.user.image.path:
                request.user.image.delete()
            
            request.user.image = request.FILES['image']
            request.user.save()
            
            return JsonResponse({
                'success': True,
                'image_url': request.user.image.url
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    return JsonResponse({'success': False, 'error': 'No image provided'})

def application_page(request):
    return render(request, 'base/applications.html')

def history_page(request):
    return render(request, 'base/history.html')

def evaluation_page(request):
    return render(request, 'base/evaluation.html')

@login_required
def evaluation_dashboard(request):
    if request.user.role != 'evaluator':
        return redirect('home')
    
    # Get upcoming sessions where the current user is the evaluator (selector)
    upcoming_sessions = Session.objects.filter(
        selector=request.user,
        start_time__gte=timezone.now()
    ).select_related('topic').order_by('start_time')
    
    context = {
        'upcoming_sessions': upcoming_sessions,
        'current_time': timezone.now(),
    }
    return render(request, 'base/EvaluatorDashboard.html', context)


@require_http_methods(["POST"])
def add_availability(request):
    data = json.loads(request.body)
    
    # Convert string dates to datetime objects
    available_from = datetime.fromisoformat(data['available_from'])
    available_to = datetime.fromisoformat(data['available_to'])
    
    # Get topic by title or create it if it doesn't exist
    try:
        # First try to get by title
        topic = Topic.objects.get(title__iexact=data['topic'])
    except Topic.DoesNotExist:
        try:
            # If not found by title, try by ID (in case a numeric ID was passed)
            topic_id = int(data['topic'])
            topic = Topic.objects.get(id=topic_id)
        except (ValueError, Topic.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': f"Topic '{data['topic']}' not found"
            }, status=404)
    
    # Create availability
    availability = EvaluatorAvailability.objects.create(
        evaluator=request.user,
        topic=topic,
        available_from=available_from,
        available_to=available_to
    )
    
    return JsonResponse({
        'id': availability.id,
        'topic': topic.title,
        'formatted_date': available_from.strftime('%A, %b %d, %Y'),
        'formatted_start_time': available_from.strftime('%I:%M %p'),
        'formatted_end_time': available_to.strftime('%I:%M %p')
    })

@require_http_methods(["DELETE"])
def delete_availability(request, availability_id):
    availability = get_object_or_404(EvaluatorAvailability, id=availability_id, evaluator=request.user)
    availability.delete()
    return JsonResponse({'status': 'success'})

def get_availability(request):
    availabilities = EvaluatorAvailability.objects.filter(evaluator=request.user)
    data = {
        'availabilities': [{
            'id': av.id,
            'topic': av.topic.title,
            'formatted_date': av.available_from.strftime('%A, %b %d, %Y'),
            'formatted_start_time': av.available_from.strftime('%I:%M %p'),
            'formatted_end_time': av.available_to.strftime('%I:%M %p')
        } for av in availabilities]
    }
    return JsonResponse(data)

# ... other view functions ...

@login_required
def available_timings(request):
    if request.user.role != 'evaluator':
        return redirect('home')
    
    # Get all topics for the dropdown
    topics = Topic.objects.all()
    
    # Get existing availabilities for this evaluator
    availabilities = EvaluatorAvailability.objects.filter(
        evaluator=request.user
    ).order_by('available_from')
    
    context = {
        'topics': topics,
        'availabilities': availabilities,
    }
    return render(request, 'base/available-timing.html', context)


@login_required(login_url='login')
def chat_room(request):
    topic_id = request.GET.get('topic')
    
    try:
        topic = Topic.objects.get(id=topic_id)
    except Topic.DoesNotExist:
        messages.error(request, "Topic not found")
        return redirect('home')
    
    # Get or create chat room for this topic
    chat_room, created = ChatRoom.objects.get_or_create(topic=topic)
    
    # Add current user to participants
    chat_room.participants.add(request.user)
    
    # Get all participants and messages in this chat room
    participants = chat_room.participants.all()
    chat_messages = ChatMessage.objects.filter(room=chat_room).order_by('timestamp')
    
    context = {
        'room_id': chat_room.id,  # Added room_id for WebSocket
        'topic': topic,
        'participants': participants,
        'chat_room': chat_room,
        'current_user': request.user,
        'messages': chat_messages
    }
    return render(request, 'base/chat.html', context)


@login_required
def send_message(request):
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        message_content = request.POST.get('message')
        
        if room_id and message_content:
            chat_room = ChatRoom.objects.get(id=room_id)
            message = ChatMessage.objects.create(
                room=chat_room,
                user=request.user,
                content=message_content
            )
            
            return JsonResponse({
                'status': 'success',
                'message': {
                    'content': message.content,
                    'user': message.user.username,
                    'timestamp': message.timestamp.strftime('%I:%M %p'),
                }
            })
    return JsonResponse({'status': 'error'}, status=400)

# class CreateSessionView(TemplateView):
#     template_name = 'base/session_assignment.html'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
        
#         # Get pending interview requests with participant details
#         requests = InterviewRequest.objects.filter(status='pending').select_related(
#             'participant', 'topic'
#         )
#         context['participants'] = requests
        
#         # Get available evaluators matching first request's criteria
#         if requests.exists():
#             request = requests.first()
#             evaluators = User.objects.filter(
#                 role='evaluator',
#                 evaluatoravailability__topic=request.topic,
#                 evaluatoravailability__available_from__lte=request.preferred_date,
#                 evaluatoravailability__available_to__gte=request.preferred_date
#             ).prefetch_related(
#                 'evaluatoravailability_set',
#                 'evaluatoravailability__topic'
#             ).distinct()
            
#             context['evaluators'] = evaluators
            
#         return context

# @require_POST
# def assign_evaluator(request):
#     try:
#         evaluator = User.objects.get(id=request.POST.get('evaluator_id'), role='evaluator')
#         interview_request = InterviewRequest.objects.get(
#             id=request.POST.get('participant_id'),
#             status='pending'
#         )
        
#         # Create session
#         session = Session.objects.create(
#             topic=interview_request.topic,
#             created_by=request.user,
#             selector=evaluator,
#             start_time=request.POST.get('start_time'),
#             duration_minutes=(timezone.datetime.fromisoformat(request.POST.get('end_time')) - 
#                             timezone.datetime.fromisoformat(request.POST.get('start_time'))).seconds // 60,
#             scheduled_by=request.user
#         )
        
#         # Generate meeting credentials
#         meeting_details = session.generate_meeting_credentials()
        
#         # Update interview request status
#         interview_request.status = 'approved'
#         interview_request.save()
        
#         # Notify participants
#         session.notify_participants()
        
#         return JsonResponse({
#             'status': 'success',
#             'meeting_link': meeting_details['link'],
#             'meeting_id': meeting_details['meeting_id']
#         })
        
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
@login_required(login_url='login')
def session_assignment(request, request_id):
    interview_request = get_object_or_404(InterviewRequest, id=request_id)
    evaluators = interview_request.get_matching_evaluators()
    
    exact_matches = evaluators.get('exact_matches', [])
    alternative_slots = evaluators.get('alternative_slots', [])

    if request.method == 'POST':
        evaluator_id = request.POST.get('evaluator')
        selected_time = request.POST.get('session_time', None)

        evaluator_availability = get_object_or_404(EvaluatorAvailability, id=evaluator_id)
        
        if evaluator_availability in exact_matches:
            match_type = 'perfect'
        else:
            match_type = 'alternative'

        session = Session.objects.create(
            topic=interview_request.topic,
            created_by=request.user,
            selector=evaluator_availability.evaluator,
            start_time=datetime.fromisoformat(selected_time) if selected_time else interview_request.preferred_date,
            duration_minutes=60,
            scheduled_by=request.user,
            assignment_type=match_type,
            status='proposed' if match_type == 'alternative' else 'scheduled',
            selector_availability=evaluator_availability
        )

        SessionParticipant.objects.create(
            session=session,
            user=interview_request.participant
        )

        if match_type == 'perfect':
            session.generate_meeting_credentials()
            session.save()
            interview_request.status = 'approved'
            msg = f"Session scheduled with {evaluator_availability.evaluator.get_full_name()}"
        else:
            session.save()  # No meeting link generated here
            interview_request.status = 'pending_confirmation'
            msg = f"Time proposal sent to participant"

        messages.success(request, f"{msg}")
        interview_request.save()
        return redirect('moderator')

    return render(request, 'base/session_assignment.html', {
        'interview_request': interview_request,
        'exact_matches': exact_matches,
        'alternative_slots': alternative_slots,
    })

def test_jitsi(request):
    """A simple view to test Jitsi integration"""
    return render(request, 'base/test_jitsi.html')


# In views.py
def assign_session(request, request_id):
    interview_request = get_object_or_404(InterviewRequest, id=request_id)
    
    if request.method == 'POST':
        evaluator_id = request.POST.get('evaluator')
        evaluator_availability = get_object_or_404(EvaluatorAvailability, id=evaluator_id)
        
        # Create session
        session = Session.objects.create(
            topic=interview_request.topic,
            created_by=request.user,
            selector=evaluator_availability.evaluator,
            scheduled_by=request.user,
            start_time=evaluator_availability.available_from,
            duration_minutes=60,
            assignment_type='perfect' if evaluator_availability.available_to >= interview_request.preferred_date + timedelta(minutes=60) else 'alternative'
        )
        
        if session.assignment_type == 'perfect':
            session.generate_meeting_credentials()
            session.participants.add(interview_request.participant)
            messages.success(request, 'Session created successfully!')
        else:
            messages.success(request, 'Session proposal sent to participant')
        
        interview_request.status = 'approved'
        interview_request.save()
        
        return redirect('moderator')

# In views.py
def accept_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        session.participant_approved = True
        session.generate_meeting_credentials()
        session.participants.add(request.user)
        session.save()
        messages.success(request, 'Session confirmed!')
        return redirect('home')

@login_required(login_url='login')
def confirm_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    
    # Verify the user is a participant of this session
    if not SessionParticipant.objects.filter(session=session, user=request.user).exists():
        messages.error(request, "You are not a participant in this session.")
        return redirect('home')
    
    if request.method == 'POST':
        session.status = 'confirmed'
        session.participant_approved = True
        
        # Generate meeting details if not already generated
        if not session.meeting_link:
            session.generate_meeting_credentials()
            
        session.save()
        messages.success(request, 'Session confirmed successfully!')
    
    return redirect('home')

@login_required(login_url='login')
def decline_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    
    # Verify the user is a participant of this session
    if not SessionParticipant.objects.filter(session=session, user=request.user).exists():
        messages.error(request, "You are not a participant in this session.")
        return redirect('home')
    
    if request.method == 'POST':
        session.status = 'declined'
        session.save()
        messages.info(request, 'Session declined')
    
    return redirect('home')

@csrf_exempt
@login_required
def submit_feedback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            rating = data.get('rating')
            comments = data.get('comments', '')
            
            session = get_object_or_404(Session, id=session_id)
            
            # Check if the current user is the evaluator for this session
            if request.user != session.selector:
                return JsonResponse({
                    'success': False,
                    'error': 'You are not authorized to provide feedback for this session.'
                }, status=403)
            
            # Get the participant
            participant = SessionParticipant.objects.filter(session=session).first()
            if not participant:
                return JsonResponse({
                    'success': False,
                    'error': 'No participant found for this session.'
                }, status=404)
            
            # Create or update feedback
            feedback, created = Feedback.objects.update_or_create(
                session=session,
                evaluator=request.user,
                participant=participant.user,
                defaults={
                    'rating': rating,
                    'comments': comments
                }
            )
            
            # Update session status
            session.status = 'completed'
            session.save()
            
            # Update participant's performance analytics
            analytics, _ = PerformanceAnalytics.objects.get_or_create(user=participant.user)
            
            # Calculate new average
            all_ratings = Feedback.objects.filter(participant=participant.user).values_list('rating', flat=True)
            analytics.average_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
            analytics.sessions_participated += 1 if created else 0
            analytics.last_feedback_date = timezone.now()
            analytics.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)