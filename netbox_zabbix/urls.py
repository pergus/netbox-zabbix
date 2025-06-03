from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_zabbix import models, views

app_name = 'netbox_zabbix' 


urlpatterns = (
    
    # Configuration
    path( "configs/",                    views.ConfigListView.as_view(),      name="config_list" ),
    path( "configs/add/",                views.ConfigEditView.as_view(),      name="config_add" ),
    path( "configs/<int:pk>/",           views.ConfigView.as_view(),          name="config" ),
    path( "configs/<int:pk>/edit/",      views.ConfigEditView.as_view(),      name="config_edit" ),
    path( "configs/<int:pk>/delete/",    views.ConfigDeleteView.as_view(),    name="config_delete" ),
    path( "configs/<int:pk>/changelog/", ObjectChangeLogView.as_view(),       name="config_changelog", kwargs={"model": models.Config},  ),


    # Check Zabbix Connection
    path("zabbix/check-connection",       views.ZabbixCheckConnectionView,    name="check_zabbix_connection"),
    
    
    # Zabbix Templates
    path( "templates/",                   views.TemplateListView.as_view(),   name="template_list" ),
    path( "templates/add/",               views.TemplateEditView.as_view(),   name="template_add" ),
    path( "templates/<int:pk>/",          views.TemplateView.as_view(),       name="template" ),
    path( "templates/<int:pk>/edit/",     views.TemplateEditView.as_view(),   name="template_edit" ),
    path( "templates/<int:pk>/delete/",   views.TemplateDeleteView.as_view(), name="template_delete" ),
    path( "templates/<int:pk>/changelog", ObjectChangeLogView.as_view(),      name="template_changelog", kwargs={"model": models.Template} ),
    path( "templates/review-deletions/",  views.templates_review_deletions,   name="templates_review_deletions" ), 
    path( "templates/confirm-deletions/", views.templates_confirm_deletions,  name="templates_confirm_deletions" ),


    # Sync Zabbix Templates
    path( "zabbix/sync_templates",        views.sync_zabbix_templates,        name="sync_zabbix_templates" ),


    # Zabbix Hostgroups
    path( 'hostgroups/',                    views.HostGroupListView.as_view(),   name='hostgroup_list' ),
    path( 'hostgroups/add/',                views.HostGroupEditView.as_view(),   name='hostgroup_add' ),
    path( 'hostgroups/<int:pk>/',           views.HostGroupView.as_view(),        name='hostgroup' ),
    path( 'hostgroups/<int:pk>/edit/',      views.HostGroupEditView.as_view(),   name='hostgroup_edit' ),
    path( 'hostgroups/<int:pk>/delete/',    views.HostGroupDeleteView.as_view(), name='hostgroup_delete' ),
    path( "hostgroups/<int:pk>/changelog/", ObjectChangeLogView.as_view(),       name="hostgroup_changelog", kwargs={"model": models.HostGroup},  ),
    
    path( 'hostgroup-mappings/',                    views.HostGroupMappingListView.as_view(),   name='hostgroupmapping_list' ),
    path( 'hostgroup-mappings/add/',                views.HostGroupMappingEditView.as_view(),   name='hostgroupmapping_add' ),
    path( 'hostgroup-mappings/<int:pk>/',           views.HostGroupMappingView.as_view(),       name='hostgroupmapping' ),
    path( 'hostgroup-mappings/<int:pk>/edit/',      views.HostGroupMappingEditView.as_view(),   name='hostgroupmapping_edit' ),
    path( 'hostgroup-mappings/<int:pk>/delete/',    views.HostGroupMappingDeleteView.as_view(), name='hostgroupmapping_delete' ),
    path( "hostgroup-mappings/<int:pk>/changelog/", ObjectChangeLogView.as_view(),              name="hostgroupmapping_changelog", kwargs={"model": models.HostGroupMapping},  ),
    
    # Sync Zabbix Hostgroups
    path( "zabbix/sync_hostgroup",        views.sync_zabbix_hostgroups,        name="sync_zabbix_hostgroups" ),
    

    # Zabbix Device Configuration
    path( "devices/zabbix-config/",                    views.DeviceZabbixConfigListView.as_view(),   name="devicezabbixconfig_list" ),
    path( "devices/zabbix-config/add/",                views.DeviceZabbixConfigEditView.as_view(),   name="devicezabbixconfig_add" ),
    path( "devices/zabbix-config/<int:pk>/",           views.DeviceZabbixConfigView.as_view(),       name="devicezabbixconfig" ),
    path( "devices/zabbix-config/<int:pk>/edit/",      views.DeviceZabbixConfigEditView.as_view(),   name="devicezabbixconfig_edit" ),
    path( "devices/zabbix-config/<int:pk>/delete/",    views.DeviceZabbixConfigDeleteView.as_view(), name="devicezabbixconfig_delete" ),
    path( "devices/zabbix-config/<int:pk>/changelog/", ObjectChangeLogView.as_view(),                name="devicezabbixconfig_changelog", kwargs={"model": models.DeviceZabbixConfig} ),
        

    # VM Zabbix Configuration
    path( "virtual-machines/zabbix-config/",                    views.VMZabbixConfigListView.as_view(),   name="vmzabbixconfig_list" ),
    path( "virtual-machines/zabbix-config/add/",                views.VMZabbixConfigEditView.as_view(),   name="vmzabbixconfig_add" ),
    path( "virtual-machines/zabbix-config/<int:pk>/",           views.VMZabbixConfigView.as_view(),       name="vmzabbixconfig" ),
    path( "virtual-machines/zabbix-config/<int:pk>/edit/",      views.VMZabbixConfigEditView.as_view(),   name="vmzabbixconfig_edit" ),
    path( "virtual-machines/zabbix-config/<int:pk>/delete/",    views.VMZabbixConfigDeleteView.as_view(), name="vmzabbixconfig_delete" ),
    path( "virtual-machines/zabbix-config/<int:pk>/changelog/", ObjectChangeLogView.as_view(),            name="vmzabbixconfig_changelog", kwargs={"model": models.VMZabbixConfig} ),
    

    # Zabbix Configs (Devices or VMs)
    path( "zabbix/configs/",                     views.ZabbixConfigListView.as_view(),   name="zabbixconfig_list" ),
    path( "zabbix/configs/edit/<int:pk>/",       views.ZabbixConfigEditView.as_view(),   name="zabbixconfig_edit" ),
    path( "zabbix/configs/delete/<int:pk>/",     views.ZabbixConfigDeleteView.as_view(), name="zabbixconfig_delete" ),
    path( "zabbix/configs/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),          name="zabbixconfig_changelog", kwargs={"model": models.ZabbixConfig} ),
        
    
    # Importable Zabbix Hosts (Devices/VMs in Zabbix but not configured in NetBox)
    path( "zabbix/importable-devices/", views.ImportableDeviceListView.as_view(), name="importabledevice_list" ),
    path( "zabbix/importable-vms/",     views.ImportableVMListView.as_view(),     name="importablevm_list" ),
    

    # NetBox-only assets (not present in Zabbix)
    path( "zabbix/netbox-only-devices/", views.NetBoxOnlyDevicesView.as_view(), name="netboxonlydevices" ),

    # Quick add Agent and SNMPv3 Device Configuration
    path("devices/zabbix-config/quick-add-agent/",  views.device_quick_add_agent,   name="device_quick_add_agent"),
    path("devices/zabbix-config/quick-add-snmpv3/", views.device_quick_add_snmpv3,  name="device_quick_add_snmpv3"),
    
    
    path( "zabbix/netbox-only-vms/",     views.NetBoxOnlyVMsView.as_view(),     name="netboxonlyvms" ),

    # Zabbix-only hosts (not in NetBox)
    path( "zabbix/zabbix-only-hosts/",   views.ZabbixOnlyHostsView.as_view(), name="zabbixonlyhosts" ),
    

    # Device Agent Interfaces
    path( "interfaces/device-agents/",                     views.DeviceAgentInterfaceListView.as_view(),       name="deviceagentinterface_list" ),
    path( "interfaces/device-agents/add/",                 views.DeviceAgentInterfaceEditView.as_view(),       name="deviceagentinterface_add" ),
    path( "interfaces/device-agents/<int:pk>/",            views.DeviceAgentInterfaceView.as_view(),           name="deviceagentinterface" ),
    path( "interfaces/device-agents/<int:pk>/edit/",       views.DeviceAgentInterfaceEditView.as_view(),       name="deviceagentinterface_edit" ),
    path( "interfaces/device-agents/<int:pk>/delete/",     views.DeviceAgentInterfaceDeleteView.as_view(),     name="deviceagentinterface_delete" ),
    path( "interfaces/device-agents/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                      name="deviceagentinterface_changelog", kwargs={"model": models.DeviceAgentInterface} ),


    # Device SNMPv3 Interfaces
    path( "interfaces/device-snmpv3/",                     views.DeviceSNMPv3InterfaceListView.as_view(),     name="devicesnmpv3interface_list" ),
    path( "interfaces/device-snmpv3/add/",                 views.DeviceSNMPv3InterfaceEditView.as_view(),     name="devicesnmpv3interface_add" ),
    path( "interfaces/device-snmpv3/<int:pk>/",            views.DeviceSNMPv3InterfaceView.as_view(),         name="devicesnmpv3interface" ),
    path( "interfaces/device-snmpv3/<int:pk>/edit/",       views.DeviceSNMPv3InterfaceEditView.as_view(),     name="devicesnmpv3interface_edit" ),
    path( "interfaces/device-snmpv3/<int:pk>/delete/",     views.DeviceSNMPv3InterfaceDeleteView.as_view(),   name="devicesnmpv3interface_delete" ),
    path( "interfaces/device-snmpv3/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                     name="devicesnmpv3interface_changelog", kwargs={"model": models.DeviceSNMPv3Interface} ),


    # VM Agent Interfaces
    path( "interfaces/vm-agents/",                     views.VMAgentInterfaceListView.as_view(),       name="vmagentinterface_list" ),
    path( "interfaces/vm-agents/add/",                 views.VMAgentInterfaceEditView.as_view(),       name="vmagentinterface_add" ),
    path( "interfaces/vm-agents/<int:pk>/",            views.VMAgentInterfaceView.as_view(),           name="vmagentinterface" ),
    path( "interfaces/vm-agents/<int:pk>/edit/",       views.VMAgentInterfaceEditView.as_view(),       name="vmagentinterface_edit" ),
    path( "interfaces/vm-agents/<int:pk>/delete/",     views.VMAgentInterfaceDeleteView.as_view(),     name="vmagentinterface_delete" ),
    path( "interfaces/vm-agents/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                  name="vmagentinterface_changelog", kwargs={"model": models.VMAgentInterface} ),

    
    # VM SNMPv3 Interfaces
    path( "interfaces/vm-snmpv3/",                     views.VMSNMPv3InterfaceListView.as_view(),       name="vmsnmpv3interface_list" ),
    path( "interfaces/vm-snmpv3/add/",                 views.VMSNMPv3InterfaceEditView.as_view(),       name="vmsnmpv3interface_add" ),
    path( "interfaces/vm-snmpv3/<int:pk>/",            views.VMSNMPv3InterfaceView.as_view(),           name="vmsnmpv3interface" ),
    path( "interfaces/vm-snmpv3/<int:pk>/edit/",       views.VMSNMPv3InterfaceEditView.as_view(),       name="vmsnmpv3interface_edit" ),
    path( "interfaces/vm-snmpv3/<int:pk>/delete/",     views.VMSNMPv3InterfaceDeleteView.as_view(),     name="vmsnmpv3interface_delete" ),
    path( "interfaces/vm-snmpv3/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                   name="vmsnmpv3interface_changelog", kwargs={"model": models.VMSNMPv3Interface} ),
    
)
