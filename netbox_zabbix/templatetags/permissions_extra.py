"""
NetBox Zabbix Plugin — Model Permission Checks

This module provides a custom Django template filter to check whether a
user has *any permission* for a given model. It simplifies template logic
for conditionally displaying content based on user permissions.

Filters:
    - has_any_model_perm: Returns True if the user has at least one of the
      standard model permissions (view, add, change, delete) for the
      specified model, given as "app_label.modelname".

Intended for use in templates where content should be shown or hidden
based on a user's permissions on a model.
"""

# Django imports
from django import template

register = template.Library()

@register.filter(name="has_any_model_perm")
def has_any_model_perm(user, model_string):
    """
    Check if the user has *any permission* for a given model.

    Usage in template:
        {% if request.user|has_any_model_perm:"app_label.modelname" %}
            ...
        {% endif %}

    Example:
        {% if request.user|has_any_model_perm:"netbox_zabbix.zabbixadminpermission" %}
    """
    try:
        app_label, model_name = model_string.split( "." )
    except ValueError:
        return False  # invalid format

    actions = ["view", "add", "change", "delete"]
    return any( user.has_perm( f"{app_label}.{action}_{model_name}" ) for action in actions )