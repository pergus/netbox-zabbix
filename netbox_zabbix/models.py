# models.py
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from utilities.choices import ChoiceSet

from dcim.models import Device, DeviceRole, Interface, Platform, Site
from core.models import Job
from netbox.models import NetBoxModel
from virtualization.models import VMInterface

from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Choices
# ------------------------------------------------------------------------------


class IPAssignmentChoices(models.TextChoices):
    MANUAL = "manual", "Manual"
    PRIMARY = "primary", "Primary IPv4 Address"


class CIDRChoices(models.TextChoices):
    CIDR_32 = '/32', '/32 (Single IP)'
    CIDR_30 = '/30', '/30'
    CIDR_29 = '/29', '/29'
    CIDR_28 = '/28', '/28'
    CIDR_27 = '/27', '/27'
    CIDR_26 = '/26', '/26'
    CIDR_25 = '/25', '/25'
    CIDR_24 = '/24', '/24 (Typical subnet)'
    CIDR_23 = '/23', '/23'
    CIDR_22 = '/22', '/22'
    CIDR_21 = '/21', '/21'
    CIDR_20 = '/20', '/20'
    CIDR_16 = '/16', '/16 (Large subnet)'


class MonitoredByChoices(models.IntegerChoices):
    ZabbixServer = (0, 'Zabbix Server')
    Proxy        = (1, 'Proxy')
    ProxyGroup   = (2, 'Proxy Group')


class TLSConnectChoices(models.IntegerChoices):
    NoEncryption = (1, 'No Encryption')
    PSK = (2, 'PSK')
    CERTIFICATE = (4, 'Certificate')


class InventoryModeChoices(models.IntegerChoices):
    DISABLED  = (-1, "Disabled")
    MANUAL    = (0, "Manual" )
    AUTOMATIC = (1, "Automatic" )


class TagNameFormattingChoices(models.TextChoices):
    KEEP  = "keep",  "Keep As Entered"
    UPPER = "upper", "Convert to Uppercase"
    LOWER = "lower", "Convert to Lowercase"


class InterfaceTypeChoices(models.IntegerChoices):
    Any   = (0, 'Any')
    Agent = (1, 'Agent')
    SNMP  = (2, 'SNMP')


class StatusChoices(models.IntegerChoices):
    ENABLED  = (0, 'Enabled')
    DISABLED = (1, 'Disabled')


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


class SyncJobIntervalChoices(ChoiceSet):
    INTERVAL_MINUTELY = 1
    INTERVAL_EVERY_5_MINUTES = 5
    INTERVAL_EVERY_15_MINUTES = 15
    INTERVAL_EVERY_30_MINUTES = 30
    INTERVAL_HOURLY = 60
    INTERVAL_EVERY_2_HOURS = 60 * 2
    INTERVAL_EVERY_3_HOURS = 60 * 3
    INTERVAL_EVERY_4_HOURS = 60 * 4
    INTERVAL_EVERY_5_HOURS = 60 * 5
    INTERVAL_EVERY_6_HOURS = 60 * 6
    INTERVAL_EVERY_7_HOURS = 60 * 7
    INTERVAL_EVERY_8_HOURS = 60 * 8
    INTERVAL_EVERY_9_HOURS = 60 * 9
    INTERVAL_EVERY_10_HOURS = 60 * 10
    INTERVAL_EVERY_11_HOURS = 60 * 11
    INTERVAL_EVERY_12_HOURS = 60 * 12
    INTERVAL_DAILY = 60 * 24
    INTERVAL_WEEKLY = 60 * 24 * 7
    INTERVAL_30_DAYS = 60 * 24 * 30

    CHOICES = (
        (INTERVAL_MINUTELY, 'Minutely'),
        (INTERVAL_EVERY_5_MINUTES, 'Every 5 minutes'),
        (INTERVAL_EVERY_15_MINUTES, 'Every 15 minutes'),
        (INTERVAL_EVERY_30_MINUTES, 'Every 30 minutes'),
        (INTERVAL_HOURLY, 'Hourly'),
        (INTERVAL_EVERY_2_HOURS, 'Every 2 hours'),
        (INTERVAL_EVERY_3_HOURS, 'Every 3 hours'),
        (INTERVAL_EVERY_4_HOURS, 'Every 4 hours'),
        (INTERVAL_EVERY_5_HOURS, 'Every 5 hours'),
        (INTERVAL_EVERY_6_HOURS, 'Every 6 hours'),
        (INTERVAL_EVERY_4_HOURS, 'Every 7 hours'),
        (INTERVAL_EVERY_8_HOURS, 'Every 8 hours'),
        (INTERVAL_EVERY_8_HOURS, 'Every 9 hours'),
        (INTERVAL_EVERY_8_HOURS, 'Every 10 hours'),
        (INTERVAL_EVERY_8_HOURS, 'Every 11 hours'),
        (INTERVAL_EVERY_12_HOURS, 'Every 12 hours'),
        (INTERVAL_DAILY, 'Daily'),
        (INTERVAL_WEEKLY, 'Weekly'),
        (INTERVAL_30_DAYS, '30 days'),
    )

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------


