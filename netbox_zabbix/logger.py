"""
NetBox Zabbix Plugin — Logger

Provides a module-level logger for the NetBox Zabbix plugin.
This logger should be used consistently across all plugin modules
to centralize logging and control log level/output via Django's logging settings.
"""

# Standard library imports
import logging

# Create a logger instance specific to the NetBox Zabbix plugin
logger = logging.getLogger( 'netbox.plugins.netbox_zabbix' )
