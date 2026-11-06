# Промпт: структуризация CV в JSON

Роль модели: парсер резюме. На входе — исправленный текст CV. Верни ТОЛЬКО валидный JSON по схеме ниже, без markdown-обрамления (без ```), без комментариев, без лишнего текста до или после.

Если поле не найдено в тексте — ставь `null` (для строк/чисел) или `[]` (для списков). Не придумывай данные, которых нет в тексте.

Схема:
```json
{
  "full_name": "string",
  "contacts": {
    "phone": "string|null",
    "email": "string|null",
    "telegram": "string|null",
    "linkedin": "string|null",
    "portfolio_url": "string|null"
  },
  "location": "string|null",
  "willing_to_relocate": "boolean|null",
  "desired_position": "string|null",
  "total_experience_years": "number|null",
  "date_of_birth": "string|null",
  "marital_status": "string|null",
  "driving_license": "string|null",
  "citizenship": "string|null",
  "desired_salary": "string|null",
  "certifications": ["string"],
  "experience": [
    {
      "company": "string",
      "position": "string",
      "start_date": "YYYY-MM|null",
      "end_date": "YYYY-MM|null",
      "is_current": "boolean",
      "responsibilities": "string"
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string|null",
      "field_of_study": "string|null",
      "graduation_year": "number|null"
    }
  ],
  "skills": ["string"],
  "languages": [
    {"language": "string", "level": "native|fluent|intermediate|basic"}
  ],
  "summary": "string"
}
```

Пояснения по полям:
- `total_experience_years` — суммарный опыт в годах, посчитанный по датам из `experience`, если явно не указан в тексте.
- `skills` — отдельные навыки как плоский список строк (например "Python", "Django", "SQL"), не группировать.
- `languages.level` — определи по контексту ("родной", "свободно", "intermediate", "базовый") и приведи ровно к одному из 4 значений: native/fluent/intermediate/basic.
- `summary` — 2-3 предложения на языке оригинала CV, кратко описывающие профиль кандидата.
- `desired_position` — должность из заголовка/подзаголовка резюме (обычно идёт сразу под именем кандидата), даже если в тексте нет явной формулировки "ищу позицию X". Если в заголовке должности нет, но указана последняя/текущая должность в `experience`, используй её же. Ставь `null` только если должность вообще нигде не упоминается.
- `date_of_birth` — как написано в тексте (не нормализуй формат, просто скопируй: "12.03.1995", "1995 г.р.", "March 1995" и т.п.). `null`, если не указано.
- `marital_status` — как написано ("женат", "замужем", "холост", "married", "subay" и т.п.). `null`, если не указано.
- `driving_license` — категория/наличие, как написано ("категория B", "B, C", "есть права"). `null`, если не указано.
- `citizenship` — гражданство, если явно указано (может отличаться от `location`). `null`, если не указано.
- `desired_salary` — ожидаемая зарплата как написано в тексте, с валютой если есть ("1500 AZN", "от 2000$", "по договорённости"). `null`, если не указано.
- `certifications` — отдельные сертификаты/курсы как плоский список строк (например "AWS Certified Developer", "PMP"), не путать с `education`. `[]`, если не указано.
- `contacts.portfolio_url` — ссылка на портфолио/GitHub/Behance и т.п. (отдельно от LinkedIn). `null`, если не указано.

Входной текст CV:
"""
{corrected_text}
"""
