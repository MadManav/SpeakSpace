from django.urls import path
from . import views
#from .views import update_user

urlpatterns = [
    path('login/', views.loginPage, name='login'),
    path('register/', views.registerPage, name='register'),
    path('logout/', views.logoutUser, name='logout'),
    path('', views.landingPage, name='landing'),
    path('home/', views.homePage, name='home'),
    path('analytics/', views.analyticsPage, name='analytics'),
]