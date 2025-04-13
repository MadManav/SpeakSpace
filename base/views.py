from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Session, Topic, SessionParticipant, InterviewRequest, EvaluatorAvailability, ChatRoom, ChatMessage
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
# ... rest of your imports ...
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from django.core.exceptions import ValidationError

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
            return redirect('home')  # Redirect to home page after successful registration
            
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
    active_sessions = Session.objects.filter(start_time__gte=timezone.now()).order_by('start_time')
    
    # Get all chat rooms where user is a participant
    user_chat_rooms = ChatRoom.objects.filter(participants=request.user)
    joined_topic_ids = user_chat_rooms.values_list('topic_id', flat=True)
    
    context = {
        'topics': topics,
        'active_sessions': active_sessions,
        'user': request.user,
        'joined_topic_ids': joined_topic_ids,
    }
    return render(request, 'base/home.html', context)


@login_required(login_url='login')
def analyticsPage(request):
    # Get the user's sessions using the direct participants field
    #user_sessions = Session.objects.filter(participants=request.user)
    
    # Calculate statistics
    # total_sessions = user_sessions.count()
    # average_rating = user_sessions.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get recent feedback
    # recent_feedback = user_sessions.exclude(feedback='').order_by('-start_time')[:5]
    
    context = {
        # 'total_sessions': total_sessions,
        # 'average_rating': round(average_rating, 1),
        # 'recent_feedback': recent_feedback,
        'user': request.user,
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
        return redirect('home')  # or wherever non-evaluators should go
    return render(request, 'base/EvaluatorDashboard.html')


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

        # Get the selected availability slot
        evaluator_availability = get_object_or_404(EvaluatorAvailability, id=evaluator_id)
        
        # Determine match type based on availability list
        if evaluator_availability in exact_matches:
            match_type = 'perfect'
        else:
            match_type = 'alternative'

        # Create session with proper type
        session = Session.objects.create(
            topic=interview_request.topic,
            created_by=request.user,
            selector=evaluator_availability.evaluator,
            start_time=datetime.fromisoformat(selected_time) if selected_time else interview_request.preferred_date,
            duration_minutes=60,
            scheduled_by=request.user,
            assignment_type=match_type
        )

        # Add participant
        SessionParticipant.objects.create(
            session=session,
            user=interview_request.participant
        )

        # Handle meeting creation based on match type
        if match_type == 'perfect':
            session.generate_meeting_credentials()
            session.save()  # Explicit save after generating credentials
            interview_request.status = 'approved'
            msg = f"Session scheduled with {evaluator_availability.evaluator.get_full_name()}"
        else:
            session.generate_meeting_credentials()
            session.meeting_link += "?provisional=true"
            session.save()
            interview_request.status = 'pending_confirmation'
            msg = f"Proposal sent to participant with {evaluator_availability.evaluator.get_full_name()}"

        messages.success(request, f"{msg}. Meeting link: {session.meeting_link}")
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




