from django.template.defaultfilters import pluralize, capfirst
from django.views.decorators.http import require_POST
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView as GenericTemplateView
from django.db.models import Count, F
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from django_tables2 import RequestConfig, SingleTableView
from django.views import View
from django.http import Http404

from utilities.paginator import EnhancedPaginator, get_paginate_count
from dcim.models import Device
from netbox.views import generic


# NetBox Zabbix Imports
from netbox_zabbix import zabbix as z
from netbox_zabbix import filtersets, forms, models, tables, jobs

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
    queryset = (
       models.Template.objects
       .annotate(
           # Count the related VMHosts and DeviceHosts separately
           vmhost_count=Count('vmhost'),
           devicehost_count=Count('devicehost')
       )
       .annotate(
           # Add the two counts together to get the total host count
           host_count=F('vmhost_count') + F('devicehost_count')
       )
    )
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

class DeviceHostView(generic.ObjectView):
    queryset = models.DeviceHost.objects.all()


class DeviceHostListView(generic.ObjectListView):
    queryset = models.DeviceHost.objects.all()
    filterset = filtersets.DeviceHostFilterSet
    filterset_form = forms.DeviceHostFilterForm
    table = tables.DeviceHostTable


class DeviceHostEditView(generic.ObjectEditView):
    queryset = models.DeviceHost.objects.all()
    form = forms.DeviceHostForm


class DeviceHostDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceHost.objects.all()


class VMHostView(generic.ObjectView):
    queryset = models.VMHost.objects.all()


class VMHostListView(generic.ObjectListView):
    queryset = models.VMHost.objects.all()
    filterset = filtersets.VMHostFilterSet
    filterset_form = forms.VMHostFilterForm
    table = tables.VMHostTable


class VMHostEditView(generic.ObjectEditView):
    queryset = models.VMHost.objects.all()
    form = forms.VMHostForm


class VMHostDeleteView(generic.ObjectDeleteView):
    queryset = models.VMHost.objects.all()

    
class ManagedHostsListView(SingleTableView):
    template_name = 'netbox_zabbix/managed_hosts_list.html'
    table_class = tables.ManagedHostTable
    
    def get_queryset(self):
        return list( models.DeviceHost.objects.all() ) + list( models.VMHost.objects.all() )
    

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


class ManagedHostEditView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            return redirect('plugins:netbox_zabbix:devicehost_edit', pk=models.DeviceHost.objects.get(pk=pk).pk)
        except models.DeviceHost.DoesNotExist:
            pass

        try:
            return redirect('plugins:netbox_zabbix:vmhost_edit', pk=models.VMHost.objects.get(pk=pk).pk)
        except models.VMHost.DoesNotExist:
            pass

        raise Http404("Host not found")    


class ManagedHostDeleteView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            models.DeviceHost.objects.get(pk=pk)
            return redirect('plugins:netbox_zabbix:devicehost_delete', pk=pk)
        except models.DeviceHost.DoesNotExist:
            pass

        try:
            models.VMHost.objects.get(pk=pk)
            return redirect('plugins:netbox_zabbix:vmhost_delete', pk=pk)
        except models.VMHost.DoesNotExist:
            pass

        raise Http404("Host not found")


class UnmanagedDeviceListView(generic.ObjectListView):
    queryset = Device.objects.exclude( id__in = models.DeviceHost.objects.values_list( "device_id", flat=True ) )
    table = tables.UnmanagedDeviceTable
    template_name = "netbox_zabbix/unmanaged_device_list.html"

    def post(self, request, *args, **kwargs):
        if '_import_zabbix' in request.POST:
            selected_ids = request.POST.getlist( 'pk' )
            queryset = Device.objects.filter( pk__in=selected_ids )

            cfg = models.Config.objects.first()
            if not cfg:
                msg = "Missing Zabbix Configuration"
                logger.error( msg )
                messages.error( request, msg )
            else:
                for device in queryset:
                    try:
                        job = jobs.ImportDeviceFromZabbix.run_job( cfg.api_endpoint, cfg.token, device, user=request.user )

                        message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {device.name} from Zabbix' )
                        messages.success( request, message )

                    except Exception as e:
                        messages.error( request, f"Failed to create job to import {device} from Zabbix" )
                    
            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        return super().get( request, *args, **kwargs )
                 


def nb_only_hosts(request):
    logger.info("nb_only_hosts")
    return redirect( request.META.get( 'HTTP_REFERER', '/' ) )


class ZBXOnlyHostsView(GenericTemplateView):
    template_name = 'netbox_zabbix/zabbix_only_hosts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data( **kwargs )

        # Check that cfg exists!
        cfg = models.Config.objects.first()
        if not cfg:
            msg = "Missing Zabbix Configuration"
            logger.error( msg )
            messages.error( self.request, msg )
            # Provide an empty valid table
            empty_table = tables.ZabbixOnlyHostTable([], orderable=False)
            RequestConfig(self.request).configure(empty_table)
            context['table'] = empty_table
            return context          
        
        try:
            data = z.get_zabbix_only_hostnames( cfg.api_endpoint, cfg.token )
        except Exception as e:
            messages.error(self.request, f"Failed to fetch data from Zabbix: {str(e)}")
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
        
        context.update({
            'table': table,
            'web_address': cfg.web_address,
        })
        return context



# ------------------------------------------------------------------------------
# Interfaces
#

# - Agent

class DeviceAgentInterfaceView(generic.ObjectView):
    queryset = models.DeviceAgentInterface.objects.all()


class DeviceAgentInterfaceListView(generic.ObjectListView):
    queryset = models.DeviceAgentInterface.objects.all()
#    filterset = filtersets.DeviceAgentInterfaceFilterSet
#    filterset_form = forms.DeviceAgentInterfaceFilterForm
    table = tables.DeviceAgentInterfaceTable


class DeviceAgentInterfaceEditView(generic.ObjectEditView):
    queryset = models.DeviceAgentInterface.objects.all()
    form = forms.DeviceAgentInterfaceForm
    template_name = 'netbox_zabbix/device_agent_interface_edit.html'

class DeviceAgentInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceAgentInterface.objects.all()


# - SNMPv3

class DeviceSNMPv3InterfaceView(generic.ObjectView):
    queryset = models.DeviceSNMPv3Interface.objects.all()


class DeviceSNMPv3InterfaceListView(generic.ObjectListView):
    queryset = models.DeviceSNMPv3Interface.objects.all()
#    filterset = filtersets.DeviceSNMPv3InterfaceFilterSet
#    filterset_form = forms.DeviceSNMPv3InterfaceFilterForm
    table = tables.DeviceSNMPv3InterfaceTable


class DeviceSNMPv3InterfaceEditView(generic.ObjectEditView):
    queryset = models.DeviceSNMPv3Interface.objects.all()
    form = forms.DeviceSNMPv3InterfaceForm
    template_name = 'netbox_zabbix/device_snmpv3_interface_edit.html'
    

class DeviceSNMPv3InterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceSNMPv3Interface.objects.all()

