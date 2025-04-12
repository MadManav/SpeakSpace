from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Session, Topic, SessionParticipant,InterviewRequest,EvaluatorAvailability,ChatRoom,ChatMessage
from django.utils import timezone
from django.db.models import Avg
from django.http import JsonResponse
from datetime import datetime

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        # Check for moderator credentials
        if username == 'moderator' and password == 'moderator':
            return redirect('moderator')
        
        try:
            user = User.objects.get(username=username)
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                if user.role == 'evaluator':
                    return redirect('evaluation-dashboard')  # Changed from evaluator_dashboard to evaluation-dashboard
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password')
        except:
            messages.error(request, 'User does not exist')
            
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
            
        except Exception as e:
            messages.error(request, 'An error occurred during registration')
            
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
            return redirect('apply-session')
    
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


def moderator(request):
    interview_requests = InterviewRequest.objects.filter(status='pending').select_related('participant', 'topic')
    return render(request, 'base/moderator.html', {
        'interview_requests': interview_requests
    })

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

@login_required
def available_timings(request):
    if request.user.role != 'evaluator':
        messages.error(request, "Access denied. Only evaluators can access this page.")
        return redirect('home')

    if request.method == 'POST':
        topic_id = request.POST.get('topic')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        # Combine date and time
        available_from = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        available_to = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")

        if available_from >= available_to:
            messages.error(request, "End time must be after start time")
        else:
            EvaluatorAvailability.objects.create(
                evaluator=request.user,
                topic_id=topic_id,
                available_from=available_from,
                available_to=available_to
            )
            messages.success(request, "Availability slot added successfully")
        return redirect('available-timings')

    context = {
        'topics': Topic.objects.all(),
        'availability_slots': EvaluatorAvailability.objects.filter(
            evaluator=request.user,
            available_from__gte=datetime.now()
        ).select_related('topic')
    }
    return render(request, 'base/available-timing.html', context)

@login_required
def delete_availability(request, slot_id):
    if request.method == 'POST':
        try:
            slot = EvaluatorAvailability.objects.get(id=slot_id, evaluator=request.user)
            slot.delete()
            messages.success(request, "Availability slot deleted successfully")
        except EvaluatorAvailability.DoesNotExist:
            messages.error(request, "Availability slot not found")
    return redirect('available-timings')




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
    chat_messages = ChatMessage.objects.filter(room=chat_room).order_by('timestamp')  # Added this line
    
    context = {
        'topic': topic,
        'participants': participants,
        'chat_room': chat_room,
        'current_user': request.user,
        'messages': chat_messages  # Added this line
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

# @login_required
# def create_session(request):
#     if request.method == 'POST':
#         form = SessionForm(request.POST)
#         if form.is_valid():
#             session = form.save(commit=False)
#             session.created_by = request.user
#             session.save()
            
#             # Generate meeting credentials
#             credentials = session.generate_meeting_credentials()
            
#             # Add participants
#             participants = form.cleaned_data['participants']
#             for user in participants:
#                 SessionParticipant.objects.create(session=session, user=user)
            
#             # Notify participants
#             session.notify_participants()
            
#             return redirect('session_detail', pk=session.pk)
#     else:
#         form = SessionForm()
    
#     return render(request, 'create_session.html', {'form': form})

# @login_required
# def session_detail(request, pk):
#     session = Session.objects.get(pk=pk)
#     return render(request, 'session_detail.html', {'session': session})

# @login_required
# def participant_dashboard(request):
#     participant_sessions = SessionParticipant.objects.filter(user=request.user)
#     selector_sessions = Session.objects.filter(selector=request.user)
#     return render(request, 'participant_dashboard.html', {
#         'participant_sessions': participant_sessions,
#         'selector_sessions': selector_sessions
#     })