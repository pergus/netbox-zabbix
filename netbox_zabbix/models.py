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
    
    name             = models.CharField( max_length=255, help_text="Name of the configuration" )
    api_endpoint     = models.CharField( verbose_name="API Endpoint", max_length=255, help_text="URL to Zabbix API Endpoint" )
    web_address      = models.CharField( verbose_name="Web Address", max_length=255, help_text="URL to Zabbix" )
    token            = models.CharField( max_length=255, help_text="Zabbix access token" )
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
# Zabbix Configs
#

class StatusChoices(models.TextChoices):
    ENABLED = 'enabled', 'Enabled'    # 0 - (default) monitored host
    DISABLED = 'disabled', 'Disabled' # 1 - unmonitored host.

class ZabbixConfig(NetBoxModel):
    class Meta:
        abstract = True

    hostid = models.PositiveIntegerField( unique=True, blank=True, null=True )
    status = models.CharField( max_length=255, choices=StatusChoices.choices, default='enabled' )
    templates = models.ManyToManyField( Template, blank=False )

    
class DeviceZabbixConfig(ZabbixConfig):
    class Meta:
        verbose_name = "Zabbix Device Configuration"
        verbose_name_plural = "Zabbix Device Configurations"
    
    device = models.OneToOneField( to='dcim.Device', on_delete=models.CASCADE, related_name='zbx_device_config' )

    def __str__(self):
        return f"zbx-{self.device.name}"

    def get_name(self):
        return f"zbx-{self.device.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:devicezabbixconfig", args=[self.pk] )


class VMZabbixConfig(ZabbixConfig):
    class Meta:
        verbose_name = "Zabbix VM Configuration"
        verbose_name_plural = "Zabbix VM Configurations"
    
    virtual_machine = models.OneToOneField( to='virtualization.VirtualMachine', on_delete=models.CASCADE, related_name='zbx_vm_config' )

    def __str__(self):
        return f"zbx-{self.virtual_machine.name}"

    def get_name(self):
        return f"zbx-{self.virtual_machine.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:vmzabbixconfig", args=[self.pk] )




# ------------------------------------------------------------------------------
# Interfaces
#

class UseIPChoices(models.IntegerChoices):
    DNS = (0, 'DNS Name')
    IP = (1, 'IP Address')

class MainChoices(models.IntegerChoices):
    NO = (0, 'No')
    YES = (1, 'Yes')

class AvailableChoices(models.IntegerChoices):
    UNKNOWN     = (0, 'Unknown')
    AVAILABLE   = (1, 'Available')
    UNAVAILABLE = (2, 'Unavailable')

class TypeChoices(models.IntegerChoices):
    AGENT = (1, 'Agent')
    SNMP =  (2, 'SNMP')

class SNMPVersionChoices(models.IntegerChoices):
    SNMPv1  = (1, 'SNMPv1')
    SNMPv2c = (2, 'SNMPv2c')
    SNMPv3  = (3, 'SNMPv3')

class SNMPBulkChoices(models.IntegerChoices):
    NO  = (0, 'No')
    YES = (1, 'Yes')

class SNMPSecurityLevelChoices(models.IntegerChoices):
    noAuthNoPriv = (0, 'noAuthNoPriv')
    authNoPriv   = (1, 'authNoPriv')
    authPriv     = (2, 'authPriv')


class SNMPAuthProtocolChoices(models.IntegerChoices):
    MD5    = (0, 'MD5')
    SHA1   = (1, 'SHA1')
    SHA224 = (2, 'SHA224')
    SHA256 = (3, 'SHA256')
    SHA384 = (4, 'SHA384')
    SHA512 = (5, 'SHA512')

class SNMPPrivProtocolChoices(models.IntegerChoices):
    DES     = (0, 'DES')
    AES128  = (1, 'AES128')
    AES192  = (2, 'AES192')
    AES256  = (3, 'AES256')
    AES192C  = (4, 'AES192C')
    AES256C = (5, 'AES256C')
    


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
    
    # Rename to device_host??
    host = models.ForeignKey( to="DeviceZabbixConfig", on_delete=models.CASCADE, related_name="agent_interfaces" )
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
    
    host = models.ForeignKey( to='DeviceZabbixConfig', on_delete=models.CASCADE, related_name='snmpv3_interfaces' )
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, related_name="snmpv3_interface" )
    

    # Interface type
    type = models.IntegerField(choices=TypeChoices, default=TypeChoices.SNMP )
    
    # Port number used by the interface
    port = models.IntegerField( default=161 )
    
    # IP address used by the interface. Can be empty if connection is made via DNS.
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="snmp3_ip" )

    # SNMP interface version
    snmp_version = models.IntegerField( choices=SNMPVersionChoices, default=SNMPVersionChoices.SNMPv3, blank=True, null=True )

    # Whether to use bulk SNMP requests
    snmp_bulk = models.IntegerField( choices=SNMPBulkChoices, default=1, blank=True, null=True )

    # Max repetition value for native SNMP bulk requests
    snmp_max_repetitions = models.IntegerField( default=10, blank=True, null=True )

    # SNMPv3 security name 
    snmp_securityname = models.CharField( max_length=255, blank=True, null=True )

    # SNMPv3 Secuirty level           
    snmp_securitylevel = models.IntegerField( choices=SNMPSecurityLevelChoices, default=SNMPSecurityLevelChoices.authPriv, blank=True, null=True )
    
    # SNMPv3 authentication passphrase
    snmp_authpassphrase = models.CharField( max_length=255, default="{$SNMPV3_AUTHPASS}", blank=True, null=True)

    # SNMPv3 privacy passphrase
    snmp_privpassphrase = models.CharField( max_length=255, default="{$SNMPV3_PRIVPASS}", blank=True, null=True )

    # SNMPv3 authentication protocol
    snmp_authprotocol = models.IntegerField( choices=SNMPAuthProtocolChoices, default=SNMPAuthProtocolChoices.SHA1, blank=True, null=True )

    # SNMPv3 privacy protocol.
    snmp_privprotocol = models.IntegerField( choices=SNMPPrivProtocolChoices, default=SNMPPrivProtocolChoices.AES128, blank=True, null=True )
    
    # SNMPv3 context name.
    snmp_contextname = models.CharField( max_length=255, blank=True, null=True )


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