from django.contrib import admin
from django.urls import path, include
from django.urls import path
from . import views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('submit/', views.submit_blood_test, name='submit_blood_test'),
    path('quiz/<str:condition_name>/', views.quiz_condition, name='quiz_condition'),
    path('clear-session/', views.clear_session, name='clear_session'),
]

