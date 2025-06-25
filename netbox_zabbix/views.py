# views.py
import netbox_zabbix.config as config
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count, Exists, F, OuterRef
from django.http import Http404
from django.shortcuts import redirect, render
from django.template.defaultfilters import capfirst, pluralize
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView as GenericTemplateView
from django_tables2 import RequestConfig, SingleTableView

from dcim.models import Device
from netbox.views import generic
from utilities.paginator import EnhancedPaginator, get_paginate_count
from utilities.views import ViewTab, register_model_view
from virtualization.models import VirtualMachine

from netbox_zabbix import filtersets, forms, jobs, models, tables, zabbix as z
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Configuration 
# ------------------------------------------------------------------------------

class ConfigView(generic.ObjectView):
    queryset = models.Config.objects.all()

    def get_extra_context(self, request, instance):
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data', 'token' ]
        fields = [ ( capfirst( field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class ConfigListView(generic.ObjectListView):
    queryset = models.Config.objects.all()
    table = tables.ConfigTable

    def get_extra_context(self, request):
        # Hide the add button if a configuration already exists.      
        context = super().get_extra_context( request )
        if models.Config.objects.exists():
            context['actions'] = []
        return context


class ConfigEditView(generic.ObjectEditView):
    queryset = models.Config.objects.all()
    form = forms.ConfigForm


class ConfigDeleteView(generic.ObjectDeleteView):
    queryset = models.Config.objects.all()


def zabbix_check_connection(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )

    try:
        z.validate_zabbix_credentials_from_config()
        config.set_version( z.get_version() )
        config.set_connection( True )
        config.set_last_checked( timezone.now() )
        messages.success( request, "Connection to Zabbix succeeded" )

    except config.ZabbixConfigNotFound as e:
        messages.error( request, e )
        return redirect( redirect_url )
            
    except Exception as e:
        error_msg = f"Failed to connect to {config.get_zabbix_api_endpoint()}: {e}"
        logger.error( error_msg )
        messages.error( request, error_msg )
        config.set_connection( False )
        config.set_last_checked( timezone.now() )

    return redirect( redirect_url )


def zabbix_import_settings(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    try:
        run_import_templates( request )
        run_import_proxies( request )
        run_import_proxy_groups( request )
        run_import_host_groups( request )
    except Exception as e:
        pass
    
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------

class TemplateView(generic.ObjectView):
    queryset = models.Template.objects.all()
    
    def get_extra_context(self, request, instance):
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data' ]
        fields = [ ( capfirst(field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class TemplateListView(generic.ObjectListView):    
    queryset = (
       models.Template.objects
       .annotate(
           # Count the related VMZabbixConfigs and DeviceZabbixConfigs separately
           VMZabbixConfig_count=Count('vmzabbixconfig'),
           DeviceZabbixConfig_count=Count('devicezabbixconfig')
       )
       .annotate(
           # Add the two counts together to get the total host count
           host_count=F('VMZabbixConfig_count') + F('DeviceZabbixConfig_count')
       )
    )
    filterset = filtersets.TemplateFilterSet
    filterset_form = forms.TemplateFilterForm
    table = tables.TemplateTable    
    template_name = "netbox_zabbix/template_list.html"


class TemplateEditView(generic.ObjectEditView):
    queryset = models.Template.objects.all()
    form = forms.TemplateForm


class TemplateDeleteView(generic.ObjectDeleteView):
    queryset = models.Template.objects.all()


def templates_review_deletions(request):
    items = models.Template.objects.filter( marked_for_deletion=True )
    return render( request, 'netbox_zabbix/template_review_deletions.html', {'items': items} )


@require_POST
def templates_confirm_deletions(request):
    selected_ids = request.POST.getlist( 'confirm_ids' )
    models.Template.objects.filter( id__in=selected_ids ).delete()
    return redirect( 'plugins:netbox_zabbix:templates_review_deletions' )


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
        if request is not None:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}" ) )
        return None, None, e

    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        if request is not None:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}" ) )
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e

def import_templates(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_templates( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Template Mappings
# ------------------------------------------------------------------------------

class TemplateMappingView(generic.ObjectView):
    queryset = models.TemplateMapping.objects.all()
    template_name = 'netbox_zabbix/template_mapping.html'
    

    def get_extra_context(self, request, instance):
        filter_data = {}
        if instance.sites.exists():
            filter_data['site_id'] = [s.pk for s in instance.sites.all()]
        if instance.roles.exists():
            filter_data['role_id'] = [r.pk for r in instance.roles.all()]
        if instance.platforms.exists():
            filter_data['platform_id'] = [p.pk for p in instance.platforms.all()]
        if instance.tags.exists():
            filter_data['tag'] = [t.slug for t in instance.tags.all()]
    
        device_qs = Device.objects.all()
        filtered_devices = filtersets.TemplateDeviceFilterSet(data=filter_data, queryset=device_qs).qs.distinct()
    
        vm_qs = VirtualMachine.objects.all()
        filtered_vms = filtersets.TemplateVMFilterSet(data=filter_data, queryset=vm_qs).qs.distinct()
    
        filter_query = urlencode(filter_data, doseq=True)
    
        return {
            "related_models": [
                {
                    "queryset": filtered_devices,
                    "url": reverse('dcim:device_list') + f"?{filter_query}",
                    "label": "Devices",
                    "count": filtered_devices.count(),
                },
                {
                    "queryset": filtered_vms,
                    "url": reverse('virtualization:virtualmachine_list') + f"?{filter_query}",
                    "label": "Virtual Machines",
                    "count": filtered_vms.count(),
                },
            ],
        }


class TemplateMappingListView(generic.ObjectListView):
    queryset = models.TemplateMapping.objects.all()
    table = tables.TemplateMappingTable
    template_name = 'netbox_zabbix/template_mapping_list.html'


class TemplateMappingEditView(generic.ObjectEditView):
    queryset = models.TemplateMapping.objects.all()
    form = forms.TemplateMappingForm
    template_name = 'netbox_zabbix/template_mapping_edit.html'

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:templatemapping_list')


class TemplateMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.TemplateMapping.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:templatemapping_list')


class TemplateMappingBulkDeleteView(generic.BulkDeleteView):
    queryset = models.TemplateMapping.objects.all()
    filterset_class = filtersets.TemplateMappingFilterSet
    table = tables.TemplateMappingTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:templatemapping_list')


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------

class ProxyView(generic.ObjectView):
    queryset = models.Proxy.objects.all()


class ProxyListView(generic.ObjectListView):    
    queryset = models.Proxy.objects.all()
    filterset = filtersets.ProxyFilterSet
    filterset_form = forms.ProxyFilterForm
    table = tables.ProxyTable    
    template_name = "netbox_zabbix/proxy_list.html"


class ProxyEditView(generic.ObjectEditView):
    queryset = models.Proxy.objects.all()
    form = forms.ProxyForm


class ProxyDeleteView(generic.ObjectDeleteView):
    queryset = models.Proxy.objects.all()


def proxies_review_deletions(request):
    items = models.Proxy.objects.filter( marked_for_deletion=True )
    return render( request, 'netbox_zabbix/proxies_review_deletions.html', {'items': items} )


@require_POST
def proxies_confirm_deletions(request):
    selected_ids = request.POST.getlist( 'confirm_ids' )
    models.Proxy.objects.filter( id__in=selected_ids ).delete()
    return redirect( 'plugins:netbox_zabbix:proxies_review_deletions' )

def run_import_proxies(request=None):
    try:
        added, deleted = z.import_proxies()
    
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
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        return None, None, e
    
    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e
    
def import_proxies(request):
    """
    View-based wrapper around import proxies.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxies()
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Proxy Mappings
# ------------------------------------------------------------------------------

class ProxyMappingView(generic.ObjectView):
    queryset = models.ProxyMapping.objects.all()
    template_name = 'netbox_zabbix/proxy_mapping.html'
    

    def get_extra_context(self, request, instance):
        filter_data = {}
        if instance.sites.exists():
            filter_data['site_id'] = [s.pk for s in instance.sites.all()]
        if instance.roles.exists():
            filter_data['role_id'] = [r.pk for r in instance.roles.all()]
        if instance.platforms.exists():
            filter_data['platform_id'] = [p.pk for p in instance.platforms.all()]
        if instance.tags.exists():
            filter_data['tag'] = [t.slug for t in instance.tags.all()]
    
        device_qs = Device.objects.all()
        filtered_devices = filtersets.ProxyDeviceFilterSet( data=filter_data, queryset=device_qs ).qs.distinct()
    
        vm_qs = VirtualMachine.objects.all()
        filtered_vms = filtersets.ProxyVMFilterSet( data=filter_data, queryset=vm_qs ).qs.distinct()
    
        filter_query = urlencode(filter_data, doseq=True)
    
        return {
            "related_models": [
                {
                    "queryset": filtered_devices,
                    "url": reverse('dcim:device_list') + f"?{filter_query}",
                    "label": "Devices",
                    "count": filtered_devices.count(),
                },
                {
                    "queryset": filtered_vms,
                    "url": reverse('virtualization:virtualmachine_list') + f"?{filter_query}",
                    "label": "Virtual Machines",
                    "count": filtered_vms.count(),
                },
            ],
        }
    

class ProxyMappingListView(generic.ObjectListView):
    queryset = models.ProxyMapping.objects.all()
    table = tables.ProxyMappingTable
    template_name = 'netbox_zabbix/proxy_mapping_list.html'


class ProxyMappingEditView(generic.ObjectEditView):
    queryset = models.ProxyMapping.objects.all()
    form = forms.ProxyMappingForm
    template_name = 'netbox_zabbix/proxy_mapping_edit.html'

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxymapping_list')


class ProxyMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.ProxyMapping.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxymapping_list')


class ProxyMappingBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ProxyMapping.objects.all()
    filterset_class = filtersets.ProxyMappingFilterSet
    table = tables.ProxyMappingTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:proxymapping_list')


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------

class ProxyGroupView(generic.ObjectView):
    queryset = models.ProxyGroup.objects.all()
    template_name = "netbox_zabbix/proxy_group.html"


class ProxyGroupListView(generic.ObjectListView):
    queryset = models.ProxyGroup.objects.all()
    filterset = filtersets.ProxyGroupFilterSet
    filterset_form = forms.ProxyGroupFilterForm
    table = tables.ProxyGroupTable 
    template_name = "netbox_zabbix/proxy_group_list.html"


class ProxyGroupEditView(generic.ObjectEditView):
    queryset = models.ProxyGroup.objects.all()
    form = forms.ProxyGroupForm
    

class ProxyGroupDeleteView(generic.ObjectDeleteView):
    queryset = models.ProxyGroup.objects.all()


def proxygroups_review_deletions(request):
    items = models.ProxyGroup.objects.filter( marked_for_deletion=True )
    return render( request, 'netbox_zabbix/proxygroup_review_deletions.html', {'items': items} )


@require_POST
def proxygroups_confirm_deletions(request):
    selected_ids = request.POST.getlist( 'confirm_ids' )
    models.ProxyGroup.objects.filter( id__in=selected_ids ).delete()
    return redirect( 'plugins:netbox_zabbix:proxygroup_review_deletions' )


def run_import_proxy_groups(request=None):
    try:
        added, deleted = z.import_proxy_groups()
    
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
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        return None, None, e
    
    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e
    

def import_proxy_groups(request):
    """
    View-based wrapper around import proxy groups
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxy_groups()
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Proxy Group Mappings
# ------------------------------------------------------------------------------

class ProxyGroupMappingView(generic.ObjectView):
    queryset = models.ProxyGroupMapping.objects.all()
    template_name = 'netbox_zabbix/proxy_group_mapping.html'

    def get_extra_context(self, request, instance):
        filter_data = {}
        if instance.sites.exists():
            filter_data['site_id'] = [s.pk for s in instance.sites.all()]
        if instance.roles.exists():
            filter_data['role_id'] = [r.pk for r in instance.roles.all()]
        if instance.platforms.exists():
            filter_data['platform_id'] = [p.pk for p in instance.platforms.all()]
        if instance.tags.exists():
            filter_data['tag'] = [t.slug for t in instance.tags.all()]
    
        device_qs = Device.objects.all()
        filtered_devices = filtersets.ProxyGroupDeviceFilterSet( data=filter_data, queryset=device_qs ).qs.distinct()
    
        vm_qs = VirtualMachine.objects.all()
        filtered_vms = filtersets.ProxyGroupVMFilterSet( data=filter_data, queryset=vm_qs ).qs.distinct()
    
        filter_query = urlencode(filter_data, doseq=True)
    
        return {
            "related_models": [
                {
                    "queryset": filtered_devices,
                    "url": reverse('dcim:device_list') + f"?{filter_query}",
                    "label": "Devices",
                    "count": filtered_devices.count(),
                },
                {
                    "queryset": filtered_vms,
                    "url": reverse('virtualization:virtualmachine_list') + f"?{filter_query}",
                    "label": "Virtual Machines",
                    "count": filtered_vms.count(),
                },
            ],
        }
    

class ProxyGroupMappingListView(generic.ObjectListView):
    queryset = models.ProxyGroupMapping.objects.all()
    table = tables.ProxyGroupMappingTable
    template_name = 'netbox_zabbix/proxy_group_mapping_list.html'


class ProxyGroupMappingEditView(generic.ObjectEditView):
    queryset = models.ProxyGroupMapping.objects.all()
    form = forms.ProxyGroupMappingForm
    template_name = 'netbox_zabbix/proxy_group_mapping_edit.html'

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxygroupmapping_list')


class ProxyGroupMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.ProxyGroupMapping.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxygroupmapping_list')


class ProxyGroupMappingBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ProxyGroupMapping.objects.all()
    filterset_class = filtersets.ProxyGroupMappingFilterSet
    table = tables.ProxyGroupMappingTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:proxygroupmapping_list')


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------

class HostGroupView(generic.ObjectView):
    queryset = models.HostGroup.objects.all()


class HostGroupListView(generic.ObjectListView):
    queryset = models.HostGroup.objects.all()
    #filterset_fields = ['hostgroup', 'role',  'platform', 'tag']
    table = tables.HostGroupTable
    template_name = 'netbox_zabbix/host_group_list.html'


class HostGroupEditView(generic.ObjectEditView):
    queryset = models.HostGroup.objects.all()
    form = forms.HostGroupForm


class HostGroupDeleteView(generic.ObjectDeleteView):
    queryset = models.HostGroup.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostgroup_list')

def run_import_host_groups(request=None):
    try:
        added, deleted = z.import_host_groups()
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
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        return None, None, e
    
    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e
    

def import_host_groups(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_host_groups()
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Host Group Mappings
# ------------------------------------------------------------------------------

class HostGroupMappingView(generic.ObjectView):
    queryset = models.HostGroupMapping.objects.all()
    template_name = 'netbox_zabbix/host_group_mapping.html'

    def get_extra_context(self, request, instance):
        filter_data = {}
        if instance.sites.exists():
            filter_data['site_id'] = [s.pk for s in instance.sites.all()]
        if instance.roles.exists():
            filter_data['role_id'] = [r.pk for r in instance.roles.all()]
        if instance.platforms.exists():
            filter_data['platform_id'] = [p.pk for p in instance.platforms.all()]
        if instance.tags.exists():
            filter_data['tag'] = [t.slug for t in instance.tags.all()]
    
        device_qs = Device.objects.all()
        filtered_devices = filtersets.HostGroupDeviceFilterSet(data=filter_data, queryset=device_qs).qs.distinct()
    
        vm_qs = VirtualMachine.objects.all()
        filtered_vms = filtersets.HostGroupVMFilterSet(data=filter_data, queryset=vm_qs).qs.distinct()
    
        filter_query = urlencode(filter_data, doseq=True)
    
        return {
            "related_models": [
                {
                    "queryset": filtered_devices,
                    "url": reverse('dcim:device_list') + f"?{filter_query}",
                    "label": "Devices",
                    "count": filtered_devices.count(),
                },
                {
                    "queryset": filtered_vms,
                    "url": reverse('virtualization:virtualmachine_list') + f"?{filter_query}",
                    "label": "Virtual Machines",
                    "count": filtered_vms.count(),
                },
            ],
        }
    

class HostGroupMappingListView(generic.ObjectListView):
    queryset = models.HostGroupMapping.objects.all()
    #filterset_fields = ['hostgroup', 'role',  'platform', 'tag']
    table = tables.HostGroupMappingTable
    template_name = 'netbox_zabbix/host_group_mapping_list.html'


class HostGroupMappingEditView(generic.ObjectEditView):
    queryset = models.HostGroupMapping.objects.all()
    form = forms.HostGroupMappingForm
    template_name = 'netbox_zabbix/host_group_mapping_edit.html'

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostgroupmapping_list')


class HostGroupMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.HostGroupMapping.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:hostgroupmapping_list')


class HostGroupMappingBulkDeleteView(generic.BulkDeleteView):
    queryset = models.HostGroupMapping.objects.all()
    filterset_class = filtersets.HostGroupMappingFilterSet
    table = tables.HostGroupMappingTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:hostgroupmapping_list')


# ------------------------------------------------------------------------------
# Host Group Mapping Devices
# ------------------------------------------------------------------------------

def count_matching_devices(obj):
    filter_data = {}
    if obj.sites.exists():
        filter_data['site_id'] = [s.pk for s in obj.sites.all()]
    if obj.roles.exists():
        filter_data['role_id'] = [r.pk for r in obj.roles.all()]
    if obj.platforms.exists():
        filter_data['platform_id'] = [p.pk for p in obj.platforms.all()]
    if obj.tags.exists():
        filter_data['tag'] = [t.slug for t in obj.tags.all()]

    qs = Device.objects.all()
    filterset = filtersets.HostGroupDeviceFilterSet( data=filter_data, queryset=qs )
    return filterset.qs.distinct().count()


@register_model_view(models.HostGroupMapping, 'devices')
class HostGroupMappingDevicesView(generic.ObjectView):
    queryset = models.HostGroupMapping.objects.all()
    template_name = 'netbox_zabbix/host_group_mapping_devices.html'
    tab = ViewTab( label="Matching Devices",                   
                  badge=lambda obj: count_matching_devices(obj),
                  weight=500 )
    
    def get_extra_context(self, request, instance):
        filter_data = {}

        if instance.sites.exists():
            filter_data['site_id'] = [s.pk for s in instance.sites.all()]
        if instance.roles.exists():
            filter_data['role_id'] = [r.pk for r in instance.roles.all()]
        if instance.platforms.exists():
            filter_data['platform_id'] = [p.pk for p in instance.platforms.all()]
        if instance.tags.exists():
            filter_data['tag'] = [t.slug for t in instance.tags.all()]
    
        # Annotate the Device with zabbix_config
        qs = Device.objects.annotate( zabbix_config=Exists( models.DeviceZabbixConfig.objects.filter( device=OuterRef( 'pk' ) ) ) )
        filterset = filtersets.HostGroupDeviceFilterSet( data=filter_data, queryset=qs )    
        device_table = tables.MatchingDeviceTable( filterset.qs.distinct(), orderable=True )
        RequestConfig(
            request,
            {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
        ).configure( device_table )
    
        return {
            "table": device_table,
        }


# ------------------------------------------------------------------------------
# Host Group Mapping Virtual Machines
# ------------------------------------------------------------------------------

def count_matching_vms(obj):
    filter_data = {}
    if obj.sites.exists():
        filter_data['site_id'] = [s.pk for s in obj.sites.all()]
    if obj.roles.exists():
        filter_data['role_id'] = [r.pk for r in obj.roles.all()]
    if obj.platforms.exists():
        filter_data['platform_id'] = [p.pk for p in obj.platforms.all()]
    if obj.tags.exists():
        filter_data['tag'] = [t.slug for t in obj.tags.all()]

    qs = VirtualMachine.objects.all()
    filterset = filtersets.HostGroupVMFilterSet( data=filter_data, queryset=qs )
    return filterset.qs.distinct().count()


@register_model_view(models.HostGroupMapping, 'vms')
class HostGroupMappingVMsView(generic.ObjectView):
    """
     View for displaying virtual machines that match the criteria defined in a HostGroupMapping.
    
     This view filters `VirtualMachine` objects based on the tags, sites, roles, and platforms 
     associated with a specific `HostGroupMapping` instance. It also annotates each VM with a 
     `zabbix_config` boolean indicating whether it has an associated Zabbix configuration.
    
     Attributes:
         queryset: The set of HostGroupMapping objects to use in this view.
         template_name: Path to the template used to render the page.
         tab: A ViewTab object used to define the tab label, badge (count of matching VMs), and weight 
              (ordering in tab list).
    
     Methods:
         get_extra_context(request, instance):
             Gathers additional context to be passed to the template, including the filtered and annotated
             table of matching virtual machines. Uses `RequestConfig` to apply pagination and sorting.
    
     Filtering Logic:
         - If the `HostGroupMapping` defines any sites, roles, platforms, or tags, these are converted 
           into filter parameters.
         - A custom filterset (`HostGroupDeviceFilterSet`) is used to filter the `VirtualMachine` queryset.
         - The queryset is annotated with `zabbix_config`, indicating if the VM has a related Zabbix config.
    
     UI:
         - A badge on the tab displays the number of matching virtual machines.
         - The result table is sortable and paginated using NetBox's standard table controls.
     """
    queryset = models.HostGroupMapping.objects.all()
    template_name = 'netbox_zabbix/host_group_mapping_vms.html'
    tab = ViewTab( label="Matching Virtual Machines", 
                  badge=lambda obj: count_matching_vms(obj),
                  weight=500 )

    def get_extra_context(self, request, instance):
        filter_data = {}

        if instance.sites.exists():
            filter_data['site_id'] = [s.pk for s in instance.sites.all()]
        if instance.roles.exists():
            filter_data['role_id'] = [r.pk for r in instance.roles.all()]
        if instance.platforms.exists():
            filter_data['platform_id'] = [p.pk for p in instance.platforms.all()]
        if instance.tags.exists():
            filter_data['tag'] = [t.slug for t in instance.tags.all()]
        
        # Annotate the VM with zabbix_config
        qs = VirtualMachine.objects.annotate( zabbix_config=Exists( models.VMZabbixConfig.objects.filter( virtual_machine=OuterRef( 'pk' ) ) ) )
        filterset = filtersets.HostGroupDeviceFilterSet( data=filter_data, queryset=qs )    
        vm_table = tables.MatchingVMTable( filterset.qs.distinct(), orderable=True )
        

        RequestConfig(
            self.request, {
                'paginator_class': EnhancedPaginator,
                'per_page': get_paginate_count( self.request ),
            }
        ).configure( vm_table )
        
        return {
            "table": vm_table,
        }


# ------------------------------------------------------------------------------
# Device Mappings
# ------------------------------------------------------------------------------

@register_model_view(Device, "mappings")
class DeviceMappingsListView(generic.ObjectListView):
    queryset = Device.objects.all().prefetch_related( "tags", "platform", "role", "site" )
    table = tables.DeviceMappingsTable
    filterset = filtersets.DeviceMappingsFilterSet
    filterset_form = forms.DeviceMappingsFilterForm
    template_name = "netbox_zabbix/device_mappings.html"


# ------------------------------------------------------------------------------
# VM Mappings
# ------------------------------------------------------------------------------

@register_model_view(VirtualMachine, "mappings")
class VMMappingsListView(generic.ObjectListView):
    queryset = VirtualMachine.objects.all().prefetch_related( "tags", "platform", "role", "site" )
    table = tables.VMMappingsTable
    filterset = filtersets.VMMappingsFilterSet
    filterset_form = forms.VMMappingsFilterForm
    template_name = "netbox_zabbix/vm_mappings.html"


# ------------------------------------------------------------------------------
# NetBox Ony Devices
# ------------------------------------------------------------------------------

class NetBoxOnlyDevicesView(generic.ObjectListView):

    table          = tables.NetBoxOnlyDevicesTable
    filterset      = filtersets.NetBoxOnlyDevicesFilterSet
    filterset_form = forms.NetBoxOnlyDevicesFilterForm
    template_name  = "netbox_zabbix/netbox_only_devices.html"

    
    def get_queryset(self, request):
        try:
            zabbix_hostnames = {host["name"] for host in z.get_zabbix_hostnames()}


        # My Zabbix is down at the moment and I want to continue coding...
        except config.ZabbixConfigNotFound as e:
            messages.error( request, str( e ) )
            #return Device.objects.none()
        except Exception as e:
            messages.error( request, f"Failed to retrieve hostnames from Zabbix: {str(e)}" )
            #return Device.objects.none()

        zabbix_hostnames = []
        
        # Return only devices that are not in Zabbix
        return Device.objects.exclude( name__in=zabbix_hostnames ).prefetch_related( "site", "role", "platform", "tags" )
    

# ------------------------------------------------------------------------------
# NetBox Ony VMs
# ------------------------------------------------------------------------------

class NetBoxOnlyVMsView(generic.ObjectListView):
    table = tables.NetBoxOnlyVMsTable
    filterset = filtersets.NetBoxOnlyVMsFilterSet
    template_name = "netbox_zabbix/netbox_only_vms.html"

    def get_queryset(self, request):
        try:
            zabbix_hostnames = {host["name"] for host in z.get_zabbix_hostnames()}
        except config.ZabbixConfigNotFound as e:
            messages.error( request, str( e ) )
            return VirtualMachine.objects.none()
        except Exception as e:
            messages.error( request, f"Failed to retrieve hostnames from Zabbix: {str(e)}" )
            return VirtualMachine.objects.none()

        # Return only Virtual Machines that are not in Zabbix
        return VirtualMachine.objects.exclude( name__in=zabbix_hostnames )


# ------------------------------------------------------------------------------
# Zabbix Only Hosts
# ------------------------------------------------------------------------------

class ZabbixOnlyHostsView(GenericTemplateView):
    template_name = 'netbox_zabbix/zabbixonlyhosts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data( **kwargs )

        error_occurred = False        
        try:            
            data = z.get_zabbix_only_hostnames()
            web_address = config.get_zabbix_web_address()

        except config.ZabbixConfigNotFound as e:
            messages.error(self.request, str(e))
            error_occurred = True

        except Exception as e:
            messages.error(self.request, f"Failed to fetch data from Zabbix: {str(e)}")
            error_occurred = True
        
        if error_occurred:
            empty_table = tables.ZabbixOnlyHostTable([], orderable=False)
            RequestConfig(self.request).configure(empty_table)
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
            web_address = config.get_zabbix_web_address()
        except Exception as e:
            raise e
        
        context.update({
            'table': table,
            'web_address': web_address,
        })
        return context


# ------------------------------------------------------------------------------
# Quick Add Zabbix Interface
# ------------------------------------------------------------------------------

def device_quick_add_agent(request):
    redirect_url = request.GET.get("return_url") or request.META.get("HTTP_REFERER", "/")

    if request.method == 'GET':
        device_id = request.GET.get( "device_id" )
        device = Device.objects.filter( pk=device_id ).first()
        if not device:
            messages.error( request, f"No Device with id {device_id} found" )
        else:
            try:
                result = jobs.DeviceQuickAddAgent.run_now( device=device, user=request.user )
                messages.success( request, result )
            except Exception as e:
                messages.error( request, str( e ) )

    return redirect( redirect_url )


def device_quick_add_snmpv3(request):
    redirect_url = request.GET.get("return_url") or request.META.get("HTTP_REFERER", "/")
    return redirect( redirect_url )    
    

# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------

class DeviceZabbixConfigView(generic.ObjectView):
    queryset = models.DeviceZabbixConfig.objects.all()


class DeviceZabbixConfigListView(generic.ObjectListView):
    queryset = models.DeviceZabbixConfig.objects.all()
    filterset = filtersets.DeviceZabbixConfigFilterSet
    filterset_form = forms.DeviceZabbixConfigFilterForm
    table = tables.DeviceZabbixConfigTable


class DeviceZabbixConfigEditView(generic.ObjectEditView):
    queryset = models.DeviceZabbixConfig.objects.all()
    form = forms.DeviceZabbixConfigForm


class DeviceZabbixConfigDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceZabbixConfig.objects.all()


class VMZabbixConfigView(generic.ObjectView):
    queryset = models.VMZabbixConfig.objects.all()


class VMZabbixConfigListView(generic.ObjectListView):
    queryset = models.VMZabbixConfig.objects.all()
    filterset = filtersets.VMZabbixConfigFilterSet
    filterset_form = forms.VMZabbixConfigFilterForm
    table = tables.VMZabbixConfigTable


class VMZabbixConfigEditView(generic.ObjectEditView):
    queryset = models.VMZabbixConfig.objects.all()
    form = forms.VMZabbixConfigForm


class VMZabbixConfigDeleteView(generic.ObjectDeleteView):
    queryset = models.VMZabbixConfig.objects.all()


class ZabbixConfigListView(SingleTableView):
    template_name = 'netbox_zabbix/zabbixconfig_list.html'
    table_class = tables.ZabbixConfigTable
    
    def get_queryset(self):
        return list( models.DeviceZabbixConfig.objects.all() ) + list( models.VMZabbixConfig.objects.all() )
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table = self.table_class(self.get_queryset(), user=self.request.user)
        RequestConfig(
            self.request, {
                'paginator_class': EnhancedPaginator,
                'per_page': get_paginate_count(self.request),
            }
        ).configure(table)
        context['table'] = table
        return context


class ZabbixConfigEditView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            return redirect('plugins:netbox_zabbix:devicezabbixconfig_edit', pk=models.DeviceZabbixConfig.objects.get(pk=pk).pk)
        except models.DeviceZabbixConfig.DoesNotExist:
            pass

        try:
            return redirect('plugins:netbox_zabbix:vmzabbixconfig_edit', pk=models.VMZabbixConfig.objects.get(pk=pk).pk)
        except models.VMZabbixConfig.DoesNotExist:
            pass

        raise Http404("Host not found")    


class ZabbixConfigDeleteView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            models.DeviceZabbixConfig.objects.get(pk=pk)
            return redirect('plugins:netbox_zabbix:devicezabbixconfig_delete', pk=pk)
        except models.DeviceZabbixConfig.DoesNotExist:
            pass

        try:
            models.VMZabbixConfig.objects.get(pk=pk)
            return redirect('plugins:netbox_zabbix:vmzabbixconfig_delete', pk=pk)
        except models.VMZabbixConfig.DoesNotExist:
            pass

        raise Http404("Host not found")


class ImportableDeviceListView(generic.ObjectListView):
    table = tables.ImportableDeviceTable
    template_name = "netbox_zabbix/importabledevice_list.html"

    def get_extra_context(self, request):
        super().get_extra_context(request)

        return { "validate_button": not config.get_auto_validate_importables() }
    
    def get_queryset(self, request):
        try:
            zabbix_hostnames = {host["name"] for host in z.get_zabbix_hostnames()}
        except Exception as e:
            messages.error( request, f"Error fetching hostnames from Zabbix: {e}" )
            return Device.objects.none()
    
        # Devices not managed by Zabbix (by name) and not already imported (no ZabbixConfig)
        return Device.objects.filter(
            name__in=zabbix_hostnames
        ).exclude(
            id__in=models.DeviceZabbixConfig.objects.values_list( "device_id", flat=True )
        )


    def post(self, request, *args, **kwargs):
        if '_validate_device' in request.POST:
            selected_ids = request.POST.getlist( 'pk' )
        
            if not selected_ids:
                messages.error( request, "Please select a device to validate." )
            elif len( selected_ids ) > 1:
                messages.error( request, "Only one device can be validated at a time." )
            else:
                device = Device.objects.filter( pk=selected_ids[0] ).first()
                if device:
                    try:
                        logger.info( f"Validating device: {device.name}" )
                        result = jobs.ValidateDeviceOrVM.run_now( device_or_vm=device, user=request.user )
                        messages.success( request, result )
                    except Exception as e:
                        messages.error( request, str( e ) )
        
            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        if '_import_device_from_zabbix' in request.POST:

            # Add a check to make sure there are any selected hosts, print a warning if not.

            selected_ids = request.POST.getlist( 'pk' )
            queryset = Device.objects.filter( pk__in=selected_ids )
            
            success_counter = 0
            max_success_messages = config.get_max_success_notifications()
            
            for device in queryset:
                try:
                    logger.info ( f"importing device {device.name}" )                    
                    job = jobs.ImportFromZabbix.run_job( device_or_vm=device, user=request.user )
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {device.name} from Zabbix' )                    
                    if success_counter < max_success_messages:
                        messages.success(request, message)
                        success_counter += 1

                except Exception as e:
                    msg = f"Failed to create job for {request.user} to import device '{device}' from Zabbix {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )

            if success_counter == max_success_messages:
                messages.info(request, f"Queued {len(queryset) - success_counter} more jobs without notifications.")

            return redirect( request.POST.get( 'return_url' ) or request.path )
        


        return super().get( request, *args, **kwargs )


class ImportableVMListView(generic.ObjectListView):
    table = tables.ImportableVMTable
    template_name = "netbox_zabbix/importablevm_list.html"
    
    
    def get_extra_context(self, request):
        super().get_extra_context(request)
    
        return { "validate_button": not config.get_auto_validate_importables() }
    
    def get_queryset(self, request):
        try:
            zabbix_hostnames = {host["name"] for host in z.get_zabbix_hostnames()}
        except Exception as e:
            messages.error( request, f"Error fetching hostnames from Zabbix: {e}" )
            return VirtualMachine.objects.none()
    
        # VMs not managed by Zabbix (by name) and not already imported (no ZabbixConfig)
        queryset = VirtualMachine.objects.filter(
            name__in=zabbix_hostnames
        ).exclude(
            id__in=models.VMZabbixConfig.objects.values_list( "virtual_machine_id", flat=True )
        )

        return queryset
        

    def post(self, request, *args, **kwargs):

        if '_validate_vm' in request.POST:
            selected_ids = request.POST.getlist( 'pk' )
        
            if not selected_ids:
                messages.error( request, "Please select a VM to validate." )
            elif len( selected_ids ) > 1:
                messages.error( request, "Only one VM can be validated at a time." )
            else:
                vm = VirtualMachine.objects.filter( pk=selected_ids[0] ).first()
                if vm:
                    try:
                        logger.info( f"Validating VM: {vm.name}" )
                        result = jobs.ValidateDeviceOrVM.run_now( device_or_vm=vm, user=request.user )
                        messages.success( request, result )
                    except Exception as e:
                        messages.error( request, str( e ) )
            
            return redirect( request.POST.get( 'return_url' ) or request.path )
            
        

        if '_import_vm_from_zabbix' in request.POST:
    
            # Add a check to make sure there are any selected hosts, print a warning if not.
            selected_ids = request.POST.getlist( 'pk' )
            queryset = VirtualMachine.objects.filter( pk__in=selected_ids )


            success_counter = 0
            max_success_messages = config.get_max_success_notifications()

            for vm in queryset:
                try:
                    logger.info ( f"importing vm {vm.name}" )                    
                    job = jobs.ImportFromZabbix.run_job( device_or_vm=vm, user=request.user )    
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {vm.name} from Zabbix' )
                    if success_counter < max_success_messages:
                        messages.success(request, message)
                        success_counter += 1    
                except Exception as e:
                    msg = f"Failed to create job for {request.user} to import vm '{vm}' from Zabbix {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )

            if success_counter == max_success_messages:
                messages.info(request, f"Queued {len(queryset) - success_counter} more jobs without notifications.")
            
            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        return super().get( request, *args, **kwargs )
    

# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------

# Device Agent

class DeviceAgentInterfaceView(generic.ObjectView):
    queryset = models.DeviceAgentInterface.objects.all()


class DeviceAgentInterfaceListView(generic.ObjectListView):
    queryset = models.DeviceAgentInterface.objects.all()
    filterset = filtersets.DeviceAgentInterfaceFilterSet
#    filterset_form = forms.DeviceAgentInterfaceFilterForm
    table = tables.DeviceAgentInterfaceTable


class DeviceAgentInterfaceEditView(generic.ObjectEditView):
    queryset = models.DeviceAgentInterface.objects.all()
    form = forms.DeviceAgentInterfaceForm
    template_name = 'netbox_zabbix/device_agent_interface_edit.html'


class DeviceAgentInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceAgentInterface.objects.all()


# Device SNMPv3

class DeviceSNMPv3InterfaceView(generic.ObjectView):
    queryset = models.DeviceSNMPv3Interface.objects.all()


class DeviceSNMPv3InterfaceListView(generic.ObjectListView):
    queryset = models.DeviceSNMPv3Interface.objects.all()
    filterset = filtersets.DeviceSNMPv3InterfaceFilterSet
#    filterset_form = forms.DeviceSNMPv3InterfaceFilterForm
    table = tables.DeviceSNMPv3InterfaceTable


class DeviceSNMPv3InterfaceEditView(generic.ObjectEditView):
    queryset = models.DeviceSNMPv3Interface.objects.all()
    form = forms.DeviceSNMPv3InterfaceForm
    template_name = 'netbox_zabbix/device_snmpv3_interface_edit.html'
    

class DeviceSNMPv3InterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceSNMPv3Interface.objects.all()


# VM Agent

class VMAgentInterfaceView(generic.ObjectView):
    queryset = models.VMAgentInterface.objects.all()


class VMAgentInterfaceListView(generic.ObjectListView):
    queryset = models.VMAgentInterface.objects.all()
    filterset = filtersets.VMAgentInterfaceFilterSet
    #filterset_form = forms.VMAgentInterfaceFilterForm
    table = tables.VMAgentInterfaceTable


class VMAgentInterfaceEditView(generic.ObjectEditView):
    queryset = models.VMAgentInterface.objects.all()
    form = forms.VMAgentInterfaceForm
    template_name = 'netbox_zabbix/vm_agent_interface_edit.html'


class VMAgentInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.VMAgentInterface.objects.all()


# VM SNMPv3

class VMSNMPv3InterfaceView(generic.ObjectView):
    queryset = models.VMSNMPv3Interface.objects.all()


class VMSNMPv3InterfaceListView(generic.ObjectListView):
    queryset = models.VMSNMPv3Interface.objects.all()
    filterset = filtersets.VMSNMPv3InterfaceFilterSet
    #filterset_form = forms.VMSNMPv3InterfaceFilterForm
    table = tables.VMSNMPv3InterfaceTable


class VMSNMPv3InterfaceEditView(generic.ObjectEditView):
    queryset = models.VMSNMPv3Interface.objects.all()
    form = forms.VMSNMPv3InterfaceForm
    template_name = 'netbox_zabbix/vm_snmpv3_interface_edit.html'
    

class VMSNMPv3InterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.VMSNMPv3Interface.objects.all()


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------

class TagMappingView(generic.ObjectView):
    queryset = models.TagMapping.objects.all()

class TagMappingListView(generic.ObjectListView):
    queryset = models.TagMapping.objects.all()
    table = tables.TagMappingTable
    template_name = 'netbox_zabbix/tag_mapping_list.html'

class TagMappingEditView(generic.ObjectEditView):
    queryset = models.TagMapping.objects.all()
    form = forms.TagMappingForm
    template_name = 'netbox_zabbix/tag_mapping_edit.html'

class TagMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.TagMapping.objects.all()
