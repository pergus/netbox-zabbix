"""
NetBox Zabbix Plugin — Navigation Menu

This module defines the top-level navigation menu for the Zabbix plugin
in NetBox. Menu items are grouped logically under "Admin" and other
categories can be added as needed.

The menu uses NetBox's PluginMenu, PluginMenuItem, and PluginMenuButton
to integrate plugin functionality into the NetBox UI.
"""

# NetBox Plugin imports
from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton

# ------------------------------------------------------------------------------
# Plugin navigation menu
# ------------------------------------------------------------------------------

menu = PluginMenu(
    label = "Zabbix",
    icon_class = "mdi mdi-bell-check",
    groups = [
        ( "Admin",
            (
                PluginMenuItem( 
                    link_text="Settings", 
                    link="plugins:netbox_zabbix:setting_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_setting" ]
                ),
                PluginMenuItem( 
                    link_text="Templates", 
                    link="plugins:netbox_zabbix:template_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_template" ]
                ),
                PluginMenuItem( 
                    link_text="Proxies", 
                    link="plugins:netbox_zabbix:proxy_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_proxy" ]
                ),
                PluginMenuItem( 
                    link_text="Proxy Groups", 
                    link="plugins:netbox_zabbix:proxygroup_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_proxygroup" ]
                ), 
                PluginMenuItem( 
                    link_text="Host Groups", 
                    link="plugins:netbox_zabbix:hostgroup_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_hostgroup" ]
                ), 
            ),
        ),
        ( "Mappings",
            (
                PluginMenuItem( 
                    link_text="Tag Mappings", 
                    link="plugins:netbox_zabbix:tagmapping_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_tagmapping" ]
                ),
                PluginMenuItem( 
                    link_text="Inventory Mappings", 
                    link="plugins:netbox_zabbix:inventorymapping_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_inventorymapping" ]
                ),
                PluginMenuItem( 
                    link_text="Device Mappings", 
                    link="plugins:netbox_zabbix:devicemapping_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_devicemapping" ]
                ),
                PluginMenuItem( 
                    link_text="Virtual Machine Mappings",
                    link="plugins:netbox_zabbix:vmmapping_list",
                    auth_required=True,
                    permissions=[ "netbox_zabbix.view_vmmapping" ]
                ),
            ),
        ),
        ( "Hosts",
            (
                PluginMenuItem( 
                    link_text="Hosts", 
                    link="plugins:netbox_zabbix:hostconfig_list",
                    auth_required=True,
                    buttons=( 
                        PluginMenuButton( "plugins:netbox_zabbix:hostconfig_add", "Add", "mdi mdi-plus-thick" ),
                    ),
                ),
                PluginMenuItem( 
                    link_text="Agent Interfaces", 
                    link="plugins:netbox_zabbix:agentinterface_list",
                    auth_required=True,
                ),
                PluginMenuItem( 
                    link_text="SNMP Interfaces", 
                    link="plugins:netbox_zabbix:snmpinterface_list",
                    auth_required=True,
                ),
                PluginMenuItem( 
                    link_text="Maintenance", 
                    link="plugins:netbox_zabbix:maintenance_list",
                    auth_required=True,
                ),
                PluginMenuItem( 
                    link_text="Importable Hosts", 
                    link="plugins:netbox_zabbix:importablehosts_list",
                    auth_required=True,
                ),
                PluginMenuItem( 
                    link_text="NetBox Only Hosts", 
                    link="plugins:netbox_zabbix:netboxhosts_list",
                    auth_required=True,
                ),
                
            ),
        ),
        ( "Zabbix",
            (
                PluginMenuItem(
                    link_text="Zabbix Only Hosts",
                    link="plugins:netbox_zabbix:zabbixonlyhosts",
                    auth_required=True,
                ),
            ),
        ),
        ( "Event Logs",
             (
                 PluginMenuItem( 
                    link_text="Event Logs", 
                    link="plugins:netbox_zabbix:eventlog_list",
                    auth_required=True,
                ), 
             )
        ),
    ]
)