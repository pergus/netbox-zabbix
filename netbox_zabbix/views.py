from django.template.defaultfilters import pluralize, capfirst
from django.views.decorators.http import require_POST
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, render
from django.db.models import Count
from django.contrib import messages
from django.utils import timezone
from django.conf import settings


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


def unsynced_hosts(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    logger.info( "unsynced_hosts" )
    return redirect( redirect_url )


def orphaned_nb_hosts(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    logger.info( "orphaned_nb_hosts" )
    return redirect( redirect_url )


def orphaned_zb_hosts(request):
    redirect_url = request.META.get( 'HTTP_REFERER', '/' )
    logger.info( "orphaned_zb_hosts" )
    return redirect( redirect_url )

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

