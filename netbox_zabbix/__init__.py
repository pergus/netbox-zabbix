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
        'tag_mappings': {
            'device': [
                ('Site',      'site.name'),
                ('Region',    'site.region'),
                ('Latitude',  'site.latitude'),
                ('Longitude', 'site.longitude'),
                ('Role',      'role.name'),
                ('Platform',  'platform.name'),
            ],
            'virtualmachine': [
                ('Site',      'site.name'),
                ('Region',    'site.region'),
                ('Latitude',  'site.latitude'),
                ('Longitude', 'site.longitude'),
                ('Cluster',   'cluster.name'),
                ('Role',      'role.name'),
                ('Platform',  'platform.name'),
            ],
        },
        "inventory_mapping": {
            'device': [
                ("Name",      "name",         ["name"]),
                ("Platform",  "os",           ["platform.name"]),
                ("Location",  "location",     ["location.name", "site.name"]),
                ("Latitude",  "location_lat", ["location.site.latitude", "site.latitude"]),
                ("Longitude", "location_lon", ["location.site.longitude", "site.longitude"]),
            ],
            'virtualmachine': [
                ("Name",      "name",         ["name"]),
                ("Platform",  "os",           ["platform.name"]),
                ("Location",  "location",     ["location.name", "site.name"]),
                ("Latitude",  "location_lat", ["location.site.latitude", "site.latitude"]),
                ("Longitude", "location_lon", ["location.site.longitude", "site.longitude"]),
            ]
            
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
