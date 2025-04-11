from django.urls import path
from . import views
#from .views import update_user

urlpatterns=[
    path('',views.loginPage,name="login"),
]
