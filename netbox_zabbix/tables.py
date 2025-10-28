# tables.py

# Standard / Django imports
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import datetime

# Third-party imports
import django_tables2 as tables

# NetBox imports
from netbox.tables import NetBoxTable, columns

# DCIM imports
from dcim.models import Device

# Virtualization imports
from virtualization.models import VirtualMachine

# netbox_zabbix imports
from netbox_zabbix import settings, jobs, models
from netbox_zabbix.utils import validate_quick_add
from netbox_zabbix.logger import logger

# Core app imports
from core.models import Job
from core.tables import JobTable


# ------------------------------------------------------------------------------
# Setting Table
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

class SettingTable(NetBoxTable):
    class Meta(NetBoxTable.Meta):
        model = models.Setting
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
            'snmp_port', 
            'snmp_bulk',
            'snmp_max_repetitions',
            'snmp_contextname',
            'snmp_securityname',
            'snmp_securitylevel',
            'snmp_authprotocol',
            'snmp_authpassphrase',
            'snmp_privprotocol',
            'snmp_privpassphrase',
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
# Template Table
# ------------------------------------------------------------------------------


class TemplateTable(NetBoxTable):
    name       = tables.Column( linkify=True )
    host_count = columns.LinkedCountColumn( 
         viewname='plugins:netbox_zabbix:hostconfig_list',
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
        )

        default_columns = (
            "name",
            "templateid",
            "host_count",
            "interface_type",
            "dependencies",
            "last_synced",
        )


# ------------------------------------------------------------------------------
# Proxy Table
# ------------------------------------------------------------------------------


class ProxyTable(NetBoxTable):
    name = tables.Column( linkify=True )
        
    class Meta(NetBoxTable.Meta):
        model           = models.Proxy
        fields          = ("name", "proxyid", "proxy_groupid", "last_synced"  )
        default_columns = ("name", "proxyid", "proxy_groupid", "last_synced"  )


# ------------------------------------------------------------------------------
# Proxy Group Table
# ------------------------------------------------------------------------------


class ProxyGroupTable(NetBoxTable):
    name = tables.Column( linkify=True )
    
    class Meta(NetBoxTable.Meta):
        model           = models.ProxyGroup
        fields          = ("name", "proxy_groupid", "last_synced"  )
        default_columns = ("name", "proxy_groupid", "last_synced"  )


# ------------------------------------------------------------------------------
# Host Group Table
# ------------------------------------------------------------------------------


class HostGroupTable(NetBoxTable):
    name = tables.Column( linkify=True, order_by="name", accessor="name" )
    
    class Meta(NetBoxTable.Meta):
        model = models.HostGroup
        fields = ( "name", "groupid", "last_synced" )
        default_columns = ( "name", "groupid"," last_synced" )


# ------------------------------------------------------------------------------
# Tag Mapping Table
# ------------------------------------------------------------------------------


