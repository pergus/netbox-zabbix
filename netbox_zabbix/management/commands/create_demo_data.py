import random
from django.core.management.base import BaseCommand
from dcim.models import Device, DeviceRole, Platform, Site
from virtualization.models import VirtualMachine
from extras.models import Tag

class Command(BaseCommand):
    help = "Create Demo Roles, Platforms, Tags, and Sites, and randomly assign them to Devices and VMs"

    def handle(self, *args, **kwargs):
        self.create_sites()
        self.create_roles()
        self.create_platforms()
        self.create_tags()
        self.assign_to_devices_and_vms()
        self.stdout.write(self.style.SUCCESS("Successfully created roles, platforms, tags, and sites."))

    def create_sites(self):
        site_names = ['Stockholm', 'Gothenburg', 'Malmo', 'Lund', 'Uppsala']
        for name in site_names:
            Site.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(" ", "-")})

    def create_roles(self):
        role_names = ['Core', 'Edge', 'Distribution', 'Access', 'DMZ']
        for name in role_names:
            DeviceRole.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(" ", "-")})

    def create_platforms(self):
        platform_names = ['Cisco IOS', 'JunOS', 'NX-OS', 'Linux', 'Windows']
        for name in platform_names:
            Platform.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(" ", "-")})

    def create_tags(self):
        tag_names = ['critical', 'test', 'legacy', 'prod', 'dev']
        for name in tag_names:
            Tag.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(" ", "-")})

    def assign_to_devices_and_vms(self):
        roles = list(DeviceRole.objects.all())
        platforms = list(Platform.objects.all())
        tags = list(Tag.objects.all())
        sites = list(Site.objects.all())

        for device in Device.objects.all():
            device.role = random.choice(roles)
            device.platform = random.choice(platforms)
            device.site = random.choice(sites)
            device.tags.set(random.sample(tags, random.randint(1, len(tags))))
            device.save()
            self.stdout.write(f"Updated Device: {device.name}")

        for vm in VirtualMachine.objects.all():
            if hasattr(vm, 'role'):
                vm.role = random.choice(roles)
            if hasattr(vm, 'platform'):
                vm.platform = random.choice(platforms)
            if hasattr(vm, 'site'):
                vm.site = random.choice(sites)
            vm.tags.set(random.sample(tags, random.randint(1, len(tags))))
            vm.save()
            self.stdout.write(f"Updated VM: {vm.name}")
