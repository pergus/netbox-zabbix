"""
NetBox Zabbix Plugin — Views

This module defines all Django class-based and function-based views for the
NetBox Zabbix integration plugin. It handles UI presentation and business logic
for managing Zabbix-related models such as Settings, Templates, Proxies,
Mappings, Interfaces, and Host Configurations.

The views extend NetBox’s generic view framework for consistency and leverage
Django’s built-in request handling. Most views use standard NetBox mixins like
ObjectView, ObjectListView, ObjectEditView, and ObjectDeleteView.

Structure:
- Setting views: Manage Zabbix connection configuration.
- Template, Proxy, and Group views: CRUD for Zabbix metadata.
- Mapping views: Manage relationships between NetBox and Zabbix objects.
- Interface views: Manage SNMP/Agent interface mappings.
- HostConfig and EventLog views: Display and synchronize host data and logs.
"""

# Standard library imports
from itertools import chain

# Django imports
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.shortcuts import redirect, render, get_object_or_404
from django.template.defaultfilters import capfirst, pluralize
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView as GenericTemplateView
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin


# Third-party imports
from django_tables2 import RequestConfig

# NetBox imports
from core.tables.jobs import JobTable
from users.models import User
from dcim.models import Device
from netbox.views import generic
from utilities.paginator import EnhancedPaginator, get_paginate_count
from utilities.views import ViewTab, register_model_view
from virtualization.models import VirtualMachine

# NetBox Zabbix plugin imports
from netbox_zabbix import settings, filtersets, forms, tables
from netbox_zabbix.jobs.host import UpdateZabbixHost
from netbox_zabbix.jobs.imports import ImportZabbixSettings, ImportHost
from netbox_zabbix.jobs.validate import ValidateHost
from netbox_zabbix.jobs.synchosts import SyncHostsNow
from netbox_zabbix.jobs.system import SystemJobHostConfigSyncRefresh
from netbox_zabbix.jobs.provision import ProvisionAgent, ProvisionSNMP
from netbox_zabbix.zabbix import api as zapi
from netbox_zabbix.models import (
    InterfaceTypeChoices,
    Setting,
    Template,
    Proxy,
    ProxyGroup,
    HostGroup,
    TagMapping,
    InventoryMapping,
    Mapping,
    DeviceMapping,
    VMMapping,
    HostConfig,
    AgentInterface,
    SNMPInterface,
    Maintenance,
    EventLog,
)
from netbox_zabbix.zabbix.validation import validate_quick_add
from netbox_zabbix.netbox.interfaces import can_delete_interface, is_interface_available
from netbox_zabbix.netbox.permissions import has_any_model_permission
from netbox_zabbix.logger import logger



# ------------------------------------------------------------------------------
# Setting 
# ------------------------------------------------------------------------------


