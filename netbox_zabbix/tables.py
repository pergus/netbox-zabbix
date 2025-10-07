# tables.py

# Standard / Django imports
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import datetime

# Third-party imports
import django_tables2 as tables

# NetBox imports
from netbox.tables import NetBoxTable, columns
from netbox.tables.columns import ActionsColumn, TagColumn

# DCIM imports
from dcim.models import Device
from dcim.tables import DeviceTable

# Virtualization imports
from virtualization.models import VirtualMachine
from virtualization.tables import VirtualMachineTable

# netbox_zabbix imports
from netbox_zabbix import config, jobs, models
from netbox_zabbix.logger import logger
from netbox_zabbix.utils import compare_zabbix_config_with_host, validate_quick_add

# Core app imports
from core.models import Job
from core.tables import JobTable


# ------------------------------------------------------------------------------
# Configuration Table
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
        fields = ( 
            'name',
            'ip_assignment_method',
            'event_log_enabled',
            'auto_validate_importables',
            'auto_validate_quick_add',
            'max_deletions',
            'max_success_notifications',
            'zabbix_sync_interval',
            'api_endpoint',
            'web_address',
            'token',
            'default_cidr',
            'delete_setting',
            'graveyard',
            'graveyard_suffix',
            'exclude_custom_field_name',
            'exclude_custom_field_enabled',
            'inventory_mode',
            'monitored_by',
            'tls_connect', 
            'tls_accept', 
            'tls_psk_identity', 
            'tls_psk', 
            'use_ip', 
            'agent_port', 
            'snmpv3_port', 
            'snmpv3_bulk',
            'snmpv3_max_repetitions',
            'snmpv3_contextname',
            'snmpv3_securityname',
            'snmpv3_securitylevel',
            'snmpv3_authprotocol',
            'snmpv3_authpassphrase',
            'snmpv3_privprotocol',
            'snmpv3_privpassphrase',
            'default_tag', 
            'tag_prefix', 
            'tag_name_formatting',
            'connection',
            'last_checked_at',
            )
        default_columns = ('name', 'api_endpoint', 'version', 'connection', 'last_checked_at')

    name = tables.Column( linkify=True )
    actions = columns.ActionsColumn( extra_buttons=EXTRA_CONFIG_BUTTONS )


# ------------------------------------------------------------------------------
# Templates Table
# ------------------------------------------------------------------------------


class TemplateTable(NetBoxTable):
    name       = tables.Column( linkify=True )
    host_count = columns.LinkedCountColumn( 
         viewname='plugins:netbox_zabbix:zabbixconfig_list',
         url_params={'templates': 'pk'},
         verbose_name="Hosts" )
    
    dependencies = columns.ManyToManyColumn( linkify_item=True, accessor="dependencies", verbose_name="Dependencies")

    parents = columns.ManyToManyColumn( linkify_item=True, accessor="parents", verbose_name="Parents")
    
    class Meta(NetBoxTable.Meta):
        model  = models.Template
        fields = (
            "name",
            "templateid",
            "host_count",
            "interface_type",
            "parents",
            "dependencies",
            "last_synced",
            "marked_for_deletion"
        )

        default_columns = (
            "name",
            "templateid",
            "host_count",
            "interface_type",
            "dependencies",
            "last_synced",
            "marked_for_deletion"
        )


# ------------------------------------------------------------------------------
# Proxy Table
# ------------------------------------------------------------------------------


class ProxyTable(NetBoxTable):
    name = tables.Column( linkify=True )
        
    class Meta(NetBoxTable.Meta):
        model           = models.Proxy
        fields          = ("name", "proxyid", "proxy_groupid", "last_synced", "marked_for_deletion"  )
        default_columns = ("name", "proxyid", "proxy_groupid", "last_synced", "marked_for_deletion"  )

# ------------------------------------------------------------------------------
# Proxy Groups Table
# ------------------------------------------------------------------------------


