from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = (
        ( "Admin",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:config_list",       link_text="Config",    permissions=["netbox_zabbix.view_config"] ),
                PluginMenuItem( link="plugins:netbox_zabbix:template_list",     link_text="Templates", permissions=["netbox_zabbix.view_config"] ),
            ),
        ),
        ( "Hosts",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:host_list",         link_text="Synced Hosts", ),
                PluginMenuItem( link="plugins:netbox_zabbix:unsynced_devices",  link_text="Unsynced Devices" ),
                PluginMenuItem( link="plugins:netbox_zabbix:unsynced_vms",      link_text="Unsynced VMs" ),                
                PluginMenuItem( link="plugins:netbox_zabbix:netbox_only_hosts", link_text="NetBox Only Hosts", ),
                PluginMenuItem( link="plugins:netbox_zabbix:zabbix_only_hosts", link_text="Zabbix Only Hosts", ),
            )        
        ),
    ),
)