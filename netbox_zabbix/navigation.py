from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = (
        ( 
            "Admin",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:config_list",
                    link_text="Configuration"
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:template_list",
                    link_text="Templates"
                ),
            ),
        ),
        ( "Devices",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:devicehost_list", link_text="Device Hosts", 
                               buttons=(  PluginMenuButton( "plugins:netbox_zabbix:devicehost_add", "Add", "mdi mdi-plus-thick" ), ),
                ),

                PluginMenuItem( link="plugins:netbox_zabbix:deviceagentinterface_list", link_text="Agent Interfaces", 
                               buttons=(  PluginMenuButton( "plugins:netbox_zabbix:deviceagentinterface_add", "Add", "mdi mdi-plus-thick" ), ),
                ),
                
                PluginMenuItem( link="plugins:netbox_zabbix:devicesnmpv3interface_list", link_text="SNMPv3 Interfaces", 
                               buttons=(  PluginMenuButton( "plugins:netbox_zabbix:devicesnmpv3interface_add", "Add", "mdi mdi-plus-thick" ), ),
                ),

            )        
        ),
        ( "Virtual Machines",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:vmhost_list", link_text="VM Hosts", 
                               buttons=(  PluginMenuButton( "plugins:netbox_zabbix:vmhost_add", "Add", "mdi mdi-plus-thick" ), ),),
            )        
        ),

        ( "Hosts", 
            ( 
                PluginMenuItem( link="plugins:netbox_zabbix:managed_hosts", link_text="Managed Hosts" ), 
                PluginMenuItem( link="plugins:netbox_zabbix:unmanaged_device_list", link_text="Importable Devices" ), 
                PluginMenuItem( link="plugins:netbox_zabbix:devices_exclusive_to_netbox", link_text="NetBox Exclusive Devices" ),
                PluginMenuItem( link="plugins:netbox_zabbix:virtual_machines_exclusive_to_netbox", link_text="NetBox Exclusive Virtual Machines" ),                 
                 
            )
        ),

        ( "Zabbix", 
         (
             PluginMenuItem( link="plugins:netbox_zabbix:zbx_only_hosts", link_text="Zabbix Only Hosts" ),
         )
        ),
    ),
)