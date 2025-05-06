from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = (
        ( "Admin",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:config_list",   link_text="Config",    permissions=["netbox_zabbix.view_config"] ),
                PluginMenuItem( link="plugins:netbox_zabbix:template_list", link_text="Templates", permissions=["netbox_zabbix.view_config"] ),
            ),
        ),
        ( "Hosts",
            (
                PluginMenuItem( link="plugins:netbox_zabbix:host_list",         link_text="Synced Hosts", ),
                PluginMenuItem( link="plugins:netbox_zabbix:unsynced_hosts",    link_text="Unsynced Hosts" ),
                PluginMenuItem( link="plugins:netbox_zabbix:orphaned_nb_hosts", link_text="Orphaned (NetBox Only)", ),
                PluginMenuItem( link="plugins:netbox_zabbix:orphaned_zb_hosts", link_text="Orphaned (Zabbix Only)", ),
            )        
        ),
    ),
)