menu = PluginMenu(
    label="Zabbix",
    icon_class="mdi mdi-bell-check",
    groups=(
        (
            "Admin",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:settings_list",
                    link_text="Settings",
                    permissions=["netbox_zabbix.view_config"],
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:template_list",
                    link_text="Templates",
                    permissions=["netbox_zabbix.view_template"],
                ),
            ),
        ),
        (
            "Devices",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:device_config_list",
                    link_text="Device Configurations",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:device_config_add", "Add", "mdi mdi-plus-thick"
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:device_agentinterface_list",
                    link_text="Agent Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:device_agentinterface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:device_snmpv3interface_list",
                    link_text="SNMPv3 Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:device_snmpv3interface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:importable_device_list",
                    link_text="Importable Devices",
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:devices_exclusive_to_netbox",
                    link_text="NetBox Exclusive Devices",
                ),
            ),
        ),
        (
            "Virtual Machines",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:vm_config_list",
                    link_text="VM Configurations",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:vm_config_add", "Add", "mdi mdi-plus-thick"
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:vm_agentinterface_list",
                    link_text="Agent Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:vm_agentinterface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:vm_snmpv3interface_list",
                    link_text="SNMPv3 Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:vm_snmpv3interface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:importable_vm_list",
                    link_text="Importable Virtual Machines",
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:virtual_machines_exclusive_to_netbox",
                    link_text="NetBox Exclusive Virtual Machines",
                ),
            ),
        ),
        (
            "Configured Zabbix Hosts",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:configured_hosts_list",
                    link_text="All Configured Hosts",
                ),
            ),
        ),
        (
            "Zabbix",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:zbx_only_hosts",
                    link_text="Zabbix Only Hosts",
                ),
            ),
        ),
    ),
)
