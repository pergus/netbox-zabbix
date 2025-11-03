from django import template

register = template.Library()


def _remove_empty_strings(obj):
    """
    Recursively remove keys with empty string values from dictionaries and lists.
    
    This helper function traverses a JSON-like object (dicts and lists) and
    removes any key-value pairs where the value is an empty string. For lists,
    it processes each item recursively. Non-iterable values are returned as-is.
    
    Args:
        obj (dict | list | any): The object to process.
    
    Returns:
        dict | list | any: A new object with all empty string values removed.
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
    Django template filter that removes all fields with empty string values
    from a JSON-like object.
    
    This filter can be applied directly in templates to clean up dictionaries
    or lists before rendering them.
    
    Example usage in a template:
        {{ my_dict|remove_empty_strings }}
    
    Args:
        value (dict | list): The object to filter.
    
    Returns:
        dict | list: A new object with all empty string values removed.
    """
    return _remove_empty_strings(value)