# tables.py
from django.db.models import Case, When, Value, IntegerField
from django.urls import reverse
from django.utils.safestring import mark_safe

import django_tables2 as tables


from netbox.tables import NetBoxTable, columns
from netbox.tables.columns import TagColumn, ActionsColumn

from dcim.models import Device
from dcim.tables import DeviceTable

from utilities import query
from virtualization.models import VirtualMachine
from virtualization.tables import VirtualMachineTable

from netbox_zabbix import config, jobs, models
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

EXTRA_CONFIG_BUTTONS = """
<span class="dropdown">
    <button id="actions" type="button" class="btn btn-sm btn-primary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
        <i class="mdi mdi-plus-thick" aria-hidden="true"></i> Actions
    </button>

    <ul class="dropdown-menu" aria-labeled-by="actions">
        <li>
            <a class="dropdown-item"
                href="{% url 'plugins:netbox_zabbix:check_zabbix_connection' %}">
                Check Connection
            </a>
        </li>
        <li>
            <a class="dropdown-item"
                href="{% url 'plugins:netbox_zabbix:import_zabbix_settings' %}">
                Import Zabbix Settings
            </a>
        </li>
        
    </ul>
</span>
"""

class ConfigTable(NetBoxTable):
    class Meta(NetBoxTable.Meta):
        model = models.Config
        fields = ( 'name', 'api_endpoint', 'web_address', 'token', 'connection', 'last_checked_at', 'version', 'monitored_by', 'tls_connect', 'tls_accept', 'tls_psk_identity', 'tls_psk', 'default_tag', 'tag_prefix', 'tag_name_formatting' )
        default_columns = ('name', 'api_endpoint', 'version', 'connection', 'last_checked_at')

    name = tables.Column( linkify=True )
    actions = columns.ActionsColumn( extra_buttons=EXTRA_CONFIG_BUTTONS )


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------

class TemplateTable(NetBoxTable):
    name = tables.Column( linkify=True )
    host_count = columns.LinkedCountColumn( 
         viewname='plugins:netbox_zabbix:zabbixconfig_list',
         url_params={'templates': 'pk'},
         verbose_name="Hosts" )
    
    class Meta(NetBoxTable.Meta):
        model = models.Template
        fields = ("name", "templateid", "host_count", "last_synced", "marked_for_deletion" )
        default_columns = ("name", "templateid", "host_count", "last_synced", "marked_for_deletion" )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------

class ProxyTable(NetBoxTable):
    name = tables.Column( linkify=True )
        
    class Meta(NetBoxTable.Meta):
        model = models.Proxy
        fields = ("name", "proxyid", "proxy_groupid", "last_synced", "marked_for_deletion"  )
        default_columns = ("name", "proxyid", "proxy_groupid", "last_synced", "marked_for_deletion"  )

# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------

class ProxyGroupTable(NetBoxTable):
    name = tables.Column( linkify=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.ProxyGroup
        fields = ("name", "proxy_groupid", "last_synced", "marked_for_deletion"  )
        default_columns = ("name", "proxy_groupid", "last_synced", "marked_for_deletion"  )


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------

class HostGroupTable(NetBoxTable):
    name = tables.Column( linkify=True, order_by="name", accessor="name" )
    
    class Meta(NetBoxTable.Meta):
        model = models.HostGroup
        fields = ( "name", "groupid", "last_synced", "marked_for_deletion" )
        default_columns = ( "name", "groupid"," last_synced", "marked_for_deletion"  )


# ------------------------------------------------------------------------------
# NetBox Only Devices
# ------------------------------------------------------------------------------

EXTRA_DEVICE_ADD_ACTIONS = """
<span class="btn-group dropdown">

    <a class="btn btn-sm btn-primary" href="{% url 'plugins:netbox_zabbix:devicezabbixconfig_add' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" type="button" aria-label="Add Config">
    <i class="mdi mdi-pen-plus"></i>
    </a>

    <a class="btn btn-sm btn-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" style="padding-left: 2px" aria-expanded="false">
        <span class="visually-hidden">Toggle Dropdown</span>
    </a>

    <ul class="dropdown-menu">
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:device_quick_add_agent' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash-auto""></i>
            Quick Add Agent
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:device_quick_add_snmpv3' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash""></i>
            Qucik Add SNMPv3
            </a>
        </li>        
    </ul>
</span>

"""


class NetBoxOnlyDevicesTable(DeviceTable):
    name     = tables.Column( linkify=True )
    site     = tables.Column( linkify=True )
    role     = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )

    zabbix_config = tables.Column( verbose_name='Zabbix Configuration', empty_values=(), orderable=False)
    mapping_name  = tables.Column( verbose_name='Mapping', empty_values=(), orderable=False )

    tags    = TagColumn( url_name='dcim:device_list' )
    actions = ActionsColumn( extra_buttons=[] )

    class Meta(DeviceTable.Meta):
        model = Device
        fields = ( "name", "zabbix_config", "site", "role", "platform", "mapping_name", "tags" )
        default_columns = fields
    
    def render_actions(self, record):
        if record.id in getattr( self, "valid_device_ids", set() ):
            return columns.ActionsColumn( extra_buttons=EXTRA_DEVICE_ADD_ACTIONS ).render( record, self )
        return columns.ActionsColumn().render( record, self )
    
