from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton

# Add permissions

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = (
        ( "Admin",
            (
                PluginMenuItem( 
                    link_text="Configuration",                
                    link="plugins:netbox_zabbix:config_list",
                ),
                PluginMenuItem( 
                    link_text="Templates",                    
                    link="plugins:netbox_zabbix:template_list",
                ),
                PluginMenuItem( 
                    link_text="Host Groups",                    
                    link="plugins:netbox_zabbix:hostgroup_list",
                ),                
                PluginMenuItem( 
                    link_text="Host Group Mappings",                    
                    link="plugins:netbox_zabbix:hostgroupmapping_list",
                ),
                
            ),
        ),
        ( "Import",
         (
             PluginMenuItem( 
                 link_text="Importable Devices", 
                 link="plugins:netbox_zabbix:importabledevice_list",
             ),
             PluginMenuItem(
                 link="plugins:netbox_zabbix:importablevm_list",
                 link_text="Importable Virtual Machines",
             ),                
             
         )
        ),
        ( "Devices",
            (
                PluginMenuItem( 
                    link_text="Device Configurations",                    
                    link="plugins:netbox_zabbix:devicezabbixconfig_list",
                    buttons=( 
                        PluginMenuButton( "plugins:netbox_zabbix:devicezabbixconfig_add", "Add", "mdi mdi-plus-thick" ),
                        ),
                ),        
            )        
        ),
        ( "Device Components",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:deviceagentinterface_list",
                    link_text="Agent Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:deviceagentinterface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                
                PluginMenuItem( 
                    link_text="SNMPv3 Interfaces", 
                    link="plugins:netbox_zabbix:devicesnmpv3interface_list", 
                    buttons=( 
                        PluginMenuButton( "plugins:netbox_zabbix:devicesnmpv3interface_add", "Add", "mdi mdi-plus-thick" ), 
                        ),
                ),
            )
        ),
        ( "Virtual Machines",
            (
                PluginMenuItem(
                    link_text="VM Configurations",                    
                    link="plugins:netbox_zabbix:vmzabbixconfig_list",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:vmzabbixconfig_add", "Add", "mdi mdi-plus-thick"
                        ),
                    ),
                ),
            )       
        ),
        ( "Virtual Machine Components",
            (
                PluginMenuItem(
                    link="plugins:netbox_zabbix:vmagentinterface_list",
                    link_text="Agent Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:vmagentinterface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_zabbix:vmsnmpv3interface_list",
                    link_text="SNMPv3 Interfaces",
                    buttons=(
                        PluginMenuButton(
                            "plugins:netbox_zabbix:vmsnmpv3interface_add",
                            "Add",
                            "mdi mdi-plus-thick",
                        ),
                    ),
                ),
                
            )
        ),
        ( "Zabbix Configurations",
            (
                PluginMenuItem(
                    link_text="All Zabbix Configurations",
                    link="plugins:netbox_zabbix:zabbixconfig_list",
                ),
            ),
        ),
        ( "NetBox",
            (
                PluginMenuItem( 
                    link_text="NetBox Only Devices",
                    link="plugins:netbox_zabbix:netboxonlydevices",                      
                ),                
                PluginMenuItem( 
                    link_text="NetBox Only Virtual Machines",                     
                    link="plugins:netbox_zabbix:netboxonlyvms", 
                ),                
                
            )
        ),
        ( "Zabbix",
            (
                PluginMenuItem(
                    link_text="Zabbix Only Hosts",
                    link="plugins:netbox_zabbix:zabbixonlyhosts",
                ),
            ),
        ),        
    ),
)