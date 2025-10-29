# views.py

# Standard library imports
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render, get_object_or_404
from django.template.defaultfilters import capfirst, pluralize
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView as GenericTemplateView
from django.contrib.contenttypes.models import ContentType
from itertools import chain

# Third-party imports
from django_tables2 import RequestConfig

# NetBox imports
from core.tables.jobs import JobTable
from dcim.models import Device
from netbox.views import generic
from utilities.paginator import EnhancedPaginator, get_paginate_count
from utilities.views import ViewTab, register_model_view
from virtualization.models import VirtualMachine

# Plugin imports
from netbox_zabbix import settings, filtersets, forms, jobs, tables, zabbix as z

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
    EventLog,
)

from netbox_zabbix.utils import validate_quick_add
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Setting 
# ------------------------------------------------------------------------------


class SettingView(generic.ObjectView):
    queryset      = Setting.objects.all()

    def get_extra_context(self, request, instance):
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data', 'token' ]
        fields = [ ( capfirst( field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class SettingListView(generic.ObjectListView):
    queryset = Setting.objects.all()
    table    = tables.SettingTable

    def get_extra_context(self, request):
        # Hide the add button if a configuration already exists.
        context = super().get_extra_context( request )
        if Setting.objects.exists():
            context['actions'] = []
        return context


class SettingEditView(generic.ObjectEditView):
    queryset = Setting.objects.all()
    form     = forms.SettingForm


class SettingDeleteView(generic.ObjectDeleteView):
    queryset = Setting.objects.all()

    def post(self, request, *args, **kwargs):
        obj = self.get_object( **kwargs )
    
        if obj:
            messages.error( request, "You cannot delete the configuration." )
            return redirect('plugins:netbox_zabbix:setting_list' )
    
        return super().post( request, *args, **kwargs )


# --------------------------------------------------------------------------
# Zabbix Check connection
# --------------------------------------------------------------------------


def zabbix_check_connection(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )

    try:
        z.validate_zabbix_credentials_from_config()
        settings.set_version( z.get_version() )
        settings.set_connection( True )
        settings.set_last_checked( timezone.now() )
        messages.success( request, "Connection to Zabbix succeeded" )

    except settings.ZabbixSettingNotFound as e:
        messages.error( request, e )
        return redirect( redirect_url )
            
    except Exception as e:
        error_msg = f"Failed to connect to {settings.get_zabbix_api_endpoint()}: {e}"
        logger.error( error_msg )
        messages.error( request, error_msg )
        settings.set_connection( False )
        settings.set_last_checked( timezone.now() )

    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Sync With Zabbix
# ------------------------------------------------------------------------------


def sync_with_zabbix(request):
    """
    View-based wrapper around sync with Zabbix
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    
    try:
        host_config_id = request.GET.get( "host_config_id" )
        host_config = HostConfig.objects.get( id=host_config_id )
        jobs.UpdateZabbixHost.run_job_now( host_config=host_config, request=request )
        messages.success( request, f"Sync {host_config.name} with Zabbix succeeded." )
    except Exception as e:
        messages.error( request, f"Failed to sync {host_config.name} with Zabbix. Reason: { str( e ) }" )

    return redirect( redirect_url )


# --------------------------------------------------------------------------
# Zabbix Import Settings (Tempate, Proxies, etc.)
# --------------------------------------------------------------------------


def zabbix_import_settings(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    try:
        jobs.ImportZabbixSettings.run_now()
    except Exception as e:
        raise e
    
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateView(generic.ObjectView):
    queryset = Template.objects.all()
    
    def get_extra_context(self, request, instance):
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data' ]
        fields = [ ( capfirst(field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class TemplateListView(generic.ObjectListView):
    queryset = (
       Template.objects
       .annotate(
           host_count=Count("hostconfig", distinct=True)
       )
    )
    filterset      = filtersets.TemplateFilterSet
    filterset_form = forms.TemplateFilterForm
    table          = tables.TemplateTable
    template_name  = "netbox_zabbix/template_list.html"


class TemplateEditView(generic.ObjectEditView):
    queryset = Template.objects.all()
    form     = forms.TemplateForm


class TemplateDeleteView(generic.ObjectDeleteView):
    queryset = Template.objects.all()


class TemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = Template.objects.all()
    table    = tables.TemplateTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:template_list')


def run_import_templates(request=None):
    """
    Run the Zabbix template import logic and optionally attach messages to the request.
    Returns a tuple: (added, deleted, error)
    """
    try:
        added, deleted = z.import_templates()

        if request is not None:
            msg_lines = ["Importing Zabbix Templates succeeded."]
            if added:
                msg_lines.append( f"Added {len(added)} template{pluralize(len(added))}." )
            if deleted:
                msg_lines.append( f"Deleted {len(deleted)} template{pluralize(len(deleted))}." )
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
        settings.set_connection = False
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_templates(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_templates( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyView(generic.ObjectView):
    queryset = Proxy.objects.all()


class ProxyListView(generic.ObjectListView):
    queryset       = Proxy.objects.all()
    filterset      = filtersets.ProxyFilterSet
    filterset_form = forms.ProxyFilterForm
    table          = tables.ProxyTable
    template_name  = "netbox_zabbix/proxy_list.html"
    


class ProxyEditView(generic.ObjectEditView):
    queryset = Proxy.objects.all()
    form     = forms.ProxyForm


class ProxyDeleteView(generic.ObjectDeleteView):
    queryset = Proxy.objects.all()


class ProxyBulkDeleteView(generic.BulkDeleteView):
    queryset = Proxy.objects.all()
    table    = tables.ProxyTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxy_list')


def run_import_proxies(request=None):
    try:
        added, deleted = z.import_proxies()

        if request is not None:
            msg_lines = ["Importing Zabbix Proxies succeeded."]
            if added:
                msg_lines.append( f"Added {len( added )} prox{pluralize(len(added), 'y,ies')}." )
            if deleted:
                msg_lines.append( f"Deleted {len( deleted )} prox{pluralize(len(deleted), 'y,ies')}." )
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
        settings.set_connection = False
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_proxies(request):
    """
    View-based wrapper around import proxies.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxies( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------


class ProxyGroupView(generic.ObjectView):
    queryset = ProxyGroup.objects.all()


class ProxyGroupListView(generic.ObjectListView):
    queryset       = ProxyGroup.objects.all()
    filterset      = filtersets.ProxyGroupFilterSet
    filterset_form = forms.ProxyGroupFilterForm
    table          = tables.ProxyGroupTable 
    template_name  = "netbox_zabbix/proxy_group_list.html"
    

class ProxyGroupEditView(generic.ObjectEditView):
    queryset = ProxyGroup.objects.all()
    form     = forms.ProxyGroupForm


class ProxyGroupDeleteView(generic.ObjectDeleteView):
    queryset = ProxyGroup.objects.all()


class ProxyGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = ProxyGroup.objects.all()
    table    = tables.ProxyGroupTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxygroup_list')


def run_import_proxy_groups(request=None):
    try:
        added, deleted = z.import_proxy_groups()
        if request is not None:
            msg_lines = ["Import Zabbix Proxy Groups succeeded."]
            if added:
                msg_lines.append( f"Added {len( added )} proxy group{pluralize( len(added) )}." )
            if deleted:
                msg_lines.append( f"Deleted {len( deleted )} proxy group{pluralize( len(deleted) )}." )
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
        settings.set_connection = False
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_proxy_groups(request):
    """
    View-based wrapper around import proxy groups
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxy_groups( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------


class HostGroupView(generic.ObjectView):
    queryset = HostGroup.objects.all()


class HostGroupListView(generic.ObjectListView):
    queryset = HostGroup.objects.all()
    table    = tables.HostGroupTable
    template_name  = "netbox_zabbix/host_group_list.html"
    

class HostGroupEditView(generic.ObjectEditView):
    queryset = HostGroup.objects.all()
    form     = forms.HostGroupForm


class HostGroupDeleteView(generic.ObjectDeleteView):
    queryset = HostGroup.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostgroup_list')


class HostGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = HostGroup.objects.all()
    table    = tables.HostGroupTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostgroup_list')


def run_import_host_groups(request=None):
    try:
        added, deleted = z.import_host_groups()

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
        settings.set_connection = False
        settings.set_last_checked = timezone.now()
        return None, None, e


def import_host_groups(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_host_groups( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingView(generic.ObjectView):
    queryset = TagMapping.objects.all()


class TagMappingListView(generic.ObjectListView):
    queryset = TagMapping.objects.all()
    table    = tables.TagMappingTable


class TagMappingEditView(generic.ObjectEditView):
    queryset = TagMapping.objects.all()
    form     = forms.TagMappingForm


class TagMappingDeleteView(generic.ObjectDeleteView):
    queryset = TagMapping.objects.all()


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingView(generic.ObjectView):
    queryset = InventoryMapping.objects.all()


class InventoryMappingListView(generic.ObjectListView):
    queryset      = InventoryMapping.objects.all()
    table         = tables.InventoryMappingTable


class InventoryMappingEditView(generic.ObjectEditView):
    queryset      = InventoryMapping.objects.all()
    form          = forms.InventoryMappingForm


class InventoryMappingDeleteView(generic.ObjectDeleteView):
    queryset = InventoryMapping.objects.all()


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


def count_matching_devices_for_mapping(obj):
    return obj.get_matching_devices().count()


@register_model_view(DeviceMapping, 'devices')
class DeviceMappingDevicesView(generic.ObjectView):
    queryset      = DeviceMapping.objects.all()
    template_name = 'netbox_zabbix/devicemapping_devices.html'
    tab           = ViewTab( label="Matching Devices",
                             badge=lambda obj: count_matching_devices_for_mapping( obj ),
                             weight=500 )

    def get_extra_context(self, request, instance):
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
    queryset = DeviceMapping.objects.all()
    
    def get_extra_context(self, request, instance):
        devices = instance.get_matching_devices()
        return {
            "related_devices": [
                {
                    "queryset": devices,
                    "label": "Devices",
                    "count": devices.count()
                }
            ]
        }


class DeviceMappingListView(generic.ObjectListView):
    queryset      = DeviceMapping.objects.all()
    table         = tables.DeviceMappingTable


class DeviceMappingEditView(generic.ObjectEditView):
    queryset      = DeviceMapping.objects.all()
    form          = forms.DeviceMappingForm


class DeviceMappingDeleteView(generic.ObjectDeleteView):
    queryset = DeviceMapping.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:devicemapping_list')

    def post(self, request, *args, **kwargs):
        obj = self.get_object( **kwargs )
    
        if obj.default:
            messages.error( request, "You cannot delete the default mapping." )
            return redirect('plugins:netbox_zabbix:devicemapping_list' )
    
        return super().post( request, *args, **kwargs )


class DeviceMappingBulkDeleteView(generic.BulkDeleteView):
    queryset        = DeviceMapping.objects.all()
    filterset_class = filtersets.DeviceMappingFilterSet
    table           = tables.DeviceMappingTable

    def post(self, request, *args, **kwargs):
        # Determine which objects are being deleted
        selected_pks = request.POST.getlist( 'pk' )
        mappings     = Mapping.objects.filter( pk__in=selected_pks )
    
        # Check if any default mappings are included
        default_mappings = mappings.filter( default=True )
        if default_mappings.exists():
            names = ", ".join( [m.name for m in default_mappings] )
            messages.error( request, f"Cannot delete default mapping: {names}" )
            return redirect('plugins:netbox_zabbix:devicemapping_list' )
    
        # No default mappings selected, proceed with normal deletion
        return super().post(request, *args, **kwargs)
    

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:devicemapping_list')


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


def count_matching_vms_for_mapping(obj):
    return obj.get_matching_virtual_machines().count()


@register_model_view(VMMapping, 'vms')
class VMMappingVMsView(generic.ObjectView):
    queryset      = VMMapping.objects.all()
    template_name = 'netbox_zabbix/vmmapping_vms.html'
    tab           = ViewTab( label="Matching VMs",
                             badge=lambda obj: count_matching_vms_for_mapping( obj ),
                             weight=500 )
    
    def get_extra_context(self, request, instance):
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
    queryset      = VMMapping.objects.all()
    
    def get_extra_context(self, request, instance):
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
    queryset      = VMMapping.objects.all()
    table         = tables.VMMappingTable


class VMMappingEditView(generic.ObjectEditView):
    queryset      = VMMapping.objects.all()
    form          = forms.VMMappingForm


class VMMappingDeleteView(generic.ObjectDeleteView):
    queryset = VMMapping.objects.all()
    
    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:vmmapping_list')
    
    def post(self, request, *args, **kwargs):
        obj = self.get_object( **kwargs )
    
        if obj.default:
            messages.error( request, "You cannot delete the default mapping." )
            return redirect('plugins:netbox_zabbix:vmmapping_list' )
    
        return super().post( request, *args, **kwargs )


class VMMappingBulkDeleteView(generic.BulkDeleteView):
    queryset        = VMMapping.objects.all()
    filterset_class = filtersets.VMMappingFilterSet
    table           = tables.VMMappingTable

    def post(self, request, *args, **kwargs):
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
        return reverse('plugins:netbox_zabbix:vmmapping_list')


# ------------------------------------------------------------------------------
# Get Instance from ConfigContext and Object ID
# ------------------------------------------------------------------------------


def get_instance_from_ct_and_pk(content_type_id, instance_id):
    """
    Given a content_type_id and an instance ID, return the model instance.
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
    Minimal queryset-like wrapper for combining Device + VM objects
    while remaining compatible with NetBox's generic ObjectListView.
    """

    def __init__(self, iterable, model):
        super().__init__( iterable )
        self.model = model  # e.g. Device, required for permission checks

    def restrict(self, user, action):
        # Permission filtering not relevant for synthetic union view
        return self

    def exists(self):
        # Mimic QuerySet.exists()
        return bool( self )

    def count(self):
        # Mimic QuerySet.count()
        return len( self )

    def all(self):
        # For compatibility with methods expecting .all()
        return self

    def __getitem__(self, key):
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
    queryset = HostConfig.objects.all()

    def get_extra_context(self, request, instance):
        super().get_extra_context( request, instance )
        web_address = settings.get_zabbix_web_address()
        problems = []
        table = None
        try:
            problems = z.get_problems( instance.assigned_object.name )
        except:
            pass
        table = tables.ZabbixProblemTable( problems )
        return { "web_address":  web_address, "table": table }


class HostConfigListView(generic.ObjectListView):
    queryset = HostConfig.objects.all()
    table    = tables.HostConfigTable


class HostConfigEditView(generic.ObjectEditView):
    queryset = HostConfig.objects.all()
    form     = forms.HostConfigForm


class HostConfigDeleteView(generic.ObjectDeleteView):
    queryset = HostConfig.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostconfig_list' )


class HostConfigBulkDeleteView(generic.BulkDeleteView):
    queryset = HostConfig.objects.all()
    table    = tables.HostConfigTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostconfig_list' )


# --------------------------------------------------------------------------
# Agent Interface
# --------------------------------------------------------------------------


class AgentInterfaceView(generic.ObjectView):
    queryset = AgentInterface.objects.all()


class AgentInterfaceListView(generic.ObjectListView):
    queryset      = AgentInterface.objects.all()
    table         = tables.AgentInterfaceTable
    filterset     = filtersets.AgentInterfaceFilterSet
    template_name = 'netbox_zabbix/agent_interface_list.html'


class AgentInterfaceEditView(generic.ObjectEditView):
    queryset      = AgentInterface.objects.all()
    form          = forms.AgentInterfaceForm
    template_name = 'netbox_zabbix/agent_interface_edit.html'


class AgentInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = AgentInterface.objects.all()


class AgentInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = AgentInterface.objects.all()
    table    = tables.AgentInterfaceTable

    def get_return_url(self, request, obj=None):
        return reverse( 'plugins:netbox_zabbix:agentinterface_list' )


# --------------------------------------------------------------------------
# SNMP Interface
# --------------------------------------------------------------------------


class SNMPInterfaceView(generic.ObjectView):
    queryset = SNMPInterface.objects.all()


class SNMPInterfaceListView(generic.ObjectListView):
    queryset      = SNMPInterface.objects.all()
    table         = tables.SNMPInterfaceTable
    filterset     = filtersets.SNMPInterfaceFilterSet
    template_name = 'netbox_zabbix/snmp_interface_list.html'
    

class SNMPInterfaceEditView(generic.ObjectEditView):
    queryset      = SNMPInterface.objects.all()
    form          = forms.SNMPInterfaceForm
    template_name = 'netbox_zabbix/snmp_interface_edit.html'


class SNMPInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = SNMPInterface.objects.all()


class SNMPInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = SNMPInterface.objects.all()
    table    = tables.SNMPInterfaceTable

    def get_return_url(self, request, obj=None):
        return reverse( 'plugins:netbox_zabbix:snmpinterface_list' )


# --------------------------------------------------------------------------
# Importable Hosts
# --------------------------------------------------------------------------


class ImportableHostsListView(generic.ObjectListView):
    table         = tables.ImportableHostsTable
    template_name = "netbox_zabbix/importable_hosts_list.html"


    def get_extra_context(self, request):
        super().get_extra_context( request )
        return { "validate_button": not settings.get_auto_validate_importables() }


    def get_queryset(self, request):
        try:
            zabbix_hostnames = z.get_cached_zabbix_hostnames()
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
        return CombinedHostsQuerySet( combined, Device )


    def post( self, request, *args, **kwargs ):
    
        # Validate Host
        if '_validate_host' in request.POST:

            logger.info( f"request {request.__dict__}" )

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
                    result = jobs.ValidateHost.run_now(
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
                        job = jobs.ImportHost.run_job( instance=instance, request=request )
    
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
    table = tables.NetBoxOnlyHostsTable
    template_name = "netbox_zabbix/netbox_only_hosts_list.html"


    def get_extra_context(self, request):
        super().get_extra_context( request )
        return { "validate_button": not settings.get_auto_validate_quick_add() }
    

    def get_queryset(self, request):
        try:
            zabbix_hostnames = z.get_cached_zabbix_hostnames()
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
       
        return CombinedHostsQuerySet( combined, Device )


    def build_mapping_cache(self, queryset, host_type):
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
        candidates = [
            m for m in mappings
            if not m["default"] and (m["interface_type"] == intf_type or m["interface_type"] == InterfaceTypeChoices.Any)
        ]
    
        def matches(m):
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
        table = super().get_table( queryset, request, has_bulk_actions )
        table.device_mapping_cache = getattr( self, "device_mapping_cache", {} )
        table.vm_mapping_cache     = getattr( self, "vm_mapping_cache", {} )
        
        return table


    def post(self, request, *args, **kwargs):

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

                        job = jobs.ProvisionAgent.run_job( instance=instance, request=request )
            
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
            logger.info( "\n\n _quick_add_snmp \n\n" )
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
        
                        job = jobs.ProvisionSNMP.run_job( instance=instance, request=request )
            
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


class ZabbixOnlyHostsView(GenericTemplateView):
    template_name = 'netbox_zabbix/zabbixonlyhosts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data( **kwargs )

        error_occurred = False
        try:            
            data        = z.get_zabbix_only_hostnames()
            web_address = settings.get_zabbix_web_address()

        except settings.ZabbixSettingNotFound as e:
            messages.error( self.request, str( e ) )
            error_occurred = True

        except Exception as e:
            messages.error( self.request, f"Failed to fetch data from Zabbix: {str(e)}" )
            error_occurred = True
        
        if error_occurred:
            empty_table = tables.ZabbixOnlyHostTable( [], orderable=False )
            RequestConfig( self.request ).configure( empty_table )
            context['table'] = empty_table
            return context
        
        table = tables.ZabbixOnlyHostTable( data, orderable=False )
        RequestConfig(
            self.request, {
                'paginator_class': EnhancedPaginator,
                'per_page': get_paginate_count( self.request ),
            }
        ).configure( table )
        
        try:
            web_address = settings.get_zabbix_web_address()
        except Exception as e:
            raise e
        
        context.update({
            'table': table,
            'web_address': web_address,
        })
        return context


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogView(generic.ObjectView):
    queryset = EventLog.objects.all()

    def get_extra_context(self, request, instance):
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

        return { 'format': format, 'prev_event': prev_event, 'next_event': next_event, "diff_added": diff_added, "diff_removed": diff_removed }


class EventLogListView(generic.ObjectListView):
    queryset = EventLog.objects.all()
    table    = tables.EventLogTable


class EventLogEditView(generic.ObjectView):
    queryset = EventLog.objects.all()


class EventLogDeleteView(generic.ObjectDeleteView):
    queryset = EventLog.objects.all()


class EventLogBulkDeleteView(generic.BulkDeleteView):
    queryset = EventLog.objects.all()
    table    = tables.EventLogTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:eventlog_list')


# ------------------------------------------------------------------------------
# Host Config Tab for Tasks
# ------------------------------------------------------------------------------


@register_model_view(HostConfig, name='jobs')
class HostConfigJobsTabView(generic.ObjectView):
    queryset      = HostConfig.objects.all()
    tab           = ViewTab( label="Tasks", badge=lambda instance: instance.jobs.count() )
    template_name = 'netbox_zabbix/host_config_tasks_tab.html'

    def get_extra_context(self, request, instance):
        queryset = instance.jobs.all()
        table    = JobTable( queryset )
        return { "table": table }


# ------------------------------------------------------------------------------
# Host Config Tab for Zabbix Diff
# ------------------------------------------------------------------------------


@register_model_view(HostConfig, name='difference')
class HostConfigDiffTabView(generic.ObjectView):
    queryset      = HostConfig.objects.all()
    tab           = ViewTab( label="Difference", badge=lambda instance: int( instance.get_sync_status() ), hide_if_empty=True )
    template_name = 'netbox_zabbix/host_config_difference_tab.html'

    def get_extra_context(self, request, instance):
        return { "configurations": instance.get_sync_diff() }



# ------------------------------------------------------------------------------
# Device Tab for Zabbix Details
# ------------------------------------------------------------------------------


@register_model_view(Device, name="Zabbix", path="zabbix")
class ZabbixDeviceTabView(generic.ObjectView):
    queryset = HostConfig.objects.all()
    tab = ViewTab(
        label="Zabbix",
        hide_if_empty=True,
        badge=lambda device: str( len( z.get_problems( device.name ) )
        ) if HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( Device ),
            object_id=device.pk
        ).exists() else 0
    )


    def get(self, request, pk):
        device = get_object_or_404( Device, pk=pk )
        config = HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( Device ),
            object_id=device.pk
        ).first()
        problems = []
        table = None

        if config:
            problems = z.get_problems( device.name )
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
    queryset = HostConfig.objects.all()
    tab = ViewTab(
        label="Zabbix",
        hide_if_empty=True,
        badge=lambda device: str( len( z.get_problems( device.name ) )
        ) if HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( VirtualMachine ),
            object_id=device.pk
        ).exists() else 0
    )

    def get(self, request, pk):
        vm = get_object_or_404( VirtualMachine, pk=pk )
        config = HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model( VirtualMachine ),
            object_id=vm.pk
        ).first()
        problems = []
        table = None

        if config:
            problems = z.get_problems( vm.name )
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