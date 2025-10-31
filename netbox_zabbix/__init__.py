"""Top-level package for netbox-zabbix."""

__author__ = """pergus"""
__email__ = "pergus@axis.com"
__version__ = "2.0.0"


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
        
        from django.contrib.contenttypes.models import ContentType
        from dcim.models import Device
        from virtualization.models import VirtualMachine
        from netbox_zabbix.models import HostConfig

        # Import and register signals
        from .signals import signals

        def get_hostconfig(self):
            ct = ContentType.objects.get_for_model( self )
            return HostConfig.objects.filter( content_type=ct, object_id=self.id ).first()
        

        Device.add_to_class( "host_config", property( get_hostconfig ) )
        VirtualMachine.add_to_class( "host_config", property(get_hostconfig) )
        



config = ZConfiguration
