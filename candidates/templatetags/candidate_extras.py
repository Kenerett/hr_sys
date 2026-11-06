import re

from django import template

register = template.Library()


@register.filter
def whatsapp_number(phone):
    """Цифры только, для wa.me/<digits> — WhatsApp не принимает +, пробелы, тире."""
    if not phone:
        return ''
    return re.sub(r'\D', '', phone)