class ProxyGroupTable(NetBoxTable):
    name = tables.Column( linkify=True )
    
    class Meta(NetBoxTable.Meta):
        model           = models.ProxyGroup
        fields          = ("name", "proxy_groupid", "last_synced", "marked_for_deletion"  )
        default_columns = ("name", "proxy_groupid", "last_synced", "marked_for_deletion"  )


# ------------------------------------------------------------------------------
# Host Groups Table
# ------------------------------------------------------------------------------


class HostGroupTable(NetBoxTable):
    name = tables.Column( linkify=True, order_by="name", accessor="name" )
    
    class Meta(NetBoxTable.Meta):
        model = models.HostGroup
        fields = ( "name", "groupid", "last_synced", "marked_for_deletion" )
        default_columns = ( "name", "groupid"," last_synced", "marked_for_deletion"  )


# ------------------------------------------------------------------------------
# Tag Mapping Table
# ------------------------------------------------------------------------------


class TagMappingTable(NetBoxTable):
    object_type    = tables.Column( verbose_name="Object Type", linkify=True )
    enabled_fields = tables.Column( verbose_name="Enabled Fields", orderable=False )

    class Meta(NetBoxTable.Meta):
        model = models.TagMapping
        fields = ('object_type',)
        attrs = {'class': 'table table-hover'}

    def __init__(self, *args, user=None, **kwargs):
        # Accept the user kwarg to avoid errors, even if unused
        super().__init__( *args, **kwargs )

    def render_enabled_fields(self, record):
        enabled_names = [f['name'] for f in record.selection if f.get('enabled')]
        return ", ".join(enabled_names) if enabled_names else "None"


# ------------------------------------------------------------------------------
# Inventory Mapping Table
# ------------------------------------------------------------------------------


class InventoryMappingTable(NetBoxTable):
    object_type    = tables.Column( verbose_name="Object Type", linkify=True )
    enabled_fields = tables.Column( verbose_name="Enabled Fields", orderable=False )

    class Meta(NetBoxTable.Meta):
        model = models.InventoryMapping
        fields = ('object_type',)
        attrs = {'class': 'table table-hover'}

    def __init__(self, *args, user=None, **kwargs):
        # Accept the user kwarg to avoid errors, even if unused
        super().__init__( *args, **kwargs )

    def render_enabled_fields(self, record):
        enabled_names = [f['name'] for f in record.selection if f.get('enabled')]
        return ", ".join(enabled_names) if enabled_names else "None"


# ------------------------------------------------------------------------------
# Base Mapping Table
# ------------------------------------------------------------------------------


class BaseMappingTable(NetBoxTable):
    """
    Abstract base class for DeviceMapping and VMMapping tables.
    Provides shared columns and Meta configuration.
    """
    name = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields = (
            "name", "interface_type", "host_groups", "templates",
            "proxy", "proxy_group", "sites", "roles", "platforms",
            "default", "description",
        )
        default_columns = (
            "name", "interface_type", "host_groups", "templates",
            "proxy", "proxy_group", "default",
        )


# ------------------------------------------------------------------------------
# Device Mapping Table
# ------------------------------------------------------------------------------


class DeviceMappingTable(BaseMappingTable):
    """
    Concrete table for DeviceMapping model.
    """
    class Meta(BaseMappingTable.Meta):
        model = models.DeviceMapping


# ------------------------------------------------------------------------------
# VM Mapping Table
# ------------------------------------------------------------------------------


class VMMappingTable(BaseMappingTable):
    """
    Concrete table for VMMapping model.
    """
    class Meta(BaseMappingTable.Meta):
        model = models.VMMapping


# ------------------------------------------------------------------------------
# Base Matching Mapping Table
# ------------------------------------------------------------------------------


