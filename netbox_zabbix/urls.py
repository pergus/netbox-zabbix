# urls.py
from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_zabbix import models, views


from core.views import JobView

app_name = 'netbox_zabbix' 


urlpatterns = (
    
    # --------------------------------------------------------------------------
    # Configuration
    # --------------------------------------------------------------------------

    # Configuration
    path( 'configs/',                    views.ConfigListView.as_view(),   name='config_list' ),
    path( 'configs/add/',                views.ConfigEditView.as_view(),   name='config_add' ),
    path( 'configs/<int:pk>/',           views.ConfigView.as_view(),       name='config' ),
    path( 'configs/<int:pk>/edit/',      views.ConfigEditView.as_view(),   name='config_edit' ),
    path( 'configs/<int:pk>/delete/',    views.ConfigDeleteView.as_view(), name='config_delete' ),
    path( 'configs/<int:pk>/changelog/', ObjectChangeLogView.as_view(),    name='config_changelog', kwargs={'model': models.Config}, ),

    # Check Zabbix Connection
    path('zabbix/check-connection', views.zabbix_check_connection, name='check_zabbix_connection' ),
        
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
    path( 'templates/review-deletions/',  views.templates_review_deletions,       name='templates_review_deletions' ), 
    path( 'templates/confirm-deletions/', views.templates_confirm_deletions,      name='templates_confirm_deletions' ),


    # --------------------------------------------------------------------------
    # Zabbix Import Settings (Tempate, Proxies, etc.)
    # --------------------------------------------------------------------------

    path( 'zabbix/import-settings',     views.zabbix_import_settings, name='import_zabbix_settings' ),
    path( 'zabbix/import_templates',    views.import_templates,       name='import_templates' ),
    path( 'zabbix/import_proxies',      views.import_proxies,         name='import_proxies' ),
    path( 'zabbix/import-proxy-groups', views.import_proxy_groups,    name='import_proxy_groups' ),
    path( 'zabbix/import-host-group',   views.import_host_groups,     name='import_host_groups' ),
    
    
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
    path( 'proxies/review-deletions/',  views.proxies_review_deletions,      name='proxies_review_deletions' ), 
    path( 'proxies/confirm-deletions/', views.proxies_confirm_deletions,     name='proxies_confirm_deletions' ),

    # --------------------------------------------------------------------------
    # Proxy Groups
    # --------------------------------------------------------------------------

    path( 'proxy-groups/',                   views.ProxyGroupListView.as_view(),       name='proxygroup_list' ),
    path( 'proxy-groups/add/',               views.ProxyGroupEditView.as_view(),       name='proxygroup_add' ),
    path( 'proxy-groups/<int:pk>/',          views.ProxyGroupView.as_view(),           name='proxygroup' ),
    path( 'proxy-groups/<int:pk>/edit/',     views.ProxyGroupEditView.as_view(),       name='proxygroup_edit' ),
    path( 'proxy-groups/<int:pk>/delete/',   views.ProxyGroupDeleteView.as_view(),     name='proxygroup_delete' ),
    path( 'proxy-groups/delete/',            views.ProxyGroupBulkDeleteView.as_view(), name='proxygroup_bulk_delete' ),
    path( 'proxy-groups/<int:pk>/changelog', ObjectChangeLogView.as_view(),            name='proxygroup_changelog', kwargs={'model': models.ProxyGroup} ),
    path( 'proxy-groups/review-deletions/',  views.proxy_groups_review_deletions,      name='proxygroups_review_deletions' ), 
    path( 'proxy-groups/confirm-deletions/', views.proxy_groups_confirm_deletions,     name='proxygroups_confirm_deletions' ),


    # --------------------------------------------------------------------------
    # Host Groups
    # --------------------------------------------------------------------------

    path( 'host-groups/',                    views.HostGroupListView.as_view(),       name='hostgroup_list' ),
    path( 'host-groups/add/',                views.HostGroupEditView.as_view(),       name='hostgroup_add' ),
    path( 'host-groups/<int:pk>/',           views.HostGroupView.as_view(),           name='hostgroup' ),
    path( 'host-groups/<int:pk>/edit/',      views.HostGroupEditView.as_view(),       name='hostgroup_edit' ),
    path( 'host-groups/<int:pk>/delete/',    views.HostGroupDeleteView.as_view(),     name='hostgroup_delete' ),
    path( 'host-groups/delete/',             views.HostGroupBulkDeleteView.as_view(), name='hostgroup_bulk_delete' ),
    path( 'host-groups/<int:pk>/changelog/', ObjectChangeLogView.as_view(),           name='hostgroup_changelog', kwargs={'model': models.HostGroup},  ),


    # --------------------------------------------------------------------------
    # Zabbix Configurations
    # --------------------------------------------------------------------------

    # Zabbix Device Configuration
    path( 'devices/zabbix-config/',                    views.DeviceZabbixConfigListView.as_view(),       name='devicezabbixconfig_list' ),
    path( 'devices/zabbix-config/add/',                views.DeviceZabbixConfigEditView.as_view(),       name='devicezabbixconfig_add' ),
    path( 'devices/zabbix-config/<int:pk>/',           views.DeviceZabbixConfigView.as_view(),           name='devicezabbixconfig' ),
    path( 'devices/zabbix-config/<int:pk>/edit/',      views.DeviceZabbixConfigEditView.as_view(),       name='devicezabbixconfig_edit' ),
    path( 'devices/zabbix-config/<int:pk>/delete/',    views.DeviceZabbixConfigDeleteView.as_view(),     name='devicezabbixconfig_delete' ),
    path( 'devices/zabbix-config/delete/',             views.DeviceZabbixConfigBulkDeleteView.as_view(), name='devicezabbixconfig_bulk_delete' ),
    path( 'devices/zabbix-config/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                    name='devicezabbixconfig_changelog', kwargs={'model': models.DeviceZabbixConfig} ),
    path( 'devices/zabbix-config/<int:pk>/jobs',       views.DeviceZabbixConfigJobsTabView.as_view(),    name='devicezabbixconfig_jobs' ),

    path( 'devices/zabbix-config/<int:pk>/difference', views.DeviceZabbixConfigDiffTabView.as_view(),    name='devicezabbixconfig_difference'),

    # VM Zabbix Configuration
    path( 'virtual-machines/zabbix-config/',                    views.VMZabbixConfigListView.as_view(),   name='vmzabbixconfig_list' ),
    path( 'virtual-machines/zabbix-config/add/',                views.VMZabbixConfigEditView.as_view(),   name='vmzabbixconfig_add' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/',           views.VMZabbixConfigView.as_view(),       name='vmzabbixconfig' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/edit/',      views.VMZabbixConfigEditView.as_view(),   name='vmzabbixconfig_edit' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/delete/',    views.VMZabbixConfigDeleteView.as_view(), name='vmzabbixconfig_delete' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/changelog/', ObjectChangeLogView.as_view(),            name='vmzabbixconfig_changelog', kwargs={'model': models.VMZabbixConfig} ),

    # Zabbix Configs (Devices and VMs combined)
    path( 'zabbix/configs/',                     views.ZabbixConfigListView.as_view(),   name='zabbixconfig_list' ),
    path( 'zabbix/configs/edit/<int:pk>/',       views.ZabbixConfigEditView.as_view(),   name='zabbixconfig_edit' ),
    path( 'zabbix/configs/delete/<int:pk>/',     views.ZabbixConfigDeleteView.as_view(), name='zabbixconfig_delete' ),
    path( 'zabbix/configs/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),          name='zabbixconfig_changelog', kwargs={'model': models.ZabbixConfig} ),


    # --------------------------------------------------------------------------
    # Sync With Zabbix
    # --------------------------------------------------------------------------
    path( 'zabbix/sync', views.sync_device_with_zabbix, name='sync_device_with_zabbix' ),


    # --------------------------------------------------------------------------
    # Importable Hosts
    # --------------------------------------------------------------------------

    # Importable Zabbix Hosts (Devices/VMs in Zabbix but not configured in NetBox)
    path( 'zabbix/importable-devices/', views.ImportableDeviceListView.as_view(), name='importabledevice_list' ),
    path( 'zabbix/importable-vms/',     views.ImportableVMListView.as_view(),     name='importablevm_list' ),


    # --------------------------------------------------------------------------
    # NetBox/Zabbix Only Hosts
    # --------------------------------------------------------------------------

    # NetBox-only Devices (not present in Zabbix)
    path( 'zabbix/netbox-only-devices/', views.NetBoxOnlyDevicesView.as_view(), name='netboxonlydevices' ),

    # Netbox-only VMs
    path( 'zabbix/netbox-only-vms/', views.NetBoxOnlyVMsView.as_view(), name='netboxonlyvms' ),

    # Zabbix-only hosts (hosts only in Zabbix and not in NetBox)
    path( 'zabbix/zabbix-only-hosts/', views.ZabbixOnlyHostsView.as_view(), name='zabbixonlyhosts' ),


    # --------------------------------------------------------------------------
    # Quick Add
    # --------------------------------------------------------------------------

    # Quick add Agent and SNMPv3 Device Configuration
    path( 'devices/zabbix-config/validate-quick-add/',  views.device_validate_quick_add, name='device_validate_quick_add' ),
    path( 'devices/zabbix-config/quick-add-agent/',     views.device_quick_add_agent,    name='device_quick_add_agent' ),
    path( 'devices/zabbix-config/quick-add-snmpv3/',    views.device_quick_add_snmpv3,   name='device_quick_add_snmpv3' ),


    # --------------------------------------------------------------------------
    # Interfaces
    # --------------------------------------------------------------------------

    # Device Agent Interfaces
    path( 'interfaces/device-agents/',                    views.DeviceAgentInterfaceListView.as_view(),       name='deviceagentinterface_list' ),
    path( 'interfaces/device-agents/add/',                views.DeviceAgentInterfaceEditView.as_view(),       name='deviceagentinterface_add' ),
    path( 'interfaces/device-agents/<int:pk>/',           views.DeviceAgentInterfaceView.as_view(),           name='deviceagentinterface' ),
    path( 'interfaces/device-agents/<int:pk>/edit/',      views.DeviceAgentInterfaceEditView.as_view(),       name='deviceagentinterface_edit' ),
    path( 'interfaces/device-agents/<int:pk>/delete/',    views.DeviceAgentInterfaceDeleteView.as_view(),     name='deviceagentinterface_delete' ),
    path( 'interfaces/device-agents/delete/',             views.DeviceAgentInterfaceBulkDeleteView.as_view(), name='deviceagentinterface_bulk_delete' ),
    path( 'interfaces/device-agents/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                      name='deviceagentinterface_changelog', kwargs={'model': models.DeviceAgentInterface} ),

    # Device SNMPv3 Interfaces
    path( 'interfaces/device-snmpv3/',                    views.DeviceSNMPv3InterfaceListView.as_view(),       name='devicesnmpv3interface_list' ),
    path( 'interfaces/device-snmpv3/add/',                views.DeviceSNMPv3InterfaceEditView.as_view(),       name='devicesnmpv3interface_add' ),
    path( 'interfaces/device-snmpv3/<int:pk>/',           views.DeviceSNMPv3InterfaceView.as_view(),           name='devicesnmpv3interface' ),
    path( 'interfaces/device-snmpv3/<int:pk>/edit/',      views.DeviceSNMPv3InterfaceEditView.as_view(),       name='devicesnmpv3interface_edit' ),
    path( 'interfaces/device-snmpv3/<int:pk>/delete/',    views.DeviceSNMPv3InterfaceDeleteView.as_view(),     name='devicesnmpv3interface_delete' ),
    path( 'interfaces/device-snmpv3/delete/',             views.DeviceSNMPv3InterfaceBulkDeleteView.as_view(), name='devicesnmpv3interface_bulk_delete' ),
    path( 'interfaces/device-snmpv3/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                       name='devicesnmpv3interface_changelog', kwargs={'model': models.DeviceSNMPv3Interface} ),

    # VM Agent Interfaces
    path( 'interfaces/vm-agents/',                    views.VMAgentInterfaceListView.as_view(),   name='vmagentinterface_list' ),
    path( 'interfaces/vm-agents/add/',                views.VMAgentInterfaceEditView.as_view(),   name='vmagentinterface_add' ),
    path( 'interfaces/vm-agents/<int:pk>/',           views.VMAgentInterfaceView.as_view(),       name='vmagentinterface' ),
    path( 'interfaces/vm-agents/<int:pk>/edit/',      views.VMAgentInterfaceEditView.as_view(),   name='vmagentinterface_edit' ),
    path( 'interfaces/vm-agents/<int:pk>/delete/',    views.VMAgentInterfaceDeleteView.as_view(), name='vmagentinterface_delete' ),
    path( 'interfaces/vm-agents/<int:pk>/changelog/', ObjectChangeLogView.as_view(),              name='vmagentinterface_changelog', kwargs={'model': models.VMAgentInterface} ),

    # VM SNMPv3 Interfaces
    path( 'interfaces/vm-snmpv3/',                    views.VMSNMPv3InterfaceListView.as_view(),   name='vmsnmpv3interface_list' ),
    path( 'interfaces/vm-snmpv3/add/',                views.VMSNMPv3InterfaceEditView.as_view(),   name='vmsnmpv3interface_add' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/',           views.VMSNMPv3InterfaceView.as_view(),       name='vmsnmpv3interface' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/edit/',      views.VMSNMPv3InterfaceEditView.as_view(),   name='vmsnmpv3interface_edit' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/delete/',    views.VMSNMPv3InterfaceDeleteView.as_view(), name='vmsnmpv3interface_delete' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/changelog/', ObjectChangeLogView.as_view(),               name='vmsnmpv3interface_changelog', kwargs={'model': models.VMSNMPv3Interface} ),


    # --------------------------------------------------------------------------
    # Tag Mapping
    # --------------------------------------------------------------------------

    path( 'tag/mappings/',                    views.TagMappingListView.as_view(),   name='tagmapping_list' ),
    path( 'tag/mappings/add/',                views.TagMappingEditView.as_view(),   name='tagmapping_add' ),
    path( 'tag/mapping/<int:pk>/',            views.TagMappingView.as_view(),       name='tagmapping' ),
    path( 'tag/mappings/<int:pk>/edit/',      views.TagMappingEditView.as_view(),   name='tagmapping_edit' ),
    path( 'tag/mappings/<int:pk>/delete/',    views.TagMappingDeleteView.as_view(), name='tagmapping_delete' ),
    path( 'tag/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),        name='tagmapping_changelog', kwargs={'model': models.TagMapping} ),


    # --------------------------------------------------------------------------
    # Inventory Mapping
    # --------------------------------------------------------------------------

    path( 'inventory/mappings/',                    views.InventoryMappingListView.as_view(),   name='inventorymapping_list' ),
    path( 'inventory/mappings/add/',                views.InventoryMappingEditView.as_view(),   name='inventorymapping_add' ),
    path( 'inventory/mapping/<int:pk>/',            views.InventoryMappingView.as_view(),       name='inventorymapping' ),
    path( 'inventory/mappings/<int:pk>/edit/',      views.InventoryMappingEditView.as_view(),   name='inventorymapping_edit' ),
    path( 'inventory/mappings/<int:pk>/delete/',    views.InventoryMappingDeleteView.as_view(), name='inventorymapping_delete' ),
    path( 'inventory/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),              name='inventorymapping_changelog', kwargs={'model': models.InventoryMapping}  ),


    # --------------------------------------------------------------------------
    # Device Mapping
    # --------------------------------------------------------------------------
    
    path( 'device/mappings/',                    views.DeviceMappingListView.as_view(),       name='devicemapping_list' ),
    path( 'device/mappings/add/',                views.DeviceMappingEditView.as_view(),       name='devicemapping_add' ),
    path( 'device/mapping/<int:pk>/',            views.DeviceMappingView.as_view(),           name='devicemapping' ),
    path( 'device/mappings/<int:pk>/edit/',      views.DeviceMappingEditView.as_view(),       name='devicemapping_edit' ),
    path( 'device/mappings/<int:pk>/delete/',    views.DeviceMappingDeleteView.as_view(),     name='devicemapping_delete' ),
    path( 'device/mappings/delete/',             views.DeviceMappingBulkDeleteView.as_view(), name='devicemapping_bulk_delete' ),
    path( 'device/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),               name='devicemapping_changelog', kwargs={'model': models.DeviceMapping}  ),
    path( 'device/mappings/<int:pk>/devices/',   views.DeviceMappingDevicesView.as_view(),    name='devicemapping_devices' ),


    # --------------------------------------------------------------------------
    # VM Mapping
    # --------------------------------------------------------------------------

    path( 'virtual-machines/mappings/',                    views.VMMappingListView.as_view(),   name='vmmapping_list' ),
    path( 'virtual-machines/mappings/add/',                views.VMMappingEditView.as_view(),   name='vmmapping_add' ),
    path( 'virtual-machines/mapping/<int:pk>/',            views.VMMappingView.as_view(),       name='vmmapping' ),
    path( 'virtual-machines/mappings/<int:pk>/edit/',      views.VMMappingEditView.as_view(),   name='vmmapping_edit' ),
    path( 'virtual-machines/mappings/<int:pk>/delete/',    views.VMMappingDeleteView.as_view(), name='vmmapping_delete' ),
    path( 'virtual-machines/mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),       name='vmmapping_changelog', kwargs={'model': models.VMMapping}  ),


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

 ) 
