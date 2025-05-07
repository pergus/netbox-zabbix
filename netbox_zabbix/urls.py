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
    path( "configs/check_connection",    views.ConfigCheckConnectionView,   name="config_check_connection" ),
        

    # Templates
    path( "templates/",                   views.TemplateListView.as_view(),   name="template_list" ),
    path( "templates/add/",               views.TemplateEditView.as_view(),   name="template_add" ),
    path( "templates/<int:pk>/",          views.TemplateView.as_view(),       name="template" ),
    path( "templates/<int:pk>/edit/",     views.TemplateEditView.as_view(),   name="template_edit"),
    path( "templates/<int:pk>/delete/",   views.TemplateDeleteView.as_view(), name="template_delete"),
    path( "templates/<int:pk>/changelog", ObjectChangeLogView.as_view(),      name="template_changelog", kwargs={"model": models.Template},  ),
    path( "templates/review-deletions/",  views.templates_review_deletions,   name="templates_review_deletions" ), 
    path( "templates/confirm-deletions/", views.templates_confirm_deletions,  name="templates_confirm_deletions"),

    # Sync Zabbix Templates
    path( "zabbix/sync_templates",   views.sync_zabbix_templates,   name="sync_zabbix_templates" ),

    # Hosts
    path( "hosts/",                     views.HostListView.as_view(),         name="host_list" ),
    path( "hosts/add/",                 views.HostEditView.as_view(),         name="host_add" ),
    path( "hosts/<int:pk>/",            views.HostView.as_view(),             name="host" ),
    path( "hosts/<int:pk>/edit/",       views.HostEditView.as_view(),         name="host_edit" ),
    path( "hosts/<int:pk>/delete/",     views.HostDeleteView.as_view(),       name="host_delete" ),
    path( "hosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),        name="host_changelog", kwargs={"model": models.Host},  ),


    # Important: If the URL paths below start with a "hosts/" prefix, 
    # NetBox will always highlight the "Synced Hosts" menu item due to URL prefix matching.
    # As a workaround, we avoid the "hosts/" prefix to ensure correct menu highlighting.
    
    # Devices in NetBox but are not yet synchronized with Zabbix
    path("unsynced_devices/",    views.UnsyncedDeviceListView.as_view(),    name="unsynced_devices"),
    
    # Virtual machines in NetBox but are not yet synchronized with Zabbix
    path("unsynced_vms/",        views.UnsyncedVMListView.as_view(),        name="unsynced_vms"),
    
    # Hosts that exist in NetBox but not in Zabbix (NetBox-only)
    path("netbox_only_hosts/", views.NetBoxOnlyHostnameListView.as_view(),  name="netbox_only_hosts"),
    
    # Hosts that exist in Zabbix but not in NetBox (Zabbix-only)
    path("zabbix_only_hosts/", views.ZabbixOnlyHostnameListView.as_view(),  name="zabbix_only_hosts"),

    # Interfaces

    path( "interfaces/add_agent",   views.agent_interface_add,   name="agent_interface_add" ),
    path( "interfaces/add_snmpv3",  views.snmpv3_interface_add,  name="snmpv3_interface_add" ),
    path( "interfaces/add_snmpv1",  views.snmpv1_interface_add,  name="snmpv1_interface_add" ),
    path( "interfaces/add_snmpv2c", views.snmpv2c_interface_add, name="snmpv2c_interface_add" ),
)
