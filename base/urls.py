from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import session_assignment

urlpatterns = [
    path('login/', views.loginPage, name='login'),
    path('register/', views.registerPage, name='register'),
    path('logout/', views.logoutUser, name='logout'),
    path('', views.landingPage, name='landing'),
    path('home/', views.homePage, name='home'),
    path('analytics/', views.analyticsPage, name='analytics'),
    path('apply-sessions/', views.applySession, name='apply-sessions'),
    path('moderator/', views.moderator_view, name='moderator'),
    path('update-user-image/', views.update_user_image, name='update-user-image'),
    path('application/', views.application_page, name='application'),
    path('history/', views.history_page, name='history'),
    path('evaluation/', views.evaluation_page, name='evaluation'),
    path('evaluation-dashboard/', views.evaluation_dashboard, name='evaluation-dashboard'),
    path('add-availability/', views.add_availability, name='add_availability'),
    path('delete-availability/<int:availability_id>/', views.delete_availability, name='delete_availability'),
    path('get-availability/', views.get_availability, name='get_availability'),
    path('available-timings/', views.available_timings, name='available-timings'),
    path('chat/', views.chat_room, name='chat_room'),
    path('send-message/', views.send_message, name='send-message'),
    # path('create-session/', views.CreateSessionView.as_view(), name='create_session'),
    path('session-assignment/<int:request_id>/', session_assignment, name='session-assignment'),
    # path('api/assign-evaluator/', views.assign_evaluator, name='assign_evaluator'),
    path('test_jitsi/', views.test_jitsi, name='test_jitsi'),
    path('sessions/<int:session_id>/confirm/', views.confirm_session, name='confirm_session'),
    path('sessions/<int:session_id>/decline/', views.decline_session, name='decline_session'),
    path('submit-feedback/', views.submit_feedback, name='submit-feedback'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)