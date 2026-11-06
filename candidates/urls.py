from django.urls import path

from . import views

app_name = 'candidates'

urlpatterns = [
    path('', views.candidate_list, name='list'),
    path('ai-search/', views.ai_search, name='ai_search'),
    path('upload/', views.cv_upload, name='upload'),
    path('export/csv/', views.export_candidates_csv, name='export_csv'),
    path('<int:pk>/', views.candidate_detail, name='detail'),
    path('<int:pk>/edit/', views.candidate_edit, name='edit'),
    path('<int:pk>/delete/', views.candidate_delete, name='delete'),
    path('<int:pk>/status-badge/', views.candidate_status_badge, name='status_badge'),
]
