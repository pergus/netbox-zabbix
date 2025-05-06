from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from . import models, views

#app_name = "netbox_zabbix"

urlpatterns = (
    # Configurations
    path("zbxconfigs/",                    views.ZBXConfigListView.as_view(),   name="zbxconfig_list"),
    path("zbxconfigs/add/",                views.ZBXConfigEditView.as_view(),   name="zbxconfig_add"),
    path("zbxconfigs/<int:pk>/",           views.ZBXConfigView.as_view(),       name="zbxconfig"),
    path("zbxconfigs/<int:pk>/edit/",      views.ZBXConfigEditView.as_view(),   name="zbxconfig_edit"),
    path("zbxconfigs/<int:pk>/delete/",    views.ZBXConfigDeleteView.as_view(), name="zbxconfig_delete"),
    path("zbxconfigs/<int:pk>/changelog/", ObjectChangeLogView.as_view(),       name="zbxconfig_changelog", kwargs={"model": models.ZBXConfig}, ),
    
    # Check Zabbix Connection
    path("zbxconfigs/check_connection", views.ZBXConfigCheckConnectionView, name="zbx_check_connection"),

    # Templates
    path("zbxtemplates/",                   views.ZBXTemplateListView.as_view(),   name="zbxtemplate_list"),
    path("zbxtemplates/add/",               views.ZBXTemplateEditView.as_view(),   name="zbxtemplate_add"),
    path("zbxtemplates/<int:pk>/",          views.ZBXTemplateView.as_view(),       name="zbxtemplate"),
    path("zbxtemplates/<int:pk>/edit/",     views.ZBXTemplateEditView.as_view(),   name="zbxtemplate_edit"),
    path("zbxtemplates/<int:pk>/delete/",   views.ZBXTemplateDeleteView.as_view(), name="zbxtemplate_delete"),
    path("zbxtemplates/<int:pk>/changelog", ObjectChangeLogView.as_view(),         name="zbxtemplate_changelog", kwargs={"model": models.ZBXTemplate}, ),
    
    path("zbxtemplates/review-deletions/",  views.zbx_templates_review_deletions, name="zbx_templates_review_deletions"), 
    path("zbxtemplates/confirm-deletions/", views.zbx_templates_confirm_deletions, name="zbx_templates_confirm_deletions"),

    path("zbxtemplates/sync/", views.zbx_templates_sync, name="zbx_templates_sync"),
    

    # VMs
    path("zbxvms/",                    views.ZBXVMListView.as_view(),   name="zbxvm_list"),
    path("zbxvms/add/",                views.ZBXVMEditView.as_view(),   name="zbxvm_add"),
    path("zbxvms/<int:pk>/",           views.ZBXVMView.as_view(),       name="zbxvm"),
    path("zbxvms/<int:pk>/edit/",      views.ZBXVMEditView.as_view(),   name="zbxvm_edit"),
    path("zbxvms/<int:pk>/delete/",    views.ZBXVMDeleteView.as_view(), name="zbxvm_delete"),
    path("zbxvms/<int:pk>/changelog/", ObjectChangeLogView.as_view(),   name="zbxvm_changelog", kwargs={"model": models.ZBXVM}, ),
    
    # Sync all VMs (ZB2NB)
    path("zbxvms/sync/", views.z_sync_hosts_zb2nb, name="zbx_hosts_sync"),

    # Sync a single VM (ZB2NB)
    path("zbxvms/sync_host/<int:vm_id>/", views.z_sync_host_zbx2nb, name="zbx_host_sync"),
    

    # Zabbix problems
    path('zabbix/host/<str:name>/problems/', views.zabbix_host_problems, name='zabbix_host_problems'),


    # Combined
    path("zbxhosts/",                     views.ZBXHostListView.as_view(),         name="zbxhost_list"),
    path("zbxhosts/add/",                 views.ZBXHostEditView.as_view(),         name="zbxhost_add"),
    path("zbxhosts/<int:pk>/",            views.ZBXHostView.as_view(),             name="zbxhost"),
    path("zbxhosts/<int:pk>/edit/",       views.ZBXHostEditView.as_view(),         name="zbxhost_edit"),
    path("zbxhosts/<int:pk>/interfaces/", views.ZBXHostInterfacesView.as_view(),   name="zbxhost_interfaces"),
    path("zbxhosts/<int:pk>/ziltoid/",    views.ZBXHostInterfacesView.as_view(),   name="zbxhost_ziltoid"),
    path("zbxhosts/<int:pk>/delete/",     views.ZBXHostDeleteView.as_view(),       name="zbxhost_delete"),
    path("zbxhosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),           name="zbxhost_changelog", kwargs={"model": models.ZBXHost}, ),

    # Hosts without Zabbix configuration
    path("zabbix/unconfigured_hosts", views.unconfigured_hosts, name="unconfigured_hosts"),

    # Interfaces
    path("zbxinterfaces/",                    views.ZBXInterfaceListView.as_view(),       name="zbxinterface_list"),
    path("zbxinterfaces/add/",                views.ZBXInterfaceEditView.as_view(),       name="zbxinterface_add"),
    path("zbxinterfaces/<int:pk>/",           views.ZBXInterfaceView.as_view(),           name="zbxinterface"),
    path("zbxinterfaces/<int:pk>/edit/",      views.ZBXInterfaceEditView.as_view(),       name="zbxinterface_edit"),
    path("zbxinterfaces/<int:pk>/delete/",    views.ZBXInterfaceDeleteView.as_view(),     name="zbxinterface_delete"),
    path("zbxinterfaces/delete/",             views.ZBXInterfaceBulkDeleteView.as_view(), name="zbxinterface_bulk_delete"),
    path("zbxinterfaces/<int:pk>/changelog/", ObjectChangeLogView.as_view(),              name="zbxinterface_changelog", kwargs={"model": models.ZBXInterface}, ),


    # Zabbix Only Hostnames
    path('zabbix-only-hostnames/', views.ZabbixOnlyHostnamesView.as_view(), name='zabbix_only_hostnames'),
    

    # HTMX SNMP fields
    path('interface-snmp-form-tst/', views.interface_snmp_form_tst, name='interface-snmp-form-tst'),
    
)
