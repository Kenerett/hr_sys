"""Views candidates: загрузка CV, карточка кандидата, работа с базой напрямую
(см. "Загрузка CV", "Карточка кандидата", "Работа с базой напрямую" в Obsidian).
"""

import csv

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_q.tasks import async_task

from . import search as ai_search_module
from .models import HR_STATUS_CHOICES, Candidate

SORT_OPTIONS = {
    'created_desc': ('-created_at', 'Newest first'),
    'experience_desc': ('-total_experience_years', 'Most experience'),
    'name_asc': ('full_name', 'Name (A-Z)'),
}


def candidate_list(request):
    """Поиск и фильтрация по базе кандидатов без привязки к вакансии (CRUD, без AI)."""
    candidates = Candidate.objects.all()

    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    hr_status = request.GET.get('hr_status', '').strip()
    skill = request.GET.get('skill', '').strip()
    language = request.GET.get('language', '').strip()
    university = request.GET.get('university', '').strip()
    min_experience = request.GET.get('min_experience', '').strip()
    sort = request.GET.get('sort', 'created_desc').strip()
    if sort not in SORT_OPTIONS:
        sort = 'created_desc'

    candidates = candidates.order_by(SORT_OPTIONS[sort][0])

    if query:
        candidates = candidates.filter(
            Q(full_name__icontains=query)
            | Q(desired_position__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )
    if location:
        candidates = candidates.filter(location__icontains=location)
    if hr_status:
        candidates = candidates.filter(hr_status=hr_status)

    candidates = list(candidates)

    # ArrayField/JSONField: фильтрация по подстроке элемента делается в Python —
    # для масштаба хакатона датасет небольшой, точный __contains на DB-уровне избыточен.
    if skill:
        skill_lower = skill.lower()
        candidates = [c for c in candidates if any(skill_lower in s.lower() for s in c.skills)]
    if language:
        language_lower = language.lower()
        candidates = [
            c for c in candidates
            if any(language_lower in (lang.get('language') or '').lower() for lang in c.languages)
        ]
    if university:
        university_lower = university.lower()
        candidates = [
            c for c in candidates
            if any(university_lower in (edu.get('institution') or '').lower() for edu in c.education)
        ]
    if min_experience:
        try:
            min_exp_value = float(min_experience)
            candidates = [c for c in candidates if (c.total_experience_years or 0) >= min_exp_value]
        except ValueError:
            pass

    return render(request, 'candidates/list.html', {
        'candidates': candidates,
        'hr_status_choices': HR_STATUS_CHOICES,
        'sort_options': SORT_OPTIONS,
        'filters': {
            'q': query, 'location': location, 'hr_status': hr_status,
            'skill': skill, 'language': language, 'university': university, 'min_experience': min_experience,
            'sort': sort,
        },
    })


def cv_upload(request):
    """HR загружает один или несколько файлов CV; обработка уходит в фон (Django-Q2),
    HTTP-ответ не ждёт её завершения.
    """
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        if not files:
            messages.error(request, 'Please select at least one file.')
            return redirect('candidates:upload')

        for uploaded_file in files:
            candidate = Candidate.objects.create(source_file=uploaded_file, processing_status='pending')
            async_task('candidates.tasks.process_candidate_cv', candidate.id)

        messages.success(request, f'Uploaded {len(files)} file(s). Processing in background.')
        return redirect('candidates:list')

    return render(request, 'candidates/upload.html')


def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        candidate.hr_status = request.POST.get('hr_status', candidate.hr_status)
        candidate.hr_notes = request.POST.get('hr_notes', '')
        candidate.save(update_fields=['hr_status', 'hr_notes'])
        messages.success(request, 'Status updated.')
        return redirect('candidates:detail', pk=pk)

    source_file_ext = ''
    if candidate.source_file:
        source_file_ext = candidate.source_file.name.rsplit('.', 1)[-1].lower()

    return render(request, 'candidates/detail.html', {
        'candidate': candidate,
        'hr_status_choices': HR_STATUS_CHOICES,
        'source_file_is_pdf': source_file_ext == 'pdf',
        'source_file_is_image': source_file_ext in ('jpg', 'jpeg', 'png'),
    })


def candidate_edit(request, pk):
    """Ручная правка полей, которые AI мог извлечь неточно (имя, навыки, опыт и т.п.).
    experience/education/languages (вложенные JSON-структуры) не редактируются здесь —
    это требует динамических форм, вне текущего скоупа.
    """
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        candidate.full_name = request.POST.get('full_name', '').strip()
        candidate.phone = request.POST.get('phone', '').strip() or None
        candidate.email = request.POST.get('email', '').strip() or None
        candidate.telegram = request.POST.get('telegram', '').strip() or None
        candidate.linkedin = request.POST.get('linkedin', '').strip() or None
        candidate.location = request.POST.get('location', '').strip() or None
        candidate.desired_position = request.POST.get('desired_position', '').strip() or None
        candidate.willing_to_relocate = request.POST.get('willing_to_relocate') == 'on'
        candidate.portfolio_url = request.POST.get('portfolio_url', '').strip() or None
        candidate.date_of_birth = request.POST.get('date_of_birth', '').strip() or None
        candidate.marital_status = request.POST.get('marital_status', '').strip() or None
        candidate.driving_license = request.POST.get('driving_license', '').strip() or None
        candidate.citizenship = request.POST.get('citizenship', '').strip() or None
        candidate.desired_salary = request.POST.get('desired_salary', '').strip() or None

        experience_years = request.POST.get('total_experience_years', '').strip()
        candidate.total_experience_years = float(experience_years) if experience_years else None

        skills_raw = request.POST.get('skills', '').strip()
        candidate.skills = [s.strip() for s in skills_raw.split(',') if s.strip()] if skills_raw else []

        certifications_raw = request.POST.get('certifications', '').strip()
        candidate.certifications = [s.strip() for s in certifications_raw.split(',') if s.strip()] if certifications_raw else []

        candidate.summary = request.POST.get('summary', '').strip()

        candidate.save()
        messages.success(request, 'Candidate profile updated.')
        return redirect('candidates:detail', pk=pk)

    return render(request, 'candidates/edit.html', {'candidate': candidate})


def candidate_delete(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if request.method == 'POST':
        full_name = candidate.full_name or f'Candidate #{candidate.pk}'
        if candidate.source_file:
            candidate.source_file.delete(save=False)
        candidate.delete()
        messages.success(request, f'{full_name} deleted.')
        return redirect('candidates:list')
    return redirect('candidates:detail', pk=pk)


def export_candidates_csv(request):
    """Экспорт всей базы кандидатов в CSV для локального скачивания."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="candidates.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'id', 'full_name', 'phone', 'email', 'telegram', 'linkedin', 'portfolio_url', 'location',
        'willing_to_relocate', 'desired_position', 'total_experience_years',
        'date_of_birth', 'marital_status', 'driving_license', 'citizenship', 'desired_salary',
        'skills', 'certifications', 'languages', 'summary', 'language_detected',
        'processing_status', 'hr_status', 'hr_notes', 'created_at',
    ])
    for c in Candidate.objects.all().order_by('id'):
        writer.writerow([
            c.id, c.full_name, c.phone, c.email, c.telegram, c.linkedin, c.portfolio_url, c.location,
            c.willing_to_relocate, c.desired_position, c.total_experience_years,
            c.date_of_birth, c.marital_status, c.driving_license, c.citizenship, c.desired_salary,
            '; '.join(c.skills or []), '; '.join(c.certifications or []),
            '; '.join(f"{lang.get('language')}:{lang.get('level')}" for lang in c.languages or []),
            c.summary, c.language_detected,
            c.processing_status, c.hr_status, c.hr_notes, c.created_at,
        ])
    return response


def candidate_status_badge(request, pk):
    """Партиал для HTMX-поллинга статуса обработки сразу после загрузки CV."""
    candidate = get_object_or_404(Candidate, pk=pk)
    return render(request, 'candidates/_status_badge.html', {'candidate': candidate})


def ai_search(request):
    """AI-поиск по базе на естественном языке: HR вводит запрос свободным текстом
    ("хочу full-stack разработчиков"), система ищет семантически близких
    кандидатов через pgvector и объясняет совпадение через LLM.
    """
    query_text = request.GET.get('q', '').strip()
    results = None
    if query_text:
        results = ai_search_module.search_candidates(query_text)

    return render(request, 'candidates/ai_search.html', {
        'query_text': query_text,
        'results': results,
    })
