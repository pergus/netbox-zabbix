# tables.py
from django.db.models import Case, When, Value, IntegerField
from django.urls import reverse
from django.utils.safestring import mark_safe

import django_tables2 as tables


from netbox.tables import NetBoxTable, columns
from netbox.tables.columns import TagColumn, ActionsColumn

from dcim.models import Device
from dcim.tables import DeviceTable

from virtualization.models import VirtualMachine
from virtualization.tables import VirtualMachineTable

from netbox_zabbix import config, jobs, models
from netbox_zabbix.logger import logger
from netbox_zabbix.utils import (
    get_hostgroups_mappings, 
    get_templates_mappings, 
    get_proxy_mapping, 
    get_proxy_group_mapping
)


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
# Template Mappings
# ------------------------------------------------------------------------------

class TemplateMappingTable(NetBoxTable):
    name      = tables.Column( linkify=True )
    templates = tables.ManyToManyColumn( linkify_item=True )
    sites     = tables.ManyToManyColumn( linkify_item=True )
    roles     = tables.ManyToManyColumn( linkify_item=True )
    platforms = tables.ManyToManyColumn( linkify_item=True )
    tags      = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = models.TemplateMapping
        fields = ( "pk", "name", "templates", "interface_type", "sites", "roles", "platforms", "tags")
        default_columns = ("pk", "name", "templates", "interface_type", "sites", "roles", "platforms", "tags" )


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
# Proxy Mappings
# ------------------------------------------------------------------------------

class ProxyMappingTable(NetBoxTable):
    name      = tables.Column( linkify=True )
    proxy     = tables.Column( linkify=True )
    sites     = tables.ManyToManyColumn( linkify_item=True )
    roles     = tables.ManyToManyColumn( linkify_item=True )
    platforms = tables.ManyToManyColumn( linkify_item=True )
    tags      = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = models.ProxyMapping
        fields = ( "pk", "name", "proxy", "sites", "roles", "platforms", "tags")
        default_columns = ("pk", "name", "proxy", "sites", "roles", "platforms", "tags" )



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
# Proxy Group Mappings
# ------------------------------------------------------------------------------

class ProxyGroupMappingTable(NetBoxTable):
    name        = tables.Column( linkify=True )
    proxy_group = tables.Column( linkify=True )
    sites       = tables.ManyToManyColumn( linkify_item=True )
    roles       = tables.ManyToManyColumn( linkify_item=True )
    platforms   = tables.ManyToManyColumn( linkify_item=True )
    tags        = columns.TagColumn()
    

    class Meta(NetBoxTable.Meta):
        model = models.ProxyGroupMapping
        fields = ( "pk", "name", "proxy_group", "sites", "roles", "platforms", "tags")
        default_columns = ("pk", "name", "proxy_group", "sites", "roles", "platforms", "tags" )



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
# Host Group Mappings
# ------------------------------------------------------------------------------

class HostGroupMappingTable(NetBoxTable):
    name        = tables.Column( linkify=True )
    host_groups = tables.ManyToManyColumn( linkify_item=True )
    sites       = tables.ManyToManyColumn( linkify_item=True )
    roles       = tables.ManyToManyColumn( linkify_item=True )
    platforms   = tables.ManyToManyColumn( linkify_item=True )
    tags        = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = models.HostGroupMapping
        fields = ( "pk", "name", "host_groups", "sites", "roles", "platforms", "tags")
        default_columns = ("pk", "name", "host_groups", "sites", "roles", "platforms", "tags" )



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
# Device Mappings
# ------------------------------------------------------------------------------

