"""Views vacancies: создание вакансии, запуск матчинга, результаты матчинга
(см. "Создание вакансии", "Матчинг под вакансию", "Результаты матчинга" в Obsidian).
"""

import csv

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from common import llm_client
from common.llm_client import LLMError

from .matching import run_matching
from .models import Vacancy


def vacancy_list(request):
    vacancies = Vacancy.objects.all()
    return render(request, 'vacancies/list.html', {'vacancies': vacancies})


def vacancy_create(request):
    """HR вводит текст вакансии свободным текстом; LLM извлекает структурированные
    требования синхронно (один быстрый вызов, ~10-20 сек — приемлемо для одного запроса).
    """
    if request.method == 'POST':
        title_hint = request.POST.get('title', '').strip()
        raw_description = request.POST.get('raw_description', '').strip()
        if not raw_description:
            messages.error(request, 'Please enter the vacancy description.')
            return redirect('vacancies:create')

        try:
            requirements = llm_client.extract_vacancy_requirements(raw_description)
        except LLMError as exc:
            messages.error(request, f'Could not parse the vacancy: {exc}')
            return redirect('vacancies:create')

        vacancy = Vacancy.objects.create(
            title=requirements.get('title') or title_hint or 'Untitled',
            raw_description=raw_description,
            must_have_skills=requirements.get('must_have_skills') or [],
            nice_to_have_skills=requirements.get('nice_to_have_skills') or [],
            min_experience_years=requirements.get('min_experience_years'),
            required_education_level=requirements.get('required_education_level'),
            required_languages=requirements.get('required_languages') or [],
            seniority=requirements.get('seniority'),
        )
        embedding_text = '\n'.join(filter(None, [
            vacancy.title,
            ', '.join(vacancy.must_have_skills),
            ', '.join(vacancy.nice_to_have_skills),
            raw_description,
        ]))
        vacancy.embedding = llm_client.get_embedding(embedding_text)
        vacancy.save(update_fields=['embedding'])

        messages.success(request, 'Vacancy created, requirements extracted.')
        return redirect('vacancies:detail', pk=vacancy.pk)

    return render(request, 'vacancies/create.html')


def vacancy_detail(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    return render(request, 'vacancies/detail.html', {'vacancy': vacancy})


def vacancy_run_match(request, pk):
    """Запускает подбор кандидатов синхронно (векторный поиск + score для всех,
    LLM-объяснение только для top-K — см. vacancies/matching.py).
    """
    vacancy = get_object_or_404(Vacancy, pk=pk)
    if request.method == 'POST':
        run_matching(vacancy)
        messages.success(request, 'Matching completed.')
    return redirect('vacancies:results', pk=pk)


def vacancy_results(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    results = vacancy.match_results.select_related('candidate').order_by('-passed_hard_filters', '-final_score')
    return render(request, 'vacancies/results.html', {'vacancy': vacancy, 'results': results})


def vacancy_delete(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    if request.method == 'POST':
        title = vacancy.title
        vacancy.delete()
        messages.success(request, f'Vacancy "{title}" deleted.')
        return redirect('vacancies:list')
    return redirect('vacancies:detail', pk=pk)


def export_vacancies_csv(request):
    """Экспорт всех вакансий в CSV для локального скачивания."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vacancies.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'id', 'title', 'must_have_skills', 'nice_to_have_skills', 'min_experience_years',
        'required_education_level', 'required_languages', 'seniority', 'status', 'created_at',
    ])
    for v in Vacancy.objects.all().order_by('id'):
        writer.writerow([
            v.id, v.title,
            '; '.join(v.must_have_skills or []),
            '; '.join(v.nice_to_have_skills or []),
            v.min_experience_years,
            v.required_education_level,
            '; '.join(f"{lang.get('language')}:{lang.get('min_level')}" for lang in v.required_languages or []),
            v.seniority, v.status, v.created_at,
        ])
    return response
