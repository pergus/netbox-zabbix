from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_zabbix import models, views

app_name = 'netbox_zabbix' 

urlpatterns = (
    
    # Configuration
    path( "configs/",                    views.ConfigListView.as_view(),    name="config_list" ),
    path( "configs/add/",                views.ConfigEditView.as_view(),    name="config_add" ),
    path( "configs/<int:pk>/",           views.ConfigView.as_view(),        name="config" ),
    path( "configs/<int:pk>/edit/",      views.ConfigEditView.as_view(),    name="config_edit" ),
    path( "configs/<int:pk>/delete/",    views.ConfigDeleteView.as_view(),  name="config_delete" ),
    path( "configs/<int:pk>/changelog/", ObjectChangeLogView.as_view(),     name="config_changelog", kwargs={"model": models.Config},  ),

    # Check Zabbix Connection
    path("zabbix/check_connection",       views.ZabbixCheckConnectionView,    name="check_zabbix_connection"),
    
    
    # Templates
    path( "templates/",                   views.TemplateListView.as_view(),   name="template_list" ),
    path( "templates/add/",               views.TemplateEditView.as_view(),   name="template_add" ),
    path( "templates/<int:pk>/",          views.TemplateView.as_view(),       name="template" ),
    path( "templates/<int:pk>/edit/",     views.TemplateEditView.as_view(),   name="template_edit" ),
    path( "templates/<int:pk>/delete/",   views.TemplateDeleteView.as_view(), name="template_delete" ),
    path( "templates/<int:pk>/changelog", ObjectChangeLogView.as_view(),      name="template_changelog", kwargs={"model": models.Template} ),
    path( "templates/review-deletions/",  views.templates_review_deletions,   name="templates_review_deletions" ), 
    path( "templates/confirm-deletions/", views.templates_confirm_deletions,  name="templates_confirm_deletions" ),

    # Sync Zabbix Templates
    path( "zabbix/sync_templates",   views.sync_zabbix_templates,   name="sync_zabbix_templates" ),

    

    
    # DeviceHosts
    path( "devicehosts/",                     views.DeviceHostListView.as_view(),   name="devicehost_list" ),
    path( "devicehosts/add/",                 views.DeviceHostEditView.as_view(),   name="devicehost_add" ),
    path( "devicehosts/<int:pk>/",            views.DeviceHostView.as_view(),       name="devicehost" ),
    path( "devicehosts/<int:pk>/edit/",       views.DeviceHostEditView.as_view(),   name="devicehost_edit" ),
    path( "devicehosts/<int:pk>/delete/",     views.DeviceHostDeleteView.as_view(), name="devicehost_delete" ),
    path( "devicehosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),        name="devicehost_changelog", kwargs={"model": models.DeviceHost} ),
    

    # VMHosts
    path( "vmhosts/",                     views.VMHostListView.as_view(),       name="vmhost_list" ),
    path( "vmhosts/add/",                 views.VMHostEditView.as_view(),       name="vmhost_add" ),
    path( "vmhosts/<int:pk>/",            views.VMHostView.as_view(),           name="vmhost" ),
    path( "vmhosts/<int:pk>/edit/",       views.VMHostEditView.as_view(),       name="vmhost_edit" ),
    path( "vmhosts/<int:pk>/delete/",     views.VMHostDeleteView.as_view(),     name="vmhost_delete" ),
    path( "vmhosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),        name="vmhost_changelog", kwargs={"model": models.VMHost} ),
    

    # Managed Hosts - Hosts in NetBox with Zabbix config and Zabbix presence.
    path( "hosts/",                     views.ManagedHostsListView.as_view(),   name="managed_hosts" ),
    path( "hosts/edit/<int:pk>/",       views.ManagedHostEditView.as_view(),    name="managedhost_edit" ),
    path( "hosts/delete/<int:pk>/",     views.ManagedHostDeleteView.as_view(),  name="managedhost_delete" ),
    path( "hosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),          name="managedhost_changelog", kwargs={"model": models.ManagedHost} ),
    

    # Unmanaged Device Hosts - Devices in NetBox and that exist in Zabbix but lack Zabbix config in NetBox.
    path("unmanaged_device_list", views.UnmanagedDeviceListView.as_view(), name="unmanaged_device_list"),

    # Devices exclustive to NetBox, i.e. not present in Zabbix
    path("devices_exclusive_to_netbox", views.DevicesExclustiveToNetBoxView.as_view(), name="devices_exclusive_to_netbox"),

    # VMs exclustive to NetBox, i.e. not present in Zabbix
    path("virtual_machines_exclusive_to_netbox", views.VirtualMachinesExclustiveToNetBoxView.as_view(), name="virtual_machines_exclusive_to_netbox"),


    # Zabbix only hosts - Hosts that only exist in Zabbix
    path("zbx_only_hosts", views.ZBXOnlyHostsView.as_view(), name="zbx_only_hosts"),


    # Interfaces
    path( "deviceagentinterfaces/",                     views.DeviceAgentInterfaceListView.as_view(),       name="deviceagentinterface_list" ),
    path( "deviceagentinterfaces/add/",                 views.DeviceAgentInterfaceEditView.as_view(),       name="deviceagentinterface_add" ),
    path( "deviceagentinterfaces/<int:pk>/",            views.DeviceAgentInterfaceView.as_view(),           name="deviceagentinterface" ),
    path( "deviceagentinterfaces/<int:pk>/edit/",       views.DeviceAgentInterfaceEditView.as_view(),       name="deviceagentinterface_edit" ),
    path( "deviceagentinterfaces/<int:pk>/delete/",     views.DeviceAgentInterfaceDeleteView.as_view(),     name="deviceagentinterface_delete" ),
    path( "deviceagentinterfaces/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                      name="deviceagentinterface_changelog", kwargs={"model": models.DeviceAgentInterface} ),

    path( "devicesnmpv3interfaces/",                     views.DeviceSNMPv3InterfaceListView.as_view(),     name="devicesnmpv3interface_list" ),
    path( "devicesnmpv3interfaces/add/",                 views.DeviceSNMPv3InterfaceEditView.as_view(),     name="devicesnmpv3interface_add" ),
    path( "devicesnmpv3interfaces/<int:pk>/",            views.DeviceSNMPv3InterfaceView.as_view(),         name="devicesnmpv3interface" ),
    path( "devicesnmpv3interfaces/<int:pk>/edit/",       views.DeviceSNMPv3InterfaceEditView.as_view(),     name="devicesnmpv3interface_edit" ),
    path( "devicesnmpv3interfaces/<int:pk>/delete/",     views.DeviceSNMPv3InterfaceDeleteView.as_view(),   name="devicesnmpv3interface_delete" ),
    path( "devicesnmpv3interfaces/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                     name="devicesnmpv3interface_changelog", kwargs={"model": models.DeviceSNMPv3Interface} ),

)