class SettingView(generic.ObjectView):
    """
    Display a single Zabbix Setting instance.
    
    Provides a filtered list of fields excluding internal ones such as ID and tokens.
    """
    queryset      = Setting.objects.all()

    def get_extra_context(self, request, instance):
        """
        Prepare additional context for the template view.
        
        Args:
            request (HttpRequest): The current request object.
            instance (Setting): The Setting instance to display.
        
        Returns:
            dict: Extra context with a list of visible fields.
        """
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data', 'token' ]
        fields = [ ( capfirst( field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class SettingListView(generic.ObjectListView):
    """
    Display a list of Zabbix Settings.
    
    Hides the add button if a configuration already exists.
    """
    queryset = Setting.objects.all()
    table    = tables.SettingTable

    def get_extra_context(self, request):
        """
        Add extra context for template rendering.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            dict: Context dictionary with optional actions.
        """
        # Hide the add button if a configuration already exists.
        context = super().get_extra_context( request )
        if Setting.objects.exists():
            context['actions'] = []
        return context


class SettingEditView(generic.ObjectEditView):
    """
    Edit a Zabbix Setting instance.
    """
    queryset = Setting.objects.all()
    form     = forms.SettingForm


class SettingDeleteView(generic.ObjectDeleteView):
    """
    Delete a Zabbix Setting instance.
    
    Prevents deletion with an error message.
    """
    queryset = Setting.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Handle deletion attempt.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirects to the settings list with a message.
        """
        obj = self.get_object( **kwargs )
    
        if obj:
            messages.error( request, "You cannot delete the configuration." )
            return redirect( 'plugins:netbox_zabbix:setting_list' )
    
        return super().post( request, *args, **kwargs )


# --------------------------------------------------------------------------
# Zabbix Check connection
# --------------------------------------------------------------------------


def zabbix_check_connection(request):
    """
    Verify connection to the Zabbix API using stored credentials.
    Updates plugin settings with connection status and last check time.
    
    Args:
        request (HttpRequest): The triggering HTTP request.
    
    Returns:
        HttpResponseRedirect: Redirect back to referring page with success/error message.
    """
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )

    try:
        zapi.validate_zabbix_credentials_from_config()
        settings.set_version( zapi.get_version() )
        settings.set_connection( status=True )
        settings.set_last_checked( timezone.now() )
        messages.success( request, "Connection to Zabbix succeeded" )

    except settings.ZabbixSettingNotFound as e:
        messages.error( request, e )
        return redirect( redirect_url )
            
    except Exception as e:
        error_msg = f"Failed to connect to {settings.get_zabbix_api_endpoint()}: {e}"
        logger.error( error_msg )
        messages.error( request, error_msg )
        settings.set_connection( status=False )
        settings.set_last_checked( timezone.now() )

    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Sync Host With Zabbix
# ------------------------------------------------------------------------------


def sync_with_zabbix(request):
    """
    Sync a specific HostConfig with Zabbix.
    Enqueues a job to update the host in Zabbix immediately.
    
    Args:
        request (HttpRequest): The triggering request with host_config_id.
    
    Returns:
        HttpResponseRedirect: Redirect back to referring page with success/error message.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    
    try:
        host_config_id = request.GET.get( "host_config_id" )
        host_config = HostConfig.objects.get( id=host_config_id )
        UpdateZabbixHost.run_job_now( host_config=host_config, request=request )
        messages.success( request, f"Sync {host_config.name} with Zabbix succeeded." )
    except Exception as e:
        messages.error( request, f"Failed to sync {host_config.name} with Zabbix. Reason: { str( e ) }" )

    return redirect( redirect_url )


# --------------------------------------------------------------------------
# Zabbix Import Settings (Tempate, Proxies, etc.)
# --------------------------------------------------------------------------


def zabbix_import_settings(request):
    """
    Trigger import of all Zabbix settings (templates, proxies, etc.).
    
    Args:
        request (HttpRequest): The HTTP request triggering the import.
    
    Returns:
        HttpResponseRedirect: Redirect back to referring page.
    """
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    try:
        ImportZabbixSettings.run_now()
    except Exception as e:
        raise e
    
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateView(generic.ObjectView):
    """
    Display a single Zabbix Template object.
    """
    queryset = Template.objects.all()
    
    def get_extra_context(self, request, instance):
        """
        Prepare extra context for template view.
        
        Args:
            request (HttpRequest): Current request.
            instance (Template): Template instance.
        
        Returns:
            dict: Extra context excluding internal fields.
        """
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data' ]
        fields = [ ( capfirst(field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class TemplateListView(generic.ObjectListView):
    """
    Display a list of Zabbix Templates with host count annotations.
    """
    queryset       = Template.objects.all()
    filterset      = filtersets.TemplateFilterSet
    filterset_form = forms.TemplateFilterForm
    table          = tables.TemplateTable
    template_name  = "netbox_zabbix/template_list.html"

    def get_queryset(self, request):
        """
        Customize the queryset to include host counts and ordering.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            QuerySet: Annotated and ordered queryset.
        """
        # Base queryset
        qs = super().get_queryset( request )
        
        # Annotate for host_count (LinkedCountColumn)
        qs = qs.annotate( host_count=Count( "hostconfig", distinct=True ) )

        # Apply default ordering manually after all annotations
        return qs.order_by( "name", "pk" )


class TemplateEditView(generic.ObjectEditView):
    """
    Edit a Zabbix Template instance.
    """
    queryset = Template.objects.all()
    form     = forms.TemplateForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


class TemplateDeleteView(generic.ObjectDeleteView):
    """
    Delete a Zabbix Template instance.
    """
    queryset = Template.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


class TemplateBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple Zabbix Template instances.
    """
    queryset = Template.objects.all()
    table    = tables.TemplateTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to template list view.
        """
        return reverse( 'plugins:netbox_zabbix:template_list' )


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


def run_import_templates(request=None):
    """
    Import Zabbix templates and optionally attach messages to the request.
    
    Args:
        request (HttpRequest, optional): Request object for adding messages.
    
    Returns:
        tuple: (added_templates, deleted_templates, error)
    """
    try:
        added, deleted = zapi.import_templates()

        if request is not None:
            msg_lines = ["Importing Zabbix Templates succeeded."]
            if added:
                msg_lines.append( f"Added {len(added)} template{pluralize( len( added ) )}." )
            if deleted:
                msg_lines.append( f"Deleted {len(deleted)} template{pluralize( len( deleted ) )}." )
            if not added and not deleted:
                msg_lines.append( "No changes detected." )
            messages.success( request, mark_safe( "<br>".join( msg_lines ) ) )

        return added, deleted, None

    except RuntimeError as e:
        error_msg = "Importing Zabbix Templates failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}" ) )
        return None, None, e

    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}" ) )
        settings.set_connection( status=False )
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_templates(request):
    """
    View wrapper to import templates and redirect back.
    
    Args:
        request (HttpRequest): Triggering request.
    
    Returns:
        HttpResponseRedirect: Redirect to referring page.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_templates( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyView(generic.ObjectView):
    """
    Display a single Zabbix Proxy object.
    """
    queryset = Proxy.objects.all()


class ProxyListView(generic.ObjectListView):
    """
    Display a list of Zabbix Proxies.
    """
    queryset       = Proxy.objects.all()
    filterset      = filtersets.ProxyFilterSet
    filterset_form = forms.ProxyFilterForm
    table          = tables.ProxyTable
    template_name  = "netbox_zabbix/proxy_list.html"


class ProxyEditView(generic.ObjectEditView):
    """
    Edit a Zabbix Proxy instance.
    """
    queryset = Proxy.objects.all()
    form     = forms.ProxyForm
    template_name = "netbox_zabbix/proxy_edit.html"

    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create or update a proxy  instance.

        - Validates form data.
        - Saves the proxy  instance and its related objects atomically.
        - Calls Zabbix API to create or update the proxy .
        - Displays error messages if external synchronization fails.
        - Redirects to the proxy list on success.

        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Either the form view with errors or a redirect to the proxy list.
        """
        obj = self.get_object( **kwargs )
        form = self.form( data=request.POST, files=request.FILES, instance=obj )

        object_created = form.instance.pk is None

        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save( commit=False )
                    instance.save()
                    form.save_m2m()

                    # Log creation or update
                    if object_created:
                        instance.create_new_proxy()
                    else:
                        instance.update_existing_proxy()

            except Exception as e:
                messages.error(request, f"Failed to create/update proxy: { str( e ) }")
                return self.get( request, *args, **kwargs )

            return redirect('plugins:netbox_zabbix:proxy_list')

        return self.get( request, *args, **kwargs )


class ProxyDeleteView(generic.ObjectDeleteView):
    """
    Delete a Zabbix Proxy instance.
    """
    queryset = Proxy.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
            """
            Handle POST request to delete a proxy instance.
            
            - Calls the instance's delete method, which may attempt to remove it from Zabbix.
            - Displays a warning message if deletion from Zabbix fails.
            - Redirects to the proxy list after deletion.
            
            Args:
                request (HttpRequest): Current HTTP request.
                *args: Additional positional arguments.
                **kwargs: Additional keyword arguments.
            
            Returns:
                HttpResponse: Redirect to the proxy list view.
            """
            obj = self.get_object( **kwargs )
            result = obj.delete()
            
            if isinstance( result, dict ) and result.get( "warning" ):
                messages.warning( request, result["message"] )
        
            return redirect( self.get_return_url( request, obj ) )


class ProxyBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple Zabbix Proxy instances.
    """
    queryset = Proxy.objects.all()
    table    = tables.ProxyTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to proxy list view.
        """
        return reverse( 'plugins:netbox_zabbix:proxy_list' )


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
            queryset = self.get_queryset( request ).filter(  pk__in=request.POST.getlist( 'pk' ) )
            
            for obj in queryset:
                try:
                    result = obj.delete()
                    if isinstance( result, dict ) and result.get( "warning" ):
                        messages.warning( request, result["message"] )
                except Exception as e:
                    messages.warning(request, f"Failed to delete {obj}: {e}")
        
            return redirect( request.GET.get( 'return_url', '/plugins/netbox_zabbix/proxy/' ) )



def run_import_proxies(request=None):
    """
    Import Zabbix proxies and optionally attach messages to the request.
    
    Args:
        request (HttpRequest, optional): Request object for messages.
    
    Returns:
        tuple: (added_proxies, deleted_proxies, error)
    """
    try:
        added, deleted = zapi.import_proxies()

        if request is not None:
            msg_lines = ["Importing Zabbix Proxies succeeded."]
            if added:
                msg_lines.append( f"Added {len( added )} prox{pluralize( len( added ), 'y,ies')}." )
            if deleted:
                msg_lines.append( f"Deleted {len( deleted )} prox{pluralize( len( deleted ), 'y,ies')}." )
            if not added and not deleted:
                msg_lines.append( "No changes detected." )
            messages.success( request, mark_safe( "<br>".join( msg_lines ) ) )
            return added, deleted, None
    
    except RuntimeError as e:
        error_msg = "Importing Zabbix Proxies failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        return None, None, e
    
    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        settings.set_connection( status=False )
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_proxies(request):
    """
    View wrapper to import proxies and redirect back.
    
    Args:
        request (HttpRequest): Triggering request.
    
    Returns:
        HttpResponseRedirect: Redirect to referring page.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxies( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------


class ProxyGroupView(generic.ObjectView):
    """
    Display a single Zabbix ProxyGroup object.
    """
    queryset = ProxyGroup.objects.all()


class ProxyGroupListView(generic.ObjectListView):
    """
    Display a list of Zabbix ProxyGroups.
    """
    queryset       = ProxyGroup.objects.all()
    filterset      = filtersets.ProxyGroupFilterSet
    filterset_form = forms.ProxyGroupFilterForm
    table          = tables.ProxyGroupTable 
    template_name  = "netbox_zabbix/proxy_group_list.html"
    

class ProxyGroupEditView(generic.ObjectEditView):
    """
    Edit a Zabbix ProxyGroup instance.
    """
    queryset = ProxyGroup.objects.all()
    form     = forms.ProxyGroupForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create or update a proxy group instance.
        
        - Validates form data.
        - Saves the proxy group instance and its related objects atomically.
        - Calls Zabbix API to create or update the proxy group.
        - Displays error messages if external synchronization fails.
        - Redirects to the proxy group list on success.
        
        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        
        Returns:
            HttpResponse: Either the form view with errors or a redirect to the proxy group list.
        """
        obj = self.get_object( **kwargs )
        form = self.form( data=request.POST, files=request.FILES, instance=obj )
        
        object_created = form.instance.pk is None
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save( commit=False )
                    instance.save()
                    form.save_m2m()
        
                    # Log creation or update
                    if object_created:
                        instance.create_new_proxy_group()
                    else:
                        instance.update_existing_proxy_group()
        
            except Exception as e:
                messages.error(request, f"Failed to create/update proxy group: {e}")
                return self.get( request, *args, **kwargs )
        
            return redirect('plugins:netbox_zabbix:proxygroup_list')
        
        return self.get( request, *args, **kwargs )


class ProxyGroupDeleteView(generic.ObjectDeleteView):
    """
    Delete a Zabbix ProxyGroup instance.
    """
    queryset = ProxyGroup.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        """
        Handle POST request to delete a proxy group instance.
        
        - Calls the instance's delete method, which may attempt to remove it from Zabbix.
        - Displays a warning message if deletion from Zabbix fails.
        - Redirects to the proxy group list after deletion.
        
        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        
        Returns:
            HttpResponse: Redirect to the proxy group list view.
        """
        obj = self.get_object( **kwargs )
        result = obj.delete()
        
        if isinstance( result, dict ) and result.get( "warning" ):
            messages.warning( request, result["message"] )
    
        return redirect( self.get_return_url( request, obj ) )


class ProxyGroupBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple Zabbix ProxyGroup instances.
    """
    queryset = ProxyGroup.objects.all()
    table    = tables.ProxyGroupTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to proxy group list view.
        """
        return reverse( 'plugins:netbox_zabbix:proxygroup_list' )


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        queryset = self.get_queryset( request ).filter(  pk__in=request.POST.getlist( 'pk' ) )
        
        for obj in queryset:
            try:
                result = obj.delete()
                if isinstance( result, dict ) and result.get( "warning" ):
                    messages.warning( request, result["message"] )
            except Exception as e:
                messages.warning(request, f"Failed to delete {obj}: {e}")
    
        return redirect( request.GET.get( 'return_url', '/plugins/netbox_zabbix/proxy-groups/' ) )


def run_import_proxy_groups(request=None):
    """
    Import Zabbix proxy groups and optionally attach messages to the request.
    
    Args:
        request (HttpRequest, optional): Request object for messages.
    
    Returns:
        tuple: (added_groups, deleted_groups, error)
    """
    try:
        added, deleted = zapi.import_proxy_groups()
        if request is not None:
            msg_lines = ["Import Zabbix Proxy Groups succeeded."]
            if added:
                msg_lines.append( f"Added {len( added )} proxy group{pluralize( len( added ) )}." )
            if deleted:
                msg_lines.append( f"Deleted {len( deleted )} proxy group{pluralize( len( deleted ) )}." )
            if not added and not deleted:
                msg_lines.append( "No changes detected." )
            messages.success( request, mark_safe( "<br>".join( msg_lines ) ) )
        return added, deleted, None

    except RuntimeError as e:
        error_msg = "Importing Zabbix Proxy Groups failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        return None, None, e
    
    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        settings.set_connection( status=False )
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_proxy_groups(request):
    """
    View wrapper to import proxy groups and redirect back.
    
    Args:
        request (HttpRequest): Triggering request.
    
    Returns:
        HttpResponseRedirect: Redirect to referring page.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxy_groups( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------


class HostGroupView(generic.ObjectView):
    """
    Display a single Zabbix HostGroup object.
    """
    queryset = HostGroup.objects.all()


class HostGroupListView(generic.ObjectListView):
    """
    Display a list of Zabbix HostGroups.
    """
    queryset  = HostGroup.objects.all()
    table     = tables.HostGroupTable
    filterset = filtersets.HostGroupFilterSet
    template_name  = "netbox_zabbix/host_group_list.html"


class HostGroupEditView(generic.ObjectEditView):
    """
    Edit a Zabbix HostGroup instance.
    """
    queryset = HostGroup.objects.all()
    form     = forms.HostGroupForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create or update a host group instance.
        
        - Validates form data.
        - Saves the host group instance and its related objects atomically.
        - Calls Zabbix API to create or update the host group.
        - Displays error messages if external synchronization fails.
        - Redirects to the host group list on success.
        
        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        
        Returns:
            HttpResponse: Either the form view with errors or a redirect to the host group list.
        """
        obj = self.get_object( **kwargs )
        form = self.form( data=request.POST, files=request.FILES, instance=obj )
        
        object_created = form.instance.pk is None
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save( commit=False )
                    instance.save()
                    form.save_m2m()
        
                    # Log creation or update
                    if object_created:
                        instance.create_new_host_group()
                    else:
                        instance.update_existing_host_group()
        
            except Exception as e:
                messages.error(request, f"Failed to create/update host group: {e}")
                return self.get( request, *args, **kwargs )
        
            return redirect('plugins:netbox_zabbix:hostgroup_list')
        
        return self.get( request, *args, **kwargs )


class HostGroupDeleteView(generic.ObjectDeleteView):
    """
    Delete a Zabbix HostGroup instance.
    """
    queryset = HostGroup.objects.all()

    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to host group list view.
        """
        return reverse( 'plugins:netbox_zabbix:hostgroup_list' )


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        """
        Handle POST request to delete a host group instance.
        
        - Calls the instance's delete method, which may attempt to remove it from Zabbix.
        - Displays a warning message if deletion from Zabbix fails.
        - Redirects to the host group list after deletion.
        
        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        
        Returns:
            HttpResponse: Redirect to the host group list view.
        """
        obj = self.get_object( **kwargs )
        result = obj.delete()
        
        if isinstance( result, dict ) and result.get( "warning" ):
            messages.warning( request, result["message"] )
    
        return redirect( self.get_return_url( request, obj ) )


class HostGroupBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple Zabbix HostGroup instances.
    """
    queryset = HostGroup.objects.all()
    table    = tables.HostGroupTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to host group list view.
        """
        return reverse( 'plugins:netbox_zabbix:hostgroup_list' )


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def post(self, request, *args, **kwargs):
        queryset = self.get_queryset( request ).filter(  pk__in=request.POST.getlist( 'pk' ) )
        
        for obj in queryset:
            try:
                result = obj.delete()
                if isinstance( result, dict ) and result.get( "warning" ):
                    messages.warning( request, result["message"] )
            except Exception as e:
                messages.warning(request, f"Failed to delete {obj}: {e}")
    
        return redirect( request.GET.get( 'return_url', '/plugins/netbox_zabbix/host-groups/' ) )


def run_import_host_groups(request=None):
    """
    Import Zabbix host groups and optionally attach messages to the request.
    
    Args:
        request (HttpRequest, optional): Request object for messages.
    
    Returns:
        tuple: (added_hostgroups, deleted_hostgroups, error)
    """
    try:
        added, deleted = zapi.import_host_groups()

        if request is not None:
            msg_lines = ["Importing Zabbix Hostgroups succeeded."]
            if added:
                msg_lines.append( f"Added {len( added )} hosgroup{ pluralize( len( added ) )}." )
            if deleted:
                msg_lines.append( f"Deleted {len( deleted )} hostgroup{ pluralize( len( deleted ) )}." )
            if not added and not deleted:
                msg_lines.append( "No changes detected." )
            messages.success( request, mark_safe( "<br>".join( msg_lines ) ) )
            return added, deleted, None
    
    except RuntimeError as e:
        error_msg = "Importing Zabbix Hostgroups failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        return None, None, e
    
    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        settings.set_connection( status=False )
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_host_groups(request):
    """
    View wrapper to import host groups and redirect back.
    
    Args:
        request (HttpRequest): Triggering request.
    
    Returns:
        HttpResponseRedirect: Redirect to referring page.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_host_groups( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingView(generic.ObjectView):
    """
    Display a single TagMapping instance.
    """
    queryset = TagMapping.objects.all()


class TagMappingListView(generic.ObjectListView):
    """
    Display a list of TagMapping instances.
    """
    queryset  = TagMapping.objects.all()
    table     = tables.TagMappingTable
    filterset = filtersets.TagMappingFilterSet


class TagMappingEditView(generic.ObjectEditView):
    """
    Edit a TagMapping instance.
    """
    queryset = TagMapping.objects.all()
    form     = forms.TagMappingForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


class TagMappingDeleteView(generic.ObjectDeleteView):
    """
    Delete a TagMapping instance.
    """
    queryset = TagMapping.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingView(generic.ObjectView):
    """
    Display a single InventoryMapping instance.
    """
    queryset = InventoryMapping.objects.all()


class InventoryMappingListView(generic.ObjectListView):
    """
    Display a list of InventoryMapping instances.
    """
    queryset  = InventoryMapping.objects.all()
    table     = tables.InventoryMappingTable
    filterset = filtersets.InventoryMappingFilterSet


class InventoryMappingEditView(generic.ObjectEditView):
    """
    Edit an InventoryMapping instance.
    """
    queryset      = InventoryMapping.objects.all()
    form          = forms.InventoryMappingForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


class InventoryMappingDeleteView(generic.ObjectDeleteView):
    """
    Delete an InventoryMapping instance.
    """
    queryset = InventoryMapping.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


def count_matching_devices_for_mapping(obj):
    """
    Count the number of devices matching a given DeviceMapping.
    
    Args:
        obj (DeviceMapping): The mapping instance.
    
    Returns:
        int: Number of matching devices.
    """
    return obj.get_matching_devices().count()


@register_model_view(DeviceMapping, 'devices')
class DeviceMappingDevicesView(generic.ObjectView):
    """
    Display devices matching a DeviceMapping in a dedicated tab.
    """
    queryset      = DeviceMapping.objects.all()
    template_name = 'netbox_zabbix/devicemapping_devices.html'
    tab           = ViewTab( label="Matching Devices",
                             badge=lambda obj: count_matching_devices_for_mapping( obj ),
                             weight=500 )

    def get_extra_context(self, request, instance):
        """
        Prepare extra context with matching devices.
        
        Args:
            request (HttpRequest): Current request.
            instance (DeviceMapping): The mapping instance.
        
        Returns:
            dict: Context with related devices list and counts.
        """
        queryset = instance.get_matching_devices()
        table    = tables.MatchingDeviceMappingTable( queryset )
        RequestConfig( request,
            {
                "paginator_class": EnhancedPaginator,
                "per_page":        get_paginate_count(request),
            }
         ).configure( table )
            
        return { "table": table }


class DeviceMappingView(generic.ObjectView):
    """
    Display a single DeviceMapping instance with related devices.
    """
    queryset = DeviceMapping.objects.all()
    
    def get_extra_context(self, request, instance):
        """
        Prepare extra context with matching devices.
        
        Args:
            request (HttpRequest): Current request.
            instance (DeviceMapping): The mapping instance.
        
        Returns:
            dict: Context with related devices list and counts.
        """
        devices = instance.get_matching_devices()
        return {
            "related_devices": [
                {
                    "queryset": devices,
                    "label":   "Devices",
                    "count":   devices.count()
                }
            ]
        }


class DeviceMappingListView(generic.ObjectListView):
    """
    Display a list of DeviceMapping instances.
    """
    queryset  = DeviceMapping.objects.all()
    table     = tables.DeviceMappingTable
    filterset = filtersets.DeviceMappingFilterSet


class DeviceMappingEditView(generic.ObjectEditView):
    """
    Edit a DeviceMapping instance.
    """
    queryset      = DeviceMapping.objects.all()
    form          = forms.DeviceMappingForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


class DeviceMappingDeleteView(generic.ObjectDeleteView):
    """
    Delete a DeviceMapping instance.
    Prevents deletion if the mapping is marked as default.
    """
    queryset = DeviceMapping.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()



    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to device mapping list view.
        """
        return reverse( 'plugins:netbox_zabbix:devicemapping_list' )

    def post(self, request, *args, **kwargs):
        """
        Handle deletion request.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirect with error if default mapping, otherwise normal deletion.
        """
        obj = self.get_object( **kwargs )
    
        if obj.default:
            messages.error( request, "You cannot delete the default mapping." )
            return redirect('plugins:netbox_zabbix:devicemapping_list' )
    
        return super().post( request, *args, **kwargs )


class DeviceMappingBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple DeviceMapping instances.
    Prevents deletion of default mappings.
    """
    queryset        = DeviceMapping.objects.all()
    filterset_class = filtersets.DeviceMappingFilterSet
    table           = tables.DeviceMappingTable


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()



    def post(self, request, *args, **kwargs):
        """
        Handle bulk deletion, checking for default mappings.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirect with error if default mapping included, otherwise proceeds.
        """
        # Determine which objects are being deleted
        selected_pks = request.POST.getlist( 'pk' )
        mappings     = Mapping.objects.filter( pk__in=selected_pks )
    
        # Check if any default mappings are included
        default_mappings = mappings.filter( default=True )
        if default_mappings.exists():
            names = ", ".join( [m.name for m in default_mappings] )
            messages.error( request, f"Cannot delete default mapping: {names}" )
            return redirect( 'plugins:netbox_zabbix:devicemapping_list' )
    
        # No default mappings selected, proceed with normal deletion
        return super().post( request, *args, **kwargs )
    

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to device mapping list view.
        """
        return reverse( 'plugins:netbox_zabbix:devicemapping_list' )


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


def count_matching_vms_for_mapping(obj):
    """
    Count the number of virtual machines matching a given VMMapping.
    
    Args:
        obj (VMMapping): The mapping instance.
    
    Returns:
        int: Number of matching VMs.
    """
    return obj.get_matching_virtual_machines().count()


@register_model_view(VMMapping, 'vms')
class VMMappingVMsView(generic.ObjectView):
    """
    Display VMs matching a VMMapping in a dedicated tab.
    """
    queryset      = VMMapping.objects.all()
    template_name = 'netbox_zabbix/vmmapping_vms.html'
    tab           = ViewTab( label="Matching VMs",
                             badge=lambda obj: count_matching_vms_for_mapping( obj ),
                             weight=500 )
    
    def get_extra_context(self, request, instance):
        """
        Prepare table of matching VMs for the tab view.
        
        Args:
            request (HttpRequest): Current request.
            instance (VMMapping): The mapping instance.
        
        Returns:
            dict: Context with the table of matching VMs.
        """
        queryset = instance.get_matching_virtual_machines()
        table    = tables.MatchingVMMappingTable( queryset )
        RequestConfig( request,
            {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
         ).configure( table )
            
        return {
            "table": table,
        }


class VMMappingView(generic.ObjectView):
    """
    Display a single VMMapping instance with related VMs.
    """
    queryset      = VMMapping.objects.all()
    
    def get_extra_context(self, request, instance):
        """
        Prepare extra context with matching VMs.
        
        Args:
            request (HttpRequest): Current request.
            instance (VMMapping): The mapping instance.
        
        Returns:
            dict: Context with related VMs list and counts.
        """
        vms = instance.get_matching_virtual_machines()

        return {
            "related_vms": [
                {
                    "queryset": vms,
                    "label": "Virtual Machines",
                    "count": vms.count()
                }
            ]
        }


class VMMappingListView(generic.ObjectListView):
    """
    Display a list of VMMapping instances.
    """
    queryset  = VMMapping.objects.all()
    table     = tables.VMMappingTable
    filterset = filtersets.VMMappingFilterSet


class VMMappingEditView(generic.ObjectEditView):
    """
    Edit a VMMapping instance.
    """
    queryset      = VMMapping.objects.all()
    form          = forms.VMMappingForm


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


class VMMappingDeleteView(generic.ObjectDeleteView):
    """
    Delete a VMMapping instance.
    
    Prevents deletion if the mapping is marked as default.
    """
    queryset = VMMapping.objects.all()


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()


    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to VM mapping list view.
        """
        return reverse( 'plugins:netbox_zabbix:vmmapping_list' )


    def post(self, request, *args, **kwargs):
        """
        Handle deletion request.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirect with error if default mapping, otherwise normal deletion.
        """
        obj = self.get_object( **kwargs )
    
        if obj.default:
            messages.error( request, "You cannot delete the default mapping." )
            return redirect( 'plugins:netbox_zabbix:vmmapping_list' )
    
        return super().post( request, *args, **kwargs )


class VMMappingBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple VMMapping instances.
    Prevents deletion of default mappings.
    """
    queryset        = VMMapping.objects.all()
    filterset_class = filtersets.VMMappingFilterSet
    table           = tables.VMMappingTable


    def dispatch(self, request, *args, **kwargs):
        """
        Controls access to the view based on the user's NetBox-Zabbix plugin permissions.
        
        This method overrides the default `dispatch` to enforce plugin-level access control.
        Only users with the `view_zabbixadminpermission` permission can access the view.
        
        Behavior:
        - If the user has the permission `netbox_zabbix.view_zabbixadminpermission`,
          the request proceeds normally by calling the parent `dispatch`.
        - If the user lacks the permission, a `PermissionDenied` exception is raised,
          resulting in a 403 Forbidden response in the UI.
        """
        
        if has_any_model_permission( request.user, "netbox_zabbix", "zabbixadminpermission" ):
            return super().dispatch( request, *args, **kwargs )
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()



    def post(self, request, *args, **kwargs):
        """
        Handle bulk deletion, checking for default mappings.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirect with error if default mapping included, otherwise proceeds.
        """
        # Determine which objects are being deleted
        selected_pks = request.POST.getlist( 'pk' )
        mappings     = Mapping.objects.filter( pk__in=selected_pks )
    
        # Check if any default mappings are included
        default_mappings = mappings.filter( default=True )
        if default_mappings.exists():
            names = ", ".join( [m.name for m in default_mappings] )
            messages.error( request, f"Cannot delete default mapping: {names}" )
            return redirect('plugins:netbox_zabbix:vmmapping_list' )
    
        # No default mappings selected, proceed with normal deletion
        return super().post(request, *args, **kwargs)
    

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to VM mapping list view.
        """
        return reverse( 'plugins:netbox_zabbix:vmmapping_list' )


# ------------------------------------------------------------------------------
# Get Instance from ConfigContext and Object ID
# ------------------------------------------------------------------------------


def get_instance_from_ct_and_pk(content_type_id, instance_id):
    """
    Retrieve a model instance from content_type_id and instance ID.
    
    Args:
        content_type_id (int): ID of the ContentType.
        instance_id (int): Primary key of the model instance.
    
    Returns:
        Model instance corresponding to the content type and ID.
    
    Raises:
        ValueError: If content type or instance does not exist.
    """
    try:
        content_type = ContentType.objects.get(id=content_type_id)
    except ContentType.DoesNotExist:
        raise ValueError(f"Invalid content type id: {content_type_id}")

    model_class = content_type.model_class()
    if model_class is None:
        raise ValueError(f"Content type {content_type_id} has no associated model")

    try:
        return model_class.objects.get(id=instance_id)
    except model_class.DoesNotExist:
        raise ValueError(f"No instance with id={instance_id} for model {model_class.__name__}")


# ------------------------------------------------------------------------------
# QuerySet Wrapper
# ------------------------------------------------------------------------------


class CombinedHostsQuerySet(list):
    """
    Minimal wrapper to combine Device and VM objects into a QuerySet-like structure.
    Compatible with NetBox ObjectListView.
    """

    def __init__(self, iterable, model):
        """
        Initialize the combined queryset.
        
        Args:
            iterable (iterable): List of objects to wrap.
            model (Model): Model class for permission checks.
        """
        super().__init__( iterable )
        self.model = model  # e.g. Device, required for permission checks

    def restrict(self, user, action):
        """
        Mimic QuerySet restrict method (permission filtering).
        
        Returns:
            CombinedHostsQuerySet: Self, permission filtering ignored.
        """
        # Permission filtering not relevant for synthetic union view
        return self

    def exists(self):
        """
        Mimic QuerySet.exists().
        
        Returns:
            bool: True if list is not empty.
        """
        return bool( self )

    def count(self):
        """
        Mimic QuerySet.count().
        
        Returns:
            int: Number of items.
        """
        return len( self )

    def all(self):
        """
        Mimic QuerySet.all().
        
        Returns:
            CombinedHostsQuerySet: Self.
        """        
        # For compatibility with methods expecting .all()
        return self

    def __getitem__(self, key):
        """
        Support indexing and slicing.
        
        Returns:
            CombinedHostsQuerySet or single item.
        """
        # Slicing and indexing
        result = super().__getitem__( key )
        if isinstance( key, slice ):
            # Preserve type on slices
            return CombinedHostsQuerySet( result, self.model )
        return result


# ------------------------------------------------------------------------------
# Host Config
# ------------------------------------------------------------------------------


class HostConfigView(generic.ObjectView):
    """
    Display a single HostConfig instance with Zabbix problems.
    """
    queryset = HostConfig.objects.all()

    def get_extra_context(self, request, instance):
        """
        Prepare extra context including web address and Zabbix problems table.
        
        Args:
            request (HttpRequest): Current request.
            instance (HostConfig): HostConfig instance.
        
        Returns:
            dict: Context for template rendering.
        """
        super().get_extra_context( request, instance )
        web_address = settings.get_zabbix_web_address()
        problems = []
        table = None
        try:
            problems = zapi.get_problems( instance.assigned_object.name )
        except:
            pass
        table = tables.ZabbixProblemTable( problems )
        return { "web_address":  web_address, "table": table }


class HostConfigListView(generic.ObjectListView):
    """
    Display a list of HostConfig instances.
    """
    queryset  = HostConfig.objects.all()
    table     = tables.HostConfigTable
    filterset = filtersets.HostConfigFilterSet


    template_name = "netbox_zabbix/host_config_list.html"
    
    def get_queryset(self, request):
        qs = super().get_queryset( request )
    
        # Check toggle
        if self.request.GET.get( "filtered" ) == "1":
            qs = qs.filter( in_sync=False )
    
        return qs

    def get_extra_context(self, request):
        return { "filtered": self.request.GET.get( "filtered" ) == "1" }


class HostConfigEditView(generic.ObjectEditView):
    """
    Edit a HostConfig instance.
    """
    queryset = HostConfig.objects.all()
    form     = forms.HostConfigForm
    template_name = "netbox_zabbix/hostconfig_edit.html"


    def dispatch(self, request, *args, **kwargs):
        """
        Intercept the request before it reaches form handling to prevent editing.
        
        If the HostConfig instance is currently under any active maintenance window,
        the user is redirected back to the listing view with a warning message. 
        
        Args:
            request (HttpRequest): The current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        
        Returns:
            HttpResponse: Either a redirect response if editing is disallowed, 
                          or proceeds to the normal dispatch if allowed.
        """
        obj = self.get_object( **kwargs )
    
        # Prevent editing if the host is in active maintenance
        if obj.in_maintenance:
            active_maintenances = ", ".join( [m.name for m in obj.active_maintenances] )
            messages.warning( request, f"HostConfig '{obj.name}' is currently under maintenance: {active_maintenances}. Editing is not allowed." )
            return redirect( self.get_return_url( request, obj ) )
    
        return super().dispatch( request, *args, **kwargs )


    def alter_object(self, obj, request, args, kwargs):
        obj._request = request
        return obj


class HostConfigDeleteView(generic.ObjectDeleteView):
    """
    Delete a HostConfig instance.
    """
    queryset = HostConfig.objects.all()
    lookup_field = "pk" 


    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to HostConfig list view.
        """
        return reverse( 'plugins:netbox_zabbix:hostconfig_list' )


    def post(self, request, *args, **kwargs):
        obj = self.get_object( **kwargs )
    
        # Prevent deletion if the host is in active maintenance
        if obj.in_maintenance:
            active_maintenances = ", ".join( [m.name for m in obj.active_maintenances] )
            messages.warning( request, f"HostConfig '{obj.name}' is currently under maintenance: {active_maintenances}. It cannot be deleted." )
            return redirect( self.get_return_url( request, obj ) )
    
        # Proceed with deletion
        obj_name = str( obj )
        obj.delete()
        messages.success( request, f"HostConfig '{obj_name}' deleted successfully." )
        return redirect( self.get_return_url( request, obj ) )


class HostConfigBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple HostConfig instances.
    """
    queryset = HostConfig.objects.all()
    table    = tables.HostConfigTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to HostConfig list view.
        """
        return reverse( 'plugins:netbox_zabbix:hostconfig_list' )

    def post(self, request, *args, **kwargs):
        queryset = self.get_queryset( request ).filter( pk__in=request.POST.getlist( "pk" ) )
    
        for obj in queryset:
            if obj.in_maintenance:
                active_maintenances = ", ".join( [m.name for m in obj.active_maintenances] )
                messages.warning( request, f"HostConfig '{obj.name}' is currently under maintenance: {active_maintenances}. It cannot be deleted." )
            else:
                obj_name = str( obj )
                obj.delete( request=request )
                messages.success( request, f"HostConfig '{obj_name}' deleted successfully." )
    
        return redirect(request.GET.get("return_url", "/plugins/netbox_zabbix/host-config/"))


def update_sync_status(request):
    """
    View wrapper to sync hosts in NetBox with hosts in Zabbix.
    
    Args:
        request (HttpRequest): Triggering request.
    
    Returns:
        HttpResponseRedirect: Redirect to referring page.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )

    try:
        result  = SystemJobHostConfigSyncRefresh.run( cutoff=0 )
        total   = result.get( "total", 0 )
        updated = result.get( "updated", 0 )
        failed  = result.get( "failed", 0 )
        messages.success( request,  mark_safe( f"Total: {total} Updated: {updated} Failed: {failed}" ) )
    except Exception as e:
        msg = f"Failed to update sync status: {str(e)}"
        messages.error( request, msg )
        logger.error( msg )

    return redirect( redirect_url )


def sync_all(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )

    try:
        # Pass result container to job via kwargs
        result = SyncHostsNow.run_now( user=request.user, name="Sync all hosts now"  )
        messages.success( request,  mark_safe( result ) )

    except Exception as e:
        msg = f"Failed to sync NetBox hosts with Zabbix: {str(e)}"
        messages.error( request, msg )
        logger.error( msg )

    return redirect( redirect_url )


# --------------------------------------------------------------------------
# Agent Interface
# --------------------------------------------------------------------------


class AgentInterfaceView(generic.ObjectView):
    """
    Display a single AgentInterface instance and check its availability.
    """
    queryset = AgentInterface.objects.all()

    def get_extra_context(self, request, instance):
        """
        Add extra context with interface availability.
        
        Args:
            request (HttpRequest): Current request.
            instance (AgentInterface): Instance to display.
        
        Returns:
            dict: Contains 'available' status of the interface.
        """
        super().get_extra_context( request, instance )
        available = None
        try:
           available = is_interface_available( instance )
        except:
            pass
        return { "available":  available }


class AgentInterfaceListView(generic.ObjectListView):
    """
    Display a list of all AgentInterface instances with table and filters.
    """
    queryset      = AgentInterface.objects.all()
    table         = tables.AgentInterfaceTable
    filterset     = filtersets.AgentInterfaceFilterSet
    template_name = 'netbox_zabbix/agent_interface_list.html'


class AgentInterfaceEditView(generic.ObjectEditView):
    """
    Edit an existing AgentInterface instance using a form.
    """
    queryset      = AgentInterface.objects.all()
    form          = forms.AgentInterfaceForm
    template_name = 'netbox_zabbix/agent_interface_edit.html'


class AgentInterfaceDeleteView(generic.ObjectDeleteView):
    """
    Delete a single AgentInterface instance if not linked to Zabbix templates.
    """
    queryset = AgentInterface.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Handle deletion of an AgentInterface instance.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirects either on success or with error message if deletion is blocked.
        """
        interface = self.get_object( pk=kwargs.get( "pk" ) )
    
        if can_delete_interface( interface ):
            return super().post( request, *args, **kwargs )
        else:
            messages.error( request, f"Interface '{interface.name}' cannot be deleted because it is linked to one or more templates in Zabbix." )
            return redirect( request.POST.get( 'return_url' ) or interface.host_config.get_absolute_url() )


class AgentInterfaceBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple AgentInterface instances.
    
    Prevents deletion of interfaces linked to Zabbix templates.
    """
    queryset = AgentInterface.objects.all()
    table    = tables.AgentInterfaceTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to AgentInterface list view.
        """
        return reverse( 'plugins:netbox_zabbix:agentinterface_list' )
    
    def post(self, request, *args, **kwargs):
        """
        Handle bulk deletion, checking that none of the interfaces are linked to Zabbix templates.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirects with error if deletion is blocked; otherwise proceeds.
        """
        # Get the list of interfaces to be deleted
        interfaces = self.get_queryset( request ).filter( pk__in=request.POST.getlist( 'pk' ) )
    
        for interface in interfaces:
            if not can_delete_interface( interface ):
                messages.error( request, f"Interface '{interface.name}' cannot be deleted because it is linked to one or more templates in Zabbix." )
                return redirect( self.get_return_url( request ) )
    
        # If all checks pass, proceed with normal bulk deletion
        return super().post( request, *args, **kwargs )


# --------------------------------------------------------------------------
# SNMP Interface
# --------------------------------------------------------------------------


class SNMPInterfaceView(generic.ObjectView):
    """
    Display a single SNMPInterface instance.
    """
    queryset = SNMPInterface.objects.all()


class SNMPInterfaceListView(generic.ObjectListView):
    """
    List all SNMPInterface instances with table and filters.
    """
    queryset      = SNMPInterface.objects.all()
    table         = tables.SNMPInterfaceTable
    filterset     = filtersets.SNMPInterfaceFilterSet
    template_name = 'netbox_zabbix/snmp_interface_list.html'


class SNMPInterfaceEditView(generic.ObjectEditView):
    """
    Edit an existing SNMPInterface instance using a form.
    """
    queryset      = SNMPInterface.objects.all()
    form          = forms.SNMPInterfaceForm
    template_name = 'netbox_zabbix/snmp_interface_edit.html'


class SNMPInterfaceDeleteView(generic.ObjectDeleteView):
    """
    Delete a single SNMPInterface instance if not linked to Zabbix templates.
    """
    queryset = SNMPInterface.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Handle deletion of an SNMPInterface instance.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirects either on success or with error message if deletion is blocked.
        """
        interface = self.get_object( pk=kwargs.get( "pk" ) )
    
        if can_delete_interface( interface ):
            return super().post( request, *args, **kwargs )
        else:
            messages.error( request, f"Interface '{interface.name}' cannot be deleted because it is linked to one or more templates in Zabbix." )
            return redirect( request.POST.get( 'return_url' ) or interface.host_config.get_absolute_url() )


class SNMPInterfaceBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple SNMPInterface instances.
    Prevents deletion of interfaces linked to Zabbix templates.
    """
    queryset = SNMPInterface.objects.all()
    table    = tables.SNMPInterfaceTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after bulk deletion.
        
        Returns:
            str: URL to SNMPInterface list view.
        """
        return reverse( 'plugins:netbox_zabbix:snmpinterface_list' )


    def post(self, request, *args, **kwargs):
        """
        Handle bulk deletion, checking that none of the interfaces are linked to Zabbix templates.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirects with error if deletion is blocked; otherwise proceeds.
        """
        # Get the list of interfaces to be deleted
        interfaces = self.get_queryset( request ).filter( pk__in=request.POST.getlist( 'pk' ) )
    
        for interface in interfaces:
            if not can_delete_interface( interface ):
                messages.error( request, f"Interface '{interface.name}' cannot be deleted because it is linked to one or more templates in Zabbix." )
                return redirect( self.get_return_url( request ) )
    
        # If all checks pass, proceed with normal bulk deletion
        return super().post( request, *args, **kwargs )


# --------------------------------------------------------------------------
# Maintenance
# --------------------------------------------------------------------------


class MaintenanceView(generic.ObjectView):
    """
    Detail view for a single Zabbix Maintenance.
    """
    queryset = Maintenance.objects.all()


class MaintenanceListView(generic.ObjectListView):
    """
    Display a list of Zabbix Maintenance windows.
    """
    queryset = Maintenance.objects.all()
    #filterset = NetBoxModelFilterSetForm
    table = tables.MaintenanceTable
    template_name = "netbox_zabbix/maintenance_list.html"


class MaintenanceEditView(generic.ObjectEditView):
    """
    Create or edit a Zabbix Maintenance window.

    Note: Maintenance windows cannot be created from NetBox scripts since
    the create_maintenance_window() is called from the post method 

    """
    queryset = Maintenance.objects.all()
    form = forms.MaintenanceForm


    def alter_object(self, obj, request, args, kwargs):
        """
        Called before rendering the form.

        Sets a default unique name for new objects based on the current user.

        Note:
            NetBox's ObjectEditView does not pass the current user to the form __init__,
            and does not call get_form or get_form_kwargs in a way we can intercept
            for new objects. Therefore, we override `alter_object` to inject the
            username directly into the model instance before the form is rendered.
        """
        user = getattr( self.request, 'user', None )

        if user and user.is_authenticated:
            obj._current_user = user

        if obj.pk is None and user and user.is_authenticated:
            base_name = f"{user.username}-maintenance"
            name = base_name
            counter = 0

            # Keep incrementing until we find a unique name
            while Maintenance.objects.filter( name=name ).exists():
                counter += 1
                name = f"{base_name}-{counter}"

            obj.name = name

        return obj


    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create or update a Maintenance instance.

        - Validates form data.
        - Saves the Maintenance instance and its related objects atomically.
        - Calls Zabbix API to create or update the maintenance window.
        - Displays error messages if external synchronization fails.
        - Redirects to the maintenance list on success.

        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Either the form view with errors or a redirect to the maintenance list.
        """
        obj = self.get_object( **kwargs )

        # Inject the current user into the instance for use in the form
        if not hasattr( obj, "_current_user" ):
            obj._current_user = request.user

        form = self.form(data=request.POST, files=request.FILES, instance=obj)

        object_created = form.instance.pk is None

        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save( commit=False )
                    instance.save()
                    form.save_m2m()

                    # Log creation or update
                    if object_created:
                        instance.create_maintenance_window()
                    else:
                        instance.update_maintenance_window()

            except Exception as e:
                messages.error(request, f"Failed to sync with external system: {e}")
                return self.get( request, *args, **kwargs )

            return redirect('plugins:netbox_zabbix:maintenance_list')

        return self.get( request, *args, **kwargs )


class MaintenanceDeleteView(generic.ObjectDeleteView):
    """
    Delete a Zabbix Maintenance window.
    """
    queryset = Maintenance.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Handle POST request to delete a Maintenance instance.

        - Calls the instance's delete method, which may attempt to remove it from Zabbix.
        - Displays a warning message if deletion from Zabbix fails.
        - Redirects to the maintenance list after deletion.

        Args:
            request (HttpRequest): Current HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Redirect to the maintenance list view.
        """
        obj = self.get_object( **kwargs )
        result = obj.delete()
        
        if isinstance( result, dict ) and result.get( "warning" ):
            messages.warning( request, result["message"] )
    
        return redirect( self.get_return_url( request, obj ) )


class MaintenanceBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple Maintenance instances.
    """
    queryset = Maintenance.objects.all()
    table    = tables.MaintenanceTable
    
    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to EventLog list view.
        """
        return reverse( 'plugins:netbox_zabbix:maintenance_list' )


    def post(self, request, *args, **kwargs):
        queryset = self.get_queryset( request ).filter(  pk__in=request.POST.getlist( 'pk' ) )
        
        for obj in queryset:
            try:
                result = obj.delete()
                if isinstance( result, dict ) and result.get( "warning" ):
                    messages.warning( request, result["message"] )
            except Exception as e:
                messages.warning(request, f"Failed to delete {obj}: {e}")

        return redirect( request.GET.get( 'return_url', '/plugins/netbox_zabbix/maintenance/' ) )


@register_model_view(Maintenance, 'host_configs')
class MaintenanceHostConfigsView(generic.ObjectView):
    """
    Display HostConfigs that match a Maintenance instance in a dedicated tab.
    """
    queryset      = Maintenance.objects.all()
    template_name = 'netbox_zabbix/maintenance_hostconfigs.html'
    tab           = ViewTab(
        label="Matching Host Configs",
        badge=lambda obj: obj.get_matching_host_configs().count(),
        weight=500
    )

    def get_extra_context(self, request, instance):
        """
        Prepare extra context with matching HostConfigs.

        Args:
            request (HttpRequest): Current request.
            instance (Maintenance): The Maintenance instance.

        Returns:
            dict: Context containing the table of matching HostConfigs.
        """
        queryset = instance.get_matching_host_configs()
        table    = tables.HostConfigTable( queryset )
        RequestConfig(
            request,
            {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
        ).configure(table)
        return { "table": table }


# --------------------------------------------------------------------------
# Importable Hosts
# --------------------------------------------------------------------------


class ImportableHostsListView(generic.ObjectListView):
    """
    Display hosts available for import from Zabbix that are not yet linked in NetBox.
    """
    table         = tables.ImportableHostsTable
    template_name = "netbox_zabbix/importable_hosts_list.html"


    def get_extra_context(self, request):
        """
        Provide extra context for the template, e.g., whether to show the validate button.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            dict: Contains 'validate_button' flag.
        """
        super().get_extra_context( request )
        return { "validate_button": not settings.get_auto_validate_importables() }


    def get_queryset(self, request):
        """
         Retrieve the list of importable hosts filtered by query and already existing NetBox entries.
        
         Args:
             request (HttpRequest): Current request.
        
         Returns:
             CombinedHostsQuerySet: Filtered list of Devices and VMs available for import.
         """
        query = request.GET.get("q", "").strip().lower()

        try:
            zabbix_hostnames = zapi.get_cached_zabbix_hostnames()
        except Exception as e:
            messages.error( request, f"Error fetching hostnames from Zabbix: {e}" )
            zabbix_hostnames = []

        device_ct = ContentType.objects.get_for_model( Device )
        devices   = ( Device.objects.filter( name__in=zabbix_hostnames ).exclude( 
                      id__in= HostConfig.objects.filter( content_type=device_ct ).values_list( "object_id", flat=True ) ) )

        vm_ct = ContentType.objects.get_for_model( VirtualMachine )
        vms = ( VirtualMachine.objects.filter( name__in=zabbix_hostnames ).exclude(
               id__in= HostConfig.objects.filter( content_type=vm_ct ).values_list( "object_id", flat=True ) ) )

        # Record the host and content types.
        for d in devices:
            d.content_type = device_ct.id
            d.host_type = "Device"
        for v in vms:
            v.content_type = vm_ct.id
            v.host_type = "VirtualMachine"
        
        combined = list( chain( devices, vms ) )

        if query:
            combined = [
                 obj for obj in combined
                 if (
                     query in obj.name.lower()
                     or (obj.site and query in obj.site.name.lower())
                     or query in obj.host_type.lower()
                 )
             ]

        return CombinedHostsQuerySet( combined, Device )


    def post( self, request, *args, **kwargs ):
        """
        Handle actions triggered by the user on importable hosts, including validation and import jobs.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirect back to the same page or provided return_url.
        """
        # Validate Host
        if '_validate_host' in request.POST:
            selected_hosts = request.POST.getlist( 'pk' )

            if not selected_hosts:
                messages.error( request, "Please select a Device or VM to validate." )
    
            elif len( selected_hosts ) > 1:
                messages.error( request, "Only one Device or VM can be validated at a time." )
    
            else:
                try:
                    host_identifier = selected_hosts[0]
                    pk, content_type_id = host_identifier.split( ":" )
                    instance = get_instance_from_ct_and_pk( content_type_id, pk )
                    result = ValidateHost.run_now(
                        instance=instance,
                        request=request,
                        name=f"Validate {instance.name}"
                    )
                    messages.success( request, result )
                except Exception as e:
                    messages.error( request, str( e ) )
    
        # Import Host from Zabbix
        if '_import_host_from_zabbix' in request.POST:
            selected_hosts = request.POST.getlist( 'pk' )
            success_counter = 0
            max_success_messages = settings.get_max_success_notifications()
    
            if not selected_hosts:
                messages.warning( request, "Please select a Device or VM to import." )
    
            else:
                for host_identifier in selected_hosts:
                    try:
                        pk, content_type_id = host_identifier.split( ":" )
                        instance = get_instance_from_ct_and_pk( content_type_id, pk )
                        job = ImportHost.run_job( instance=instance, request=request )
    
                        message = mark_safe(
                            f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> '
                            f'to import {instance.name} from Zabbix'
                        )
    
                        if success_counter < max_success_messages:
                            messages.success( request, message )
                            success_counter += 1
    
                    except Exception as e:
                        msg = f"Failed to queue import job for '{instance.name}' from Zabbix: {str( e )}"
                        messages.error( request, msg )
                        logger.error( msg )
    
        return redirect( request.POST.get( 'return_url' ) or request.path )


# --------------------------------------------------------------------------
# NetBox Only Hosts
# --------------------------------------------------------------------------


class NetBoxOnlyHostsView(generic.ObjectListView):
    """
    Display NetBox hosts that do not exist in Zabbix, with options for quick add and validation.
    """
    table = tables.NetBoxOnlyHostsTable
    template_name = "netbox_zabbix/netbox_only_hosts_list.html"


    def get_extra_context(self, request):
        """
        Provide extra context for the template, e.g., whether to show the validate button.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            dict: Contains 'validate_button' flag.
        """
        super().get_extra_context( request )
        return { "validate_button": not settings.get_auto_validate_quick_add() }
    

    def get_queryset(self, request):
        """
        Retrieve NetBox-only hosts, optionally filtered by search query.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            CombinedHostsQuerySet: List of Devices and VMs filtered by query and exclusions.
        """
        query = request.GET.get("q", "").strip().lower()
        
        try:
            zabbix_hostnames = zapi.get_cached_zabbix_hostnames()
        except Exception as e:
            messages.error( request, f"Error fetching hostnames from Zabbix: {e}" )
            zabbix_hostnames = []

        device_ct = ContentType.objects.get_for_model( Device )
        devices = (
            Device.objects.exclude( name__in=zabbix_hostnames )
            .select_related( "site", "role", "platform" )
            .prefetch_related( "tags" )
        )

        vm_ct = ContentType.objects.get_for_model( VirtualMachine )
        vms = (
            VirtualMachine.objects.exclude( name__in=zabbix_hostnames )
            .select_related( "site", "role", "platform" )
            .prefetch_related( "tags" )
        )

        if settings.get_exclude_custom_field_enabled():
            cf_name = settings.get_exclude_custom_field_name()
            filter_kwargs = { f"custom_field_data__{cf_name}": True }
            devices = devices.exclude( **filter_kwargs )
            vms = vms.exclude( **filter_kwargs )

        # Annotate type
        for d in devices:
            d.content_type = device_ct.id
            d.host_type = "Device"
        for v in vms:
            v.content_type = vm_ct.id
            v.host_type = "VirtualMachine"

        combined = list( chain( devices, vms ) )
        self.device_mapping_cache = self.build_mapping_cache( devices, host_type="Device" )
        self.vm_mapping_cache = self.build_mapping_cache( vms, host_type="VM" )
       
        if query:
            combined = [
                 obj for obj in combined
                 if (
                     query in obj.name.lower()
                     or (obj.site and query in obj.site.name.lower())
                     or query in obj.host_type.lower()
                 )
             ]
        
        return CombinedHostsQuerySet( combined, Device )


    def build_mapping_cache(self, queryset, host_type):
        """
        Build mapping cache for hosts based on sites, roles, and platforms.
        
        Args:
            queryset (QuerySet): List of hosts (Devices or VMs).
            host_type (str): 'Device' or 'VM'.
        
        Returns:
            dict: Mapping cache keyed by (host_id, interface_type) -> mapping object.
        """
        cache = {}
    
        if host_type == "Device":
            all_mappings = DeviceMapping.objects.prefetch_related( "sites", "roles", "platforms" )
        else:
            all_mappings = VMMapping.objects.prefetch_related( "sites", "roles", "platforms" )
    
        # Convert to dicts for fast matching
        mappings = []
        for m in all_mappings:
            mappings.append({
                "obj":            m,
                "default":        m.default,
                "interface_type": m.interface_type,
                "sites":          set( m.sites.values_list( "id", flat=True ) ),
                "roles":          set( m.roles.values_list( "id", flat=True ) ),
                "platforms":      set( m.platforms.values_list( "id", flat=True ) ),
            })
    
        for host in queryset:
            site_id = host.site_id
            role_id = host.role_id
            platform_id = host.platform_id
    
            for intf_type in [ InterfaceTypeChoices.Agent, InterfaceTypeChoices.SNMP ]:
                mapping = self._find_best_mapping( site_id, role_id, platform_id, intf_type, mappings )
                cache[(host.pk, intf_type)] = mapping
    
        return cache


    def _find_best_mapping(self, site_id, role_id, platform_id, intf_type, mappings):
        """
        Determine the best mapping for a host based on site, role, platform, and interface type.
        
        Args:
            site_id (int): Site ID of the host.
            role_id (int): Role ID of the host.
            platform_id (int): Platform ID of the host.
            intf_type (str): Interface type (Agent/SNMP).
            mappings (list): List of mapping dicts to evaluate.
        
        Returns:
            Mapping: Best-matching mapping object or default if none match.
        """
        candidates = [
            m for m in mappings
            if not m["default"] and (m["interface_type"] == intf_type or m["interface_type"] == InterfaceTypeChoices.Any)
        ]
    
        def matches(m):
            """
            Check if a mapping matches the host's site, role, and platform.
            
            Args:
                m (dict): A mapping dictionary containing 'sites', 'roles', 'platforms' sets.
            
            Returns:
                bool: True if the host matches the mapping's site, role, and platform constraints; otherwise False.
            """
            site_ok = not m["sites"] or site_id in m["sites"]
            role_ok = not m["roles"] or role_id in m["roles"]
            platform_ok = not m["platforms"] or platform_id in m["platforms"]
            return site_ok and role_ok and platform_ok
    
        matched = [m for m in candidates if matches(m)]
    
        if matched:
            # Most specific: more filters first
            matched.sort( key=lambda m: (bool( m["sites"] ), bool( m["roles"] ), bool( m["platforms"] )), reverse=True )
            return matched[0]["obj"]
    
        # fallback default
        for m in mappings:
            if m["default"]:
                return m["obj"]
        return None


    def get_table(self, queryset, request, has_bulk_actions):
        """
        Attach mapping cache to table before rendering.
        
        Args:
            queryset (QuerySet): Queryset to display in table.
            request (HttpRequest): Current request.
            has_bulk_actions (bool): Whether table supports bulk actions.
        
        Returns:
            Table: Configured table with mapping caches attached.
        """
        table = super().get_table( queryset, request, has_bulk_actions )
        table.device_mapping_cache = getattr( self, "device_mapping_cache", {} )
        table.vm_mapping_cache     = getattr( self, "vm_mapping_cache", {} )
        
        return table


    def post(self, request, *args, **kwargs):
        """
        Handle validation and quick-add operations for NetBox-only hosts.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            HttpResponseRedirect: Redirect back to the same page or provided return_url.
        """
        if "_validate_quick_add" in request.POST:
            selected_hosts = request.POST.getlist( 'pk' )
        
            if not selected_hosts:
                messages.error( request, "Please select a Device or VM to validate." )

            else:
                for host_identifier in selected_hosts:
                    try:
                        pk, content_type_id = host_identifier.split( ":" )
                        host = get_instance_from_ct_and_pk( content_type_id, pk )
                        validate_quick_add( host )
                        messages.success( request, f"{host.name} is valid." )
                    except Exception as e:
                        messages.error( request, str( e ) )
        
            return redirect( request.POST.get( "return_url" ) or request.path )


        if "_quick_add_agent" in request.POST:
            selected_hosts = request.POST.getlist( 'pk' )
            success_counter = 0
            max_success_messages = settings.get_max_success_notifications()
            if not selected_hosts:
                messages.warning( request, "Please select a Device or VM to add." )

            else:
                for host_identifier in selected_hosts:
                    try:
                        pk, content_type_id = host_identifier.split( ":" )
                        instance = get_instance_from_ct_and_pk( content_type_id, pk )

                        job = ProvisionAgent.run_job( instance=instance, request=request )
            
                        message = mark_safe(
                            f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> '
                            f'to import {instance.name} from Zabbix'
                        )
            
                        if success_counter < max_success_messages:
                            messages.success( request, message )
                            success_counter += 1
            
                    except Exception as e:
                        msg = f"Failed to queue import job for '{instance.name}' from Zabbix: {str( e )}"
                        messages.error( request, msg )
                        logger.error( msg )


        if "_quick_add_snmp" in request.POST:
            selected_hosts = request.POST.getlist( 'pk' )
            success_counter = 0
            max_success_messages = settings.get_max_success_notifications()
            if not selected_hosts:
                messages.warning( request, "Please select a Device or VM to add." )

            else:
                for host_identifier in selected_hosts:
                    try:
                        pk, content_type_id = host_identifier.split( ":" )
                        instance = get_instance_from_ct_and_pk( content_type_id, pk )
        
                        job = ProvisionSNMP.run_job( instance=instance, request=request )
            
                        message = mark_safe(
                            f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> '
                            f'to import {instance.name} from Zabbix'
                        )
            
                        if success_counter < max_success_messages:
                            messages.success( request, message )
                            success_counter += 1
            
                    except Exception as e:
                        msg = f"Failed to queue import job for '{instance.name}' from Zabbix: {str( e )}"
                        messages.error( request, msg )
                        logger.error( msg )

        return redirect( request.POST.get( "return_url" ) or request.path )


# ------------------------------------------------------------------------------
# Zabbix Only Hosts
# ------------------------------------------------------------------------------


class ZabbixOnlyHostsView(LoginRequiredMixin, GenericTemplateView):
    template_name = 'netbox_zabbix/zabbixonlyhosts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            data = zapi.get_zabbix_only_hostnames()
        except Exception as e:
            messages.error(self.request, f"Failed to fetch data from Zabbix: {str(e)}")
            data = []

        # Quick search
        search = self.request.GET.get('q', '').strip()
        if search:
            search_lower = search.lower()
            data = [h for h in data if search_lower in h['name'].lower()]

        table = tables.ZabbixOnlyHostTable(data, orderable=False)
        RequestConfig(self.request, {
            'paginator_class': EnhancedPaginator,
            'per_page': get_paginate_count(self.request),
        }).configure(table)

        context.update({
            'table': table,
            'web_address': settings.get_zabbix_web_address(),
            'search': search,
        })

        # If HTMX, render only the table partial
        if self.request.htmx:
            self.template_name = 'netbox_zabbix/zabbixonlyhosts_table.html'

        return context


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogView(generic.ObjectView):
    """
    Display a single EventLog instance, including differences from previous state.
    """
    queryset = EventLog.objects.all()

    def get_extra_context(self, request, instance):
        """
        Provide extra context including prev/next events, differences, and creator info.
        
        Args:
            request (HttpRequest): Current request.
            instance (EventLog): EventLog instance.
        
        Returns:
            dict: Context data for template rendering.
        """
        from utilities.data import shallow_compare_dict

        # Find previous and next events (ordered by created)
        prev_event = EventLog.objects.filter( created__lt=instance.created ).order_by( '-created' ).first()
        next_event = EventLog.objects.filter( created__gt=instance.created ).order_by( 'created' ).first()
        

        if request.GET.get( 'format' ) in ['json', 'yaml']:
            format = request.GET.get('format')
        else:
            format = 'json'

        diff_added   = shallow_compare_dict( instance.pre_data, instance.post_data )
        diff_removed = { x: instance.pre_data.get(x) for x in diff_added } if instance.pre_data else {}

        # Get the created by user
        created_by = None
        if getattr( instance, "job", None ) and getattr( instance.job, "user_id", None ):
            created_by = (
                User.objects.filter( id=instance.job.user_id )
                .values_list( "username", flat=True )
                .first()
            )

        return { 'created_by': created_by, 'format': format, 'prev_event': prev_event, 'next_event': next_event, "diff_added": diff_added, "diff_removed": diff_removed }


class EventLogListView(generic.ObjectListView):
    """
    Display a list of EventLog entries with table and filtering.
    """
    queryset  = EventLog.objects.all()
    table     = tables.EventLogTable
    filterset = filtersets.EventLogFilterSet
    template_name = "netbox_zabbix/eventlog_list.html"

    def get_extra_context(self, request):
        """
        Add extra context for EventLog rendering.
        
        Args:
            request (HttpRequest): Current request.
        
        Returns:
            dict: Context dictionary with optional actions.
        """
        # Hide the add button since no evenlog should be added by the user.
        context = super().get_extra_context( request )
        #context['actions'] = []
        return context


class EventLogEditView(generic.ObjectView):
    """
    Display details for a single EventLog instance.
    """
    queryset = EventLog.objects.all()


class EventLogDeleteView(generic.ObjectDeleteView):
    """
    Delete a single EventLog instance
    """
    queryset = EventLog.objects.all()

    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to EventLog list view.
        """
        return reverse( 'plugins:netbox_zabbix:eventlog_list' )


class EventLogBulkDeleteView(generic.BulkDeleteView):
    """
    Bulk delete multiple EventLog instances.
    """
    queryset = EventLog.objects.all()
    table    = tables.EventLogTable

    def get_return_url(self, request, obj=None):
        """
        Return URL after deletion.
        
        Returns:
            str: URL to EventLog list view.
        """
        return reverse( 'plugins:netbox_zabbix:eventlog_list' )


# ------------------------------------------------------------------------------
# Host Config Tab for Zabbix Problems
# ------------------------------------------------------------------------------


@register_model_view(HostConfig, name='problems')
class HostConfigProblemsTabView(generic.ObjectView):
    """
    Tab view to display Zabbix problems for a HostConfig.
    """
    queryset      = HostConfig.objects.all()
    tab           = ViewTab( label="Zabbix Problems", badge=lambda instance: len( zapi.get_problems( instance.assigned_object.name ) ) )
    template_name = 'netbox_zabbix/host_config_zabbix_problems_tab.html'


    def get_extra_context(self, request, instance):
        """
        Fetch all Zabbix problems for the host and provide table context.
        
        Args:
            request (HttpRequest): Current request.
            instance (HostConfig): Host configuration instance.
        
        Returns:
            dict: Contains 'table' of Zabbix problems.
        """
        # Jobs table
        jobs_queryset = instance.jobs.all()
        jobs_table    = JobTable(jobs_queryset)
        
        # Zabbix problems table
        problems = []
        try:
            problems = zapi.get_problems(instance.assigned_object.name)
        except Exception:
            pass
        problems_table = tables.ZabbixProblemTable(problems)
        
        return {
            "jobs_table":     jobs_table,
            "problems_table": problems_table,
        }


# ------------------------------------------------------------------------------
# Host Config Tab for Tasks
# ------------------------------------------------------------------------------


@register_model_view(HostConfig, name='jobs')
class HostConfigJobsTabView(generic.ObjectView):
    """
    Tab view to display Zabbix problems for a HostConfig.
    """
    queryset      = HostConfig.objects.all()
    tab           = ViewTab( label="Tasks", badge=lambda instance: instance.jobs.count() )
    template_name = 'netbox_zabbix/host_config_tasks_tab.html'

    def get_extra_context(self, request, instance):
        """
        Fetch all jobs for the host and provide table context.
        
        Args:
            request (HttpRequest): Current request.
            instance (HostConfig): Host configuration instance.
        
        Returns:
            dict: Contains 'table' of jobs.
        """
        queryset = instance.jobs.all()
        table    = JobTable( queryset )
        return { "table": table }


# ------------------------------------------------------------------------------
# Host Config Tab for Zabbix Diff
# ------------------------------------------------------------------------------


@register_model_view(HostConfig, name='difference')
class HostConfigDiffTabView(generic.ObjectView):
    """
    Tab view to display configuration differences for a HostConfig.
    """
    queryset      = HostConfig.objects.all()
    tab           = ViewTab( label="Difference", badge=lambda instance: int( instance.get_in_sync_status() ), hide_if_empty=True )
    template_name = 'netbox_zabbix/host_config_difference_tab.html'

    def get_extra_context(self, request, instance):
        """
        Fetch and display sync differences for the host configuration.
        
        Args:
            request (HttpRequest): Current request.
            instance (HostConfig): Host configuration instance.
        
        Returns:
            dict: Contains 'configurations' showing differences.
        """
        return { "configurations": instance.get_sync_diff() }



# ------------------------------------------------------------------------------
# Device Tab for Zabbix Details
# ------------------------------------------------------------------------------


@register_model_view(Device, name="Zabbix", path="zabbix")
class ZabbixDeviceTabView(generic.ObjectView):
    """
    Device tab displaying Zabbix problems for a Device.
    """
    queryset = HostConfig.objects.all()
    tab = ViewTab(
        label="Zabbix",
        hide_if_empty=True,
        badge=lambda device: str( len( zapi.get_problems( device.name ) )
        ) if HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( Device ),
            object_id=device.pk
        ).exists() else 0
    )


    def get(self, request, pk):
        """
        Render device-specific Zabbix problems table.
        
        Args:
            request (HttpRequest): Current request.
            pk (int): Device primary key.
        
        Returns:
            HttpResponse: Rendered template with Zabbix problems.
        """
        device = get_object_or_404( Device, pk=pk )
        config = HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( Device ),
            object_id=device.pk
        ).first()
        problems = []
        table = None

        if config:
            try:
                problems = zapi.get_problems( device.name )
            except:
                problems = []
            table = tables.ZabbixProblemTable( problems )

        return render(
            request,
            "netbox_zabbix/additional_device_tab.html",
            context={
                "tab": self.tab,
                "object": device,
                "config": config,
                "table": table,
                "web_address": settings.get_zabbix_web_address(),
            },
        )


# ------------------------------------------------------------------------------
# VM Tab for Zabbix Details
# ------------------------------------------------------------------------------


@register_model_view(VirtualMachine, name="Zabbix", path="zabbix")
class VMVirtualMachineTabView(generic.ObjectView):
    """
    VM tab displaying Zabbix problems for a VirtualMachine.
    """
    queryset = HostConfig.objects.all()
    tab = ViewTab(
        label="Zabbix",
        hide_if_empty=True,
        badge=lambda device: str( len( zapi.get_problems( device.name ) )
        ) if HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( VirtualMachine ),
            object_id=device.pk
        ).exists() else 0
    )

    def get(self, request, pk):
        """
        Render VM-specific Zabbix problems table.
        
        Args:
            request (HttpRequest): Current request.
            pk (int): VM primary key.
        
        Returns:
            HttpResponse: Rendered template with Zabbix problems.
        """
        vm = get_object_or_404( VirtualMachine, pk=pk )
        config = HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( VirtualMachine ),
            object_id=vm.pk
        ).first()
        problems = []
        table = None

        if config:
            try:
                problems = zapi.get_problems( vm.name )
            except:
                problems = []
            table = tables.ZabbixProblemTable( problems )

        return render(
            request,
            "netbox_zabbix/additional_vm_tab.html",
            context={
                "tab": self.tab,
                "object": vm,
                "config": config,
                "table": table,
                "web_address": settings.get_zabbix_web_address(),
            },
        )


# end
