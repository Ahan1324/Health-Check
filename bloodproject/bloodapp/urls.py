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
    path('demo/', views.demo_signup_view, name='demo_signup'),
    
    # New 4-stage system
    path('patient-info/', views.patient_info_view, name='patient_info'),
    path('patient-info/parse-pdf/', views.parse_pdf_markers, name='parse_pdf_markers'),
    path('health-concerns/', views.health_concerns_view, name='health_concerns'),
    path('treatment-plans/', views.treatment_plans_view, name='treatment_plans'),
    path('completed/', views.completed_view, name='completed'),
    path('report/', views.report_view, name='report'),
    
    # Legacy URLs (for backward compatibility)
    path('submit/', views.patient_info_view, name='submit_blood_test'),
    path('quiz/<str:condition_name>/', views.quiz_condition, name='quiz_condition'),
    # Async risk computation endpoints
    path('api/risk/start/<str:condition_id>/', views.api_start_risk_task, name='api_start_risk_task'),
    path('api/risk/status/<str:task_id>/', views.api_risk_task_status, name='api_risk_task_status'),
    path('clear-session/', views.clear_session, name='clear_session'),
    path('treatment-plan/', views.treatment_plans_view, name='treatment_plan'),
    path('health/', views.health_check, name='health_check'),
]

