from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def average(queryset, field):
    values = [getattr(obj, field, 0) for obj in queryset if getattr(obj, field, None) not in (None, '')]
    return round(sum(values) / len(values), 2) if values else 0

@register.filter
def sum_max_marks(answers):
    return sum(a.question.max_marks for a in answers)

@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg) if arg else 0
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0