class DeviceMappingsTable(DeviceTable):
    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )

    hostgroups  = tables.Column( empty_values=(), verbose_name="Host Groups", order_by='hostgroups' )
    templates   = tables.Column( empty_values=(), verbose_name="Templates", order_by='templates' )
    proxy       = tables.Column( empty_values=(), verbose_name="Proxy", order_by='proxy' )
    proxy_group  = tables.Column( empty_values=(), verbose_name="Proxy Group", order_by='proxy_group' )

    tags = columns.TagColumn( url_name='dcim:device_list' )

    class Meta(DeviceTable.Meta):
        model = Device
        fields = ("name", "hostgroups", "templates", "proxy", "proxy_group", "site", "role", "platform", "tags")
        default_columns = ("name", "hostgroups", "templates", "proxy", "proxy_group", "site", "role", "platform", "tags")

    # Generic render method for columns that return iterable mappings (hostgroups, templates)
    def _render_mappings(self, record, get_mapping_func):
        items = get_mapping_func( record )
        if not items:
            return mark_safe( '<span class="text-muted">&mdash;</span>' )
        return mark_safe(", ".join(
            f'<a href="{item.get_absolute_url()}">{item.name}</a>'
            for item in items
        ))

    # Generic order method for columns based on counts of mappings
    def _order_by_mapping_count(self, queryset, is_descending, get_mapping_func):
        devices = list( queryset )
        devices.sort(
            key=lambda x: len( get_mapping_func(x) ),
            reverse=is_descending
        )
        ordered_pks = [device.pk for device in devices]
        preserved_order = Case(*[When( pk=pk, then=pos ) for pos, pk in enumerate( ordered_pks )])
        queryset = queryset.model.objects.filter( pk__in=ordered_pks ).order_by( preserved_order )
        return queryset, True

    # Generic render method for single-mapping columns (proxy, proxy_group)
    def _render_single_mapping(self, record, get_mapping_func):
        item = get_mapping_func( record )
        if not item:
            return mark_safe('<span class="text-muted">&mdash;</span>')
        return mark_safe(f'<a href="{item.get_absolute_url()}">{item.name}</a>')

    # Generic order method for single-mapping columns (proxy, proxy_group)
    def _order_by_single_mapping(self, queryset, is_descending, get_mapping_func):
        devices = list( queryset )
        devices.sort(
            key=lambda x: (
                0 if get_mapping_func(x) is None else 1,
                get_mapping_func(x).name if get_mapping_func(x) else '',
                x.name
            ),
            reverse=is_descending
        )
        ordered_pks = [device.pk for device in devices]
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_pks)])
        queryset = queryset.model.objects.filter(pk__in=ordered_pks).order_by(preserved_order, 'name')
        return queryset, True

    # Now, bind each column's render and order methods to the generic ones with proper function

    def render_hostgroups(self, record):
        return self._render_mappings( record, get_hostgroups_mappings )

    def order_hostgroups(self, queryset, is_descending):
        return self._order_by_mapping_count( queryset, is_descending, get_hostgroups_mappings )

    def render_templates(self, record):
        return self._render_mappings( record, get_templates_mappings )

    def order_templates(self, queryset, is_descending):
        return self._order_by_mapping_count( queryset, is_descending, get_templates_mappings )

    def render_proxy(self, record):
        return self._render_single_mapping( record, get_proxy_mapping )

    def order_proxy(self, queryset, is_descending):
        return self._order_by_single_mapping( queryset, is_descending, get_proxy_mapping )

    def render_proxy_group(self, record):
        return self._render_single_mapping( record, get_proxy_group_mapping )

    def order_proxy_group(self, queryset, is_descending):
        return self._order_by_single_mapping( queryset, is_descending, get_proxy_group_mapping )


# ------------------------------------------------------------------------------
# VM Mappings
# ------------------------------------------------------------------------------

