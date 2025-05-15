from click import version_option
from django.urls import reverse
from django.db import models
from django.core.exceptions import ValidationError

from netbox.models import NetBoxModel


# ------------------------------------------------------------------------------
# Configuration
#

class IPAssignmentChoices(models.TextChoices):
    MANUAL = "manual", "Manual"
    PRIMARY = "primary", "Primary IPv4 Address"



class Config(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Configuration"
        verbose_name_plural = "Zabbix Configurations"
    
    name             = models.CharField( max_length=255 )
    api_endpoint     = models.CharField( verbose_name="API Edpoint", max_length=255 )
    web_address      = models.CharField( verbose_name="WEB Address", max_length=255 )
    token            = models.CharField( max_length=255 )
    connection       = models.BooleanField( default=False )
    last_checked_at  = models.DateTimeField( null=True, blank=True )
    version          = models.CharField( max_length=255, blank=True, null=True )
    
    ip_assignment_method = models.CharField(
        verbose_name="IP Assignment Method",
        max_length=16,
        choices=IPAssignmentChoices.choices,
        default=IPAssignmentChoices.PRIMARY,
        help_text="Select how to assign IP addresses to host interfaces."
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:config", args=[self.pk])

# ------------------------------------------------------------------------------
# Templates
#

class Template(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Template"
        verbose_name_plural = "Zabbix Templates"
    
    name = models.CharField( max_length=255 )
    templateid = models.CharField( max_length=255 )
    last_synced = models.DateTimeField( blank=True, null=True )
    marked_for_deletion = models.BooleanField( default=False )
     
    def __str__(self):
        return self.name
    
# ------------------------------------------------------------------------------
# Host
#

class StatusChoices(models.TextChoices):
    ENABLED = 'enabled', 'Enabled'
    DISABLEd = 'disabled', 'Disabled'

class ManagedHost(NetBoxModel):
    class Meta:
        abstract = True

    zabbix_host_id = models.PositiveIntegerField( unique=True, blank=True, null=True )
    status = models.CharField( max_length=255, choices=StatusChoices.choices, default='enabled' )
    templates = models.ManyToManyField( Template, blank=True )

    
class DeviceHost(ManagedHost):
    device = models.OneToOneField( to='dcim.Device', on_delete=models.CASCADE, related_name='zabbix_device_host' )

    def __str__(self):
        return f"zbx-{self.device.name}"

    def get_name(self):
        return f"zbx-{self.device.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:devicehost", args=[self.pk] )


class VMHost(ManagedHost):
    virtual_machine = models.OneToOneField( to='virtualization.VirtualMachine', on_delete=models.CASCADE, related_name='zabbix_vm_host' )

    def __str__(self):
        return f"zbx-{self.virtual_machine.name}"

    def get_name(self):
        return f"zbx-{self.virtual_machine.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:vmhost", args=[self.pk] )


# ------------------------------------------------------------------------------
# Interface
#

class UseIPChoices(models.IntegerChoices):
    DNS = (0, 'DNS Name')
    IP = (1, 'IP Address')

class MainChoices(models.IntegerChoices):
    NO = (0, 'No')
    YES = (1, 'Yes')

class AvailableChoices(models.IntegerChoices):
    NO = (0, 'No')
    YES = (1, 'Yes')


class HostInterface(NetBoxModel):
    class Meta:
        abstract = True
    
    name = models.CharField( max_length=255, blank=False, null=False )
    zabbix_host_id = models.IntegerField( blank=True, null=True )
    zabbix_interface_id = models.IntegerField( blank=True, null=True )
    available = models.IntegerField( choices=AvailableChoices, default=AvailableChoices.YES )
    useip = models.IntegerField( choices=UseIPChoices, default=UseIPChoices.IP )
    main = models.IntegerField( choices=MainChoices, default=MainChoices.YES )


class DeviceAgentInterface(HostInterface):
    class Meta:
        verbose_name = "Device Agent Interface"
        verbose_name_plural = "Device Agent Interfaces"
    
    port = models.IntegerField( default=10050 )
    host = models.ForeignKey( to="DeviceHost", on_delete=models.CASCADE, related_name="agent_interfaces" )
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, blank=True, null=True, related_name="agent_interface" )
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="agent_ip" )

    def __str__(self):
        return f"{self.name}"
    
    def get_name(self):
        return f"{self.name}"

    @property
    def resolved_dns_name(self):
        config = Config.objects.first()
        if config.ip_assignment_method == 'primary':
            return self.host.device.primary_ip4.dns_name
        else:
            return self.ip_address.dns_name

    @property
    def resolved_ip_address(self):
        config = Config.objects.first()
        if config.ip_assignment_method == 'primary':
            return self.host.device.primary_ip4
        else:
            return self.ip_address
        
class DeviceSNMPv3Interface(HostInterface):
    class Meta:
        verbose_name = "Device SNMPv3 Interface"
        verbose_name_plural = "Device SNMPv3 Interfaces"
    
    port = models.IntegerField( default=161 )
    host = models.ForeignKey( to='DeviceHost', on_delete=models.CASCADE, related_name='snmpv3_interfaces' )
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, related_name="snmpv3_interface" )

    def __str__(self):
        return f"{self.name}"
    
    def get_name(self):
        return f"{self.name}"

    def clean(self):
        super().clean()
    
        # Prevent duplicate use of the interface across HostInterfaces
        if DeviceSNMPv3Interface.objects.filter( interface=self.interface ).exclude( pk=self.pk ).exists():
            raise ValidationError({'interface': 'This interface is already assigned to another HostInterface.'})
    
        # Optional: ensure interface belongs to the same device as host
        if self.host.device != self.interface.device:
            raise ValidationError({'interface': 'Selected interface does not belong to the same device as the host.'})

#
#
#class VMAgentInterface(HostInterface):
#    class Meta:
#        verbose_name = "VM Agent Interface"
#        verbose_name_plural = "VM Agent Interfaces"
#
#    port = models.IntegerField( default=10050 )
#    host = models.OneToOneField( to='VMHost', on_delete=models.CASCADE, related_name='agent_interfaces' )
#
#
#class VMSNMPv1(HostInterface):
#    class Meta:
#        verbose_name = "VM SNMPv1 Interface"
#        verbose_name_plural = "VM SNMPv1 Interfaces"
#        
#    port = models.IntegerField( default=161 )
#    host = models.OneToOneField( to='VMHost', on_delete=models.CASCADE, related_name='snmpv1_interfaces' )


# Proxy model so that it is possible to register a ViewSet.
# The ViewSet is used to filter out interfaces that has already been assoicated
# with a Device interface.

from dcim.models import Interface
class AvailableDeviceInterface(Interface):
    class Meta:
        proxy = True