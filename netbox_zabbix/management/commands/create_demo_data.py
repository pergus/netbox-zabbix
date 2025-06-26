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
            region, created = Region.objects.get_or_create(name=name, defaults={'slug': name.lower()})
            if created:
                self.stdout.write(f"Created Region: {name}")
            else:
                self.stdout.write(f"Region already exists: {name}")

    def create_sites(self):
        for d in self.sites:
            region_obj = Region.objects.get(name=d['region'])
            site, created = Site.objects.get_or_create(
                name=d['name'],
                defaults={
                    'slug': d['name'].lower().replace(' ', '-'),
                    'region': region_obj,
                    'latitude': d['latitude'],
                    'longitude': d['longitude'],
                }
            )
            if created:
                self.stdout.write(f"Created Site: {d['name']}")
            else:
                self.stdout.write(f"Site already exists: {d['name']}")

    def create_cluster_types(self):
        for ct in self.cluster_types:
            ct_obj, created = ClusterType.objects.get_or_create(name=ct['name'], defaults={'slug': ct['slug']})
            if created:
                self.stdout.write(f"Created ClusterType: {ct['name']}")
            else:
                self.stdout.write(f"ClusterType already exists: {ct['name']}")

    def create_cluster_groups(self):
        for g in self.cluster_groups:
            group, created = ClusterGroup.objects.get_or_create(name=g, defaults={'slug': g.lower()})
            if created:
                self.stdout.write(f"Created ClusterGroup: {g}")
            else:
                self.stdout.write(f"ClusterGroup already exists: {g}")

    def create_clusters(self):
        for cluster in self.clusters:
            cluster_obj, created = Cluster.objects.get_or_create(
                name=cluster['name'],
                defaults={
                    'type': ClusterType.objects.get(name=cluster['type']),
                    'group': ClusterGroup.objects.get(name=cluster['group'])
                }
            )
            if created:
                self.stdout.write(f"Created Cluster: {cluster['name']}")
            else:
                self.stdout.write(f"Cluster already exists: {cluster['name']}")

    def create_prefixes(self):
        for p in self.prefixes:
            prefix, created = Prefix.objects.get_or_create(prefix=p, vrf=None)
            if created:
                self.stdout.write(f"Created Prefix: {p}")
            else:
                self.stdout.write(f"Prefix already exists: {p}")

    def create_manufacturers(self):
        for m in self.manufacturers:
            man, created = Manufacturer.objects.get_or_create(name=m, defaults={'slug': m.lower()})
            if created:
                self.stdout.write(f"Created Manufacturer: {m}")
            else:
                self.stdout.write(f"Manufacturer already exists: {m}")

    def create_device_types(self):
        for man in Manufacturer.objects.all():
            for model_suffix in self.device_types:
                model_name = f"{man.name} {model_suffix}"
                devtype, created = DeviceType.objects.get_or_create(
                    model=model_name,
                    manufacturer=man,
                    defaults={'slug': f"{man.slug}-{model_suffix.lower().replace(' ', '-')}"}
                )
                if created:
                    self.stdout.write(f"Created DeviceType: {model_name}")
                else:
                    self.stdout.write(f"DeviceType already exists: {model_name}")

    def create_roles(self):
        for r in self.device_roles:
            role, created = DeviceRole.objects.get_or_create(name=r, defaults={'slug': r.lower()})
            if created:
                self.stdout.write(f"Created DeviceRole: {r}")
            else:
                self.stdout.write(f"DeviceRole already exists: {r}")

    def create_platforms(self):
        for p in self.platforms:
            platform, created = Platform.objects.get_or_create(name=p, defaults={'slug': p.lower()})
            if created:
                self.stdout.write(f"Created Platform: {p}")
            else:
                self.stdout.write(f"Platform already exists: {p}")

    def create_tags(self):
        for t in self.tags:
            tag, created = Tag.objects.get_or_create(name=t, defaults={'slug': t})
            if created:
                self.stdout.write(f"Created Tag: {t}")
            else:
                self.stdout.write(f"Tag already exists: {t}")

    def build_ip_pool(self):
        used_ips = set(IPAddress.objects.values_list("address", flat=True))
        pool = []
        for prefix in Prefix.objects.all():
            net = ipaddress.ip_network(prefix.prefix)
            for ip in net.hosts():
                ip_str = str(ip)
                if ip_str not in used_ips:
                    pool.append((ip_str, prefix))
        random.shuffle(pool)
        return pool

    def allocate_ip(self):
        if not self.ip_pool:
            raise RuntimeError("No IPs left in pool")
    
        while self.ip_pool:
            ip_str, prefix = self.ip_pool.pop()
            ip_with_prefix = f"{ip_str}/{prefix.prefix.prefixlen}"
    
            # Skip IPs already assigned as a primary to a device or VM
            if Device.objects.filter(primary_ip4__address=ip_with_prefix).exists():
                continue
            if VirtualMachine.objects.filter(primary_ip4__address=ip_with_prefix).exists():
                continue
    
            ip_obj, _ = IPAddress.objects.get_or_create(address=ip_with_prefix)
            return ip_obj
    
        raise RuntimeError("No unused IPs available for primary assignment")
        

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

            dev, created = Device.objects.get_or_create(
                name=name,
                defaults={
                    'device_type': random.choice(devtypes),
                    'site': site,
                    'role': random.choice(roles),
                    'platform': platform,
                }
            )

            if not created:
                self.stdout.write(f"Device {name} already exists, skipping.")
                continue

            dev.tags.set(random.sample(tags, 2))

            iface = Interface.objects.create(device=dev, name="eth0")
            ip = self.allocate_ip()
            iface.ip_addresses.add(ip)
            dev.primary_ip4 = ip
            dev.save()

            self.stdout.write(f"Created Device {name} → {dev.primary_ip4.address}")

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

            vm, created = VirtualMachine.objects.get_or_create(
                name=name,
                defaults={
                    'site': site,
                    'cluster': random.choice(clusters),
                    'role': random.choice(roles),
                    'platform': platform,
                }
            )

            if not created:
                self.stdout.write(f"VM {name} already exists, skipping.")
                continue

            vm.tags.set(random.sample(tags, 2))

            iface = VMInterface.objects.create(virtual_machine=vm, name="eth0")
            ip = self.allocate_ip()
            iface.ip_addresses.add(ip)
            vm.primary_ip4 = ip
            vm.save()

            self.stdout.write(f"Created VM {name} → {vm.primary_ip4.address}")
