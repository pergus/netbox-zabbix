from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import pluralize, capfirst
from django.views.decorators.http import require_POST
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView as GenericTemplateView
from django.shortcuts import redirect, render
from django.db.models import Count
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from django_tables2 import RequestConfig
from utilities.paginator import EnhancedPaginator, get_paginate_count

from virtualization.models import VirtualMachine
from dcim.models import Device

from netbox_zabbix import zabbix as z
from netbox_zabbix import filtersets, forms, models, tables
from netbox.views import generic

import logging
logger = logging.getLogger( 'netbox.plugins.netbox_zabbix' )

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get( "netbox_zabbix", {} )

# ------------------------------------------------------------------------------
# Configuration 
#

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


def ConfigCheckConnectionView(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    cfg = models.Config.objects.first()
    
    if not cfg:
        msg = "Missing Zabbix Configuration"
        logger.error( msg )
        messages.error( request, msg )
        return redirect( redirect_url )

    try:
        z.verify_token( cfg.api_endpoint, cfg.token )
        cfg.version = z.get_version( cfg.api_endpoint, cfg.token )
        cfg.connection = True
        cfg.last_checked = timezone.now()
        cfg.save()
        messages.success( request, "Connection to Zabbix succeeded" )

    except Exception as e:
        error_msg = f"Failed to connect to {cfg.api_endpoint}: {e}"
        logger.error( error_msg )
        messages.error( request, error_msg )
        cfg.connection = False
        cfg.last_checked = timezone.now()
        cfg.save()

    return redirect( redirect_url )

# ------------------------------------------------------------------------------
# Templates
#

class TemplateView(generic.ObjectView):
    queryset = models.Template.objects.all()
    
    def get_extra_context(self, request, instance):
        excluded_fields = ['id', 'created', 'last_updated', 'custom_field_data' ]
        fields = [ ( capfirst(field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class TemplateListView(generic.ObjectListView):
    queryset = models.Template.objects.annotate( host_count = Count( 'host' ) )
    filterset = filtersets.TemplateFilterSet
    filterset_form = forms.TemplateFilterForm
    table = tables.TemplateTable    
    template_name = "netbox_zabbix/template_list.html"

    def get_extra_context(self, request):
        # Hide the default actions since a user isn't supposed to manually add templates.
        context = super().get_extra_context( request )
        context['actions'] = []
        return context


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


def sync_zabbix_templates(request):
    """
    View-based wrapper around template synchronization.
    """
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    cfg = models.Config.objects.first()

    if not cfg:
        msg = "Missing Zabbix Configuration"
        logger.error( msg )
        messages.error( request, msg )
        return redirect( redirect_url )

    try:
        added, deleted = z.synchronize_templates( cfg.api_endpoint, cfg.token )

        msg_lines = ["Syncing Zabbix Templates succeeded."]
        if added:
            msg_lines.append( f"Added {len( added )} template{ pluralize( len( added ) )}." )
        if deleted:
            msg_lines.append( f"Deleted {len( deleted )} template{ pluralize( len( deleted ) )}." )
        if not added and not deleted:
            msg_lines.append( "No changes detected." )

        messages.success( request, mark_safe( "<br>".join( msg_lines ) ) )

    except RuntimeError as e:
        error_msg = "Syncing Zabbix Templates failed."
        logger.error( f"{error_msg} {e}" )
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )

    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        messages.error( request, mark_safe( error_msg + "<br>" + f"{e}") )
        cfg.connection = False
        cfg.last_checked = timezone.now()
        cfg.save()

    return redirect( redirect_url)


# ------------------------------------------------------------------------------
# Hosts
#

class HostView(generic.ObjectView):
    queryset = models.Host.objects.all()

    def get_extra_context(self, request, instance):
        excluded_fields = [ 'created', 'last_updated', 'custom_field_data', 'content_type', 'object_id' ]
        fields = [ ( capfirst(field.verbose_name), field.name )  for field in instance._meta.fields if field.name not in excluded_fields ]
        return {'fields': fields}


class HostListView(generic.ObjectListView):
    queryset = models.Host.objects.all()
    filterset = filtersets.HostFilterSet
    filterset_form = forms.HostFilterForm
    table = tables.HostTable


class HostEditView(generic.ObjectEditView):
    queryset = models.Host.objects.all()
    form = forms.HostForm


class HostDeleteView(generic.ObjectDeleteView):
    queryset = models.Host.objects.all()

class UnsyncedDeviceListView(generic.ObjectListView):
    # Add a check to make sure the host exists in Zabbix
    queryset = Device.objects.none()
    table = tables.UnsyncedDeviceTable
    template_name = "netbox_zabbix/unsynced_devices.html"
    actions = []

    def get_queryset(self, request):
        device_ct = ContentType.objects.get( app_label='dcim', model='device' )
        linked_device_ids = models.Host.objects.filter( content_type=device_ct ).values_list( 'object_id', flat=True )
        self.device_ct = device_ct
        return Device.objects.exclude(id__in=linked_device_ids )

    def get_extra_context(self, request, instance=None):
        return {
            "device_ct": self.device_ct
        }


class UnsyncedVMListView(generic.ObjectListView):
    # Add a check to make sure the host exists in Zabbix
    queryset = VirtualMachine.objects.none()
    table = tables.UnsyncedVMTable
    template_name = "netbox_zabbix/unsynced_vms.html"
    actions = []

    def get_queryset(self, request):
        vm_ct = ContentType.objects.get( app_label='virtualization', model='virtualmachine' )
        linked_vm_ids = models.Host.objects.filter( content_type=vm_ct ).values_list( 'object_id', flat=True )
        self.vm_ct = vm_ct

        return VirtualMachine.objects.exclude( id__in=linked_vm_ids )

    def get_extra_context(self, request, instance=None):
        return { "vm_ct": self.vm_ct }


class NetBoxOnlyHostnameListView(GenericTemplateView):
    template_name = "netbox_zabbix/netbox_only_hostname_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        cfg = models.Config.objects.first()
        zabbix_hostnames = set()

        # Fetch Zabbix hostnames
        if cfg:
            try:
                zabbix_hostnames = set( h["name"] for h in z.get_zabbix_hostnames( cfg.api_endpoint, cfg.token ) )
            except Exception as e:
                logger.error( f"Failed to fetch Zabbix-only hostnames: {e}" )

        # Fetch NetBox hostnames (from Device and VirtualMachine models)
        netbox_hostnames = set( Device.objects.values_list( 'name', flat=True ) ).union( VirtualMachine.objects.values_list( 'name', flat=True ) )

        # Compute the difference between NetBox hostnames and Zabbix hostnames
        hostnames_only_in_netbox = netbox_hostnames - zabbix_hostnames

        # Convert to table-compatible format
        data = []
        for hostname in hostnames_only_in_netbox:
            # Check if it's a device or virtual machine and create the correct URL
            device = Device.objects.filter(name=hostname).first()
            virtual_machine = VirtualMachine.objects.filter(name=hostname).first()
                    
            url = None
            if device:
                url = device.get_absolute_url()  # Assuming Device model has get_absolute_url() method
            elif virtual_machine:
                url = virtual_machine.get_absolute_url()  # Assuming VirtualMachine model has get_absolute_url() method
        
            data.append({"name": hostname, "url": url})
        
#        { "name": hostname } for hostname in hostnames_only_in_netbox ]

        # Create the table
        table = tables.NetBoxOnlyHostnameTable( data )

        # Pagination
        RequestConfig( request, { 'paginator_class': EnhancedPaginator, 'per_page': get_paginate_count(request)} ).configure( table )

        context.update({ "table": table })

        return context
    

class ZabbixOnlyHostnameListView(GenericTemplateView):
    template_name = "netbox_zabbix/zabbix_only_hostname_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        cfg = models.Config.objects.first()
        zabbix_only_hostnames = []

        if cfg:
            try:
                zabbix_only_hostnames = z.get_zabbix_only_hostnames( cfg.api_endpoint, cfg.token )
            except Exception as e:
                logger.error(f"Failed to fetch Zabbix-only hostnames: {e}")

        # Convert to table-compatible format
        data = [ {"name": h["name"], "hostid": h["hostid"] } for h in zabbix_only_hostnames ]

        # Create the table
        table = tables.ZabbixOnlyHostnameTable(data)

        # Pagination
        RequestConfig( request, { 'paginator_class': EnhancedPaginator, 'per_page': get_paginate_count(request)} ).configure( table )

        context.update({ "table": table, "zabbix_web_address": cfg.web_address if cfg else None })

        return context
    
# ------------------------------------------------------------------------------
# Interfaces
#

def agent_interface_add(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    logger.info( "agent_interface_add" )
    return redirect( redirect_url )


def snmpv3_interface_add(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    logger.info( "snmpv3_interface_add" )
    return redirect( redirect_url )


def snmpv1_interface_add(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    logger.info( "snmpv1_interface_add" )
    return redirect( redirect_url )


def snmpv2c_interface_add(request):
    redirect_url = request.META.get('HTTP_REFERER', '/')
    logger.info( "snmpv2c_interface_add" )
    return redirect(redirect_url)