class BaseMatchingMappingTable(NetBoxTable):
    """
    Abstract base class for MatchingDeviceMappingTable and MatchingVMMappingTable.
    Provides shared columns, Zabbix config rendering, and Meta configuration.
    """
    name          = tables.Column( linkify=True )
    site          = tables.Column( linkify=True )
    role          = tables.Column( linkify=True )
    platform      = tables.Column( linkify=True )
    zabbix_config = tables.BooleanColumn(
        accessor="zabbix_config",
        verbose_name="Zabbix Config",
        orderable=False,
    )

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields = ("name", "zabbix_config", "site", "role", "platform")
        default_columns = ("name", "zabbix_config", "site", "role", "platform")

    def render_zabbix_config(self, record):
        """
        Render a checkmark or cross depending on Zabbix config existence.
        """
        return mark_safe( "✔" ) if self.has_zabbix_config( record ) else mark_safe( "✘" )

    def has_zabbix_config(self, record):
        """
        Subclasses must implement the model-specific Zabbix config check.
        """
        raise NotImplementedError( "Subclasses must implement has_zabbix_config()" )


# ------------------------------------------------------------------------------
# Matching Device Mapping Table
# ------------------------------------------------------------------------------


class MatchingDeviceMappingTable(BaseMatchingMappingTable):
    """
    Matching table for Device model with Zabbix config and tags.
    """
    tags = columns.TagColumn( url_name="dcim:device_list" )

    class Meta(BaseMatchingMappingTable.Meta):
        model = Device
        fields = BaseMatchingMappingTable.Meta.fields + ( "tags", )

    def has_zabbix_config(self, record):
        return models.DeviceZabbixConfig.objects.filter(device=record).exists()


# ------------------------------------------------------------------------------
# Matching VM Mapping Table
# ------------------------------------------------------------------------------


class MatchingVMMappingTable(BaseMatchingMappingTable):
    """
    Matching table for VirtualMachine model with Zabbix config and tags.
    """
    tags = columns.TagColumn( url_name="virtualization:virtualmachine_list" )

    class Meta(BaseMatchingMappingTable.Meta):
        model  = VirtualMachine
        fields = BaseMatchingMappingTable.Meta.fields + ( "tags", )

    def has_zabbix_config(self, record):
        return models.VMZabbixConfig.objects.filter( virtual_machine=record ).exists()



# ------------------------------------------------------------------------------
# Base Zabbix Configuration Table
# ------------------------------------------------------------------------------


class BaseZabbixConfigTable(NetBoxTable):
    """
    Abstract base class for Zabbix configuration tables.
    Provides shared columns and sync rendering logic.
    """
    name        = tables.Column( accessor='name', order_by='name', verbose_name='Name', linkify=True )
    sync        = tables.BooleanColumn( accessor='sync', verbose_name="In Sync", orderable=False )
    status      = tables.Column()
    hostid      = tables.Column( verbose_name='Zabbix Host ID' )
    templates   = tables.ManyToManyColumn( linkify_item=True )
    proxy       = tables.Column( linkify=True )
    proxy_group = tables.Column( linkify=True )
    host_groups = tables.ManyToManyColumn( linkify_item=True )
    description = tables.Column()

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields   = ('name', 'sync', 'status', 'monitored_by', 
                    'hostid', 'templates', 'proxy', 'proxy_group', 
                    'host_groups', 'description')
        default_columns = ('name', 'sync', 'status', 'monitored_by', 
                           'templates', 'proxy', 'proxy_group', 'host_groups')

    def render_sync(self, record):
        """
        Render ✔ if the Zabbix config is in sync, ✘ otherwise.
        """
        try:
            result = compare_zabbix_config_with_host( record )
        except Exception:
            return mark_safe( "✘" )
        return mark_safe( "✘" ) if result["differ"] else mark_safe( "✔" )


# ------------------------------------------------------------------------------
# Device Zabbix Configuration Table
# ------------------------------------------------------------------------------


class DeviceZabbixConfigTable(BaseZabbixConfigTable):
    """
    Concrete table for DeviceZabbixConfig model.
    """
    device = tables.Column( accessor='device', verbose_name='Device', linkify=True )

    class Meta(BaseZabbixConfigTable.Meta):
        model  = models.DeviceZabbixConfig
        fields = ('device', ) + BaseZabbixConfigTable.Meta.fields
        default_columns = ('device', ) + BaseZabbixConfigTable.Meta.default_columns