class TagMappingTable(NetBoxTable):
    object_type    = tables.Column( verbose_name="Object Type", linkify=True )
    enabled_fields = tables.Column( verbose_name="Enabled Fields", orderable=False )

    class Meta(NetBoxTable.Meta):
        model = models.TagMapping
        fields = ('object_type',)
        default_columns = fields

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
    Provides shared columns, Host config rendering, and Meta configuration.
    """
    name        = tables.Column( linkify=True )
    site        = tables.Column( linkify=True )
    role        = tables.Column( linkify=True )
    platform    = tables.Column( linkify=True )
    host_config = tables.BooleanColumn( accessor="host_config", verbose_name="Host Config", orderable=False )

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields = ("name", "host_config", "site", "role", "platform")
        default_columns = ("name", "host_config", "site", "role", "platform")

    def render_host_config(self, record):
        """
        Render a checkmark or cross depending on Zabbix config existence.
        """
        return mark_safe( "✔" ) if self.has_host_config( record ) else mark_safe( "✘" )

    def has_host_config(self, record):
        """
        Subclasses must implement the model-specific Host config check.
        """
        raise NotImplementedError( "Subclasses must implement has_host_config()" )


# ------------------------------------------------------------------------------
# Matching Device Mapping Table
# ------------------------------------------------------------------------------


class MatchingDeviceMappingTable(BaseMatchingMappingTable):
    """
    Matching table for Device mapping
    """
    tags = columns.TagColumn( url_name="dcim:device_list" )

    class Meta(BaseMatchingMappingTable.Meta):
        model = Device
        fields = BaseMatchingMappingTable.Meta.fields + ( "tags", )

    def has_host_config(self, record):
        return record.host_config != None


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

    def has_host_config(self, record):
        return record.host_config != None


# ------------------------------------------------------------------------------
# Host Config Table
# ------------------------------------------------------------------------------


class HostConfigTable(NetBoxTable):
    name            = tables.Column( accessor='name', order_by='name', verbose_name='Name', linkify=True )
    assigned_object = tables.Column( accessor='assigned_object', verbose_name='Linked Object', linkify=True, orderable=False )
    host_type       = tables.Column( accessor="host_type", empty_values=(), verbose_name="Type", orderable=False )

    class Meta(NetBoxTable.Meta):
        model = models.HostConfig
        fields =  ('name', 
                   'assigned_object',
                   'host_type',
                   'sync',
                   'status',
                   'monitored_by',
                   'hostid',
                   'templates',
                   'proxy',
                   'proxy_group',
                   'host_groups', 
                   'description')
        default_columns = fields

    def render_host_type(self, record):
        return mark_safe( f'{ "Device" if type( record.assigned_object ) == Device else "VirtualMachine" }' )


# ------------------------------------------------------------------------------
# Base Interface Table
# ------------------------------------------------------------------------------


class BaseInterfaceTable(NetBoxTable):
    """
    Abstract base table for Agent and SNMP interfaces for Devices and VMs.
    Provides shared columns like name, interface, IP address, and DNS name.
    """
    name                = tables.Column( linkify=True )
    interface           = tables.Column( linkify=True )
    resolved_ip_address = tables.Column( verbose_name="IP Address", linkify=True )
    resolved_dns_name   = tables.Column( verbose_name="DNS Name", linkify=True )

    class Meta(NetBoxTable.Meta):
        abstract = True
        fields = ("name", "host_config", "interface", "resolved_ip_address", "resolved_dns_name")
        default_columns = ("name", "host_config", "interface", "resolved_ip_address", "resolved_dns_name")


# ------------------------------------------------------------------------------
# Agent Interface Table
# ------------------------------------------------------------------------------


class AgentInterfaceTable(BaseInterfaceTable):
    class Meta(BaseInterfaceTable.Meta):
        model   = models.AgentInterface
        actions = ("bulk_edit", "bulk_delete", "edit", "delete")
        fields  = BaseInterfaceTable.Meta.fields + ("hostid", "interfaceid", "useip", "main", "port")
        default_columns = BaseInterfaceTable.Meta.default_columns + ("port", "useip", "main")


# ------------------------------------------------------------------------------
# Agent Interface Table
# ------------------------------------------------------------------------------


class SNMPInterfaceTable(BaseInterfaceTable):
    class Meta(BaseInterfaceTable.Meta):
        model   = models.SNMPInterface
        actions = ("bulk_edit", "bulk_delete", "edit", "delete")
        fields  = BaseInterfaceTable.Meta.fields + ("hostid", 
                                                    "interfaceid", 
                                                    "useip", 
                                                    "main", 
                                                    "port", 
                                                    "max_repetitions",
                                                    "contextname",
                                                    "securityname",
                                                    "securitylevel",
                                                    "authprotocol",
                                                    "authpassphrase",
                                                    "privprotocol",
                                                    "privpassphrase",
                                                    "bulk")
        default_columns = BaseInterfaceTable.Meta.default_columns + ("port", "useip", "main")


# ------------------------------------------------------------------------------
# Importable Hosts Table
# ------------------------------------------------------------------------------


class ImportableHostsTable(NetBoxTable):
    pk        = tables.Column( verbose_name=mark_safe( '<input type="checkbox" class="toggle form-check-input" title="Toggle all">'), 
                              attrs={
                                   "td": {"class": "w-1"},
                                   "th": {"class": "w-1"},
                               },
                               orderable=False )
    name      = tables.Column( linkify=True )
    host_type = tables.Column( verbose_name="Type" )
    valid     = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason    = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )
    actions   = []


    class Meta(NetBoxTable.Meta):
        model = models.HostConfig
        fields   = ("pk", "name", "host_type", "site", "status", "role", "valid", "reason")
        default_columns = fields

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs )
        self.reasons = {}


    def get_actions(self, record):
        return []

    def render_pk(self, record):
        return mark_safe( f'<input class="form-check-input" type="checkbox" name="pk" value="{record.pk}:{record.content_type}">' )

    def _validate_record(self, record):
        # Construct a key using the record's PK and content type.
        # The PK alone is not reliable, as a record can be either a Device or a VM,
        # so it is not guaranteed to be unique.
        key = f"{record.pk}:{record.content_type}"
        if key not in self.reasons:
            try:
                jobs.ValidateHost.run_now( instance=record )
                self.reasons[key] = None
            except Exception as e:
                self.reasons[key] = e
        return self.reasons[key]
    
    def render_valid(self, record):
        if settings.get_auto_validate_quick_add():
            return mark_safe( "✔" if self._validate_record( record ) is None else "✘" )
        return mark_safe( "-" )
    
    def render_reason(self, record):
        if settings.get_auto_validate_quick_add():
            reason = self._validate_record( record )
            return reason or ""
        return ""
    


# ------------------------------------------------------------------------------
# NetBox Only Hosts Table
# ------------------------------------------------------------------------------


class NetBoxOnlyHostsTable(NetBoxTable):
    """
    Unified table showing both Devices and VirtualMachines
    that are not yet represented in Zabbix.
    """

    pk            = tables.Column( verbose_name=mark_safe( '<input type="checkbox" class="toggle form-check-input" title="Toggle all">'), 
                              attrs={
                                   "td": {"class": "w-1"},
                                   "th": {"class": "w-1"},
                               },
                               orderable=False )
    name          = tables.Column( linkify=True )
    host_type     = tables.Column( verbose_name="Type" )
    site          = tables.Column( linkify=True )
    role          = tables.Column()
    platform      = tables.Column()
    agent_mapping = tables.Column( verbose_name="Agent Mapping", empty_values=(), accessor="agent_mapping" )
    snmp_mapping  = tables.Column( verbose_name="SNMP Mapping",  empty_values=(), accessor="snmp_mapping" )
    valid         = tables.BooleanColumn( accessor='valid', verbose_name="Valid", orderable=False )
    reason        = tables.Column( empty_values=(), verbose_name="Invalid Reason", orderable=False )
    
    actions = [] # Remove default actions since hosts cannot be added or edited

    class Meta(NetBoxTable.Meta):
        model = models.HostConfig
        fields = (
            "pk",
            "name",
            "host_type",
            "site",
            "role",
            "platform",
            "agent_mapping",
            "snmp_mapping",
            "valid",
            "reason",
        )
        default_columns = fields


    def __init__(self, *args, request=None, device_mapping_cache=None, **kwargs):
        super().__init__( *args, **kwargs )
        self.reasons = {}

    def get_actions(self, record):
        return []

    def _validate_record(self, record):
        # Construct a key using the record's PK and content type.
        # The PK alone is not reliable, as a record can be either a Device or a VM,
        # so it is not guaranteed to be unique.
        key = f"{record.pk}:{record.content_type}"
        if key not in self.reasons:
            try:
                validate_quick_add( record )
                self.reasons[key] = None
            except Exception as e:
                self.reasons[key] = e
        return self.reasons[key]
    
    def render_valid(self, record):
        if settings.get_auto_validate_quick_add():
            return mark_safe( "✔" if self._validate_record( record ) is None else "✘" )
        return mark_safe( "-" )
    
    def render_reason(self, record):
        if settings.get_auto_validate_quick_add():
            reason = self._validate_record( record )
            return reason or ""
        return ""
    
    def render_pk(self, record):
        return mark_safe( f'<input class="form-check-input" type="checkbox" name="pk" value="{record.pk}:{record.content_type}">' )

    def render_agent_mapping(self, record):
        if record.host_type == "Device":
            mapping = self.device_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.Agent) )
            
        else:
            mapping = self.vm_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.Agent) )
        
        if not mapping:
            return "—"
        
        return mark_safe( f'<a href="{mapping.get_absolute_url()}">{mapping.name}</a>' )

    def render_snmp_mapping(self, record):
        if record.host_type == "Device":
            mapping = self.device_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.SNMP) )
        else:
            mapping = self.vm_mapping_cache.get( (record.pk, models.InterfaceTypeChoices.SNMP) )

        if not mapping:
            return "-"
        
        return mark_safe( f'<a href="{mapping.get_absolute_url()}">{mapping.name}</a>' )


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



# end