class Config(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Configuration"
        verbose_name_plural = "Zabbix Configurations"

    # General
    name                      = models.CharField( verbose_name="Name", max_length=255, help_text="Name of the configuration." )
    ip_assignment_method      = models.CharField(
        verbose_name="IP Assignment Method",
        max_length=16,
        choices=IPAssignmentChoices.choices,
        default=IPAssignmentChoices.PRIMARY,
        help_text="Method used to assign IPs to host interfaces."
    )
    auto_validate_importables = models.BooleanField( verbose_name="Validate Importables", default=False, help_text="Automatically validate importable hosts before displaying them. Otherwise, validation is manual." )
    max_deletions             = models.IntegerField(
        verbose_name="Max Deletions On Import",
        default=3,
        help_text="Limits deletions of stale entries on Zabbix imports."
    )    
    max_success_notifications = models.IntegerField(
        verbose_name="Maximum Success Notifications",
        default=3,
        help_text="Max number of success messages shown per job."
    )
    event_log_enabled         = models.BooleanField( verbose_name="Event Log Enabled", default=False )
    zabbix_sync_interval      = models.PositiveSmallIntegerField( verbose_name="Zabbix Sync Interval", null=True, blank=True, choices=SyncJobIntervalChoices, default=SyncJobIntervalChoices.INTERVAL_DAILY, help_text="Interval in minutes between each Zabbix sync. Must be at least 1 minute." )

    # Zabbix
    version                  = models.CharField( verbose_name="Version", max_length=255, null=True, blank=True )
    api_endpoint             = models.CharField( verbose_name="API Endpoint", max_length=255, help_text="URL to the Zabbix API endpoint." )
    web_address              = models.CharField( verbose_name="Web Address", max_length=255, help_text="URL to the Zabbix web interface." )
    token                    = models.CharField( verbose_name="Token", max_length=255, help_text="Zabbix access token." )
    default_cidr             = models.CharField(
        verbose_name="Default CIDR",
        max_length=4,
        choices=CIDRChoices.choices,
        default=CIDRChoices.CIDR_24,
        help_text="CIDR suffix used for interface IP lookups in NetBox."
    )
    
    connection               = models.BooleanField( verbose_name="Connection", default=False )
    last_checked_at          = models.DateTimeField( verbose_name="Last Checked At", null=True, blank=True )

    inventory_mode = models.IntegerField(
        verbose_name="Inventory Mode",
        choices=InventoryModeChoices,
        default=InventoryModeChoices.MANUAL,
        help_text="Mode for populating inventory."
    )

    monitored_by = models.IntegerField(
        verbose_name="Monitored By",
        choices=MonitoredByChoices,
        default=MonitoredByChoices.ZabbixServer,
        help_text="Method used to monitor hosts."
    )

    tls_connect = models.IntegerField(
        verbose_name="TLS Connect",
        choices=TLSConnectChoices,
        default=TLSConnectChoices.PSK,
        help_text="TLS mode for outgoing connections."
    )

    tls_accept = models.IntegerField(
        verbose_name="TLS Accept",
        choices=TLSConnectChoices,
        default=TLSConnectChoices.PSK,
        help_text="TLS mode accepted for incoming connections."
    )

    tls_psk_identity = models.CharField(
        verbose_name="PSK Identity",
        max_length=255,
        null=True,
        blank=True,
        help_text="PSK identity."
    )

    tls_psk = models.CharField(
        verbose_name="TLS PSK",
        max_length=255,
        null=True,
        blank=True,
        help_text="Pre-shared key (at least 32 hex digits)."
    )

    # Tags

    default_tag = models.CharField(
        verbose_name="Default Tag",
        max_length=255,
        null=True,
        blank=True,
        help_text="Tag applied to all hosts."
    )
    
    tag_prefix = models.CharField(
        verbose_name="Tag Prefix",
        max_length=255,
        null=True,
        blank=True,
        help_text="Prefix added to all tags."
    )
    
    tag_name_formatting =  models.CharField( verbose_name="Tag Name Formatting", choices=TagNameFormattingChoices, default=TagNameFormattingChoices.KEEP, help_text="Tag name formatting.")
    

    def __str__(self):
        return self.name


    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:config", args=[self.pk])


    def save(self, *args, **kwargs):
        from netbox_zabbix import jobs
        super().save(*args, **kwargs)
        jobs.ImportZabbixSetting.run_job( interval=self.zabbix_sync_interval )

# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class Template(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Template"
        verbose_name_plural = "Zabbix Templates"
    
    name                = models.CharField( max_length=255 )
    templateid          = models.CharField( max_length=255 )
    last_synced         = models.DateTimeField( blank=True, null=True )
    marked_for_deletion = models.BooleanField( default=False )
     
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:template", args=[self.pk] )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------

class Proxy(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Proxy"
        verbose_name_plural = "Zabbix Proxies"
    
    name                = models.CharField( verbose_name="Proxy", max_length=255, help_text="Name of the proxy" )
    proxyid             = models.CharField( verbose_name="Proxy ID", max_length=255, help_text="Proxy ID")
    proxy_groupid       = models.CharField( verbose_name="Proxy Group ID", max_length=255 , help_text="Proxy Group ID")
    last_synced         = models.DateTimeField( blank=True, null=True )
    marked_for_deletion = models.BooleanField( default=False )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:proxy", args=[self.pk] )


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------

class ProxyGroup(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Proxy Group"
        verbose_name_plural = "Zabbix Proxy Groups"
    
    name                = models.CharField( verbose_name="Proxy Group", max_length=255, help_text="Name of the proxy group" )
    proxy_groupid       = models.CharField( verbose_name="Proxy Group ID", max_length=255, help_text="Proxy Group ID" )
    last_synced         = models.DateTimeField( blank=True, null=True )
    marked_for_deletion = models.BooleanField( default=False )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:proxygroup", args=[self.pk] )


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------

class HostGroup(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Hostgroup"
        verbose_name_plural = "Zabbix Hostgroups"
    
    name                = models.CharField( max_length=255 )
    groupid             = models.CharField( max_length=255 )
    last_synced         = models.DateTimeField( blank=True, null=True )
    marked_for_deletion = models.BooleanField( default=False )
    

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:hostgroup", args=[self.pk] )


# ------------------------------------------------------------------------------
# Zabbix Configs
# ------------------------------------------------------------------------------


class ZabbixConfig(NetBoxModel):
    class Meta:
        abstract = True

    hostid       = models.PositiveIntegerField( unique=True, blank=True, null=True, help_text="Zabbix Host ID." )
    status       = models.IntegerField( choices=StatusChoices.choices, default=StatusChoices.ENABLED, help_text="Host monitoring status." )
    host_groups  = models.ManyToManyField( HostGroup,  blank=True , help_text="Assigned Host Groups" )
    templates    = models.ManyToManyField( Template,   blank=True , help_text="Assgiend Tempalates" )
    monitored_by = models.IntegerField( choices=MonitoredByChoices, default=MonitoredByChoices.ZabbixServer, help_text="Monitoring source for the host" )
    proxy        = models.ForeignKey( Proxy, on_delete=models.CASCADE, blank=True, null=True, help_text="Assigned Proxy" )
    proxy_group  = models.ForeignKey( ProxyGroup, on_delete=models.CASCADE, blank=True, null=True, help_text="Assigned Proxy Group" )


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
# ------------------------------------------------------------------------------

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


class BaseAgentInterface(HostInterface):
    class Meta:
        abstract = True
    
    # Interface type
    type = models.IntegerField(choices=TypeChoices, default=TypeChoices.AGENT )

    # Port number used by the interface.
    port = models.IntegerField( default=10050 )
    
    def __str__(self):
        return f"{self.name}"
    
    def get_name(self):
        return f"{self.name}"


    def _get_primary_ip(self):
        """
        Return the primary IP from the host's device or VM, or None.
        """
        host = self.host
        if hasattr(host, "device") and host.device:
            return host.device.primary_ip4 or host.device.primary_ip6
        elif hasattr(host, "virtual_machine") and host.virtual_machine:
            return host.virtual_machine.primary_ip4 or host.virtual_machine.primary_ip6
        return None
    
    @property
    def resolved_dns_name(self):
        config = Config.objects.first()
        primary_ip = self._get_primary_ip()
        if config.ip_assignment_method == 'primary' and primary_ip == self.ip_address:
            primary_ip = self._get_primary_ip()
            return primary_ip.dns_name if primary_ip else None
        else:
            return self.ip_address.dns_name if self.ip_address else None
    
    @property
    def resolved_ip_address(self):
        config = Config.objects.first()
        primary_ip = self._get_primary_ip()

        if config.ip_assignment_method == 'primary' and primary_ip == self.ip_address:
            return self._get_primary_ip()
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


class BaseSNMPv3Interface(HostInterface):
    class Meta:
        abstract = True
    
    host = models.ForeignKey( to='DeviceZabbixConfig', on_delete=models.CASCADE, related_name='snmpv3_interfaces' )
    
    # Interface type
    type = models.IntegerField(choices=TypeChoices, default=TypeChoices.SNMP )
    
    # Port number used by the interface
    port = models.IntegerField( default=161 )
    
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
    
    def _get_primary_ip(self):
        """
        Return the primary IP from the host's device or VM, or None.
        """
        host = self.host
        if hasattr(host, "device") and host.device:
            return host.device.primary_ip4 or host.device.primary_ip6
        elif hasattr(host, "virtual_machine") and host.virtual_machine:
            return host.virtual_machine.primary_ip4 or host.virtual_machine.primary_ip6
        return None
    
    @property
    def resolved_dns_name(self):
        config = Config.objects.first()
        primary_ip = self._get_primary_ip()
        if config.ip_assignment_method == 'primary' and primary_ip == self.ip_address:
            primary_ip = self._get_primary_ip()
            return primary_ip.dns_name if primary_ip else None
        else:
            return self.ip_address.dns_name if self.ip_address else None
    
    @property
    def resolved_ip_address(self):
        config = Config.objects.first()
        primary_ip = self._get_primary_ip()
        if config.ip_assignment_method == 'primary' and primary_ip == self.ip_address:
            return self._get_primary_ip()
        else:
            return self.ip_address


class DeviceAgentInterface(BaseAgentInterface):
    class Meta:
        verbose_name = "Device Agent Interface"
        verbose_name_plural = "Device Agent Interfaces"
    
    # Reference to the Zabbix configuration object for the device this interface belongs to.
    host = models.ForeignKey( to="DeviceZabbixConfig", on_delete=models.CASCADE, related_name="agent_interfaces" )

    # The physical interface associated with this Agent configuration.
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, blank=True, null=True, related_name="agent_interface" )

    # IP address used by tahe interface. Can be empty if connection is made via DNS.
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="device_agent_interface" )


class DeviceSNMPv3Interface(BaseSNMPv3Interface):
    class Meta:
            verbose_name = "Device SNMPv3 Interface"
            verbose_name_plural = "Device SNMPv3 Interfaces"
    
    # Reference to the Zabbix configuration object for the device this interface belongs to.
    host = models.ForeignKey( to="DeviceZabbixConfig", on_delete=models.CASCADE, related_name="snmpv3_interfaces" )
    
    # The physical interface associated with this SNMPv3 configuration.
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, related_name="snmpv3_interface" )
    
    # IP address used by the interface. Can be empty if connection is made via DNS.
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="device_snmp3_interface" )


