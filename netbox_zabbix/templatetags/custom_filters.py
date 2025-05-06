from django import template

register = template.Library()

@register.filter(name="get_value")
def get_value(obj, attr_name):
    """
    Template filter to safely retrieve the value from an object.
    
    Usage in template:
        {{ object|get_value:"field_name" }}
    
    Returns the value of the specified attribute, or None if it doesn't exist.
    """        
    return getattr(obj, attr_name, None)