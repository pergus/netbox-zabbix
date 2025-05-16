from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = (
        ( "Admin",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:config_list", link_text="Config",    permissions=["netbox_zabbix.view_config"] ),
                PluginMenuItem( link="plugins:netbox_zabbix:template_list", link_text="Templates", permissions=["netbox_zabbix.view_config"] ),
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
                PluginMenuItem( link="plugins:netbox_zabbix:unmanaged_device_list", link_text="Unmanged Devices" ), 
                PluginMenuItem( link="plugins:netbox_zabbix:nb_only_hosts", link_text="NetBox-Only Hosts" ), 
                PluginMenuItem( link="plugins:netbox_zabbix:zbx_only_hosts", link_text="Zabbix-Only Hosts" ), 
            )
        ),
    ),
)