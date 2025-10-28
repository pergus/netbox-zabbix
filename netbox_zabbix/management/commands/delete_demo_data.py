from django.core.management.base import BaseCommand
from dcim.models import (
    Device, DeviceRole, Platform, Site, Region, Manufacturer, DeviceType,
    Interface
)
from extras.models import Tag
from ipam.models import Prefix, IPAddress
from virtualization.models import VirtualMachine, VMInterface, Cluster, ClusterGroup, ClusterType

import sys
import os

sys.path.append(os.path.dirname(__file__))
from demo_data_config import config

os.environ["DISABLE_NETBOX_ZABBIX_SIGNALS"] = "1"

class Command(BaseCommand):
    help = "Delete all demo data created by create_demo_data command"

    # === Configuration: Change these lists to match your demo data naming ===
    device_name_regex   = config['device_name_regex']
    vm_name_regex       = config['vm_name_regex']
    interface_name      = config['interface_name']
    ip_address_prefixes = config['ip_address_prefixes']
    tag_names           = config['tags']
    regions             = list(config['region_codes'].keys())
    sites               = [site['name'] for site in config['sites']]
    manufacturers       = config['manufacturers']
    device_roles        = config['device_roles']
    platforms           = config['platforms']
    cluster_names       = [cluster['name'] for cluster in config['clusters']]
    cluster_groups      = config['cluster_groups']
    cluster_types       = [ct['name'] for ct in config['cluster_types']]
    prefixes            = config['prefixes']

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting cleanup of demo data...")
        self.delete_devices_and_vms()
        self.delete_interfaces()
        self.delete_ip_addresses()
        self.delete_tags()
        self.delete_sites_and_regions()
        self.delete_manufacturers_and_device_types()
        self.delete_roles_platforms()
        self.delete_clusters_and_related()
        self.delete_prefixes()
        self.stdout.write(self.style.SUCCESS("Successfully deleted all demo data."))

    def delete_queryset(self, queryset, description):
        count = queryset.count()
        if count:
            self.stdout.write(f"Deleting {count} {description}...")
            for obj in queryset:
                self.stdout.write(f" - {obj}")
            queryset.delete()
        else:
            self.stdout.write(f"No {description} found to delete.")

    def delete_devices_and_vms(self):
        self.delete_queryset(Device.objects.filter(name__regex=self.device_name_regex), "Devices")
        self.delete_queryset(VirtualMachine.objects.filter(name__regex=self.vm_name_regex), "Virtual Machines")

    def delete_interfaces(self):
        self.delete_queryset(
            Interface.objects.filter(name__endswith=f"-{self.interface_name}", device__name__regex=self.device_name_regex),
            "Device Interfaces"
        )
        self.delete_queryset(
            VMInterface.objects.filter(name__endswith=f"-{self.interface_name}", virtual_machine__name__regex=self.vm_name_regex),
            "VM Interfaces"
        )

    def delete_ip_addresses(self):
        for prefix in self.ip_address_prefixes:
            queryset = IPAddress.objects.filter(address__startswith=prefix)
            self.delete_queryset(queryset, f"IP addresses starting with {prefix}")

    def delete_tags(self):
        self.delete_queryset(Tag.objects.filter(name__in=self.tag_names), "Tags")

    def delete_sites_and_regions(self):
        self.delete_queryset(Site.objects.filter(name__in=self.sites), "Sites")
        self.delete_queryset(Region.objects.filter(name__in=self.regions), "Regions")

    def delete_manufacturers_and_device_types(self):
        self.delete_queryset(DeviceType.objects.filter(manufacturer__name__in=self.manufacturers), "Device Types")
        self.delete_queryset(Manufacturer.objects.filter(name__in=self.manufacturers), "Manufacturers")

    def delete_roles_platforms(self):
        self.delete_queryset(DeviceRole.objects.filter(name__in=self.device_roles), "Device Roles")
        self.delete_queryset(Platform.objects.filter(name__in=self.platforms), "Platforms")

    def delete_clusters_and_related(self):
        clusters = Cluster.objects.filter(group__name__in=self.cluster_groups)
        self.delete_queryset(clusters, "Clusters")
        self.delete_queryset(ClusterGroup.objects.filter(name__in=self.cluster_groups), "Cluster Groups")

    def delete_prefixes(self):
        self.delete_queryset(Prefix.objects.filter(prefix__in=self.prefixes), "Prefixes")
