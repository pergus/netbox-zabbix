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


class Command(BaseCommand):
    help = "Delete all demo data created by create_demo_data command"

    # === Configuration: Change these lists to match your demo data naming ===
    device_name_regex = config['device_name_regex']
    vm_name_regex = config['vm_name_regex']
    interface_name = config['interface_name']
    ip_address_prefixes = config['ip_address_prefixes']
    tag_names = config['tags']
    regions = list(config['region_codes'].keys())
    sites = [site['name'] for site in config['sites']]
    manufacturers = config['manufacturers']
    device_roles = config['device_roles']
    platforms = config['platforms']
    cluster_names = [cluster['name'] for cluster in config['clusters']]
    cluster_groups = config['cluster_groups']
    cluster_types = [ct['name'] for ct in config['cluster_types']]
    prefixes = config['prefixes']

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

    def delete_devices_and_vms(self):
        Device.objects.filter(name__regex=self.device_name_regex).delete()
        VirtualMachine.objects.filter(name__regex=self.vm_name_regex).delete()

    def delete_interfaces(self):
        Interface.objects.filter(
            name=self.interface_name,
            device__name__regex=self.device_name_regex
        ).delete()
        VMInterface.objects.filter(
            name=self.interface_name,
            virtual_machine__name__regex=self.vm_name_regex
        ).delete()

    def delete_ip_addresses(self):
        for prefix in self.ip_address_prefixes:
            IPAddress.objects.filter(address__startswith=prefix).delete()

    def delete_tags(self):
        Tag.objects.filter(name__in=self.tag_names).delete()

    def delete_sites_and_regions(self):
        Site.objects.filter(name__in=self.sites).delete()
        Region.objects.filter(name__in=self.regions).delete()

    def delete_manufacturers_and_device_types(self):
        DeviceType.objects.filter(manufacturer__name__in=self.manufacturers).delete()
        Manufacturer.objects.filter(name__in=self.manufacturers).delete()

    def delete_roles_platforms(self):
        DeviceRole.objects.filter(name__in=self.device_roles).delete()
        Platform.objects.filter(name__in=self.platforms).delete()

    def delete_clusters_and_related(self):
        clusters_to_delete = Cluster.objects.filter(group__name__in=self.cluster_groups)
        clusters_to_delete.delete()
        ClusterGroup.objects.filter(name__in=self.cluster_groups).delete()

    def delete_prefixes(self):
        Prefix.objects.filter(prefix__in=self.prefixes).delete()
