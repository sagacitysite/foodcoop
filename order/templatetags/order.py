from django import template

register = template.Library()


@register.filter
def get_argument(value, arg):
    """Get argument by variable"""
    return value.get(arg, None)
