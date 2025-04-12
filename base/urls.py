from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login/', views.loginPage, name='login'),
    path('register/', views.registerPage, name='register'),
    path('logout/', views.logoutUser, name='logout'),
    path('', views.landingPage, name='landing'),
    path('home/', views.homePage, name='home'),
    path('analytics/', views.analyticsPage, name='analytics'),
    path('apply-sessions/', views.applySession, name='apply-sessions'),
    path('moderator/', views.moderator, name='moderator'),
    path('update-user-image/', views.update_user_image, name='update-user-image'),
    path('application/', views.application_page, name='application'),
    path('history/', views.history_page, name='history'),
    path('evaluation/', views.evaluation_page, name='evaluation'),
    path('evaluation-dashboard/', views.evaluation_dashboard, name='evaluation-dashboard'),
    path('available-timings/', views.available_timings, name='available-timings'),
    path('delete-availability/<int:slot_id>/', views.delete_availability, name='delete-availability'),
    path('chat/', views.chat_room, name='chat_room'),
    path('send-message/', views.send_message, name='send-message'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)