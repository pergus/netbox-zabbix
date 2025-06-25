"""Top-level package for netbox-zabbix."""

__author__ = """pergus"""
__email__ = "pergus@axis.com"
__version__ = "0.1.0"


from netbox.plugins import PluginConfig


class ZConfiguration(PluginConfig):
    name = "netbox_zabbix"
    verbose_name = "netbox-zabbix"
    description = "NetBox plugin for Zabbix."
    version = __version__
    author = __author__
    email = __email__
    base_url = "netbox_zabbix"

    default_settings = {
        'field_mappings': {
            'device': [
                ('Role', 'role.name'),
                ('Platform', 'platform.name'),
                ('Site', 'site.name'),
                ('Region', 'site.region'),
                ('Longitude', 'site.longitude'),
                ('Latitude', 'site.latitude'),
                ('Tags', 'tags'),
            ],
            'virtualmachine': [
                ('Role', 'role.name'),
                ('Platform', 'platform.name'),
                ('Cluster', 'cluster.name'),
                ('Site', 'site.name'),
                ('Region', 'site.region'),
                ('Longitude', 'site.longitude'),
                ('Latitude', 'site.latitude'),
                ('Tags', 'tags'),
            ],
        }
    }

    def ready(self):
            super().ready()
            # Import and register signals
            from .signals import signals
    
            # Register api
            #from netbox_zabbix.api import urls as api_urls        
            #api_urls = api_urls

config = ZConfiguration
