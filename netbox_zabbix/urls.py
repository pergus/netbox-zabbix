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
    

    # Base hosts is DeviceHosts and VMHosts combied.
    path( "hosts/",                     views.BaseHostsListView.as_view(),   name="base_hosts" ),
    path( "hosts/edit/<int:pk>/",       views.BaseHostEditView.as_view(),    name="basehost_edit" ),
    path( "hosts/delete/<int:pk>/",     views.BaseHostDeleteView.as_view(),  name="basehost_delete" ),
    path( "hosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),       name="basehost_changelog", kwargs={"model": models.BaseHost} ),
    
)
