import django_tables2 as tables
from netbox.tables import NetBoxTable, columns
from netbox.tables.columns import ActionsColumn
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Case, When

from dcim.tables import DeviceTable
from virtualization.tables import VirtualMachineTable

from dcim.models import Device
from virtualization.models import VirtualMachine


from netbox_zabbix import models, jobs, config
from netbox_zabbix.utils import get_device_hostgroups

from netbox_zabbix.logger import logger

# ------------------------------------------------------------------------------
# Configuration
#

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
    </ul>
</span>
"""

class ConfigTable(NetBoxTable):
    class Meta(NetBoxTable.Meta):
        model = models.Config
        fields = ('name', 'api_endpoint', 'web_address', 'version', 'connection', 'last_checked_at', 'ip_assignment_method')
        default_columns = ('name', 'api_endpoint', 'version', 'connection', 'last_checked_at')

    name = tables.Column( linkify=True )
    actions = columns.ActionsColumn( extra_buttons=EXTRA_CONFIG_BUTTONS )


# ------------------------------------------------------------------------------
# Templates
#

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
# Template Mappings
#

class TemplateMappingTable(NetBoxTable):
    name = tables.Column( linkify=True )
    template = tables.Column( linkify=True )
    roles = tables.ManyToManyColumn(  )
    platforms = tables.ManyToManyColumn(  )
    tags = tables.ManyToManyColumn(  )

    class Meta(NetBoxTable.Meta):
        model = models.TemplateMapping
        fields = ( "pk", "name", "template", "interface_type", "sites", "roles", "platforms", "tags")
        default_columns = ("pk", "name", "template", "interface_type", "sites", "roles", "platforms", "tags" )


# ------------------------------------------------------------------------------
# Host Groups
#

class HostGroupTable(NetBoxTable):
    name = tables.Column( verbose_name="Name", order_by="name", accessor="name", )
    groupid = tables.Column( verbose_name="Group ID", order_by="groupid", )
    
    # Hide the action buttons since it isn't possible to edit the hosts groups
    # in NetBox, since they are imported from Zabbix.
    actions = [] 

    class Meta(NetBoxTable.Meta):
        model = models.HostGroup
        fields = ( "name", "groupid", )
        default_columns = ( "name", "groupid", )

# ------------------------------------------------------------------------------
# Host Group Mappings
#

class HostGroupMappingTable(NetBoxTable):
    name = tables.Column( linkify=True )
    hostgroup = tables.Column( linkify=True )
    roles = tables.ManyToManyColumn(  )
    platforms = tables.ManyToManyColumn(  )
    tags = tables.ManyToManyColumn(  )

    class Meta(NetBoxTable.Meta):
        model = models.HostGroupMapping
        fields = ( "pk", "name", "hostgroup", "sites", "roles", "platforms", "tags")
        default_columns = ("pk", "name", "hostgroup", "sites", "roles", "platforms", "tags" )



class MatchingDeviceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )
    zabbix_config = tables.BooleanColumn( accessor='zabbix_config', verbose_name="Zabbix Config", orderable=True )
    tags = columns.TagColumn( url_name='dcim:device_list' )

    class Meta(NetBoxTable.Meta):
        model = Device
        fields = ( "name", "zabbix_config", "site", "role", "platform", "tags" )

    def render_zabbix_config(self, record):
        return mark_safe("✔") if  models.DeviceZabbixConfig.objects.filter( device=record ).exists() else mark_safe("✘")

    
class MatchingVMTable(NetBoxTable):
    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )    
    zabbix_config = tables.BooleanColumn( accessor='zabbix_config', verbose_name="Zabbix Config", orderable=True )
    tags = columns.TagColumn( url_name='virtualization:virtualmachine_list' )

    class Meta(NetBoxTable.Meta):
        model = VirtualMachine
        fields = ("name", "zabbix_config", "site", "role", "platform", "tags")

    def render_zabbix_config(self, record):
        return mark_safe("✔") if  models.VMZabbixConfig.objects.filter( virtual_machine=record ).exists() else mark_safe("✘")
    

# ------------------------------------------------------------------------------
# Device Host Groups
#

class DeviceHostGroupTable(DeviceTable):
    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )

    # The `empty_values=()` is required to prevent django-tables2 from
    # attempting to fetch a `hostgroups` attribute from the Device model, which
    # doesn't exist. This ensures that the custom `render_hostgroups()` method
    # is always called to render the column using computed data.
    hostgroups = tables.Column( empty_values=(), verbose_name="Host Groups", order_by='hostgroups' )
    
    tags = columns.TagColumn( url_name='dcim:device_list' )

    class Meta(DeviceTable.Meta):
        model = Device
        fields = ("name", "hostgroups", "site", "role", "platform", "tags")

    def render_hostgroups(self, record):
        hostgroups = get_device_hostgroups(record)
        if not hostgroups:
            return mark_safe('<span class="text-muted">&mdash;</span>')

        return mark_safe(", ".join(
            f'<a href="{hg.get_absolute_url()}">{hg.name}</a>'
            for hg in hostgroups
        ))

    def order_hostgroups(self, queryset, is_descending):
        """
        Orders the queryset by the number of host groups associated with each device.
        
        This method fetches all records from the queryset and sorts them in Python
        based on the count of host groups. It then creates a new queryset ordered
        by the primary keys in the sorted order.
        
        Args:
            queryset: The initial queryset to be ordered.
            is_descending: A boolean indicating whether the ordering should be descending.
        
        Returns:
            A tuple containing the ordered queryset and a boolean indicating success.
        """ 
        devices = list(queryset)
        devices.sort(
            key=lambda x: len(get_device_hostgroups(x)),
            reverse=is_descending
        )

        # Create a new queryset with the sorted order
        ordered_pks = [device.pk for device in devices]
        # Reorders the queryset by filtering records with primary keys in the
        # sorted list and then ordering them based on their positions in that
        # list, ensuring the final queryset is ordered by the number of host
        # groups associated with each device.
        queryset = queryset.model.objects.filter( pk__in=ordered_pks ).order_by(
            Case(*[ When( pk=pk, then=pos ) for pos, pk in enumerate( ordered_pks ) ])
        )

        return queryset, True


# ------------------------------------------------------------------------------
# Zabbix Configurations
#

class DeviceZabbixConfigTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    device = tables.Column( accessor='device', verbose_name='Device', linkify=True )
    status = tables.Column()
    hostid = tables.Column( verbose_name='Zabbix Host ID' )
    templates = tables.ManyToManyColumn( linkify_item=True )
    
    class Meta(NetBoxTable.Meta):
        model = models.DeviceZabbixConfig
        fields = ('name', 'device', 'status', 'hostid', 'templates')
        default_columns = ('name', 'device', 'status', 'templates')
    

class VMZabbixConfigTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    virtual_machine = tables.Column( accessor='virtual_machine', verbose_name='VM', linkify=True )
    status = tables.Column()
    hostid = tables.Column( verbose_name='Zabbix Host ID' )
    templates = tables.ManyToManyColumn(linkify_item=True)
    
    class Meta(NetBoxTable.Meta):
        model = models.VMZabbixConfig
        fields = ('name', 'virtual_machine', 'status', 'hostid',  'templates')
        default_columns = ('name', 'virtual_machine', 'status', 'templates')

        
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
                logger.info( f"valdating device {record} ")
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
                logger.info( f"valdating virtual machine '{record}' ")
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
            Add Agent
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:device_quick_add_snmpv3' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash""></i>
            Add SNMPv3
            </a>
        </li>        
    </ul>
</span>

"""
class NetBoxOnlyDevicesTable(DeviceTable):

    #def render_actions(self, record):
    #       url = reverse('plugins:netbox_zabbix:devicezabbixconfig_add') + f'?device_id={record.pk}'
    #       return format_html(
    #           '<a href="{}" class="btn btn-sm btn-success">Create Zabbix Config</a>',
    #           url
    #       )
   
    class Meta(DeviceTable.Meta):
        model = Device
        fields = DeviceTable.Meta.fields
        default_columns = DeviceTable.Meta.default_columns

    actions = columns.ActionsColumn( extra_buttons=EXTRA_DEVICE_ADD_ACTIONS )


class NetBoxOnlyVMsTable(VirtualMachineTable):

    def render_actions(self, record):
           url = reverse('plugins:netbox_zabbix:vmzabbixconfig_add') + f'?vm_id={record.pk}'
           return format_html(
               '<a href="{}" class="btn btn-sm btn-success">Create Zabbix Config</a>',
               url
           )
    
    class Meta(VirtualMachineTable.Meta):
        model = VirtualMachine
        fields = VirtualMachineTable.Meta.fields
        default_columns = VirtualMachineTable.Meta.default_columns


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
# Interface
#

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
