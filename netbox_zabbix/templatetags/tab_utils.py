"""
NetBox Zabbix Plugin — Model View Tabs (Excluding Jobs)

This module defines a custom Django template tag for rendering the navigation
tabs of a NetBox model view while excluding any tabs related to "Jobs". 

The `model_view_tabs_exlude_jobs` tag dynamically generates tabs based on the
registered views for a model, checks user permissions, computes URLs, and
marks the active tab. It is intended to be used in templates for model
instances where the "Jobs" tab should not be displayed.

Key features:
    - Retrieves all registered views for a given model from the NetBox registry.
    - Filters tabs based on user permissions.
    - Excludes tabs labeled "Jobs".
    - Computes URLs for tabs using Django `reverse`.
    - Marks the active tab based on the current context.
    - Sorts tabs by weight for display ordering.
"""

# Django imports
from django import template
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.module_loading import import_string

# NetBox imports
from netbox.registry import registry
from utilities.views import get_viewname

# NetBox Zabbix plugin imports
from netbox_zabbix.logger import logger

register = template.Library()

# This code is copied from NetBox
@register.inclusion_tag('tabs/model_view_tabs.html', takes_context=True)
def model_view_tabs_exlude_jobs(context, instance):
    """
    Render the tabs for a NetBox model view, excluding the "Jobs" tab.
    
    This template tag is used to dynamically generate the navigation tabs for a
    given model instance in the NetBox UI, while skipping tabs related to Jobs.
    
    Steps performed:
        1. Retrieves all registered views for the model from NetBox's registry.
        2. Checks user permissions for each tab.
        3. Excludes any tab labeled "Jobs".
        4. Renders attributes for each tab (label, badge, weight).
        5. Computes the URL for the tab using Django reverse.
        6. Marks the tab as active if it matches the current context.
        7. Sorts tabs by weight before returning.
    
    Args:
        context (dict): The template context containing at least the request object.
        instance (Model): A Django model instance for which to render the tabs.
    
    Returns:
        dict: A dictionary with a single key 'tabs', containing a list of
              dictionaries for each tab. Each tab dictionary contains:
                  - name (str): The view name.
                  - url (str): The URL for the tab.
                  - label (str): The display label.
                  - badge (str | None): Optional badge for the tab.
                  - weight (int): Tab ordering weight.
                  - is_active (bool): Whether this tab is currently active.
    """
    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    user = context['request'].user
    tabs = []

    # Retrieve registered views for this model
    try:
        views = registry['views'][app_label][model_name]
    except KeyError:
        # No views have been registered for this model
        views = []
    
    # Compile a list of tabs to be displayed in the UI
    for config in views:
        view = import_string( config['view'] ) if type( config['view'] ) is str else config['view']
        if tab := getattr( view, 'tab', None ):
            if tab.permission and not user.has_perm( tab.permission ):
                continue

            if tab.label == "Jobs":
                continue

            if attrs := tab.render( instance ):
                viewname = get_viewname( instance, action=config['name'] )
                active_tab = context.get( 'tab' )
                try:
                    url = reverse( viewname, args=[instance.pk] )
                except NoReverseMatch:
                    # No URL has been registered for this view; skip
                    continue
                tabs.append({
                    'name': config['name'],
                    'url': url,
                    'label': attrs['label'],
                    'badge': attrs['badge'],
                    'weight': attrs['weight'],
                    'is_active': active_tab and active_tab == tab,
                })

    # Order tabs by weight
    tabs = sorted( tabs, key=lambda x: x['weight'] )

    return {
        'tabs': tabs,
    }