#    def render_mapping_name(self, record):
#        filter = models.DeviceMapping.get_matching_filter( record )
#        return mark_safe( filter.name )

    def render_mapping_name(self, record):
        mapping = models.DeviceMapping.get_matching_filter(record)
        if not mapping:
            return "—"  # or mark_safe("<em>No mapping</em>") or similar
    
        url = mapping.get_absolute_url()  # or construct manually using reverse()
        return mark_safe(f'<a href="{url}">{mapping.name}</a>')

    def render_zabbix_config(self, record):
        return mark_safe("✔") if  models.DeviceZabbixConfig.objects.filter( device=record ).exists() else mark_safe("✘")

    
# ------------------------------------------------------------------------------
# NetBox Only VMs
# ------------------------------------------------------------------------------

EXTRA_VM_ADD_ACTIONS = """
<span class="btn-group dropdown">

    <a class="btn btn-sm btn-primary" href="{% url 'plugins:netbox_zabbix:devicezabbixconfig_add' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" type="button" aria-label="Add Config">
    <i class="mdi mdi-pen-plus"></i>
    </a>

    <a class="btn btn-sm btn-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" style="padding-left: 2px" aria-expanded="false">
        <span class="visually-hidden">Toggle Dropdown</span>
    </a>

    <ul class="dropdown-menu">
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:device_quick_add_agent' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash-auto""></i>
            Quick Add Agent
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:device_quick_add_snmpv3' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash""></i>
            Qucik Add SNMPv3
            </a>
        </li>        
    </ul>
</span>

"""

class NetBoxOnlyVMsTable(VirtualMachineTable):
    name     = tables.Column( linkify=True )
    site     = tables.Column( linkify=True )
    role     = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )
    mapping  = tables.Column( linkify=True )
    tags     = TagColumn( url_name='dcim:device_list' )
    actions  = ActionsColumn( extra_buttons=[] )
    
    class Meta(VirtualMachineTable.Meta):
        model = VirtualMachine
        fields = ( "name", "zabbix_config", "site", "role", "platform", "mapping", "tags" )
        default_columns = fields
    
    def render_actions(self, record):
        if record.id in getattr( self, "valid_device_ids", set() ):
            return columns.ActionsColumn( extra_buttons=EXTRA_VM_ADD_ACTIONS ).render( record, self )
        return columns.ActionsColumn().render( record, self )
    
    def render_mapping(self, record):
        return record.get_macthing_filter().name

    def render_zabbix_config(self, record):
        return mark_safe("✔") if  models.DeviceZabbixConfig.objects.filter( device=record ).exists() else mark_safe("✘")


# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------

