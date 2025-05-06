from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = (
        ( "Zabbix",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:zbxconfig_list", link_text="Config", ),
                PluginMenuItem( link="plugins:netbox_zabbix:zbxtemplate_list", link_text="Templates", ),
            ),
        ),
        (
            "Hosts",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:zbxhost_list", link_text="Hosts", ),
                PluginMenuItem( link="plugins:netbox_zabbix:unconfigured_hosts", link_text="Unconfigured Hosts", ),
                PluginMenuItem( link="plugins:netbox_zabbix:zbxvm_list", link_text="VMs", ),
                PluginMenuItem( link="plugins:netbox_zabbix:zabbix_only_hostnames", link_text="Zabbix Only Hosts", ),                             
            )

        ),
        (
            "Interfaces",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:zbxinterface_list", link_text="Zabbix Interfaces", ),                                
            )
        
        ),
        
    ),
)