# ------------------------------------------------------------------------------
# VM Zabbix Configuration Table
# ------------------------------------------------------------------------------


class VMZabbixConfigTable(BaseZabbixConfigTable):
    """
    Concrete table for VMZabbixConfig model.
    """
    virtual_machine = tables.Column(accessor='virtual_machine', verbose_name='VM', linkify=True)

    class Meta(BaseZabbixConfigTable.Meta):
        model  = models.VMZabbixConfig
        fields = ('virtual_machine', ) + BaseZabbixConfigTable.Meta.fields
        default_columns = ('virtual_machine', ) + BaseZabbixConfigTable.Meta.default_columns


# ------------------------------------------------------------------------------
# Zabbix Configurations Table
# ------------------------------------------------------------------------------


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
    name   = tables.Column( accessor='name', verbose_name='Host Name', linkify=True )
    type   = tables.Column( empty_values=(), verbose_name='Type', order_by=('device__name', 'virtual_machine__name') )
    hostid = tables.Column( verbose_name='Zabbix Host ID' )
    status = tables.Column()
    object = tables.Column( empty_values=(), verbose_name='NetBox Object', order_by=('device__name', 'virtual_machine__name') )

    actions = ZabbixConfigActionsColumn()
     
    class Meta(NetBoxTable.Meta):
        model  = models.ZabbixConfig
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
# Base Importable Hosts Table
# ------------------------------------------------------------------------------


class BaseImportableTable(NetBoxTable):
    """
    Abstract base table for importable Zabbix hosts.
    Handles shared columns, validation logic, and reason tracking.
    """
    name   = tables.Column( linkify=True )
    valid  = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields   = ("name", "site", "status", "role", "valid", "reason")
        default_columns = ("name", "site", "status", "valid", "reason")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reasons = {}

    def render_valid(self, record):
        """
        Validate the record if auto-validation is enabled.
        Returns ✔ for valid, ✘ for invalid, or - if validation is disabled.
        """
        if config.get_auto_validate_importables():
            try:
                # Run validation job without request logging
                jobs.ValidateDeviceOrVM.run(model_instance=record)
                return mark_safe("✔")
            except Exception as e:
                self.reasons[record] = e
                return mark_safe("✘")
        else:
            return mark_safe("-")

    def render_reason(self, record):
        """
        Render the reason for an invalid record if auto-validation is enabled.
        """
        if config.get_auto_validate_importables():
            return self.reasons.get(record, "")
        return ""


# ------------------------------------------------------------------------------
# Importable Device Table
# ------------------------------------------------------------------------------


class ImportableDeviceTable(BaseImportableTable):
    """
    Table for importable Device Zabbix hosts.
    """
    class Meta(BaseImportableTable.Meta):
        model = models.Device


# ------------------------------------------------------------------------------
# Importable VM Table
# ------------------------------------------------------------------------------


