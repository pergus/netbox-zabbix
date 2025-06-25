# urls.py
from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_zabbix import models, views

app_name = 'netbox_zabbix' 


urlpatterns = (
    
    # --------------------------------------------------------------------------
    # Configuration
    # --------------------------------------------------------------------------

    # Configuration
    path( 'configs/',                    views.ConfigListView.as_view(),      name='config_list' ),
    path( 'configs/add/',                views.ConfigEditView.as_view(),      name='config_add' ),
    path( 'configs/<int:pk>/',           views.ConfigView.as_view(),          name='config' ),
    path( 'configs/<int:pk>/edit/',      views.ConfigEditView.as_view(),      name='config_edit' ),
    path( 'configs/<int:pk>/delete/',    views.ConfigDeleteView.as_view(),    name='config_delete' ),
    path( 'configs/<int:pk>/changelog/', ObjectChangeLogView.as_view(),       name='config_changelog', kwargs={'model': models.Config},  ),

    # Check Zabbix Connection
    path('zabbix/check-connection', views.zabbix_check_connection, name='check_zabbix_connection'),
        
    # --------------------------------------------------------------------------
    # Templates + Mappings
    # --------------------------------------------------------------------------

    # Zabbix Templates
    path( 'templates/',                   views.TemplateListView.as_view(),   name='template_list' ),
    path( 'templates/add/',               views.TemplateEditView.as_view(),   name='template_add' ),
    path( 'templates/<int:pk>/',          views.TemplateView.as_view(),       name='template' ),
    path( 'templates/<int:pk>/edit/',     views.TemplateEditView.as_view(),   name='template_edit' ),
    path( 'templates/<int:pk>/delete/',   views.TemplateDeleteView.as_view(), name='template_delete' ),
    path( 'templates/<int:pk>/changelog', ObjectChangeLogView.as_view(),      name='template_changelog', kwargs={'model': models.Template} ),
    path( 'templates/review-deletions/',  views.templates_review_deletions,   name='templates_review_deletions' ), 
    path( 'templates/confirm-deletions/', views.templates_confirm_deletions,  name='templates_confirm_deletions' ),

    # Zabbix Template Mappings
    path( 'template-mappings/',                    views.TemplateMappingListView.as_view(),         name='templatemapping_list' ),
    path( 'template-mappings/add/',                views.TemplateMappingEditView.as_view(),         name='templatemapping_add' ),
    path( 'template-mappings/delete/',             views.TemplateMappingBulkDeleteView.as_view(),   name='templatemapping_bulk_delete' ),        
    path( 'template-mappings/<int:pk>/',           views.TemplateMappingView.as_view(),             name='templatemapping' ),
    path( 'template-mappings/<int:pk>/edit/',      views.TemplateMappingEditView.as_view(),         name='templatemapping_edit' ),        
    path( 'template-mappings/<int:pk>/delete/',    views.TemplateMappingDeleteView.as_view(),       name='templatemapping_delete' ),
    path( 'template-mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                   name='templatemapping_changelog', kwargs={'model': models.TemplateMapping},  ),
    
    path( 'template-mappings/<int:pk>/devices/',   views.HostGroupMappingDevicesView.as_view(),  name='hostgroupmapping_devices' ),
    path( 'template-mappings/<int:pk>/vms/',       views.HostGroupMappingVMsView.as_view(),      name='hostgroupmapping_vms' ),

    # --------------------------------------------------------------------------
    # Zabbix Imports
    # --------------------------------------------------------------------------
    
    # Import Zabbix Settings
    path( 'zabbix/import-settings', views.zabbix_import_settings,  name='import_zabbix_settings' ),    
    path( 'zabbix/import_templates',    views.import_templates,    name='import_templates' ),
    path( 'zabbix/import_proxies',      views.import_proxies,      name='import_proxies' ),
    path( 'zabbix/import-proxy-groups', views.import_proxy_groups, name='import_proxy_groups' ),
    path( 'zabbix/import-host-group',   views.import_host_groups,  name='import_host_groups' ),
    
    
    # --------------------------------------------------------------------------
    # Proxy + Mappings
    # --------------------------------------------------------------------------

    # Zabbix Proxy
    path( 'proxies/',                   views.ProxyListView.as_view(),   name='proxy_list' ),
    path( 'proxies/add/',               views.ProxyEditView.as_view(),   name='proxy_add' ),
    path( 'proxies/<int:pk>/',          views.ProxyView.as_view(),       name='proxy' ),
    path( 'proxies/<int:pk>/edit/',     views.ProxyEditView.as_view(),   name='proxy_edit' ),
    path( 'proxies/<int:pk>/delete/',   views.ProxyDeleteView.as_view(), name='proxy_delete' ),
    path( 'proxies/<int:pk>/changelog', ObjectChangeLogView.as_view(),   name='proxy_changelog', kwargs={'model': models.Proxy} ),
    path( 'proxies/review-deletions/',  views.proxies_review_deletions,  name='proxies_review_deletions' ), 
    path( 'proxies/confirm-deletions/', views.proxies_confirm_deletions, name='proxies_confirm_deletions' ),

    # Zabbix Proxy Mappings
    path( 'proxy-mappings/',                    views.ProxyMappingListView.as_view(),         name='proxymapping_list' ),
    path( 'proxy-mappings/add/',                views.ProxyMappingEditView.as_view(),         name='proxymapping_add' ),
    path( 'proxy-mappings/delete/',             views.ProxyMappingBulkDeleteView.as_view(),   name='proxymapping_bulk_delete' ),        
    path( 'proxy-mappings/<int:pk>/',           views.ProxyMappingView.as_view(),             name='proxymapping' ),
    path( 'proxy-mappings/<int:pk>/edit/',      views.ProxyMappingEditView.as_view(),         name='proxymapping_edit' ),        
    path( 'proxy-mappings/<int:pk>/delete/',    views.ProxyMappingDeleteView.as_view(),       name='proxymapping_delete' ),
    path( 'proxy-mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                name='proxymapping_changelog', kwargs={'model': models.ProxyMapping},  ),

    # --------------------------------------------------------------------------
    # Proxy Groups + Mappings
    # --------------------------------------------------------------------------
        
    # Zabbix Proxy Groups
    path( 'proxy-groups/',                   views.ProxyGroupListView.as_view(),   name='proxygroup_list' ),
    path( 'proxy-groups/add/',               views.ProxyGroupEditView.as_view(),   name='proxygroup_add' ),
    path( 'proxy-groups/<int:pk>/',          views.ProxyGroupView.as_view(),       name='proxygroup' ),
    path( 'proxy-groups/<int:pk>/edit/',     views.ProxyGroupEditView.as_view(),   name='proxygroup_edit' ),
    path( 'proxy-groups/<int:pk>/delete/',   views.ProxyGroupDeleteView.as_view(), name='proxygroup_delete' ),
    path( 'proxy-groups/<int:pk>/changelog', ObjectChangeLogView.as_view(),        name='proxygroup_changelog', kwargs={'model': models.ProxyGroup} ),
    path( 'proxy-groups/review-deletions/',  views.proxygroups_review_deletions,   name='proxygroups_review_deletions' ), 
    path( 'proxy-groups/confirm-deletions/', views.proxygroups_confirm_deletions,  name='proxygroups_confirm_deletions' ),

    # Zabbix Proxy Group Mappings
    path( 'proxy-group-mappings/',                    views.ProxyGroupMappingListView.as_view(),         name='proxygroupmapping_list' ),
    path( 'proxy-group-mappings/add/',                views.ProxyGroupMappingEditView.as_view(),         name='proxygroupmapping_add' ),
    path( 'proxy-group-mappings/delete/',             views.ProxyGroupMappingBulkDeleteView.as_view(),   name='proxygroupmapping_bulk_delete' ),        
    path( 'proxy-group-mappings/<int:pk>/',           views.ProxyGroupMappingView.as_view(),             name='proxygroupmapping' ),
    path( 'proxy-group-mappings/<int:pk>/edit/',      views.ProxyGroupMappingEditView.as_view(),         name='proxygroupmapping_edit' ),        
    path( 'proxy-group-mappings/<int:pk>/delete/',    views.ProxyGroupMappingDeleteView.as_view(),       name='proxygroupmapping_delete' ),
    path( 'proxy-group-mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                     name='proxygroupmapping_changelog', kwargs={'model': models.ProxyGroupMapping},  ),
    

    # --------------------------------------------------------------------------
    # Host Groups + Mappings
    # --------------------------------------------------------------------------

    # Zabbix Host Groups
    path( 'host-groups/',                            views.HostGroupListView.as_view(),              name='hostgroup_list' ),
    path( 'host-groups/add/',                        views.HostGroupEditView.as_view(),              name='hostgroup_add' ),
    path( 'host-groups/<int:pk>/',                   views.HostGroupView.as_view(),                  name='hostgroup' ),
    path( 'host-groups/<int:pk>/edit/',              views.HostGroupEditView.as_view(),              name='hostgroup_edit' ),
    path( 'host-groups/<int:pk>/delete/',            views.HostGroupDeleteView.as_view(),            name='hostgroup_delete' ),
    path( 'host-groups/<int:pk>/changelog/',         ObjectChangeLogView.as_view(),                  name='hostgroup_changelog', kwargs={'model': models.HostGroup},  ),

    # Zabbix Host Group Mappings    
    path( 'host-group-mappings/',                    views.HostGroupMappingListView.as_view(),       name='hostgroupmapping_list' ),
    path( 'host-group-mappings/add/',                views.HostGroupMappingEditView.as_view(),       name='hostgroupmapping_add' ),
    path( 'host-group-mappings/delete/',             views.HostGroupMappingBulkDeleteView.as_view(), name='hostgroupmapping_bulk_delete' ),        
    path( 'host-group-mappings/<int:pk>/',           views.HostGroupMappingView.as_view(),           name='hostgroupmapping' ),
    path( 'host-group-mappings/<int:pk>/edit/',      views.HostGroupMappingEditView.as_view(),       name='hostgroupmapping_edit' ),        
    path( 'host-group-mappings/<int:pk>/delete/',    views.HostGroupMappingDeleteView.as_view(),     name='hostgroupmapping_delete' ),
    path( 'host-group-mappings/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                  name='hostgroupmapping_changelog', kwargs={'model': models.HostGroupMapping},  ),
    
    path( 'host-group-mappings/<int:pk>/devices/',   views.HostGroupMappingDevicesView.as_view(),    name='hostgroupmapping_devices' ),
    path( 'host-group-mappings/<int:pk>/vms/',       views.HostGroupMappingVMsView.as_view(),        name='hostgroupmapping_vms' ),
    

    # --------------------------------------------------------------------------
    # Zabbix Configurations
    # --------------------------------------------------------------------------
    
    # Zabbix Device Configuration
    path( 'devices/zabbix-config/',                    views.DeviceZabbixConfigListView.as_view(),   name='devicezabbixconfig_list' ),
    path( 'devices/zabbix-config/add/',                views.DeviceZabbixConfigEditView.as_view(),   name='devicezabbixconfig_add' ),
    path( 'devices/zabbix-config/<int:pk>/',           views.DeviceZabbixConfigView.as_view(),       name='devicezabbixconfig' ),
    path( 'devices/zabbix-config/<int:pk>/edit/',      views.DeviceZabbixConfigEditView.as_view(),   name='devicezabbixconfig_edit' ),
    path( 'devices/zabbix-config/<int:pk>/delete/',    views.DeviceZabbixConfigDeleteView.as_view(), name='devicezabbixconfig_delete' ),
    path( 'devices/zabbix-config/<int:pk>/changelog/', ObjectChangeLogView.as_view(),                name='devicezabbixconfig_changelog', kwargs={'model': models.DeviceZabbixConfig} ),


    # Device Mappings
    path( 'device-mappings/', views.DeviceMappingsListView.as_view(), name='devicemappings_list' ),

    # VM Zabbix Configuration
    path( 'virtual-machines/zabbix-config/',                    views.VMZabbixConfigListView.as_view(),   name='vmzabbixconfig_list' ),
    path( 'virtual-machines/zabbix-config/add/',                views.VMZabbixConfigEditView.as_view(),   name='vmzabbixconfig_add' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/',           views.VMZabbixConfigView.as_view(),       name='vmzabbixconfig' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/edit/',      views.VMZabbixConfigEditView.as_view(),   name='vmzabbixconfig_edit' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/delete/',    views.VMZabbixConfigDeleteView.as_view(), name='vmzabbixconfig_delete' ),
    path( 'virtual-machines/zabbix-config/<int:pk>/changelog/', ObjectChangeLogView.as_view(),            name='vmzabbixconfig_changelog', kwargs={'model': models.VMZabbixConfig} ),
    

    # VM Mappings
    path( 'vm-mappings/', views.VMMappingsListView.as_view(), name='vmmappings_list' ),
    

    # Zabbix Configs (Devices and VMs combined)
    path( 'zabbix/configs/',                     views.ZabbixConfigListView.as_view(),   name='zabbixconfig_list' ),
    path( 'zabbix/configs/edit/<int:pk>/',       views.ZabbixConfigEditView.as_view(),   name='zabbixconfig_edit' ),
    path( 'zabbix/configs/delete/<int:pk>/',     views.ZabbixConfigDeleteView.as_view(), name='zabbixconfig_delete' ),
    path( 'zabbix/configs/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),          name='zabbixconfig_changelog', kwargs={'model': models.ZabbixConfig} ),



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
    path( 'zabbix/netbox-only-vms/',     views.NetBoxOnlyVMsView.as_view(),     name='netboxonlyvms' ),

    # Zabbix-only hosts (hosts only in Zabbix and not in NetBox)
    path( 'zabbix/zabbix-only-hosts/',   views.ZabbixOnlyHostsView.as_view(), name='zabbixonlyhosts' ),
    


    # --------------------------------------------------------------------------
    # Quick Add
    # --------------------------------------------------------------------------

    # Quick add Agent and SNMPv3 Device Configuration
    path( 'devices/zabbix-config/quick-add-agent/',  views.device_quick_add_agent,   name='device_quick_add_agent' ),
    path( 'devices/zabbix-config/quick-add-snmpv3/', views.device_quick_add_snmpv3,  name='device_quick_add_snmpv3' ),
        
    

    # --------------------------------------------------------------------------
    # Interfaces
    # --------------------------------------------------------------------------

    # Device Agent Interfaces
    path( 'interfaces/device-agents/',                     views.DeviceAgentInterfaceListView.as_view(),       name='deviceagentinterface_list' ),
    path( 'interfaces/device-agents/add/',                 views.DeviceAgentInterfaceEditView.as_view(),       name='deviceagentinterface_add' ),
    path( 'interfaces/device-agents/<int:pk>/',            views.DeviceAgentInterfaceView.as_view(),           name='deviceagentinterface' ),
    path( 'interfaces/device-agents/<int:pk>/edit/',       views.DeviceAgentInterfaceEditView.as_view(),       name='deviceagentinterface_edit' ),
    path( 'interfaces/device-agents/<int:pk>/delete/',     views.DeviceAgentInterfaceDeleteView.as_view(),     name='deviceagentinterface_delete' ),
    path( 'interfaces/device-agents/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),                      name='deviceagentinterface_changelog', kwargs={'model': models.DeviceAgentInterface} ),


    # Device SNMPv3 Interfaces
    path( 'interfaces/device-snmpv3/',                     views.DeviceSNMPv3InterfaceListView.as_view(),     name='devicesnmpv3interface_list' ),
    path( 'interfaces/device-snmpv3/add/',                 views.DeviceSNMPv3InterfaceEditView.as_view(),     name='devicesnmpv3interface_add' ),
    path( 'interfaces/device-snmpv3/<int:pk>/',            views.DeviceSNMPv3InterfaceView.as_view(),         name='devicesnmpv3interface' ),
    path( 'interfaces/device-snmpv3/<int:pk>/edit/',       views.DeviceSNMPv3InterfaceEditView.as_view(),     name='devicesnmpv3interface_edit' ),
    path( 'interfaces/device-snmpv3/<int:pk>/delete/',     views.DeviceSNMPv3InterfaceDeleteView.as_view(),   name='devicesnmpv3interface_delete' ),
    path( 'interfaces/device-snmpv3/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),                     name='devicesnmpv3interface_changelog', kwargs={'model': models.DeviceSNMPv3Interface} ),


    # VM Agent Interfaces
    path( 'interfaces/vm-agents/',                     views.VMAgentInterfaceListView.as_view(),       name='vmagentinterface_list' ),
    path( 'interfaces/vm-agents/add/',                 views.VMAgentInterfaceEditView.as_view(),       name='vmagentinterface_add' ),
    path( 'interfaces/vm-agents/<int:pk>/',            views.VMAgentInterfaceView.as_view(),           name='vmagentinterface' ),
    path( 'interfaces/vm-agents/<int:pk>/edit/',       views.VMAgentInterfaceEditView.as_view(),       name='vmagentinterface_edit' ),
    path( 'interfaces/vm-agents/<int:pk>/delete/',     views.VMAgentInterfaceDeleteView.as_view(),     name='vmagentinterface_delete' ),
    path( 'interfaces/vm-agents/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),                  name='vmagentinterface_changelog', kwargs={'model': models.VMAgentInterface} ),


    # VM SNMPv3 Interfaces
    path( 'interfaces/vm-snmpv3/',                     views.VMSNMPv3InterfaceListView.as_view(),       name='vmsnmpv3interface_list' ),
    path( 'interfaces/vm-snmpv3/add/',                 views.VMSNMPv3InterfaceEditView.as_view(),       name='vmsnmpv3interface_add' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/',            views.VMSNMPv3InterfaceView.as_view(),           name='vmsnmpv3interface' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/edit/',       views.VMSNMPv3InterfaceEditView.as_view(),       name='vmsnmpv3interface_edit' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/delete/',     views.VMSNMPv3InterfaceDeleteView.as_view(),     name='vmsnmpv3interface_delete' ),
    path( 'interfaces/vm-snmpv3/<int:pk>/changelog/',  ObjectChangeLogView.as_view(),                   name='vmsnmpv3interface_changelog', kwargs={'model': models.VMSNMPv3Interface} ),
    
)