class VMMappingsTable(VirtualMachineTable):
    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )

    hostgroups  = tables.Column( empty_values=(), verbose_name="Host Groups", order_by='hostgroups' )
    templates   = tables.Column( empty_values=(), verbose_name="Templates", order_by='templates' )
    proxy       = tables.Column( empty_values=(), verbose_name="Proxy", order_by='proxy' )
    proxy_group = tables.Column( empty_values=(), verbose_name="Proxy Group", order_by='proxy_group' )

    tags = columns.TagColumn( url_name='dcim:device_list' )

    class Meta(VirtualMachineTable.Meta):
        model = VirtualMachine
        fields = ("name", "hostgroups", "templates", "proxy", "proxy_group", "site", "role", "platform", "tags")
        default_columns = ("name", "hostgroups", "templates", "proxy", "proxy_group", "site", "role", "platform", "tags")

    # Generic render method for columns that return iterable mappings (hostgroups, templates)
    def _render_mappings(self, record, get_mapping_func):
        items = get_mapping_func( record )
        if not items:
            return mark_safe( '<span class="text-muted">&mdash;</span>' )
        return mark_safe(", ".join(
            f'<a href="{item.get_absolute_url()}">{item.name}</a>'
            for item in items
        ))

    # Generic order method for columns based on counts of mappings
    def _order_by_mapping_count(self, queryset, is_descending, get_mapping_func):
        vms = list( queryset )
        vms.sort(
            key=lambda x: len( get_mapping_func(x) ),
            reverse=is_descending
        )
        ordered_pks = [vm.pk for vm in vms]
        preserved_order = Case(*[When( pk=pk, then=pos ) for pos, pk in enumerate( ordered_pks )])
        queryset = queryset.model.objects.filter( pk__in=ordered_pks ).order_by( preserved_order )
        return queryset, True

    # Generic render method for single-mapping columns (proxy, proxy_group)
    def _render_single_mapping(self, record, get_mapping_func):
        item = get_mapping_func(record)
        if not item:
            return mark_safe('<span class="text-muted">&mdash;</span>')
        return mark_safe(f'<a href="{item.get_absolute_url()}">{item.name}</a>')

    # Generic order method for single-mapping columns (proxy, proxy_group)
    def _order_by_single_mapping(self, queryset, is_descending, get_mapping_func):
        vms = list( queryset )
        vms.sort(
            key=lambda x: (
                0 if get_mapping_func( x ) is None else 1,
                get_mapping_func( x ).name if get_mapping_func( x ) else '',
                x.name
            ),
            reverse=is_descending
        )
        ordered_pks = [vm.pk for vm in vms]
        preserved_order = Case(*[When( pk=pk, then=pos ) for pos, pk in enumerate( ordered_pks )])
        queryset = queryset.model.objects.filter( pk__in=ordered_pks ).order_by( preserved_order, 'name' )
        return queryset, True

    # Now, bind each column's render and order methods to the generic ones with proper function

    def render_hostgroups(self, record):
        return self._render_mappings( record, get_hostgroups_mappings )

    def order_hostgroups(self, queryset, is_descending):
        return self._order_by_mapping_count( queryset, is_descending, get_hostgroups_mappings )

    def render_templates(self, record):
        return self._render_mappings( record, get_templates_mappings )

    def order_templates(self, queryset, is_descending):
        return self._order_by_mapping_count( queryset, is_descending, get_templates_mappings )

    def render_proxy(self, record):
        return self._render_single_mapping( record, get_proxy_mapping )

    def order_proxy(self, queryset, is_descending):
        return self._order_by_single_mapping( queryset, is_descending, get_proxy_mapping )

    def render_proxy_group(self, record):
        return self._render_single_mapping( record, get_proxy_group_mapping )

    def order_proxy_group(self, queryset, is_descending):
        return self._order_by_single_mapping( queryset, is_descending, get_proxy_group_mapping )


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

from netbox_zabbix.utils import (
    get_host_groups_mapping_bulk,
    get_templates_mapping_bulk,
    get_proxy_mapping_bulk,
    get_proxy_group_mapping_bulk,
    get_valid_device_ids
)