class ImportableVMTable(BaseImportableTable):
    """
    Table for importable VirtualMachine Zabbix hosts.
    """
    class Meta(BaseImportableTable.Meta):
        model = models.VirtualMachine


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
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:device_validate_quick_add' %}?device_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlydevices'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash-auto""></i>
            Validate
            </a>
        </li>

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

    zabbix_config        = tables.Column( verbose_name='Zabbix Configuration', empty_values=(), orderable=False )
    agent_mapping_name   = tables.Column( verbose_name='Agent Mapping',        empty_values=(), orderable=False )
    snmpv3_mapping_name  = tables.Column( verbose_name='SNMPv3 Mapping',       empty_values=(), orderable=False )

    valid   = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason  = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )
    tags    = TagColumn( url_name='dcim:device_list' )
    actions = ActionsColumn( extra_buttons=[] )

    class Meta(DeviceTable.Meta):
        model = Device
        fields = ("name", "zabbix_config", "site", "role", "platform", 
                  "agent_mapping_name", "snmpv3_mapping_name", "valid", 
                  "reason", "tags")
        default_columns = fields


    def __init__(self, *args, request=None, device_mapping_cache=None, **kwargs):
            super().__init__( *args, **kwargs )
            self.reasons = {}
            self.device_mapping_cache = device_mapping_cache or {}


    def render_valid(self, record):
        if config.get_auto_validate_quick_add():
            try:
                validate_quick_add( record )
                return mark_safe("✔")
            except Exception as e:
                self.reasons[record] = e
                return mark_safe("✘")
        else:
            return mark_safe("-")


    def render_reason(self, record):
        if config.get_auto_validate_quick_add():
            return self.reasons[record] if record in self.reasons else ""
        return ""


    def render_actions(self, record):
        return columns.ActionsColumn( extra_buttons=EXTRA_DEVICE_ADD_ACTIONS ).render( record, self )


    def render_agent_mapping_name(self, record):
        mapping = self.device_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.Agent) )

        # fallback to view.context if you want backward compatibility
        if not mapping:
            view = self.context.get( "view" )
            mapping = getattr( view, "device_mapping_cache", {}).get(
                (record.pk, models.InterfaceTypeChoices.Agent)
            )

        if not mapping:
            return "—"

        return mark_safe( f'<a href="{mapping.get_absolute_url()}">{mapping.name}</a>' )


    def render_snmpv3_mapping_name(self, record):
        mapping = self.device_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.SNMP) )

        if not mapping:
            view = self.context.get( "view" )
            mapping = getattr( view, "device_mapping_cache", {}).get(
                (record.pk, models.InterfaceTypeChoices.SNMP)
            )

        if not mapping:
            return "—"

        return mark_safe( f'<a href="{mapping.get_absolute_url()}">{mapping.name}</a>' )


    def render_zabbix_config(self, record):
        # Prefetching zabbix configs will reduce DB hits
        return mark_safe( "✔" ) if hasattr( record, 'zcfg' ) and record.zcfg else mark_safe( "✘" )


# ------------------------------------------------------------------------------
# NetBox Only VMs
# ------------------------------------------------------------------------------


