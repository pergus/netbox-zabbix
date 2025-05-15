import django_tables2 as tables
from netbox.tables import NetBoxTable, columns
from netbox.tables.columns import ActionsColumn
from django.utils.safestring import mark_safe

from netbox_zabbix import models

from django.urls import reverse

# ------------------------------------------------------------------------------
# Configuration
#

EXTRA_BUTTONS = """
<span class="dropdown">
    <button id="actions" type="button" class="btn btn-sm btn-primary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
        <i class="mdi mdi-plus-thick" aria-hidden="true"></i> Actions
    </button>

    <ul class="dropdown-menu" aria-labeled-by="actions">
        <li>
            <a class="dropdown-item"
                href="{% url 'plugins:netbox_zabbix:config_check_connection' %}">
                Check Connection
            </a>
        </li>
    </ul>
</span>
"""

class ConfigTable(NetBoxTable):
    class Meta(NetBoxTable.Meta):
        model = models.Config
        fields = ('name', 'api_endpoint', 'web_address', 'version', 'connection', 'last_checked_at', 'ip_assignment_method')
        default_columns = ('name', 'api_endpoint', 'version', 'connection', 'last_checked_at')

    name = tables.Column( linkify=True )
    actions = columns.ActionsColumn( extra_buttons=EXTRA_BUTTONS )


# ------------------------------------------------------------------------------
# Templates
#

class TemplateTable(NetBoxTable):
    name = tables.Column( linkify=True )
    host_count = columns.LinkedCountColumn( 
         viewname='plugins:netbox_zabbix:managed_hosts',
         url_params={'templates': 'pk'},
         verbose_name="Hosts" )
    
    class Meta(NetBoxTable.Meta):
        model = models.Template
        fields = ("name", "templateid", "host_count", "last_synced", "marked_for_deletion" )
        default_columns = ("name", "templateid", "host_count", "last_synced", "marked_for_deletion" )


# ------------------------------------------------------------------------------
# Hosts
#

class DeviceHostTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    device = tables.Column( accessor='device', verbose_name='Device', linkify=True )
    status = tables.Column()
    zabbix_host_id = tables.Column( verbose_name='Zabbix Host ID' )
    templates = tables.ManyToManyColumn(linkify_item=True)
    
    class Meta(NetBoxTable.Meta):
        model = models.DeviceHost
        fields = ('name', 'device', 'status', 'zabbix_host_id', 'templates')
        default_columns = ('name', 'device', 'status', 'templates')
    

class VMHostTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    virtual_machine = tables.Column( accessor='virtual_machine', verbose_name='VM', linkify=True )
    status = tables.Column()
    zabbix_host_id = tables.Column( verbose_name='Zabbix Host ID' )
    templates = tables.ManyToManyColumn(linkify_item=True)
    
    class Meta(NetBoxTable.Meta):
        model = models.VMHost
        fields = ('name', 'virtual_machine', 'status', 'zabbix_host_id',  'templates')
        default_columns = ('name', 'virtual_machine', 'status', 'templates')

        
class ManagedHostActionsColumn(ActionsColumn):

    def get_actions(self, record):
        actions = []
    
        if isinstance( record, models.DeviceHost ):
            prefix = 'devicehost'
        elif isinstance( record, models.VMHost ):
            prefix = 'vmhost'
        else:
            return []
    
        for action in ['edit', 'delete']:
            url = reverse( f'plugins:netbox_zabbix:{prefix}_{action}', args=[record.pk] )
            actions.append( (action, url) )
    
        return actions


class ManagedHostTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Host Name', linkify=True )
    type = tables.Column( empty_values=(), verbose_name='Type', order_by=('device__name', 'virtual_machine__name') )
    zabbix_host_id = tables.Column( verbose_name='Zabbix Host ID' )
    status = tables.Column()
    object = tables.Column( empty_values=(), verbose_name='NetBox Object', order_by=('device__name', 'virtual_machine__name') )

    actions = ManagedHostActionsColumn()
     
    class Meta(NetBoxTable.Meta):
        model = models.ManagedHost
        fields = ('name', 'object', 'status', 'type', 'zabbix_host_id', 'status', 'templates' )
        default_columns = ('name', 'object', 'status', 'templates', 'type' )

    def render_type(self, record):
        return 'Device' if isinstance( record, models.DeviceHost ) else 'VM'


    def render_object(self, record):
           if isinstance(record, models.DeviceHost):
               # Return the device link
               return mark_safe( f'<a href="{record.device.get_absolute_url()}">{record.device}</a>' )
           else:
               # Return the virtual machine link
               return mark_safe( f'<a href="{record.virtual_machine.get_absolute_url()}">{record.virtual_machine}</a>' )

# ------------------------------------------------------------------------------
# Interface
#

class DeviceAgentInterfaceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address" )
    resolved_dns_name = tables.Column( verbose_name="DNS Name" )
        
    class Meta(NetBoxTable.Meta):
        model = models.DeviceAgentInterface
        fields = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "zabbix_host_id", "zabbix_interface_id", "available", "useip", "main",  "port" )
        default_columns = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "port" )


class DeviceSNMPv3InterfaceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.DeviceSNMPv3Interface
        fields = ("name", "host", "interface", "zabbix_host_id", "zabbix_interface_id", "available", "useip", "main",  "port" )
        default_columns = ("name", "host", "interface", "port" )
