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
    ENABLED = 'enabled', 'Enabled'    # 0 - (default) monitored host
    DISABLED = 'disabled', 'Disabled' # 1 - unmonitored host.

class ManagedHost(NetBoxModel):
    class Meta:
        abstract = True

    hostid = models.PositiveIntegerField( unique=True, blank=True, null=True )
    status = models.CharField( max_length=255, choices=StatusChoices.choices, default='enabled' )
    templates = models.ManyToManyField( Template, blank=True )

    
class DeviceHost(ManagedHost):
    class Meta:
        verbose_name = "Device Host"
        verbose_name_plural = "Device Hosts"
    
    device = models.OneToOneField( to='dcim.Device', on_delete=models.CASCADE, related_name='zbx_device_host' )

    def __str__(self):
        return f"zbx-{self.device.name}"

    def get_name(self):
        return f"zbx-{self.device.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:devicehost", args=[self.pk] )


class VMHost(ManagedHost):
    class Meta:
        verbose_name = "VM Host"
        verbose_name_plural = "VM Hosts"
    
    virtual_machine = models.OneToOneField( to='virtualization.VirtualMachine', on_delete=models.CASCADE, related_name='zbx_vm_host' )

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
    UNKNOWN = (0, 'Unknown')
    AVAILABLE = (1, 'Available')
    UNAVAILABLE = (2, 'Unavailable')

class TypeChoices(models.IntegerChoices):
    AGENT = (1, 'Agent')
    SNMP =  (2, 'SNMP')

class HostInterface(NetBoxModel):
    class Meta:
        abstract = True
    
    name = models.CharField( max_length=255, blank=False, null=False )

    # Zabbix Host ID
    hostid = models.IntegerField( blank=True, null=True )

    # Zabbix Host Interface ID
    interfaceid = models.IntegerField( blank=True, null=True )

    # Availablility of host interface. 
    available = models.IntegerField( choices=AvailableChoices, default=AvailableChoices.AVAILABLE )

    # Whether a connection should be made via IP or DNS.
    useip = models.IntegerField( choices=UseIPChoices, default=UseIPChoices.IP )

    # Whether the interface is used as default on the host.
    # Only one interface of some type can be set as default on a host.
    main = models.IntegerField( choices=MainChoices, default=MainChoices.YES )

        

class DeviceAgentInterface(HostInterface):
    class Meta:
        verbose_name = "Device Agent Interface"
        verbose_name_plural = "Device Agent Interfaces"
    
    host = models.ForeignKey( to="DeviceHost", on_delete=models.CASCADE, related_name="agent_interfaces" )
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, blank=True, null=True, related_name="agent_interface" )

    # Interface type
    type = models.IntegerField(choices=TypeChoices, default=TypeChoices.AGENT )

    # Port number used by the interface.
    port = models.IntegerField( default=10050 )
    
    # IP address used by the interface. Can be empty if connection is made via DNS.
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


    def clean(self):
        super().clean()
    
        interface = self.interface
        ip_address = self.ip_address
    
        # Validate interface/IP match
        if ip_address and interface:
            if ip_address.assigned_object != interface:
                raise ValidationError({ "ip_address": "The selected IP address is not assigned to the selected interface." })
    
            
    def save(self, *args, **kwargs):
        self.full_clean()

        # Ensure only one agent interface is the the main interface.
        if self.main == MainChoices.YES:
            existing_mains = self.host.agent_interfaces.filter( main=MainChoices.YES )
            if existing_mains.exists():
                existing_mains.update( main=MainChoices.NO )
        
        
        return super().save(*args, **kwargs)
    

class DeviceSNMPv3Interface(HostInterface):
    class Meta:
        verbose_name = "Device SNMPv3 Interface"
        verbose_name_plural = "Device SNMPv3 Interfaces"
    
    host = models.ForeignKey( to='DeviceHost', on_delete=models.CASCADE, related_name='snmpv3_interfaces' )
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, related_name="snmpv3_interface" )
    

    # Interface type
    type = models.IntegerField(choices=TypeChoices, default=TypeChoices.SNMP )
    
    # Port number used by the interface.
    port = models.IntegerField( default=161 )

    
    # IP address used by the interface. Can be empty if connection is made via DNS.
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="snmp3_ip" )


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