EXTRA_VM_ADD_ACTIONS = """
<span class="btn-group dropdown">

    <a class="btn btn-sm btn-primary" href="{% url 'plugins:netbox_zabbix:vmzabbixconfig_add' %}?virtual_machine_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlyvms'%}" type="button" aria-label="Add Config">
    <i class="mdi mdi-pen-plus"></i>
    </a>

    <a class="btn btn-sm btn-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" style="padding-left: 2px" aria-expanded="false">
        <span class="visually-hidden">Toggle Dropdown</span>
    </a>

    <ul class="dropdown-menu">
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:vm_validate_quick_add' %}?virtual_machine_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlyvms'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash-auto""></i>
            Validate
            </a>
        </li>

        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:vm_quick_add_agent' %}?virtual_machine_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlyvms'%}" class="btn btn-sm btn-info">
            <i class="mdi mdi-flash-auto""></i>
            Quick Add Agent
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="{% url 'plugins:netbox_zabbix:vm_quick_add_snmpv3' %}?virtual_machine_id={{ record.pk }}&return_url={% url 'plugins:netbox_zabbix:netboxonlyvms'%}" class="btn btn-sm btn-info">
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

    zabbix_config        = tables.Column( verbose_name='Zabbix Configuration', empty_values=(), orderable=False )
    agent_mapping_name   = tables.Column( verbose_name='Agent Mapping',        empty_values=(), orderable=False )
    snmpv3_mapping_name  = tables.Column( verbose_name='SNMPv3 Mapping',       empty_values=(), orderable=False )

    valid   = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason  = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )
    tags    = TagColumn( url_name='virtualization:virtualmachine_list' )
    actions = ActionsColumn( extra_buttons=[] )

    class Meta(VirtualMachineTable.Meta):
        model = VirtualMachine
        fields = ("name", "zabbix_config", "site", "role", "platform", 
                  "agent_mapping_name", "snmpv3_mapping_name", "valid", 
                  "reason", "tags")
        default_columns = fields


    def __init__(self, *args, request=None, vm_mapping_cache=None, **kwargs):
            super().__init__( *args, **kwargs )
            self.reasons = {}
            self.vm_mapping_cache = vm_mapping_cache or {}


    def render_valid(self, record):
        if config.get_auto_validate_quick_add():
            try:
                validate_quick_add( record )
                return mark_safe("✔")
            except Exception as e:
                self.reasons[record] = e
                return mark_safe("✘")
        else:
            return mark_safe("-")


    def render_reason(self, record):
        if config.get_auto_validate_quick_add():
            return self.reasons[record] if record in self.reasons else ""
        return ""


    def render_actions(self, record):
        return columns.ActionsColumn( extra_buttons=EXTRA_VM_ADD_ACTIONS ).render( record, self )


    def render_agent_mapping_name(self, record):
        mapping = self.vm_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.Agent) )

        # fallback to view.context if you want backward compatibility
        if not mapping:
            view = self.context.get( "view" )
            mapping = getattr(view, "vm_mapping_cache", {}).get(
                (record.pk, models.InterfaceTypeChoices.Agent)
            )

        if not mapping:
            return "—"

        return mark_safe( f'<a href="{mapping.get_absolute_url()}">{mapping.name}</a>' )


    def render_snmpv3_mapping_name(self, record):
        mapping = self.vm_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.SNMP) )

        if not mapping:
            view = self.context.get( "view" )
            mapping = getattr( view, "vm_mapping_cache", {}).get(
                (record.pk, models.InterfaceTypeChoices.SNMP)
            )

        if not mapping:
            return "—"

        return mark_safe(f'<a href="{mapping.get_absolute_url()}">{mapping.name}</a>')


    def render_zabbix_config(self, record):
        # Prefetching zabbix configs will reduce DB hits
        return mark_safe( "✔" ) if hasattr( record, 'zcfg' ) and record.zcfg else mark_safe( "✘" )


# ------------------------------------------------------------------------------
# Zabbix Only Hosts Table
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
# Base Interface Table
# ------------------------------------------------------------------------------


class BaseInterfaceTable(NetBoxTable):
    """
    Abstract base table for Agent and SNMPv3 interfaces for Devices and VMs.
    Provides shared columns like name, interface, IP address, and DNS name.
    """
    name                = tables.Column( linkify=True )
    interface           = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address", linkify=True )
    resolved_dns_name   = tables.Column( verbose_name="DNS Name", linkify=True )

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields = ("name", "zcfg", "interface", "resolved_ip_address", "resolved_dns_name")
        default_columns = ("name", "zcfg", "interface", "resolved_ip_address", "resolved_dns_name")


# ------------------------------------------------------------------------------
# Device Agent Interface Table
# ------------------------------------------------------------------------------


class DeviceAgentInterfaceTable(BaseInterfaceTable):
    """
    Table for Device Agent interfaces.
    """
    class Meta(BaseInterfaceTable.Meta):
        model   = models.DeviceAgentInterface
        actions = ("bulk_edit", "bulk_delete", "edit", "delete")
        fields  = BaseInterfaceTable.Meta.fields + ("hostid", "interfaceid", "available", "useip", "main", "port")
        default_columns = BaseInterfaceTable.Meta.default_columns + ("port", "useip", "main")


# ------------------------------------------------------------------------------
# Device SNMPv3 Interface Table
# ------------------------------------------------------------------------------

class DeviceSNMPv3InterfaceTable(BaseInterfaceTable):
    """
    Table for Device SNMPv3 interfaces.
    """
    class Meta(BaseInterfaceTable.Meta):
        model  = models.DeviceSNMPv3Interface
        fields = BaseInterfaceTable.Meta.fields + (
            "hostid", "interfaceid", "available", "useip", "main", "port",
            "max_repetitions", "contextname", "securityname", "securitylevel",
            "authprotocol", "authpassphrase", "privprotocol", "privpassphrase", "bulk"
        )
        default_columns = BaseInterfaceTable.Meta.default_columns + ("port", "useip", "main")


# ------------------------------------------------------------------------------
# VM Agent Interface Table
# ------------------------------------------------------------------------------

class VMAgentInterfaceTable(BaseInterfaceTable):
    """
    Table for VM Agent interfaces.
    """
    class Meta(BaseInterfaceTable.Meta):
        model  = models.VMAgentInterface
        fields = BaseInterfaceTable.Meta.fields + ("hostid", "interfaceid", "available", "useip", "main", "port")
        default_columns = BaseInterfaceTable.Meta.default_columns + ("port", "useip", "main")


# ------------------------------------------------------------------------------
# VM SNMPv3 Interface Table
# ------------------------------------------------------------------------------

class VMSNMPv3InterfaceTable(BaseInterfaceTable):
    """
    Table for VM SNMPv3 interfaces.
    """
    class Meta(BaseInterfaceTable.Meta):
        model = models.VMSNMPv3Interface
        fields = BaseInterfaceTable.Meta.fields + (
            "hostid", "interfaceid", "available", "useip", "main", "port",
            "snmp_max_repetitions", "snmp_contextname", "snmp_securityname",
            "snmp_securitylevel", "snmp_authprotocol", "snmp_authpassphrase",
            "snmp_privprotocol", "snmp_privpassphrase", "snmp_bulk"
        )
        default_columns = BaseInterfaceTable.Meta.default_columns + ("port", "useip", "main")


# ------------------------------------------------------------------------------
# Event Log Table
# ------------------------------------------------------------------------------


class EventLogTable(NetBoxTable):
    name       = tables.Column( linkify=True )
    job        = tables.Column( linkify=True )
    job_status = columns.ChoiceFieldColumn( accessor="job.status", verbose_name="Job Status" )
    message    = tables.Column()
    exception  = tables.Column()
    data       = tables.Column()
    pre_data   = tables.Column()
    post_data  = tables.Column()
    created    = tables.DateTimeColumn( format="Y-m-d H:i:s" )

    class Meta(NetBoxTable.Meta):
        model  = models.EventLog
        fields = ( 'name', 'job', 'job_status', 'created', 'message', 
                   'exception', 'data', 'pre_data', 'post_data')
        default_columns = ( 'name', 'job', 'job_status', 'created', 'message' )
        attrs = {'class': 'table table-hover table-headings'}


# ------------------------------------------------------------------------------
# Zabbix Problem Table
# ------------------------------------------------------------------------------


class ZabbixProblemTable(tables.Table):
    eventid      = tables.Column( verbose_name="Event ID" )
    severity     = tables.Column( verbose_name="Severity" )
    name         = tables.Column( verbose_name="Problem" )
    acknowledged = tables.Column( verbose_name="Acknowledged" )
    clock        = tables.Column( verbose_name="Time" )

    class Meta:
        model = None
        object_type_column = False
        attrs = {"class": "table table-hover object-list"}
        sequence = ("eventid", "severity", "name", "acknowledged", "clock")
    

    def render_severity(self, value):
        ZABBIX_SEVERITY = {
            "0": ("Not classified", "default"),
            "1": ("Information",    "info"),
            "2": ("Warning",        "warning"),
            "3": ("Average",        "orange"),
            "4": ("High",           "danger"),
            "5": ("Disaster",       "dark"),
        }
        label, css = ZABBIX_SEVERITY.get(str(value), ("Unknown", "secondary"))
        return format_html( '<span class="badge bg-{} text-light">{}</span>', css, label )

    def render_acknowledged(self, value):
        return "Yes" if str( value ) == "1" else "No"

    def render_clock(self, value):
        try:
            ts = datetime.fromtimestamp( int( value ) )
            return ts.strftime( "%Y-%m-%d %H:%M:%S" )
        except Exception:
            return value



# ------------------------------------------------------------------------------
# Device Zabbix Tasks Table
# ------------------------------------------------------------------------------


class DeviceZabbixTasksTable(JobTable):
    actions = []

    class Meta(NetBoxTable.Meta):
        model  = Job
        fields = ("id", "name", "status", "user", "started", "completed")

    def get_actions(self, record):
            return []


# end