class DeviceZabbixConfigTable(NetBoxTable):
    name         = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    device       = tables.Column( accessor='device', verbose_name='Device', linkify=True )
    status       = tables.Column()
    hostid       = tables.Column( verbose_name='Zabbix Host ID' )
    templates    = tables.ManyToManyColumn( linkify_item=True )
    proxies      = tables.ManyToManyColumn( linkify_item=True )
    proxy_groups = tables.ManyToManyColumn( linkify_item=True )
    host_groups  = tables.ManyToManyColumn( linkify_item=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.DeviceZabbixConfig
        fields = ('name', 'device', 'status', 'monitored_by', 'hostid', 'templates', 'proxies', 'proxy_groups', 'host_groups' )
        default_columns = ('name', 'device', 'status', 'monitored_by', 'templates', 'proxies', 'proxy_groups', 'host_groups')
    

class VMZabbixConfigTable(NetBoxTable):
    name            = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    virtual_machine = tables.Column( accessor='virtual_machine', verbose_name='VM', linkify=True )
    status          = tables.Column()
    hostid          = tables.Column( verbose_name='Zabbix Host ID' )
    templates       = tables.ManyToManyColumn(linkify_item=True)
    proxies         = tables.ManyToManyColumn( linkify_item=True )
    proxy_groups    = tables.ManyToManyColumn( linkify_item=True )
    host_groups     = tables.ManyToManyColumn( linkify_item=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.VMZabbixConfig
        fields = ('name', 'virtual_machine', 'status', 'monitored_by', 'hostid',  'templates', 'proxies', 'proxy_groups', 'host_groups')
        default_columns = ('name', 'virtual_machine', 'status', 'monitored_by', 'templates', 'proxies', 'proxy_groups', 'host_groups')

        
class ZabbixConfigActionsColumn(ActionsColumn):

    def get_actions(self, record):
        actions = []
    
        if isinstance( record, models.DeviceZabbixConfig ):
            prefix = 'devicezabbixconfig'
        elif isinstance( record, models.VMZabbixConfig ):
            prefix =  'vmzabbixconfig'
        else:
            return []
    
        for action in ['edit', 'delete']:
            url = reverse( f'plugins:netbox_zabbix:{prefix}_{action}', args=[record.pk] )
            actions.append( (action, url) )
    
        return actions


class ZabbixConfigTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Host Name', linkify=True )
    type = tables.Column( empty_values=(), verbose_name='Type', order_by=('device__name', 'virtual_machine__name') )
    hostid = tables.Column( verbose_name='Zabbix Host ID' )
    status = tables.Column()
    object = tables.Column( empty_values=(), verbose_name='NetBox Object', order_by=('device__name', 'virtual_machine__name') )

    actions = ZabbixConfigActionsColumn()
     
    class Meta(NetBoxTable.Meta):
        model = models.ZabbixConfig
        fields = ('name', 'object', 'status', 'type', 'hostid', 'status', 'templates' )
        default_columns = ('name', 'object', 'status', 'templates', 'type' )

    def render_type(self, record):
        return 'Device' if isinstance( record, models.ZabbixConfig ) else 'VM'


    def render_object(self, record):
        if isinstance( record, models.DeviceZabbixConfig ):
            # Return the device link
            return mark_safe( f'<a href="{record.device.get_absolute_url()}">{record.device}</a>' )
        elif isinstance( record, models.VMZabbixConfig ):
            # Return the virtual machine link
            return mark_safe( f'<a href="{record.virtual_machine.get_absolute_url()}">{record.virtual_machine}</a>' )
        else:
            return mark_safe('<span class="text-muted">Unknown</span>')


# ------------------------------------------------------------------------------
# Importable Devices
# ------------------------------------------------------------------------------


class ImportableDeviceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    valid = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )
    
    class Meta(NetBoxTable.Meta):
        model = Device
        fields = ("name", "site", "status", "role", "valid", "reason" )
        default_columns = ("name", "site", "status", "valid", "reaon" )

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reasons = {}
    
    def render_valid(self, record):
        if config.get_auto_validate_importables():
            try:
                jobs.ValidateDeviceOrVM.run( device_or_vm = record, user=None )
                return mark_safe("✔")     
            except Exception as e:
                self.reasons[record] = e
                return mark_safe("✘")
        else:
            return mark_safe("-")
    
    def render_reason(self, record):
        if config.get_auto_validate_importables():
            return self.reasons[record] if record in self.reasons else ""
        return ""
    

# ------------------------------------------------------------------------------
# Importable VMs
# ------------------------------------------------------------------------------

class ImportableVMTable(NetBoxTable):
    name = tables.Column( linkify=True )
    valid = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )

    class Meta(NetBoxTable.Meta):
        model = VirtualMachine
        fields = ("name", "site", "status", "role", "valid", "reason" )
        default_columns = ("name", "site", "status", "valid", "reason" )

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reasons = {}

    def render_valid(self, record):
        if config.get_auto_validate_importables():
            try:
                jobs.ValidateDeviceOrVM.run( device_or_vm = record, user=None )
                return mark_safe("✔")        
            except Exception as e:
                self.reasons[record] = e
                return mark_safe("✘")
        else:
            return mark_safe("-")
    
    def render_reason(self, record):
        if config.get_auto_validate_importables():
            return self.reasons[record] if record in self.reasons else ""
        return ""
    


# ------------------------------------------------------------------------------
# Zabbix Only Hosts
# ------------------------------------------------------------------------------

