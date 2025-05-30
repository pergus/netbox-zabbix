from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_zabbix import models, views

app_name = 'netbox_zabbix'

urlpatterns = (

    # Settings
    path("settings/",                     views.SettingListView.as_view(),    name="setting_list"),
    path("settings/add/",                 views.SettingEditView.as_view(),    name="setting_add"),
    path("settings/<int:pk>/",            views.SettingView.as_view(),        name="setting"),
    path("settings/<int:pk>/edit/",       views.SettingEditView.as_view(),    name="setting_edit"),
    path("settings/<int:pk>/delete/",     views.SettingDeleteView.as_view(),  name="setting_delete"),
    path("settings/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),      name="setting_changelog", kwargs={"model": models.Setting}),

    # Templates
    path("templates/",                    views.TemplateListView.as_view(),   name="template_list"),
    path("templates/add/",                views.TemplateEditView.as_view(),   name="template_add"),
    path("templates/<int:pk>/",           views.TemplateView.as_view(),       name="template"),
    path("templates/<int:pk>/edit/",      views.TemplateEditView.as_view(),   name="template_edit"),
    path("templates/<int:pk>/delete/",    views.TemplateDeleteView.as_view(), name="template_delete"),
    path("templates/<int:pk>/changelog",  ObjectChangeLogView.as_view(),      name="template_changelog", kwargs={"model": models.Template}),
    path("templates/review-deletions/",   views.templates_review_deletions,   name="templates_review_deletions"),
    path("templates/confirm-deletions/",  views.templates_confirm_deletions,  name="templates_confirm_deletions"),

    # Sync Zabbix Templates
    path("zabbix/sync_templates",         views.sync_zabbix_templates,        name="sync_zabbix_templates"),

    # Check Zabbix Connection
    path("zabbix/check_connection",       views.ZabbixCheckConnectionView,    name="check_zabbix_connection"),

    # Device Zabbix Configuration
    path("devices/zabbix_config/",                    views.DeviceZabbixConfigListView.as_view(),   name="device_zabbix_config_list"),
    path("devices/zabbix_config/add/",                views.DeviceZabbixConfigEditView.as_view(),   name="device_zabbix_config_add"),
    path("devices/zabbix_config/<int:pk>/",           views.DeviceZabbixConfigView.as_view(),       name="device_zabbix_config"),
    path("devices/zabbix_config/<int:pk>/edit/",      views.DeviceZabbixConfigEditView.as_view(),   name="device_zabbix_config_edit"),
    path("devices/zabbix_config/<int:pk>/delete/",    views.DeviceZabbixConfigDeleteView.as_view(), name="device_zabbix_config_delete"),
    path("devices/zabbix_config/<int:pk>/changelog/", ObjectChangeLogView.as_view(),                name="device_zabbix_config_changelog", kwargs={"model": models.DeviceZabbixConfig}),

    # VM Zabbix Configuration
    path("virtual-machines/zabbix_config/",                    views.VMZabbixConfigListView.as_view(),   name="vm_zabbix_config_list"),
    path("virtual-machines/zabbix_config/add/",                views.VMZabbixConfigEditView.as_view(),   name="vm_zabbix_config_add"),
    path("virtual-machines/zabbix_config/<int:pk>/",           views.VMZabbixConfigView.as_view(),       name="vm_zabbix_config"),
    path("virtual-machines/zabbix_config/<int:pk>/edit/",      views.VMZabbixConfigEditView.as_view(),   name="vm_zabbix_config_edit"),
    path("virtual-machines/zabbix_config/<int:pk>/delete/",    views.VMZabbixConfigDeleteView.as_view(), name="vm_zabbix_config_delete"),
    path("virtual-machines/zabbix_config/<int:pk>/changelog/", ObjectChangeLogView.as_view(),            name="vm_zabbix_config_changelog", kwargs={"model": models.VMZabbixConfig}),

    # Configured Zabbix Hosts (Devices or VMs with config in NetBox & Zabbix)
    path("zabbix/configured_hosts/",                     views.ConfiguredZabbixHostListView.as_view(),   name="configuredzabbixhost_list"),
    path("zabbix/configured_hosts/edit/<int:pk>/",       views.ConfiguredZabbixHostEditView.as_view(),   name="configuredzabbixhost_edit"),
    path("zabbix/configured_hosts/delete/<int:pk>/",     views.ConfiguredZabbixHostDeleteView.as_view(), name="configuredzabbixhost_delete"),
    path("zabbix/configured_hosts/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                  name="configuredzabbixhost_changelog", kwargs={"model": models.ConfiguredZabbixHost}),

    # Importable Zabbix Hosts (Devices/VMs in Zabbix but not configured in NetBox)
    path("zabbix/importable_devices/", views.ImportableDeviceListView.as_view(), name="importable_device_list"),
    path("zabbix/importable_vms/",     views.ImportableVMListView.as_view(),     name="importable_vm_list"),

    # NetBox-only assets (not present in Zabbix)
    path("zabbix/netbox_only_devices/", views.DevicesExclusiveToNetBoxView.as_view(), name="devices_exclusive_to_netbox"),
    path("zabbix/netbox_only_vms/",     views.VirtualMachinesExclusiveToNetBoxView.as_view(), name="virtual_machines_exclusive_to_netbox"),

    # Zabbix-only hosts (not in NetBox)
    path("zabbix/zabbix_only_hosts/",   views.ZabbixOnlyHostsView.as_view(), name="zabbix_only_hosts"),

    # Device Agent Interfaces
    path("interfaces/device_agents/",                     views.DeviceAgentInterfaceListView.as_view(),       name="deviceagentinterface_list"),
    path("interfaces/device_agents/add/",                 views.DeviceAgentInterfaceEditView.as_view(),       name="deviceagentinterface_add"),
    path("interfaces/device_agents/<int:pk>/",            views.DeviceAgentInterfaceView.as_view(),           name="deviceagentinterface"),
    path("interfaces/device_agents/<int:pk>/edit/",       views.DeviceAgentInterfaceEditView.as_view(),       name="deviceagentinterface_edit"),
    path("interfaces/device_agents/<int:pk>/delete/",     views.DeviceAgentInterfaceDeleteView.as_view(),     name="deviceagentinterface_delete"),
    path("interfaces/device_agents/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                      name="deviceagentinterface_changelog", kwargs={"model": models.DeviceAgentInterface}),

    # Device SNMPv3 Interfaces
    path("interfaces/device_snmpv3/",                     views.DeviceSNMPv3InterfaceListView.as_view(),       name="devicesnmpv3interface_list"),
    path("interfaces/device_snmpv3/add/",                 views.DeviceSNMPv3InterfaceEditView.as_view(),       name="devicesnmpv3interface_add"),
    path("interfaces/device_snmpv3/<int:pk>/",            views.DeviceSNMPv3InterfaceView.as_view(),           name="devicesnmpv3interface"),
    path("interfaces/device_snmpv3/<int:pk>/edit/",       views.DeviceSNMPv3InterfaceEditView.as_view(),       name="devicesnmpv3interface_edit"),
    path("interfaces/device_snmpv3/<int:pk>/delete/",     views.DeviceSNMPv3InterfaceDeleteView.as_view(),     name="devicesnmpv3interface_delete"),
    path("interfaces/device_snmpv3/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                       name="devicesnmpv3interface_changelog", kwargs={"model": models.DeviceSNMPv3Interface}),

    # VM Agent Interfaces
    path("interfaces/vm_agents/",                     views.VMAgentInterfaceListView.as_view(),       name="vmagentinterface_list"),
    path("interfaces/vm_agents/add/",                 views.VMAgentInterfaceEditView.as_view(),       name="vmagentinterface_add"),
    path("interfaces/vm_agents/<int:pk>/",            views.VMAgentInterfaceView.as_view(),           name="vmagentinterface"),
    path("interfaces/vm_agents/<int:pk>/edit/",       views.VMAgentInterfaceEditView.as_view(),       name="vmagentinterface_edit"),
    path("interfaces/vm_agents/<int:pk>/delete/",     views.VMAgentInterfaceDeleteView.as_view(),     name="vmagentinterface_delete"),
    path("interfaces/vm_agents/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                  name="vmagentinterface_changelog", kwargs={"model": models.VMAgentInterface}),

    # VM SNMPv3 Interfaces
    path("interfaces/vm_snmpv3/",                     views.VMSNMPv3InterfaceListView.as_view(),       name="vmsnmpv3interface_list"),
    path("interfaces/vm_snmpv3/add/",                 views.VMSNMPv3InterfaceEditView.as_view(),       name="vmsnmpv3interface_add"),
    path("interfaces/vm_snmpv3/<int:pk>/",            views.VMSNMPv3InterfaceView.as_view(),           name="vmsnmpv3interface"),
    path("interfaces/vm_snmpv3/<int:pk>/edit/",       views.VMSNMPv3InterfaceEditView.as_view(),       name="vmsnmpv3interface_edit"),
    path("interfaces/vm_snmpv3/<int:pk>/delete/",     views.VMSNMPv3InterfaceDeleteView.as_view(),     name="vmsnmpv3interface_delete"),
    path("interfaces/vm_snmpv3/<int:pk>/changelog/",  ObjectChangeLogView.as_view(),                   name="vmsnmpv3interface_changelog", kwargs={"model": models.VMSNMPv3Interface}),
)
