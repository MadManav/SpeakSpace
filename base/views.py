from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Session, Topic, SessionParticipant,InterviewRequest
from django.utils import timezone
from django.db.models import Avg
from django.http import JsonResponse

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
            # Check if user exists
            user = User.objects.get(username=username)
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password')
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
        except Exception as e:
            messages.error(request, 'An error occurred during login')

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
    
    context = {
        'topics': topics,
        'active_sessions': active_sessions,
        'user': request.user,
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

def evaluation_dashboard(request):
    return render(request, 'base/EvaluatorDashboard.html')

def available_timings(request):
    return render(request, 'base/available-timing.html')

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