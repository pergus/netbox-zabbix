"""Top-level package for NetBox Zabbix Plugin."""

__email__ = "john.doe@netbox.com"


from netbox.plugins import PluginConfig

class ZBXConfigConfig(PluginConfig):
    name = "netbox_zabbix"
    verbose_name = "NetBox Zabbix Plugin"
    description = "NetBox plugin for Zabbix."
    author  = "John Doe"
    version = "0.1.0"
    base_url = "netbox_zabbix"
    
    # Do I need this?
    static_root = 'netbox_zabbix/static'

    def ready(self):
        super().ready()
        # Import and register signals
        from .signals import signals

        # Register api
        from .api import urls as api_urls        
        api_urls = api_urls
        

config = ZBXConfigConfig