class VMAgentInterface(BaseAgentInterface):
    class Meta:
        verbose_name = "VM Agent Interface"
        verbose_name_plural = "VM Agent Interfaces"

    # Reference to the Zabbix configuration object for the virtual machine this interface belongs to.
    host = models.ForeignKey( to="VMZabbixConfig", on_delete=models.CASCADE, related_name="agent_interfaces" )

    # The interface associated with this Agent configuration.
    interface = models.OneToOneField( to="virtualization.VMInterface", on_delete=models.CASCADE, blank=True, null=True, related_name="agent_interface" )

    # IP address used by tahe interface. Can be empty if connection is made via DNS.
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="vm_agent_interface" )


class VMSNMPv3Interface(BaseSNMPv3Interface):
    class Meta:
        verbose_name = "VM SNMPv3 Interface"
        verbose_name_plural = "VM SNMPv3 Interfaces"

    # Reference to the Zabbix configuration object for the virtual machine this interface belongs to.
    host = models.ForeignKey( to="VMZabbixConfig", on_delete=models.CASCADE, related_name="snmpv3_interfaces" )

    # The interface associated with this SNMPv3 configuration.
    interface = models.OneToOneField( to="virtualization.VMInterface", on_delete=models.CASCADE, related_name="snmpv3_interface" )
    
    # IP address used by the interface. Can be empty if connection is made via DNS.
    ip_address = models.ForeignKey( to="ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="vm_snmp3_interface" )


# ------------------------------------------------------------------------------
# Interfaces Proxy Models
# ------------------------------------------------------------------------------

# Proxy model so that it is possible to register a ViewSet.
# The ViewSet is used to filter out interfaces that has already been assoicated
# with a Device interface. See api/views.py for details.

class AvailableDeviceInterface(Interface):
    class Meta:
        proxy = True

class AvailableVMInterface(VMInterface):
    class Meta:
        proxy = True


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------

class TagMapping(NetBoxModel):
    OBJECT_TYPE_CHOICES = [
        ('device', 'Device'),
        ('virtualmachine', 'Virtual Machine'),
    ]

    object_type = models.CharField( max_length=20, choices=OBJECT_TYPE_CHOICES, unique=True )
    selection = models.JSONField( default=list, help_text="List of field paths to use as Zabbix tags" )

    def __str__(self):
        return f"Tag Mapping {self.object_type}"
    
    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:tagmapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------

class InventoryMapping(NetBoxModel):
    OBJECT_TYPE_CHOICES = [
        ('device', 'Device'),
        ('virtualmachine', 'Virtual Machine'),
    ]

    object_type = models.CharField( max_length=20, choices=OBJECT_TYPE_CHOICES, unique=True )
    selection = models.JSONField( default=list, help_text="List of field paths to use as Zabbix inventory" )

    def __str__(self):
        return f"Inventory Mapping {self.object_type}"
    
    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:inventorymapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# Mapping Base Object
# ------------------------------------------------------------------------------

class Mapping(NetBoxModel):
    name = models.CharField( verbose_name="Name", max_length=255, help_text="Name of the mapping." )
    description = models.TextField( blank=True )
    default = models.BooleanField( default=False )

    # Configuration Settings
    host_groups = models.ManyToManyField( HostGroup, help_text="Host groups used for matching hosts." )
    templates   = models.ManyToManyField( Template, help_text="Templates used for matching hosts. Multiple templates can be selected." )
    proxy       = models.ForeignKey( Proxy, on_delete=models.CASCADE, null=True, help_text="Proxy for matching hosts." )
    proxy_group = models.ForeignKey( ProxyGroup, on_delete=models.CASCADE, null=True, help_text="Proxy group for matching hosts." )

    interface_type = models.IntegerField( verbose_name="Interface Type", choices=InterfaceTypeChoices, default=InterfaceTypeChoices.Any, help_text="Limit mapping to interfaces of this type. Select 'Any' to include all types." )
    
    # Filters
    sites     = models.ManyToManyField( Site, blank=True, help_text="Restrict mapping to hosts at these sites. Leave blank to apply to all sites." )
    roles     = models.ManyToManyField( DeviceRole, blank=True, help_text="Restrict mapping to hosts with these roles. Leave blank to include all roles." )
    platforms = models.ManyToManyField( Platform, blank=True, help_text="Restrict mapping to hosts running these platforms. Leave blank to include all platforms." )


    def delete(self, *args, **kwargs):
        if self.default == True:
            raise ValidationError( "Cannot delete default config" )
        super().delete(*args, **kwargs)


    def __str__(self):
        return self.name


    def get_absolute_url(self):
        # Return None or a placeholder URL; you could log this if needed
        return None

# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------

class DeviceMapping(Mapping):

    @classmethod
    def get_matching_filter(cls, device):
        filters = cls.objects.filter( default=False )
        matches = []
        for f in filters:
            if (
                (not f.sites.exists() or device.site in f.sites.all()) and
                (not f.roles.exists() or device.role in f.roles.all()) and
                (not f.platforms.exists() or device.platform in f.platforms.all())
            ):
                matches.append( f )
        if matches:
            # Return the most specific filter (most fields set)
            matches.sort( key=lambda f: (
                f.sites.count() > 0,
                f.roles.count() > 0,
                f.platforms.count() > 0
            ), reverse=True )
            return matches[0]
        # Fallback
        return cls.objects.get( default=True )


    def get_matching_devices(self):
    
        # Step 1: Start with all devices and apply current mapping's filters
        qs = Device.objects.all()
        if self.sites.exists():
            qs = qs.filter( site__in=self.sites.all() )
        if self.roles.exists():
            qs = qs.filter( role__in=self.roles.all() )
        if self.platforms.exists():
            qs = qs.filter( platform__in=self.platforms.all() )
    
        # Step 2: Define specificity count (how many fields are filtered)
        def count_fields(mapping):
            return sum([ mapping.sites.exists(), mapping.roles.exists(), mapping.platforms.exists() ])
    
        my_fields = count_fields(self)
    
        # Step 3: Get other, more specific mappings (more filters applied)
        more_specific_mappings = DeviceMapping.objects.exclude( pk=self.pk ).filter( default=False )
        more_specific_mappings = [m for m in more_specific_mappings if count_fields(m) > my_fields]
    
        # Step 4: A mapping is more specific if it filters at least as narrowly as self in all fields
        def is_more_specific(more_specific, current):
            for field in ['sites', 'roles', 'platforms']:
                current_ids  = set( getattr( current, field ).values_list( 'pk', flat=True ) )
                specific_ids = set( getattr( more_specific, field ).values_list( 'pk', flat=True ))
    
                # current matches all: allow anything in more_specific
                if not current_ids:
                    continue
    
                # more_specific must match at least everything current does
                if not specific_ids or not current_ids.issubset( specific_ids ):
                    return False
            return True
    
        # Step 5: Exclude devices matched by more specific mappings
        for m in more_specific_mappings:
            if is_more_specific( m, self ):
                qs = qs.exclude( pk__in=m.get_matching_devices().values_list( 'pk', flat=True ) )

        return qs
    

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:devicemapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------

class VMMapping(Mapping):

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:vmmapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------

class EventLog(NetBoxModel):
    name       = models.CharField( verbose_name="Name", max_length=256, help_text="Event name" )
    job       = models.ForeignKey( Job, on_delete=models.CASCADE, null=True, related_name='logs', help_text="Job reference." )
    message   = models.TextField( verbose_name="Message", blank=True, default="", help_text="Event message." )
    exception = models.TextField( verbose_name="Exception", blank=True, default="", help_text="Exception." )
    data      = models.JSONField( verbose_name="Data", null=True, blank=True, default=dict, help_text="Event data." )
    created   = models.DateTimeField( verbose_name="Created", auto_now_add=True )

    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
       return reverse( 'plugins:netbox_zabbix:eventlog', args=[self.pk] )

# end