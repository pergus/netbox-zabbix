from django import template

register = template.Library()


def _remove_empty_strings(obj):
    """
    Recursively remove keys with empty string values from dicts and lists.
    """
    if isinstance(obj, dict):
        return {k: _remove_empty_strings(v) for k, v in obj.items() if v != ""}
    elif isinstance(obj, list):
        return [_remove_empty_strings(item) for item in obj]
    else:
        return obj

@register.filter(name="remove_empty_strings")
def remove_empty_strings(value):
    """
    Remove all fields with empty string values from a JSON-like object.
    """
    return _remove_empty_strings(value)