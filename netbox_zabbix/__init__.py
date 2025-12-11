"""
Top-level package for netbox-zabbix.

Defines the NetBox plugin configuration, default settings, and integrates
HostConfig objects with Device and VirtualMachine models for enhanced
Zabbix monitoring capabilities.

Attributes:
    __author__ (str): The author of the plugin.
    __email__ (str): The author's email.
    __version__ (str): Plugin version.
"""

__author__ = """pergus"""
__email__ = "pergus@axis.com"
__version__ = "2.0.0"


# NetBox imports
from netbox.plugins import PluginConfig

class NetboxZabbixConfig(PluginConfig):
    """
    NetBox plugin configuration for the netbox-zabbix plugin.
    
    This class defines metadata about the plugin, default tag and inventory
    mappings, and attaches the `host_config` property to Device and VirtualMachine
    models.
    
    Attributes:
        name (str): Internal plugin name.
        verbose_name (str): Human-readable plugin name.
        description (str): Short description of the plugin.
        version (str): Plugin version.
        author (str): Author name.
        email (str): Author email.
        base_url (str): Base URL for the plugin.
        default_settings (dict): Default tag and inventory mappings.
    """
    name         = "netbox_zabbix"
    verbose_name = "NetBox Zabbix"
    description  = "NetBox plugin for Zabbix."
    version      = __version__
    author       = __author__
    author_email = __email__
    email        = __email__
    base_url     = "netbox_zabbix"

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
            
        },
        "FERNET_KEY_PATH": "fernet.key",
    }

    def ready(self):
        """
        Initialize the plugin when NetBox is ready.
        
        This method registers signals, imports required models, and adds a `host_config`
        property to Device and VirtualMachine models. The property allows each object
        to access its corresponding HostConfig instance, if one exists.
        
        The property `host_config` is dynamically added via `add_to_class`.
        """

        super().ready()

        from django.contrib.contenttypes.models import ContentType
        from dcim.models import Device
        from virtualization.models import VirtualMachine
        from netbox_zabbix.models import HostConfig

        # Import and register signals
        from .signals import signals


        def get_hostconfig(self):
            """
            Retrieve the HostConfig instance associated with this object.
            
            Returns:
                HostConfig or None: The HostConfig instance for the current Device
                or VirtualMachine, or None if not found.
            """
            ct = ContentType.objects.get_for_model( self )
            return HostConfig.objects.filter( content_type=ct, object_id=self.id ).first()

        Device.add_to_class( "host_config", property( get_hostconfig ) )
        VirtualMachine.add_to_class( "host_config", property(get_hostconfig) )
        


config = NetboxZabbixConfig
