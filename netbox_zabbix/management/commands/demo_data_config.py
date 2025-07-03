# demo_data_config.py

config = {
    "num_devices": 100,
    "num_vms": 100,
    "dns_domain": "se.axis.com",
    "region_codes": {'Sweden': 'se', 'Norway': 'no', 'Denmark': 'dk'},

    "sites": [
        {'name': 'Stockholm', 'region': 'Sweden', 'latitude': 59.3293, 'longitude': 18.0686},
        {'name': 'Gothenburg', 'region': 'Sweden', 'latitude': 57.7089, 'longitude': 11.9746},
        {'name': 'Malmo', 'region': 'Sweden', 'latitude': 55.6050, 'longitude': 13.0038},
        {'name': 'Lund', 'region': 'Sweden', 'latitude': 55.7047, 'longitude': 13.1910},
        {'name': 'Uppsala', 'region': 'Sweden', 'latitude': 59.8586, 'longitude': 17.6389},
        {'name': 'Oslo', 'region': 'Norway', 'latitude': 59.9139, 'longitude': 10.7522},
        {'name': 'Bergen', 'region': 'Norway', 'latitude': 60.3913, 'longitude': 5.3221},
        {'name': 'Trondheim', 'region': 'Norway', 'latitude': 63.4305, 'longitude': 10.3951},
        {'name': 'Copenhagen', 'region': 'Denmark', 'latitude': 55.6761, 'longitude': 12.5683},
        {'name': 'Aarhus', 'region': 'Denmark', 'latitude': 56.1629, 'longitude': 10.2039},
        {'name': 'Odense', 'region': 'Denmark', 'latitude': 55.4038, 'longitude': 10.4024},
    ],

    "cluster_types": [
        {'name': 'VMware', 'slug': 'vmware'},
    ],

    "cluster_groups": ['Production', 'Development', 'Testing', 'Stage'],

    "clusters": [
        {'name': 'Prod Cluster', 'group': 'Production', 'type': 'VMware'},
        {'name': 'Dev Cluster', 'group': 'Development', 'type': 'VMware'},
        {'name': 'Stage Cluster', 'group': 'Stage', 'type': 'VMware'},
    ],

    "prefixes": ['10.0.0.0/24', '10.0.1.0/24', '10.0.2.0/24'],

    "manufacturers": ['Cisco', 'Supermicro', 'Dell', 'HPE', 'IBM'],

    "device_types": ["Model 1"],

    "device_roles": ['Server', 'Edge', 'Access', 'DMZ'],

    "platforms": ['Linux', 'Windows'],

    "tags": ['prod', 'dev', 'test'],

    "linux_platform_name": 'Linux',
    "windows_platform_name": 'Windows',

    "device_name_flags": ['x', 'w'],
    "vm_name_flags": ['x', 'w'],

    # Delete config specific
    "device_name_regex": r'^(se|no|dk)-ece\d{3}[xw]$',
    "vm_name_regex": r'^(se|no|dk)-vm\d{3}[xw]$',
    "interface_name": 'eth0',
    "ip_address_prefixes": ['10.0.0.', '10.0.1.', '10.0.2.'],
}
