from django.urls import path

from . import views

app_name = 'vacancies'

urlpatterns = [
    path('', views.vacancy_list, name='list'),
    path('create/', views.vacancy_create, name='create'),
    path('export/csv/', views.export_vacancies_csv, name='export_csv'),
    path('<int:pk>/', views.vacancy_detail, name='detail'),
    path('<int:pk>/delete/', views.vacancy_delete, name='delete'),
    path('<int:pk>/match/', views.vacancy_run_match, name='run_match'),
    path('<int:pk>/results/', views.vacancy_results, name='results'),
]