class NetBoxOnlyDevicesTable(DeviceTable):
    name     = tables.Column( linkify=True )
    site     = tables.Column( linkify=True )
    role     = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )

    host_groups  = tables.Column( empty_values=(), verbose_name="Host Groups", order_by='host_groups' )
    templates    = tables.Column( empty_values=(), verbose_name="Templates",   order_by='templates' )
    proxy        = tables.Column( empty_values=(), verbose_name="Proxy",       order_by='proxy' )
    proxy_group  = tables.Column( empty_values=(), verbose_name="Proxy Group", order_by='proxy_group' )

    tags    = TagColumn( url_name='dcim:device_list' )
    actions = ActionsColumn( extra_buttons=[] )

    class Meta(DeviceTable.Meta):
        model = Device
        fields = (
            "name", "site", "role", "platform",
            "host_groups", "templates", "proxy", "proxy_group", "tags"
        )
        default_columns = fields


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.host_groups_map = {}
        self.templates_map = {}
        self.proxy_map = {}
        self.proxy_group_map = {}
        self.valid_device_ids = set()
    
    def render_actions(self, record):
        if record.id in getattr( self, "valid_device_ids", set() ):
            return columns.ActionsColumn( extra_buttons=EXTRA_DEVICE_ADD_ACTIONS ).render( record, self )
        return columns.ActionsColumn().render( record, self )
    
    def _render_mappings(self, record, map_data):
        items = map_data.get( record.id, [] )
        if not items:
            return mark_safe( '<span class="text-muted">&mdash;</span>' )
        return mark_safe(", ".join(
            f'<a href="{item.get_absolute_url()}">{item.name}</a>'
            for item in items
        ))
    
    def render_host_groups(self, record):
        return self._render_mappings( record, self.host_groups_map )
    
    def render_templates(self, record):
        return self._render_mappings( record, self.templates_map )
    
    def render_proxy(self, record):
        return self._render_mappings( record, self.proxy_map )
    
    def render_proxy_group(self, record):
        return self._render_mappings( record, self.proxy_group_map )
    
    # N.B. Patch required attribute(s) before ordering:
    #
    # Django Tables2 re-instantiates the table class on every request, including
    # sort requests triggered by clicking on column headers. As a result, any data
    # attached to the table instance during initial construction (e.g., in the view)
    # is *not* preserved across requests.
    #
    # To support ordering on computed or related fields (e.g., proxy name, site name),
    # we must inject the necessary mapping (e.g., `proxy_map`, `site_map`, etc.)
    # directly onto the table instance (`self`) before sorting.
    #
    # This pattern ensures:
    # - The mapping is computed only once (on first use), not repeatedly per row
    # - Sorting logic (e.g., in `_order_by_single_mapping`) has the required context
    # - We avoid repeated or expensive DB queries during sorting
    #
    # This patching works because Django Tables2 calls `order_<column>()` methods
    # after table instantiation, allowing us to lazily inject any required data
    # as attributes on `self`.
    #
    # If the mapping is already present (e.g., explicitly attached in the view),
    # it is reused to avoid recomputation.
    

    def order_host_groups(self, queryset, is_descending):
        if not hasattr(self, 'host_groups_map') or not self.host_groups_map:
            self.host_groups_map = get_host_groups_mapping_bulk( queryset, use_cache=True )
        return self._order_by_mapping_count( queryset, is_descending, self.host_groups_map )

    def order_templates(self, queryset, is_descending):
        if not hasattr(self, 'templates_map') or not self.templates_map:
            self.templates_map = get_templates_mapping_bulk( queryset, use_cache=True )        
        return self._order_by_mapping_count( queryset, is_descending, self.templates_map )

    def order_proxy(self, queryset, is_descending):
        if not hasattr(self, 'proxy_map') or not self.proxy_map:
            self.proxy_map = get_proxy_mapping_bulk( queryset, use_cache=True )
        return self._order_by_single_mapping( queryset, is_descending, self.proxy_map )
    
    def order_proxy_group(self, queryset, is_descending):
        if not hasattr(self, 'proxy_group_map') or not self.proxy_group_map:
            self.proxy_group_map = get_proxy_group_mapping_bulk( queryset, use_cache=True )        
        return self._order_by_single_mapping( queryset, is_descending, self.proxy_group_map )

    def _order_by_mapping_count(self, queryset, is_descending, mapping_dict):
        device_list = list( queryset )
        device_list.sort(
            key=lambda d: len( mapping_dict.get( d.pk, [] ) ),
            reverse=is_descending
        )
        ordered_pks = [d.pk for d in device_list]
        preserved = Case(*[ When( pk=pk, then=pos ) for pos, pk in enumerate( ordered_pks )] )
        return queryset.model.objects.filter( pk__in=ordered_pks ).order_by( preserved ), True

    def _order_by_single_mapping(self, queryset, is_descending, mapping_dict):
        device_list = list( queryset )
        
        def get_sort_key(device):
            proxies = mapping_dict.get( device.pk )
            proxy_name = proxies[0].name if proxies else ''

            # Devices without mapping come first if not descending
            has_mapping = 1 if proxies else 0
            return (has_mapping, proxy_name.lower(), device.name.lower())
    
        device_list.sort( key=get_sort_key, reverse=is_descending )
    
        ordered_pks = [device.pk for device in device_list]
    
        # Preserve the sort order using a CASE expression
        preserved_order = Case(
            *[When(pk=pk, then=Value(i)) for i, pk in enumerate(ordered_pks)],
            output_field=IntegerField()
        )
    
        # Reconstruct the queryset using this ordering
        ordered_queryset = queryset.model.objects.filter( pk__in=ordered_pks ).order_by( preserved_order, 'name' )
    
        return ordered_queryset, True
    

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

    name = tables.Column( linkify=True )
    site = tables.Column( linkify=True )
    role = tables.Column( linkify=True )
    platform = tables.Column( linkify=True )
    
    hostgroups  = tables.Column( empty_values=(), verbose_name="Host Groups", order_by='hostgroups' )
    templates   = tables.Column( empty_values=(), verbose_name="Templates", order_by='templates' )
    proxy       = tables.Column( empty_values=(), verbose_name="Proxy", order_by='proxy' )
    proxy_group = tables.Column( empty_values=(), verbose_name="Proxy Group", order_by='proxy_group' )
    
    tags = columns.TagColumn( url_name='dcim:device_list' )
    
    actions = columns.ActionsColumn( extra_buttons=EXTRA_VM_ADD_ACTIONS )
    
    class Meta(VirtualMachineTable.Meta):
        model = Device
        fields = ("name", "site", "role", "platform", "hostgroups", "templates", "proxy", "proxy_group", "tags")
        default_columns = ("name","site", "role", "platform", "hostgroups", "templates", "proxy", "proxy_group", "tags")
    
    # Generic render method for columns that return iterable mappings (hostgroups, templates)
    def _render_mappings(self, record, get_mapping_func):
        items = get_mapping_func( record )
        if not items:
            return mark_safe( '<span class="text-muted">&mdash;</span>' )
        return mark_safe(", ".join(
            f'<a href="{item.get_absolute_url()}">{item.name}</a>'
            for item in items
        ))
    
    # Generic order method for columns based on counts of mappings
    def _order_by_mapping_count(self, queryset, is_descending, get_mapping_func):
        vms = list( queryset )
        vms.sort(
            key=lambda x: len( get_mapping_func(x) ),
            reverse=is_descending
        )
        ordered_pks = [vm.pk for vm in vms]
        preserved_order = Case(*[When( pk=pk, then=pos ) for pos, pk in enumerate( ordered_pks )])
        queryset = queryset.model.objects.filter( pk__in=ordered_pks ).order_by( preserved_order )
        return queryset, True
    
    # Generic render method for single-mapping columns (proxy, proxy_group)
    def _render_single_mapping(self, record, get_mapping_func):
        item = get_mapping_func( record )
        if not item:
            return mark_safe('<span class="text-muted">&mdash;</span>')
        return mark_safe(f'<a href="{item.get_absolute_url()}">{item.name}</a>')
    
    # Generic order method for single-mapping columns (proxy, proxy_group)
    def _order_by_single_mapping(self, queryset, is_descending, get_mapping_func):
        devices = list( queryset )
        devices.sort(
            key=lambda x: (
                0 if get_mapping_func(x) is None else 1,
                get_mapping_func(x).name if get_mapping_func(x) else '',
                x.name
            ),
            reverse=is_descending
        )
        ordered_pks = [vm.pk for vm in devices]
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_pks)])
        queryset = queryset.model.objects.filter(pk__in=ordered_pks).order_by(preserved_order, 'name')
        return queryset, True
    
    # Now, bind each column's render and order methods to the generic ones with proper function
    
    def render_hostgroups(self, record):
        return self._render_mappings( record, get_hostgroups_mappings )
    
    def order_hostgroups(self, queryset, is_descending):
        return self._order_by_mapping_count( queryset, is_descending, get_hostgroups_mappings )
    
    def render_templates(self, record):
        return self._render_mappings( record, get_templates_mappings )
    
    def order_templates(self, queryset, is_descending):
        return self._order_by_mapping_count( queryset, is_descending, get_templates_mappings )
    
    def render_proxy(self, record):
        return self._render_single_mapping( record, get_proxy_mapping )
    
    def order_proxy(self, queryset, is_descending):
        return self._order_by_single_mapping( queryset, is_descending, get_proxy_mapping )
    
    def render_proxy_group(self, record):
        return self._render_single_mapping( record, get_proxy_group_mapping )
    
    def order_proxy_group(self, queryset, is_descending):
        return self._order_by_single_mapping( queryset, is_descending, get_proxy_group_mapping )
    

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