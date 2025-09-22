# views.py
from core.tables.jobs import JobTable
import netbox_zabbix.config as config
from django.shortcuts import get_object_or_404

from django.contrib import messages
from django.db.models import Count, F
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
from netbox_zabbix.utils import validate_quick_add

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

    def post(self, request, *args, **kwargs):
        obj = self.get_object( **kwargs )
    
        if obj:
            messages.error( request, "You cannot delete the configuration." )
            return redirect('plugins:netbox_zabbix:config_list' )
    
        return super().post( request, *args, **kwargs )
    

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
        jobs.ImportZabbixSetting.run_now( name=f"import zabbix settings" )
    except Exception as e:
        raise e
    
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


class TemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Template.objects.all()
    table = tables.TemplateTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:template_list')


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
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}" ) )
        return None, None, e

    except Exception as e:
        error_msg = "Connection to Zabbix failed."
        logger.error( f"{error_msg} {e}" )
        if request:
            messages.error( request, mark_safe( error_msg + "<br>" + f"{e}" ) )
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e


def import_templates(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_templates( request )
    return redirect( redirect_url )


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


class ProxyBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Proxy.objects.all()
    table = tables.ProxyTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxy_list')


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
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e


def import_proxies(request):
    """
    View-based wrapper around import proxies.
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxies( request )
    return redirect( redirect_url )


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


class ProxyGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ProxyGroup.objects.all()
    table = tables.ProxyGroupTable

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:proxygroup_list')


def proxy_groups_review_deletions(request):
    items = models.ProxyGroup.objects.filter( marked_for_deletion=True )
    return render( request, 'netbox_zabbix/proxygroup_review_deletions.html', {'items': items} )


@require_POST
def proxy_groups_confirm_deletions(request):
    selected_ids = request.POST.getlist( 'confirm_ids' )
    models.ProxyGroup.objects.filter( id__in=selected_ids ).delete()
    return redirect( 'plugins:netbox_zabbix:proxygroup_review_deletions' )


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
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e


def import_proxy_groups(request):
    """
    View-based wrapper around import proxy groups
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_proxy_groups( request )
    return redirect( redirect_url )


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


class HostGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = models.HostGroup.objects.all()
    table = tables.HostGroupTable

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
        config.set_connection = False
        config.set_last_checked = timezone.now()
        return None, None, e


def import_host_groups(request):
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    run_import_host_groups( request )
    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Quick Add Zabbix Interface
# ------------------------------------------------------------------------------


def device_validate_quick_add(request):
    redirect_url = request.GET.get( "return_url ") or request.META.get( "HTTP_REFERER", "/" )
    if request.method == 'GET':
        device_id = request.GET.get( "device_id" )
        device = Device.objects.filter( pk=device_id ).first()
        if not device:
            messages.error( request, f"No Device with id {device_id} found" )
        else:
            try:
                validate_quick_add( device )
                messages.success( request, f"{device.name} is valid" )
            except Exception as e:
                messages.error( request, str( e ) )
    return redirect( redirect_url )


def device_quick_add_agent(request):
    redirect_url = request.GET.get( "return_url ") or request.META.get( "HTTP_REFERER", "/" )

    if request.method == 'GET':
        device_id = request.GET.get( "device_id" )
        device = Device.objects.filter( pk=device_id ).first()
        if not device:
            messages.error( request, f"No Device with id {device_id} found" )
        else:
            try:
                validate_quick_add( device )
                job = jobs.ProvisionDeviceAgent.run_job( device=device, request=request)
                message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to add agent for {device.name}' )
                messages.success( request, message )
            except Exception as e:
                messages.error( request, str( e ) )

    return redirect( redirect_url )


def device_quick_add_snmpv3(request):
    redirect_url = request.GET.get("return_url") or request.META.get("HTTP_REFERER", "/")

    if request.method == 'GET':
        device_id = request.GET.get( "device_id" )
        device = Device.objects.filter( pk=device_id ).first()
        if not device:
            messages.error( request, f"No Device with id {device_id} found" )
        else:
            try:
                validate_quick_add( device )
                job = jobs.ProvisionDeviceSNMPv3.run_job( device=device, reques=request )
                message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to add SNMPv3 for {device.name}' )
                messages.success( request, message )
            except Exception as e:
                messages.error( request, str( e ) )
    return redirect( redirect_url )    


# ------------------------------------------------------------------------------
# NetBox Ony Devices
# ------------------------------------------------------------------------------


class NetBoxOnlyDevicesView(generic.ObjectListView):
    """
    View that lists NetBox devices which are not yet represented in Zabbix.
    For each device, we also precompute and cache which DeviceMapping
    applies (per interface type: Agent or SNMP). This avoids N+1 queries
    when rendering the table.
    """

    table = tables.NetBoxOnlyDevicesTable
    filterset = filtersets.NetBoxOnlyDevicesFilterSet
    template_name = "netbox_zabbix/netbox_only_devices.html"


    def build_device_mapping_cache(self, queryset):

        # Load all mappings + M2M fields at once
        all_mappings = (
            models.DeviceMapping.objects.prefetch_related("sites", "roles", "platforms")
        )

        # Turn mappings into dictionaries so that all filtering can be done
        # in Python instead of repetaded database queries.
        # Each dict contains the mapping object itself and its filter sets.
        mappings = []
        for m in all_mappings:
            mappings.append({
                "obj": m,
                "default": m.default,
                "interface_type": m.interface_type,
                "sites": set(m.sites.values_list("id", flat=True)),
                "roles": set(m.roles.values_list("id", flat=True)),
                "platforms": set(m.platforms.values_list("id", flat=True)),
            })
    

        # Build a lookup cache of (device.id, interface_type) -> mapping
        #
        # Otherwise, when rendering the table, a to call
        # `DeviceMapping.get_matching_filter()` is required per device * per interface type,
        # which means hundreds/thousands of DB queries.
        #
        # Instead, we compute everything once here, in-memory, in O(#devices × #mappings),
        # and table rendering just does a dictionary lookup.
        #
        cache = {}
        for device in queryset:
            device_site = device.site_id
            device_role = device.role_id
            device_platform = device.platform_id
    
            for interface_type in [ models.InterfaceTypeChoices.Agent, models.InterfaceTypeChoices.SNMP, ]:
                mapping = self._find_best_mapping( device_site, device_role, device_platform, interface_type, mappings )
                cache[(device.pk, interface_type)] = mapping
    
        return cache

    def get_queryset(self, request):

        """
        Build the base queryset for devices, and precompute a mapping cache
        so table rendering can look up the correct DeviceMapping for each
        device without hitting the database repeatedly.
        """
        
        # Get all devices that do NOT already exist in Zabbix
        zabbix_hostnames = z.get_cached_zabbix_hostnames()
        
        if config.get_exclude_custom_field_enabled():
            custom_field_name = config.get_exclude_custom_field_name()
            filter_kwargs = { f"custom_field_data__{custom_field_name}": True }
            queryset = (
                Device.objects
                .exclude( name__in=zabbix_hostnames )
                .exclude(**filter_kwargs) 
                .select_related( "site", "role", "platform" )
                .prefetch_related( "tags", "zbx_device_config" )
            )
        else:
            queryset = (
                Device.objects
                .exclude( name__in=zabbix_hostnames )
                .select_related( "site", "role", "platform" )
                .prefetch_related( "tags", "zbx_device_config" )
            )

        # Build the mapping cache
        self.device_mapping_cache = self.build_device_mapping_cache(queryset)

        return queryset

    def get_table(self, queryset, request, has_bulk_actions):
        # Let NetBox build the table first
        table = super().get_table(queryset, request, has_bulk_actions)
    
        # Now attach the cache
        table.device_mapping_cache = getattr(self, "device_mapping_cache", {})
    
        return table

    def _find_best_mapping(self, site_id, role_id, platform_id, intf_type, mappings):
        """
        Given a device (represented by its site/role/platform IDs) and an interface type,
        find the most appropriate DeviceMapping from the preloaded list.
        """

        # Filter candidates - none default mappings that either explicitly match
        # the interface type or are 'Any'.
        candidates = [
            m for m in mappings
            if not m["default"] and (
                m["interface_type"] == intf_type or m["interface_type"] == models.InterfaceTypeChoices.Any
            )
        ]

        # Keep only those that match this device
        def matches(m):
            site_ok = not m["sites"] or site_id in m["sites"]
            role_ok = not m["roles"] or role_id in m["roles"]
            platform_ok = not m["platforms"] or platform_id in m["platforms"]
            return site_ok and role_ok and platform_ok

        matches_filtered = [ m for m in candidates if matches( m ) ]

        # Pick the *most specific* match.
        # Specificity = a mapping that sets more filters (sites, roles, platforms).
        if matches_filtered:
            matches_filtered.sort(
                key=lambda m: ( bool( m["sites"] ), bool( m["roles"] ), bool( m["platforms"] ) ),
                reverse=True
            )
            return matches_filtered[0]["obj"]

        # If no matches, fall back to the default mapping.
        for m in mappings:
            if m["default"]:
                return m["obj"]

        return None
    
    def get_extra_context(self, request, instance=None):
        """
        Pass the view instance itself to the template context, so the table
        can access `view.device_mapping_cache` when rendering columns.
        """
        return {"view": self}
    
    def post(self, request, *args, **kwargs):

        if '_validate_quick_add' in request.POST:
            
            selected_ids = request.POST.getlist( 'pk' )
            queryset = Device.objects.filter( pk__in=selected_ids )
            
            for device in queryset:
                try:
                    validate_quick_add( device )
                    messages.success( request, f"{device.name} is valid" )
                except Exception as e:
                    messages.error( request, f"{str( e )}" )

            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        if '_quick_add_agent' in request.POST:

            # Add a check to make sure there are any selected hosts, print a warning if not.
            selected_ids = request.POST.getlist( 'pk' )
            queryset = Device.objects.filter( pk__in=selected_ids )

            success_counter = 0
            max_success_messages = config.get_max_success_notifications()

            for device in queryset:
                try:
                    validate_quick_add( device )
                    job = jobs.ProvisionDeviceAgent.run_job( device=device, request=request )
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to add agent for {device.name}' )
                    if success_counter < max_success_messages:
                        messages.success( request, message )
                        success_counter += 1

                except Exception as e:
                    msg = f"Failed to create job for {request.user} to quick add agent to '{device}' {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )
            if len( queryset ) > max_success_messages:
                suppressed = len(queryset) - max_success_messages
                messages.info(request, f"Queued {suppressed} more job{'s' if suppressed != 1 else ''} without notifications." )
            return redirect( request.POST.get( 'return_url' ) or request.path )

        if '_quick_add_snmpv3' in request.POST:
        
            # Add a check to make sure there are any selected hosts, print a warning if not.
            selected_ids = request.POST.getlist( 'pk' )
            queryset = Device.objects.filter( pk__in=selected_ids )

            success_counter = 0
            max_success_messages = config.get_max_success_notifications()

            for device in queryset:
                try:
                    validate_quick_add( device )
                    job = jobs.ProvisionDeviceSNMPv3.run_job( device=device, request=request )
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to add SNMPv3 for {device.name}' )
                    if success_counter < max_success_messages:
                        messages.success( request, message )
                        success_counter += 1

                except Exception as e:
                    msg = f"Failed to create job for {request.user} to quick add snmpv3 to '{device}' {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )

            if len( queryset ) > max_success_messages:
                suppressed = len(queryset) - max_success_messages
                messages.info(request, f"Queued {suppressed} more job{'s' if suppressed != 1 else ''} without notifications." )

            return redirect( request.POST.get( 'return_url' ) or request.path )


# ------------------------------------------------------------------------------
# NetBox Ony VMs
# ------------------------------------------------------------------------------


class NetBoxOnlyVMsView(generic.ObjectListView):
    table = tables.NetBoxOnlyVMsTable
    #filterset = filtersets.NetBoxOnlyVMsFilterSet
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


class DeviceZabbixConfigBulkDeleteView(generic.BulkDeleteView):
    queryset = models.DeviceZabbixConfig.objects.all()
    table = tables.DeviceZabbixConfigTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:devicezabbixconfig_list')


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


# ------------------------------------------------------------------------------
# Device & VM Zabbix Configurations (Combined)
# ------------------------------------------------------------------------------


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


# ------------------------------------------------------------------------------
# Sync With Zabbix
# ------------------------------------------------------------------------------


def run_sync_device_with_zabbix(request):
    try:
        zabbix_config_id = request.GET.get( "device_zabbix_config_id" )
        config = models.DeviceZabbixConfig.objects.get( id = zabbix_config_id )

        jobs.UpdateZabbixHost.run_job_now( zabbix_config=config, request=request )

        messages.success( request, f"Sync {config.get_name()} with Zabbix succeeded." )
    except Exception as e:
        messages.error( request, f"Failed to sync {config.get_name()} with Zabbix. Reason: {str( e ) }" )


def sync_device_with_zabbix(request):
    """
    View-based wrapper around sync with Zabbix
    """
    redirect_url = request.GET.get( "return_url" ) or request.META.get( "HTTP_REFERER", "/" )
    
    run_sync_device_with_zabbix( request )

    return redirect( redirect_url )


# ------------------------------------------------------------------------------
# Importable Devices
# ------------------------------------------------------------------------------


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
                        logger.info( f"Validating device '{device.name}'" )
                        result = jobs.ValidateDeviceOrVM.run_now( model_instance=device, request=request, name=f"Validate {device.name}" )
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
                    logger.info ( f"Importing device {device.name}" )
                    job = jobs.ImportFromZabbix.run_job( model_instance=device, request=request )
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {device.name} from Zabbix' )
                    if success_counter < max_success_messages:
                        messages.success( request, message )
                        success_counter += 1

                except Exception as e:
                    msg = f"Failed to create job for {request.user} to import device '{device}' from Zabbix {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )

            if len( queryset ) > max_success_messages:
                suppressed = len(queryset) - max_success_messages
                messages.info(request, f"Queued {suppressed} more job{'s' if suppressed != 1 else ''} without notifications." )
            
            return redirect( request.POST.get( 'return_url' ) or request.path )

        return super().get( request, *args, **kwargs )


# ------------------------------------------------------------------------------
# Importable VMs
# ------------------------------------------------------------------------------


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
                        logger.info( f"Validating VM '{vm.name}'" )
                        result = jobs.ValidateDeviceOrVM.run_now( model_instance=vm, request=request, name=f"Validate {vm.name}" )
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
                    job = jobs.ImportFromZabbix.run_job( device_or_vm=vm, user=request.user, request_id=request.id )
                    message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to import {vm.name} from Zabbix' )
                    if success_counter < max_success_messages:
                        messages.success(request, message)
                        success_counter += 1    
                except Exception as e:
                    msg = f"Failed to create job for {request.user} to import vm '{vm}' from Zabbix {str( e )}"
                    messages.error( request, msg )
                    logger.error( msg )

            if len( queryset ) > max_success_messages:
                suppressed = len(queryset) - max_success_messages
                messages.info(request, f"Queued {suppressed} more job{'s' if suppressed != 1 else ''} without notifications." )

            return redirect( request.POST.get( 'return_url' ) or request.path )
        
        return super().get( request, *args, **kwargs )


# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------

#
# Device Agent
#

class DeviceAgentInterfaceView(generic.ObjectView):
    queryset = models.DeviceAgentInterface.objects.all()


class DeviceAgentInterfaceListView(generic.ObjectListView):
    queryset = models.DeviceAgentInterface.objects.all()
    table = tables.DeviceAgentInterfaceTable
    filterset = filtersets.DeviceAgentInterfaceFilterSet


class DeviceAgentInterfaceEditView(generic.ObjectEditView):
    queryset = models.DeviceAgentInterface.objects.all()
    form = forms.DeviceAgentInterfaceForm
    template_name = 'netbox_zabbix/device_agent_interface_edit.html'


class DeviceAgentInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceAgentInterface.objects.all()

    def post(self, request, *args, **kwargs):
        # Get the interface instance to delete

        try:
            interface = self.get_object( pk=kwargs.get("pk") )
            hostid = interface.host.hostid
            interfaceid = interface.interfaceid
            name = interface.name

            # If the inteface is the main interface and if there are other agent interfaces
            # then Zabbix allows it to be deleted.
            if interface.main == models.MainChoices.YES and interface.host.agent_interfaces.all().count() < 1:
                return super().post(request, *args, **kwargs)
            
            # Otherwise a check to verify if there are templates that needs to be deleted before we can delete the interface.
            if not z.can_remove_interface( hostid, interfaceid ):
                messages.error( request, f"Interface {name} is linked to one or more items in Zabbix. Unable to delete interface." )
                return redirect( request.POST.get('return_url') or interface.host.get_absolute_url() )
        except:
            pass

        # If safe, proceed with normal deletion
        return super().post(request, *args, **kwargs)

class DeviceAgentInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.DeviceAgentInterface.objects.all()
    table = tables.DeviceAgentInterfaceTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:deviceagentinterface_list')


#
# Device SNMPv3
#

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
    
    def post(self, request, *args, **kwargs):
        # Get the interface instance to delete

        try:
            interface = self.get_object( pk=kwargs.get("pk") )
            hostid = interface.host.hostid
            interfaceid = interface.interfaceid
            name = interface.name

            # If the inteface is the main interface and if there are other agent interfaces
            # then Zabbix allows it to be deleted.
            if interface.main == models.MainChoices.YES and interface.host.snmpv3_interface.all().count() < 1:
                return super().post(request, *args, **kwargs)
            
            # Otherwise a check to verify if there are templates that needs to be deleted before we can delete the interface.
            if not z.can_remove_interface( hostid, interfaceid ):
                messages.error( request, f"Interface {name} is linked to one or more items in Zabbix. Unable to delete interface." )
                return redirect( request.POST.get('return_url') or interface.host.get_absolute_url() )
        except:
            pass

        # If safe, proceed with normal deletion
        return super().post(request, *args, **kwargs)


class DeviceSNMPv3InterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.DeviceSNMPv3Interface.objects.all()
    table = tables.DeviceSNMPv3InterfaceTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:devicesnmpv3interface_list')


#
# VM Agent
#

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

#
# VM SNMPv3
#

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


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingView(generic.ObjectView):
    queryset = models.InventoryMapping.objects.all()


class InventoryMappingListView(generic.ObjectListView):
    queryset = models.InventoryMapping.objects.all()
    table = tables.InventoryMappingTable
    template_name = 'netbox_zabbix/inv_mapping_list.html'


class InventoryMappingEditView(generic.ObjectEditView):
    queryset = models.InventoryMapping.objects.all()
    form = forms.InventoryMappingForm
    template_name = 'netbox_zabbix/inv_mapping_edit.html'


class InventoryMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.InventoryMapping.objects.all()


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


def count_matching_devices_for_mapping(obj):
    return obj.get_matching_devices().count()


@register_model_view(models.DeviceMapping, 'devices')
class DeviceMappingDevicesView(generic.ObjectView):
    queryset = models.DeviceMapping.objects.all()
    template_name = 'netbox_zabbix/device_mapping_devices.html'
    tab = ViewTab( label="Matching Devices",
                   badge=lambda obj: count_matching_devices_for_mapping( obj ),
                   weight=500 )
    
    def get_extra_context(self, request, instance):
        queryset = instance.get_matching_devices()
        table = tables.MatchingDeviceMappingTable( queryset )
        RequestConfig( request,
            {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
         ).configure( table )
            
        return {
            "table": table,
        }


class DeviceMappingView(generic.ObjectView):
    queryset = models.DeviceMapping.objects.all()
    template_name = 'netbox_zabbix/device_mapping.html'
    tab = ViewTab( label="Matching Devices",
                  badge=lambda obj: obj.count(),
                  weight=500 )
    
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
    queryset = models.DeviceMapping.objects.all()
    table = tables.DeviceMappingTable
    template_name = 'netbox_zabbix/device_mapping_list.html'


class DeviceMappingEditView(generic.ObjectEditView):
    queryset = models.DeviceMapping.objects.all()
    form = forms.DeviceMappingForm
    template_name = 'netbox_zabbix/device_mapping_edit.html'


class DeviceMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceMapping.objects.all()

    def get_return_url(self, request, obj=None):
        return reverse('plugins:netbox_zabbix:devicemapping_list')

    def post(self, request, *args, **kwargs):
        obj = self.get_object( **kwargs )
    
        if obj.default:
            messages.error( request, "You cannot delete the default mapping." )
            return redirect('plugins:netbox_zabbix:devicemapping_list' )
    
        return super().post( request, *args, **kwargs )


class DeviceMappingBulkDeleteView(generic.BulkDeleteView):
    queryset = models.DeviceMapping.objects.all()
    filterset_class = filtersets.DeviceMappingFilterSet
    table = tables.DeviceMappingTable

    def post(self, request, *args, **kwargs):
        # Determine which objects are being deleted
        selected_pks = request.POST.getlist( 'pk' )
        mappings = models.Mapping.objects.filter( pk__in=selected_pks )
    
        # Check if any default mappings are included
        default_mappings = mappings.filter( default=True )
        if default_mappings.exists():
            names = ", ".join( [m.name for m in default_mappings] )
            messages.error( request, f"Cannot delete default mapping(s): {names}" )
            return redirect('plugins:netbox_zabbix:devicemapping_list' )
    
        # No default mappings selected, proceed with normal deletion
        return super().post(request, *args, **kwargs)
    

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:devicemapping_list')


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingView(generic.ObjectView):
    queryset = models.VMMapping.objects.all()


class VMMappingListView(generic.ObjectListView):
    queryset = models.VMMapping.objects.all()
    table = tables.VMMappingTable
    template_name = 'netbox_zabbix/vm_mapping_list.html'


class VMMappingEditView(generic.ObjectEditView):
    queryset = models.VMMapping.objects.all()
    form = forms.VMMappingForm
    template_name = 'netbox_zabbix/vm_mapping_edit.html'


class VMMappingDeleteView(generic.ObjectDeleteView):
    queryset = models.VMMapping.objects.all()


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogView(generic.ObjectView):
    queryset = models.EventLog.objects.all()

    def get_extra_context(self, request, instance):
        from utilities.data import shallow_compare_dict

        # Find previous and next events (ordered by created)
        prev_event = models.EventLog.objects.filter( created__lt=instance.created ).order_by( '-created' ).first()
        next_event = models.EventLog.objects.filter( created__gt=instance.created ).order_by( 'created' ).first()
        

        if request.GET.get( 'format' ) in ['json', 'yaml']:
            format = request.GET.get('format')
        else:
            format = 'json'

        diff_added = shallow_compare_dict( instance.pre_data, instance.post_data )
        diff_removed = { x: instance.pre_data.get(x) for x in diff_added } if instance.pre_data else {}

        return { 'format': format, 'prev_event': prev_event, 'next_event': next_event, "diff_added": diff_added, "diff_removed": diff_removed }


class EventLogListView(generic.ObjectListView):
    queryset = models.EventLog.objects.all()
    table = tables.EventLogTable


class EventLogEditView(generic.ObjectView):
    queryset = models.EventLog.objects.all()


class EventLogDeleteView(generic.ObjectDeleteView):
    queryset = models.EventLog.objects.all()


class EventLogBulkDeleteView(generic.BulkDeleteView):
    queryset = models.EventLog.objects.all()
    table = tables.EventLogTable

    def get_return_url(self, request, obj=None):
            return reverse('plugins:netbox_zabbix:eventlog_list')


# ------------------------------------------------------------------------------
# Device Tab for Zabbix Details
# ------------------------------------------------------------------------------

@register_model_view(Device, name="Zabbix", path="zabbix")
class ZabbixDeviceTabView(generic.ObjectView):
    queryset = models.DeviceZabbixConfig.objects.all()
    tab = ViewTab(
        label="Zabbix",
        hide_if_empty=True,
        badge=lambda device: str( len( z.get_problems( device.name ) ) )  if models.DeviceZabbixConfig.objects.filter( device=device ).exists() else 0
    )

    def get(self, request, pk):
        device = get_object_or_404( Device, pk=pk )
        config = models.DeviceZabbixConfig.objects.filter( device=device ).first()

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
            },
        )


# ------------------------------------------------------------------------------
# Tasks Tab 
# ------------------------------------------------------------------------------


@register_model_view(models.DeviceZabbixConfig, name='jobs')
class DeviceZabbixConfigJobsTabView(generic.ObjectView):

    queryset = models.DeviceZabbixConfig.objects.all()
    tab = ViewTab( label="Tasks", badge=lambda instance: instance.jobs.count() )
    template_name = 'netbox_zabbix/device_jobs.html'

    def get_extra_context(self, request, instance):
        queryset = instance.jobs.all()
        table = JobTable( queryset )
        return { "table": table }


# ------------------------------------------------------------------------------
# Zabbix Diff Tab
# ------------------------------------------------------------------------------


@register_model_view(models.DeviceZabbixConfig, name='difference')
class DeviceZabbixConfigDiffTabView(generic.ObjectView):

    queryset = models.DeviceZabbixConfig.objects.all()
    tab = ViewTab( label="Difference", badge=lambda instance: int( instance.get_sync_status() ), hide_if_empty=True )
    template_name = 'netbox_zabbix/device_difference.html'

    def get_extra_context(self, request, instance):
        return { "diff": instance.get_sync_diff() }
    
# end