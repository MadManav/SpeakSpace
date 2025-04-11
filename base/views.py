from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Session, Topic, SessionParticipant
from django.utils import timezone
from django.db.models import Avg

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username').lower()  # Convert to lowercase
        password = request.POST.get('password')

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
        'user': request.user,  # Add user to context
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