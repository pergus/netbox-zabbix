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
from virtualization.models import VirtualMachine
from netbox.views import generic


# NetBox Zabbix Imports
from netbox_zabbix import zabbix as z
from netbox_zabbix import filtersets, forms, models, tables, jobs
from netbox_zabbix.logger import logger

import netbox_zabbix.config as config


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


def ZabbixCheckConnectionView(request):
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

    try:
        added, deleted = z.synchronize_templates()

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
        config.set_connection = False
        config.set_last_checked = timezone.now()

    return redirect( redirect_url)


# ------------------------------------------------------------------------------
# Hosts
#

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


# Zabbix Config(s) (Devices & VMs)
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
        if '_import_device_from_zabbix' in request.POST:

            # Add a check to make sure there are any selected hosts, print a warning if not.
            selected_ids = request.POST.getlist( 'pk' )
            queryset = Device.objects.filter( pk__in=selected_ids )

            for device in queryset:
                try:
                    job = jobs.ImportFromZabbix.run_job( device_or_vm=device, user=request.user )

                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {device.name} from Zabbix' )
                    messages.success( request, message )

                except Exception as e:
                    msg = f"Failed to create job for {request.user} to import device '{device}' from Zabbix {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )

            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        return super().get( request, *args, **kwargs )


class ImportableVMListView(generic.ObjectListView):
    table = tables.ImportableVMTable
    template_name = "netbox_zabbix/importablevm_list.html"
    
    
    def get_queryset(self, request):
        try:
            zabbix_hostnames = {host["name"] for host in z.get_zabbix_hostnames()}
        except Exception as e:
            messages.error( request, f"Error fetching hostnames from Zabbix: {e}" )
            return VirtualMachine.objects.none()
    
        # VMs not managed by Zabbix (by name) and not already imported (no ZabbixConfig)
        return VirtualMachine.objects.filter(
            name__in=zabbix_hostnames
        ).exclude(
            id__in=models.VMZabbixConfig.objects.values_list( "virtual_machine_id", flat=True )
        )
    
    
    def post(self, request, *args, **kwargs):
        if '_import_vm_from_zabbix' in request.POST:
    
            # Add a check to make sure there are any selected hosts, print a warning if not.
            selected_ids = request.POST.getlist( 'pk' )
            queryset = VirtualMachine.objects.filter( pk__in=selected_ids )
    
            for vm in queryset:
                try:
                    job = jobs.ImportFromZabbix.run_job( device_or_vm=vm, user=request.user )
    
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {vm.name} from Zabbix' )
                    messages.success( request, message )
    
                except Exception as e:
                    msg = f"Failed to create job for {request.user} to import vm '{vm}' from Zabbix {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )
    
            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        return super().get( request, *args, **kwargs )
    
    

class NetBoxOnlyDevicesView(generic.ObjectListView):

    table = tables.NetBoxOnlyDevicesTable
    filterset = filtersets.NetBoxOnlyDevicesFilterSet
    template_name = "netbox_zabbix/netboxonlydevices.html"

    def get_queryset(self, request):
        try:
            zabbix_hostnames = {host["name"] for host in z.get_zabbix_hostnames()}
        except config.ZabbixConfigNotFound as e:
            messages.error( request, str( e ) )
            return Device.objects.none()
        except Exception as e:
            messages.error( request, f"Failed to retrieve hostnames from Zabbix: {str(e)}" )
            return Device.objects.none()

        # Return only devices that are not in Zabbix
        return Device.objects.exclude( name__in=zabbix_hostnames )


class NetBoxOnlyVMsView(generic.ObjectListView):
    table = tables.NetBoxOnlyVMsTable
    filterset = filtersets.NetBoxOnlyVMsFilterSet
    template_name = "netbox_zabbix/netboxonlyvms.html"

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
# Interfaces
#

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