class ZabbixOnlyHostTable(tables.Table):

    name = tables.TemplateColumn(
        template_code='<a href="{{web_address}}/zabbix.php?action=host.edit&hostid={{ record.hostid }}">{{ record.name }}</a>',
        verbose_name="Host"
    )
    hostid = tables.Column(verbose_name="Zabbix Host ID")

    class Meta:
        attrs = {'class': 'table table-hover panel-table'}
        fields = ('name', 'hostid')


# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------

class DeviceAgentInterfaceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    interface = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address", linkify=True )
    resolved_dns_name = tables.Column( verbose_name="DNS Name", linkify=True )
        
    class Meta(NetBoxTable.Meta):
        model = models.DeviceAgentInterface
        fields = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "hostid", "interfaceid", "available", "useip", "main",  "port" )
        default_columns = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "port" )


class DeviceSNMPv3InterfaceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    interface = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address", linkify=True )
    resolved_dns_name = tables.Column( verbose_name="DNS Name", linkify=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.DeviceSNMPv3Interface
        fields = ( "name", "host", "interface", 
                    "resolved_ip_address", "resolved_dns_name", 
                    "hostid", "interfaceid", "available", "useip", "main",  "port",
                    "snmp_max_repetitions",
                    "snmp_contextname",
                    "snmp_securityname",
                    "snmp_securitylevel",
                    "snmp_authprotocol",
                    "snmp_authpassphrase",
                    "snmp_privprotocol",
                    "snmp_privpassphrase",
                    "snmp_bulk" )
        default_columns = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "port" )


class VMAgentInterfaceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    interface = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address", linkify=True )
    resolved_dns_name = tables.Column( verbose_name="DNS Name", linkify=True )
        
    class Meta(NetBoxTable.Meta):
        model = models.VMAgentInterface
        fields = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "hostid", "interfaceid", "available", "useip", "main",  "port" )
        default_columns = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "port" )


class VMSNMPv3InterfaceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    interface = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address", linkify=True )
    resolved_dns_name = tables.Column( verbose_name="DNS Name", linkify=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.VMSNMPv3Interface
        fields = ( "name", "host", "interface", 
                    "resolved_ip_address", "resolved_dns_name", 
                    "hostid", "interfaceid", "available", "useip", "main",  "port",
                    "snmp_max_repetitions",
                    "snmp_contextname",
                    "snmp_securityname",
                    "snmp_securitylevel",
                    "snmp_authprotocol",
                    "snmp_authpassphrase",
                    "snmp_privprotocol",
                    "snmp_privpassphrase",
                    "snmp_bulk" )
        default_columns = ("name", "host", "interface", "resolved_ip_address", "resolved_dns_name", "port" )


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------

class TagMappingTable(NetBoxTable):
    object_type = tables.Column( verbose_name="Object Type", linkify=True )
    enabled_fields = tables.Column( verbose_name="Enabled Fields", orderable=False )

    class Meta(NetBoxTable.Meta):
        model = models.TagMapping
        fields = ('object_type',)
        attrs = {'class': 'table table-hover'}

    def __init__(self, *args, user=None, **kwargs):
        # Accept the user kwarg to avoid errors, even if unused
        super().__init__(*args, **kwargs)

    def render_enabled_fields(self, record):
        enabled_names = [f['name'] for f in record.field_selection if f.get('enabled')]
        return ", ".join(enabled_names) if enabled_names else "None"


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------

class DeviceMappingTable(NetBoxTable):
    name = tables.Column( linkify=True )

    class Meta(NetBoxTable.Meta):
        model = models.DeviceMapping
        fields = ( "name", "host_groups", "templates", "proxy", "proxy_group", "sites", "roles", "platforms", "default", "description" )
        default_columns = ( "name", "host_groups", "templates", "proxy", "proxy_group", "default" ) 


class MatchingDeviceMappingTable(NetBoxTable):
    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )
    zabbix_config = tables.BooleanColumn( accessor='zabbix_config', verbose_name="Zabbix Config", orderable=False )
    tags = columns.TagColumn( url_name='dcim:device_list' )

    class Meta(NetBoxTable.Meta):
        model = Device
        fields = ( "name", "zabbix_config", "site", "role", "platform", "tags" )

    def render_zabbix_config(self, record):
        return mark_safe("✔") if  models.DeviceZabbixConfig.objects.filter( device=record ).exists() else mark_safe("✘")


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------

class VMMappingTable(NetBoxTable):
    name = tables.Column( linkify=True )

    class Meta(NetBoxTable.Meta):
        model = models.VMMapping
        fields = ( "name", "host_groups", "templates", "proxy", "proxy_group", "sites", "roles", "platforms", "default", "description" )
        default_columns = ( "name", "host_groups", "templates", "proxy", "proxy_group", "default" ) 

# end