"""
NetBox Zabbix Plugin — URL Configuration

Defines all URL routes for the NetBox Zabbix integration plugin.
Each route maps a specific view to handle CRUD operations, jobs, 
and synchronization endpoints for Zabbix-related models such as 
Settings, Templates, and Mappings.

This module integrates seamlessly with NetBox’s generic view system
and provides clean namespacing under `plugins:netbox_zabbix`.

Usage:
    Included automatically by NetBox when the plugin is installed
    and enabled in the `PLUGINS` configuration.

Namespace:
    app_name = 'netbox_zabbix'
"""

# Django imports
from django.urls import path

# NetBox imports
from netbox.views.generic import ObjectChangeLogView

# NetBox Zabbix plugin imports
from netbox_zabbix import models, views

# App namespace
app_name = 'netbox_zabbix' 

# ------------------------------------------------------------------------------
# URL patterns
# ------------------------------------------------------------------------------

urlpatterns = (

    # --------------------------------------------------------------------------
    # Setting
    # --------------------------------------------------------------------------

    path( 'settings/',                    views.SettingListView.as_view(),   name='setting_list' ),
    path( 'settings/add/',                views.SettingEditView.as_view(),   name='setting_add' ),
    path( 'settings/<int:pk>/',           views.SettingView.as_view(),       name='setting' ),
    path( 'settings/<int:pk>/edit/',      views.SettingEditView.as_view(),   name='setting_edit' ),
    path( 'settings/<int:pk>/delete/',    views.SettingDeleteView.as_view(), name='setting_delete' ),
    path( 'settings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),     name='setting_changelog', kwargs={'model': models.Setting}, ),


    # --------------------------------------------------------------------------
    # Zabbix Check connection
    # --------------------------------------------------------------------------

    path( 'zabbix/check-connection', views.zabbix_check_connection, name='check_zabbix_connection' ),


    # --------------------------------------------------------------------------
    # Sync With Zabbix
    # --------------------------------------------------------------------------

    path( 'zabbix/sync', views.sync_with_zabbix, name='sync_with_zabbix' ),


    # --------------------------------------------------------------------------
    # Zabbix Import Settings (Tempate, Proxies, etc.)
    # --------------------------------------------------------------------------

    path( 'zabbix/import-settings',     views.zabbix_import_settings, name='import_zabbix_settings' ),
    path( 'zabbix/import_templates',    views.import_templates,       name='import_templates' ),
    path( 'zabbix/import_proxies',      views.import_proxies,         name='import_proxies' ),
    path( 'zabbix/import-proxy-groups', views.import_proxy_groups,    name='import_proxy_groups' ),
    path( 'zabbix/import-host-group',   views.import_host_groups,     name='import_host_groups' ),


    # --------------------------------------------------------------------------
    # Templates
    # --------------------------------------------------------------------------

    path( 'templates/',                   views.TemplateListView.as_view(),       name='template_list' ),
    path( 'templates/add/',               views.TemplateEditView.as_view(),       name='template_add' ),
    path( 'templates/<int:pk>/',          views.TemplateView.as_view(),           name='template' ),
    path( 'templates/<int:pk>/edit/',     views.TemplateEditView.as_view(),       name='template_edit' ),
    path( 'templates/<int:pk>/delete/',   views.TemplateDeleteView.as_view(),     name='template_delete' ),
    path( 'templates/delete/',            views.TemplateBulkDeleteView.as_view(), name='template_bulk_delete' ),
    path( 'templates/<int:pk>/changelog', ObjectChangeLogView.as_view(),          name='template_changelog', kwargs={'model': models.Template} ),


    # --------------------------------------------------------------------------
    # Proxy
    # --------------------------------------------------------------------------

    path( 'proxies/',                   views.ProxyListView.as_view(),       name='proxy_list' ),
    path( 'proxies/add/',               views.ProxyEditView.as_view(),       name='proxy_add' ),
    path( 'proxies/<int:pk>/',          views.ProxyView.as_view(),           name='proxy' ),
    path( 'proxies/<int:pk>/edit/',     views.ProxyEditView.as_view(),       name='proxy_edit' ),
    path( 'proxies/<int:pk>/delete/',   views.ProxyDeleteView.as_view(),     name='proxy_delete' ),
    path( 'proxies/delete/',            views.ProxyBulkDeleteView.as_view(), name='proxy_bulk_delete' ),
    path( 'proxies/<int:pk>/changelog', ObjectChangeLogView.as_view(),       name='proxy_changelog', kwargs={'model': models.Proxy} ),


    # --------------------------------------------------------------------------
    # Proxy Group
    # --------------------------------------------------------------------------
    
    path( 'proxy-groups/',                   views.ProxyGroupListView.as_view(),       name='proxygroup_list' ),
    path( 'proxy-groups/add/',               views.ProxyGroupEditView.as_view(),       name='proxygroup_add' ),
    path( 'proxy-groups/<int:pk>/',          views.ProxyGroupView.as_view(),           name='proxygroup' ),
    path( 'proxy-groups/<int:pk>/edit/',     views.ProxyGroupEditView.as_view(),       name='proxygroup_edit' ),
    path( 'proxy-groups/<int:pk>/delete/',   views.ProxyGroupDeleteView.as_view(),     name='proxygroup_delete' ),
    path( 'proxy-groups/delete/',            views.ProxyGroupBulkDeleteView.as_view(), name='proxygroup_bulk_delete' ),
    path( 'proxy-groups/<int:pk>/changelog', ObjectChangeLogView.as_view(),            name='proxygroup_changelog', kwargs={'model': models.ProxyGroup} ),


    # --------------------------------------------------------------------------
    # Host Group
    # --------------------------------------------------------------------------

    path( 'host-groups/',                    views.HostGroupListView.as_view(),       name='hostgroup_list' ),
    path( 'host-groups/add/',                views.HostGroupEditView.as_view(),       name='hostgroup_add' ),
    path( 'host-groups/<int:pk>/',           views.HostGroupView.as_view(),           name='hostgroup' ),
    path( 'host-groups/<int:pk>/edit/',      views.HostGroupEditView.as_view(),       name='hostgroup_edit' ),
    path( 'host-groups/<int:pk>/delete/',    views.HostGroupDeleteView.as_view(),     name='hostgroup_delete' ),
    path( 'host-groups/delete/',             views.HostGroupBulkDeleteView.as_view(), name='hostgroup_bulk_delete' ),
    path( 'host-groups/<int:pk>/changelog/', ObjectChangeLogView.as_view(),           name='hostgroup_changelog', kwargs={'model': models.HostGroup},  ),


    # --------------------------------------------------------------------------
    # Tag Mapping
    # --------------------------------------------------------------------------

    path( 'tag/mappings/',                    views.TagMappingListView.as_view(),   name='tagmapping_list' ),
    path( 'tag/mappings/add/',                views.TagMappingEditView.as_view(),   name='tagmapping_add' ),
    path( 'tag/mappings/<int:pk>/',           views.TagMappingView.as_view(),       name='tagmapping' ),
    path( 'tag/mappings/<int:pk>/edit/',      views.TagMappingEditView.as_view(),   name='tagmapping_edit' ),
    path( 'tag/mappings/<int:pk>/delete/',    views.TagMappingDeleteView.as_view(), name='tagmapping_delete' ),
    path( 'tag/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),        name='tagmapping_changelog', kwargs={'model': models.TagMapping} ),


    # --------------------------------------------------------------------------
    # Inventory Mapping
    # --------------------------------------------------------------------------

    path( 'inventory/mappings/',                    views.InventoryMappingListView.as_view(),   name='inventorymapping_list' ),
    path( 'inventory/mappings/add/',                views.InventoryMappingEditView.as_view(),   name='inventorymapping_add' ),
    path( 'inventory/mappings/<int:pk>/',           views.InventoryMappingView.as_view(),       name='inventorymapping' ),
    path( 'inventory/mappings/<int:pk>/edit/',      views.InventoryMappingEditView.as_view(),   name='inventorymapping_edit' ),
    path( 'inventory/mappings/<int:pk>/delete/',    views.InventoryMappingDeleteView.as_view(), name='inventorymapping_delete' ),
    path( 'inventory/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),              name='inventorymapping_changelog', kwargs={'model': models.InventoryMapping}  ),


    # --------------------------------------------------------------------------
    # Device Mapping
    # --------------------------------------------------------------------------

    path( 'device/mappings/',                    views.DeviceMappingListView.as_view(),       name='devicemapping_list' ),
    path( 'device/mappings/add/',                views.DeviceMappingEditView.as_view(),       name='devicemapping_add' ),
    path( 'device/mappings/<int:pk>/',           views.DeviceMappingView.as_view(),           name='devicemapping' ),
    path( 'device/mappings/<int:pk>/edit/',      views.DeviceMappingEditView.as_view(),       name='devicemapping_edit' ),
    path( 'device/mappings/<int:pk>/delete/',    views.DeviceMappingDeleteView.as_view(),     name='devicemapping_delete' ),
    path( 'device/mappings/delete/',             views.DeviceMappingBulkDeleteView.as_view(), name='devicemapping_bulk_delete' ),
    path( 'device/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),               name='devicemapping_changelog', kwargs={'model': models.DeviceMapping}  ),
    path( 'device/mappings/<int:pk>/devices/',   views.DeviceMappingDevicesView.as_view(),    name='devicemapping_devices' ),


    # --------------------------------------------------------------------------
    # VM Mapping
    # --------------------------------------------------------------------------

    path( 'virtual-machines/mappings/',                    views.VMMappingListView.as_view(),       name='vmmapping_list' ),
    path( 'virtual-machines/mappings/add/',                views.VMMappingEditView.as_view(),       name='vmmapping_add' ),
    path( 'virtual-machines/mappings/<int:pk>/',           views.VMMappingView.as_view(),           name='vmmapping' ),
    path( 'virtual-machines/mappings/<int:pk>/edit/',      views.VMMappingEditView.as_view(),       name='vmmapping_edit' ),
    path( 'virtual-machines/mappings/<int:pk>/delete/',    views.VMMappingDeleteView.as_view(),     name='vmmapping_delete' ),
    path( 'virtual-machines/mappings/delete/',             views.VMMappingBulkDeleteView.as_view(), name='vmmapping_bulk_delete' ),
    path( 'virtual-machines/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),           name='vmmapping_changelog', kwargs={'model': models.VMMapping}  ),
    path( 'virtual-machines/mappings/<int:pk>/vms/',       views.VMMappingVMsView.as_view(),        name='vmmapping_vms' ),


    # --------------------------------------------------------------------------
    # Host Config
    # --------------------------------------------------------------------------

    path( 'host-config/',                    views.HostConfigListView.as_view(),        name='hostconfig_list' ),
    path( 'host-config/add/',                views.HostConfigEditView.as_view(),        name='hostconfig_add' ),
    path( 'host-config/<int:pk>/',           views.HostConfigView.as_view(),            name='hostconfig' ),
    path( 'host-config/<int:pk>/edit/',      views.HostConfigEditView.as_view(),        name='hostconfig_edit' ),
    path( 'host-config/<int:pk>/delete/',    views.HostConfigDeleteView.as_view(),      name='hostconfig_delete' ),
    path( 'host-config/delete/',             views.HostConfigBulkDeleteView.as_view(),  name='hostconfig_bulk_delete' ),
    path( 'host-config/<int:pk>/changelog/', ObjectChangeLogView.as_view(),             name='hostconfig_changelog', kwargs={'model': models.HostConfig} ),
    path( 'host-config/<int:pk>/problems',   views.HostConfigProblemsTabView.as_view(), name='hostconfig_problems' ),
    path( 'host-config/<int:pk>/jobs',       views.HostConfigJobsTabView.as_view(),     name='hostconfig_jobs' ),
    path( 'host-config/<int:pk>/difference', views.HostConfigDiffTabView.as_view(),     name='hostconfig_difference' ),
    path( 'host-config/update-sync-status',  views.update_sync_status,                  name='hostconfig_updatesyncstatus' ),


    # --------------------------------------------------------------------------
    # Agent Interface
    # --------------------------------------------------------------------------

    path( 'agent-interface/',                    views.AgentInterfaceListView.as_view(),       name='agentinterface_list' ),
    path( 'agent-interface/add/',                views.AgentInterfaceEditView.as_view(),       name='agentinterface_add' ),
    path( 'agent-interface/<int:pk>/',           views.AgentInterfaceView.as_view(),           name='agentinterface' ),
    path( 'agent-interface/<int:pk>/edit/',      views.AgentInterfaceEditView.as_view(),       name='agentinterface_edit' ),
    path( 'agent-interface/<int:pk>/delete/',    views.AgentInterfaceDeleteView.as_view(),     name='agentinterface_delete' ),
    path( 'agent-interface/delete/',             views.AgentInterfaceBulkDeleteView.as_view(), name='agentinterface_bulk_delete' ),
    path( 'agent-interface/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                name='agentinterface_changelog', kwargs={'model': models.AgentInterface} ),


    # --------------------------------------------------------------------------
    # SNMP Interface
    # --------------------------------------------------------------------------

    path( 'snmp-interface/',                     views.SNMPInterfaceListView.as_view(),       name='snmpinterface_list' ),
    path( 'snmp-interface/add/',                 views.SNMPInterfaceEditView.as_view(),       name='snmpinterface_add' ),
    path( 'snmp-interface/<int:pk>/',            views.SNMPInterfaceView.as_view(),           name='snmpinterface' ),
    path( 'snmp-interface/<int:pk>/edit/',       views.SNMPInterfaceEditView.as_view(),       name='snmpinterface_edit' ),
    path( 'snmp-interface/<int:pk>/delete/',     views.SNMPInterfaceDeleteView.as_view(),     name='snmpinterface_delete' ),
    path( 'snmp-interface/delete/',              views.SNMPInterfaceBulkDeleteView.as_view(), name='snmpinterface_bulk_delete' ),
    path( 'snmp-interface/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),               name='snmpinterface_changelog', kwargs={'model': models.SNMPInterface} ),

    # --------------------------------------------------------------------------
    # Importable Hosts
    # --------------------------------------------------------------------------

    path( 'importable-hosts/', views.ImportableHostsListView.as_view(), name='importablehosts_list' ),


    # --------------------------------------------------------------------------
    # NetBox Only Hosts
    # --------------------------------------------------------------------------

    path( 'netbox/netbox-only-hosts/', views.NetBoxOnlyHostsView.as_view(), name='netboxhosts_list' ),


    # --------------------------------------------------------------------------
    # Zabbix Only Hosts
    # --------------------------------------------------------------------------

    path( 'zabbix/zabbix-only-hosts/', views.ZabbixOnlyHostsView.as_view(), name='zabbixonlyhosts' ),


    # --------------------------------------------------------------------------
    # Event Log
    # --------------------------------------------------------------------------

    path( 'events/',                   views.EventLogListView.as_view(),       name='eventlog_list' ),
    path( 'events/add',                views.EventLogEditView.as_view(),       name='eventlog_add' ),
    path( 'events/<int:pk>/',          views.EventLogView.as_view(),           name='eventlog' ),
    path( 'events/<int:pk>/edit',      views.EventLogEditView.as_view(),       name='eventlog_edit' ),
    path( 'events/<int:pk>/delete',    views.EventLogDeleteView.as_view(),     name='eventlog_delete' ),
    path( 'events/delete/',            views.EventLogBulkDeleteView.as_view(), name='eventlog_bulk_delete' ),
    path( 'events/<int:pk>/changelog', ObjectChangeLogView.as_view(),          name='eventlog_changelog', kwargs={'model': models.EventLog} ),


    # --------------------------------------------------------------------------
    # Maintenance
    # --------------------------------------------------------------------------
    
    path( 'maintenance/',                       views.MaintenanceListView.as_view(),        name='maintenance_list' ),
    path( 'maintenance/add/',                   views.MaintenanceEditView.as_view(),        name='maintenance_add' ),
    path( 'maintenance/<int:pk>/',              views.MaintenanceView.as_view(),            name='maintenance' ),
    path( 'maintenance/<int:pk>/edit/',         views.MaintenanceEditView.as_view(),        name='maintenance_edit' ),
    path( 'maintenance/<int:pk>/delete/',       views.MaintenanceDeleteView.as_view(),      name='maintenance_delete' ),
    path( 'maintenance/delete/',                views.MaintenanceBulkDeleteView.as_view(),  name='maintenance_bulk_delete' ),
    path( 'maintenance/<int:pk>/host_configs/', views.MaintenanceHostConfigsView.as_view(), name='maintenance_host_configs' ),
    path( 'maintenance/<int:pk>/changelog',     ObjectChangeLogView.as_view(),              name='maintenance_changelog', kwargs={'model': models.Maintenance} ),
    
 ) 
