import random
import ipaddress
from django.core.management.base import BaseCommand
from dcim.models import (
    Device, DeviceRole, Platform, Site, Region, Manufacturer, DeviceType,
    Interface
)
from extras.models import Tag
from ipam.models import Prefix, IPAddress
from virtualization.models import (
    VirtualMachine, Cluster, ClusterGroup, ClusterType,
    VMInterface
)

import sys
import os

sys.path.append(os.path.dirname(__file__))
from demo_data_config import config

class Command(BaseCommand):
    help = "Create demo Devices and VMs with interface and primary IPv4"

    # === Configurable parameters ===
    num_devices = config['num_devices']
    num_vms = config['num_vms']

    
    region_code = config['region_codes']
    sites = config['sites']
    cluster_types = config['cluster_types']
    cluster_groups = config['cluster_groups']
    clusters = config['clusters']
    prefixes = config['prefixes']
    manufacturers = config['manufacturers']
    device_types = config['device_types']
    device_roles = config['device_roles']
    platforms = config['platforms']
    tags = config['tags']
    linux_platform_name = config['linux_platform_name']
    windows_platform_name = config['windows_platform_name']
    device_name_flags = config['device_name_flags']
    vm_name_flags = config['vm_name_flags']


    # ================================

    def handle(self, *args, **kwargs):
        self.setup_demo_data()
        self.ip_pool = self.build_ip_pool()
        self.create_devices(self.num_devices)
        self.create_virtual_machines(self.num_vms)
        self.stdout.write(self.style.SUCCESS("Successfully created demo Devices and VMs with IPs."))

    def setup_demo_data(self):
        self.create_regions()
        self.create_sites()
        self.create_cluster_types()
        self.create_cluster_groups()
        self.create_clusters()
        self.create_prefixes()
        self.create_manufacturers()
        self.create_device_types()
        self.create_roles()
        self.create_platforms()
        self.create_tags()

    def create_regions(self):
        for name in self.region_code:
            Region.objects.get_or_create(name=name, defaults={'slug': name.lower()})

    def create_sites(self):
        for d in self.sites:
            region_obj = Region.objects.get(name=d['region'])
            Site.objects.get_or_create(
                name=d['name'],
                defaults={
                    'slug': d['name'].lower().replace(' ', '-'),
                    'region': region_obj,
                    'latitude': d['latitude'],
                    'longitude': d['longitude'],
                }
            )

    def create_cluster_types(self):
        for ct in self.cluster_types:
            ClusterType.objects.get_or_create(name=ct['name'], defaults={'slug': ct['slug']})

    def create_cluster_groups(self):
        for g in self.cluster_groups:
            ClusterGroup.objects.get_or_create(name=g, defaults={'slug': g.lower()})

    def create_clusters(self):
        for cluster in self.clusters:
            Cluster.objects.get_or_create(
                name=cluster['name'],
                defaults={
                    'type': ClusterType.objects.get(name=cluster['type']),
                    'group': ClusterGroup.objects.get(name=cluster['group'])
                }
            )

    def create_prefixes(self):
        for p in self.prefixes:
            Prefix.objects.get_or_create(prefix=p, vrf=None)

    def create_manufacturers(self):
        for m in self.manufacturers:
            Manufacturer.objects.get_or_create(name=m, defaults={'slug': m.lower()})

    def create_device_types(self):
        for man in Manufacturer.objects.all():
            for model_suffix in self.device_types:
                model_name = f"{man.name} {model_suffix}"
                DeviceType.objects.get_or_create(
                    model=model_name,
                    manufacturer=man,
                    defaults={'slug': f"{man.slug}-{model_suffix.lower().replace(' ', '-')}"}
                )

    def create_roles(self):
        for r in self.device_roles:
            DeviceRole.objects.get_or_create(name=r, defaults={'slug': r.lower()})

    def create_platforms(self):
        for p in self.platforms:
            Platform.objects.get_or_create(name=p, defaults={'slug': p.lower()})

    def create_tags(self):
        for t in self.tags:
            Tag.objects.get_or_create(name=t, defaults={'slug': t})

    def build_ip_pool(self):
        pool = []
        for prefix in Prefix.objects.all():
            net = ipaddress.ip_network(prefix.prefix)
            for ip in net.hosts():
                pool.append((str(ip), prefix))
        random.shuffle(pool)
        return pool

    def allocate_ip(self):
        if not self.ip_pool:
            raise RuntimeError("No IP left")
        ip_str, prefix = self.ip_pool.pop()
        ip_obj, _ = IPAddress.objects.get_or_create(
            address=f"{ip_str}/{prefix.prefix.prefixlen}"
        )
        return ip_obj

    def get_region_code(self, site):
        return self.region_code.get(site.region.name, 'xx')

    def get_platform(self, flag):
        if flag == 'x':
            name = self.linux_platform_name
        else:
            name = self.windows_platform_name
        return Platform.objects.get(name=name)

    def create_devices(self, count):
        roles = list(DeviceRole.objects.all())
        tags = list(Tag.objects.all())
        sites = list(Site.objects.all())
        devtypes = list(DeviceType.objects.all())
        counters = {code: 1 for code in self.region_code.values()}
        for _ in range(count):
            site = random.choice(sites)
            code = self.get_region_code(site)
            flag = random.choice(self.device_name_flags)
            name = f"{code}-ece{counters[code]:03d}{flag}"
            counters[code] += 1
            platform = self.get_platform(flag)
            dev, created = Device.objects.get_or_create(name=name, defaults={
                'device_type': random.choice(devtypes),
                'site': site,
                'role': random.choice(roles),
                'platform': platform,
            })
            dev.tags.set(random.sample(tags, 2))

            if created:
                iface = Interface.objects.create(device=dev, name="eth0")
                ip = self.allocate_ip()
                iface.ip_addresses.add(ip)
                dev.primary_ip4 = ip
                dev.save()

            self.stdout.write(f"Device {name} → {dev.primary_ip4.address if dev.primary_ip4 else 'no IP'}")

    def create_virtual_machines(self, count):
        roles = list(DeviceRole.objects.all())
        tags = list(Tag.objects.all())
        sites = list(Site.objects.all())
        clusters = list(Cluster.objects.all())
        counters = {code: 1 for code in self.region_code.values()}
        for _ in range(count):
            site = random.choice(sites)
            code = self.get_region_code(site)
            flag = random.choice(self.vm_name_flags)
            name = f"{code}-vm{counters[code]:03d}{flag}"
            counters[code] += 1
            platform = self.get_platform(flag)

            vm, created = VirtualMachine.objects.get_or_create(name=name, defaults={
                'site': site,
                'cluster': random.choice(clusters),
                'role': random.choice(roles),
                'platform': platform,
            })
            vm.tags.set(random.sample(tags, 2))

            if created:
                iface = VMInterface.objects.create(virtual_machine=vm, name="eth0")
                ip = self.allocate_ip()
                iface.ip_addresses.add(ip)
                vm.primary_ip4 = ip
                vm.save()

            self.stdout.write(f"VM {name} → {vm.primary_ip4.address if vm.primary_ip4 else 'no IP'}")
