# models.py
"""
NetBox Zabbix Plugin — Models

This module defines the data models used by the Zabbix plugin.
It includes configuration models, host mappings, templates, proxies,
and related inventory objects.

Models extend NetBox's core models and integrate with the
content type framework where needed.
"""

# Django imports
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.db import models
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


# NetBox imports
from dcim.models import Device, DeviceRole, Interface, Platform, Site
from ipam.models import IPAddress
from core.models import Job
from netbox.models import NetBoxModel
from netbox.models import JobsMixin
from virtualization.models.virtualmachines import VirtualMachine
from utilities.choices import ChoiceSet

# NetBox Zabbix plugin imports
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Choices
# ------------------------------------------------------------------------------


class IPAssignmentChoices(models.TextChoices):
    """
    Choices for assigning IP addresses to host interfaces.
    
    Attributes:
        MANUAL: IP assigned manually by user.
        PRIMARY: Use host's primary IPv4 address.
    """
    MANUAL  = "manual", "Manual"
    PRIMARY = "primary", "Primary IPv4 Address"


class MonitoredByChoices(models.IntegerChoices):
    """
    Defines the monitoring source for a host.
    
    Attributes:
        ZabbixServer: Monitored directly by Zabbix server.
        Proxy: Monitored via a Zabbix Proxy.
        ProxyGroup: Monitored via a group of proxies.
    """
    ZabbixServer = (0, 'Zabbix Server')
    Proxy        = (1, 'Proxy')
    ProxyGroup   = (2, 'Proxy Group')


class TLSConnectChoices(models.IntegerChoices):
    """
    TLS connection options for host communication.
    
    Attributes:
        NoEncryption: Do not use TLS.
        PSK: Use pre-shared key for TLS.
        CERTIFICATE: Use certificate-based TLS.
    """
    NoEncryption = (1, 'No Encryption')
    PSK          = (2, 'PSK')
    CERTIFICATE  = (4, 'Certificate')


class InventoryModeChoices(models.IntegerChoices):
    """
    Mode for populating inventory data.
    
    Attributes:
        DISABLED: Do not populate inventory.
        MANUAL: Populate inventory manually.
        AUTOMATIC: Populate inventory automatically.
    """
    DISABLED  = (-1, "Disabled")
    MANUAL    = (0, "Manual" )
    AUTOMATIC = (1, "Automatic" )


class TagNameFormattingChoices(models.TextChoices):
    """
    Formatting options for Zabbix tags.
    
    Attributes:
        KEEP: Keep tag names as entered.
        UPPER: Convert tag names to uppercase.
        LOWER: Convert tag names to lowercase.
    """
    KEEP  = "keep",  "Keep As Entered"
    UPPER = "upper", "Convert to Uppercase"
    LOWER = "lower", "Convert to Lowercase"


class DeleteSettingChoices(models.TextChoices):
    """
    Determines how hosts are deleted in Zabbix synchronization.
    
    Attributes:
        SOFT: Soft delete (move to graveyard).
        HARD: Hard delete (remove permanently).
    """
    SOFT  = "soft", "Soft Delete"
    HARD  = "hard", "Hard Delete"


class InterfaceTypeChoices(models.IntegerChoices):
    """
    Interface types for Zabbix templates and hosts.
    
    Attributes:
        Any: Any interface type.
        Agent: Zabbix agent interface.
        SNMP: SNMP interface.
    """
    Any   = (0, 'Any')
    Agent = (1, 'Agent')
    SNMP  = (2, 'SNMP')


class StatusChoices(models.IntegerChoices):
    """
    Status of a Zabbix host.
    
    Attributes:
        ENABLED: Host is enabled for monitoring.
        DISABLED: Host is disabled for monitoring.
    """
    ENABLED  = (0, 'Enabled')
    DISABLED = (1, 'Disabled')


class UseIPChoices(models.IntegerChoices):
    """
    Determines how host interfaces connect to Zabbix.
    
    Attributes:
        DNS: Use DNS name.
        IP: Use IP address.
    """
    DNS = (0, 'DNS Name')
    IP  = (1, 'IP Address')


class MainChoices(models.IntegerChoices):
    """
    Indicates whether an interface is the main/default interface.
    
    Attributes:
        NO: Not the main interface.
        YES: Main interface.
    """
    NO  = (0, 'No')
    YES = (1, 'Yes')


class TypeChoices(models.IntegerChoices):
    """
    Type of host interface.
    
    Attributes:
        AGENT: Agent interface.
        SNMP: SNMP interface.
    """
    AGENT = (1, 'Agent')
    SNMP =  (2, 'SNMP')


class SNMPVersionChoices(models.IntegerChoices):
    """
    SNMP protocol version for SNMP interfaces.
    
    Attributes:
        SNMPv1:  SNMPv1  (not implemented).
        SNMPv2c: SNMPv2c (not implemented).
        SNMPv3:  SNMPv3.
    """
    SNMPv1  = (1, 'SNMPv1')  # Not Implemented
    SNMPv2c = (2, 'SNMPv2c') # Not Implemented
    SNMPv3  = (3, 'SNMPv3')


class SNMPBulkChoices(models.IntegerChoices):
    """
    Whether to use SNMP bulk requests.
    
    Attributes:
        NO: Do not use bulk requests.
        YES: Use bulk requests.
    """
    NO  = (0, 'No')
    YES = (1, 'Yes')


class SNMPSecurityLevelChoices(models.IntegerChoices):
    """
    SNMPv3 security level.
    
    Attributes:
        noAuthNoPriv: No authentication, no privacy.
        authNoPriv: Authentication, no privacy.
        authPriv: Authentication with privacy.
    """
    noAuthNoPriv = (0, 'noAuthNoPriv')
    authNoPriv   = (1, 'authNoPriv')
    authPriv     = (2, 'authPriv')


class SNMPAuthProtocolChoices(models.IntegerChoices):
    """
    SNMPv3 authentication protocols.
    
    Attributes:
        MD5, SHA1, SHA224, SHA256, SHA384, SHA512
    """
    MD5    = (0, 'MD5')
    SHA1   = (1, 'SHA1')
    SHA224 = (2, 'SHA224')
    SHA256 = (3, 'SHA256')
    SHA384 = (4, 'SHA384')
    SHA512 = (5, 'SHA512')


class SNMPPrivProtocolChoices(models.IntegerChoices):
    """
    SNMPv3 privacy protocols.
    
    Attributes:
        DES, AES128, AES192, AES256, AES192C, AES256C
    """
    DES     = (0, 'DES')
    AES128  = (1, 'AES128')
    AES192  = (2, 'AES192')
    AES256  = (3, 'AES256')
    AES192C = (4, 'AES192C')
    AES256C = (5, 'AES256C')


class SyncJobIntervalChoices(ChoiceSet):
    """
    Available intervals (in minutes) for Zabbix sync jobs.
    
    Example:
        INTERVAL_HOURLY = 60
        INTERVAL_DAILY = 1440
    """
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


class HostSyncModeChoices(models.IntegerChoices):
    """
    Choices for controlling how NetBox synchronizes host configurations with Zabbix.

    Attributes:
        OVERWRITE: NetBox enforces exact configuration; it overwrites all host settings in Zabbix.
        PRESERVE: NetBox merges its configuration with existing Zabbix settings, preserving extra items.
    """
    OVERWRITE = 0, 'Overwrite'
    PRESERVE  = 1, 'Preserve'


# ------------------------------------------------------------------------------
# Setting
# ------------------------------------------------------------------------------


class Setting(NetBoxModel):
    """
    Stores global settings for the netbox-zabbix plugin.
    
    Attributes:
        name (str): Name of the setting.
        host_sync_mode(int): Overwrite or preserve Zabbix host settings.
        ip_assignment_method (str): Method to assign IPs to host interfaces.
        event_log_enabled (bool): Whether event logging is enabled.
        auto_validate_importables (bool): Automatically validate importable hosts.
        auto_validate_quick_add (bool): Automatically validate hosts eligible for quick add.
        max_deletions (int): Max deletions allowed during import.
        max_success_notifications (int): Max success notifications per job.
        zabbix_sync_interval (int): Interval in minutes for Zabbix sync jobs.
        version (str): Zabbix server version.
        api_endpoint (str): Zabbix API endpoint URL.
        web_address (str): Zabbix web interface URL.
        token (str): Zabbix API token.
        delete_setting (str): Soft or hard delete behavior.
        graveyard (str): Host group for soft-deleted hosts.
        useip(int): Connect via IP or DNS.
        inventory_mode (int): Inventory population mode.
        monitored_by (int): Monitoring method.
        tls_connect / tls_accept (int): TLS configuration for connections.
        agent_port / snmp_port (int): Default ports for agent and SNMP interfaces.
        tag_prefix / tag_name_formatting: Tagging settings.
    """
    class Meta:
        verbose_name = "Setting"
        verbose_name_plural = "Settings"

    # General
    name                      = models.CharField( verbose_name="Name", max_length=255, help_text="Name of the setting." )
    host_sync_mode            = models.PositiveIntegerField( verbose_name="Host Sync Mode",
                                                 choices=HostSyncModeChoices,
                                                 default=HostSyncModeChoices.OVERWRITE, 
                                                 help_text="Determines how NetBox synchronizes host configurations with Zabbix." )
    
    ip_assignment_method      = models.CharField(
        verbose_name="IP Assignment Method",
        max_length=16,
        choices=IPAssignmentChoices.choices,
        default=IPAssignmentChoices.PRIMARY,
        help_text="Method used to assign IPs to host interfaces."
    )
    event_log_enabled         = models.BooleanField( verbose_name="Event Log Enabled", default=False )
    auto_validate_importables = models.BooleanField( verbose_name="Validate Importables", default=False, 
                                                    help_text="When enabled, importable hosts are validated automatically." )
    auto_validate_quick_add   = models.BooleanField( verbose_name="Validate Quick Add", default=False, 
                                                    help_text="When enabled, hosts eligible for Quick Add are validated automatically." )


    # Background Job(s)
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
    zabbix_sync_interval      = models.PositiveIntegerField( verbose_name="Zabbix Sync Interval", null=True, blank=True, choices=SyncJobIntervalChoices, default=SyncJobIntervalChoices.INTERVAL_DAILY, help_text="Interval in minutes between each Zabbix sync. Must be at least 1 minute." )

    # Zabbix Server
    version                  = models.CharField( verbose_name="Version", max_length=255, null=True, blank=True )
    api_endpoint             = models.CharField( verbose_name="API Endpoint", max_length=255, help_text="URL to the Zabbix API endpoint." )
    web_address              = models.CharField( verbose_name="Web Address", max_length=255, help_text="URL to the Zabbix web interface." )
    token                    = models.CharField( verbose_name="Token", max_length=255, help_text="Zabbix access token." )
    
    connection               = models.BooleanField( verbose_name="Connection", default=False )
    last_checked_at          = models.DateTimeField( verbose_name="Last Checked At", null=True, blank=True )


    # Delete Setting
    delete_setting =  models.CharField( verbose_name="Delete Settings", choices=DeleteSettingChoices, default=DeleteSettingChoices.SOFT, help_text="Delete Settings.")

    graveyard = models.CharField(
        verbose_name="Host Group",
        max_length=255,
        null=True,
        blank=True,
        default="graveyard",
        help_text="Host Group 'graveyard' for soft deletes."
    )
    
    graveyard_suffix = models.CharField(
        verbose_name="Deleted host suffix",
        max_length=255,
        null=True,
        blank=True,
        default="_archived",
        help_text="Suffix for deleted hosts in the 'graveyard'."
    )
    
    # Additional Settings

    exclude_custom_field_name = models.CharField(
        verbose_name="Exclution Custom Field",
        max_length=255,
        null=True,
        blank=True,
        default="Exclude from Zabbix",
        help_text="If this custom field is set, the object will be excluded from Zabbix synchronization and from listings of devices and virtual machines in NetBox."
    )
    
    exclude_custom_field_enabled = models.BooleanField( verbose_name="Exclude Custom Field Enabled", default=False )
    

    # Common Defaults

    useip = models.IntegerField( verbose_name="Use IP", choices=UseIPChoices, default=UseIPChoices.IP, help_text="Connect via IP or DNS." )

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

    # Agent Specific Defaults
    agent_port = models.IntegerField( verbose_name="Port", default=10050, help_text="Agent default port." )

    # SNMP Specific Defaults
    snmp_port            = models.IntegerField( verbose_name="Port", default=161, help_text="SNMP default port." )
    snmp_bulk            = models.IntegerField( verbose_name="Bulk", choices=SNMPBulkChoices, default=SNMPBulkChoices.YES, help_text="Whether to use bulk SNMP requests." )
    snmp_max_repetitions = models.IntegerField( verbose_name="Max Repetitions", default=10, help_text="Max repetition value for native SNMP bulk requests." )
    snmp_contextname     = models.CharField( verbose_name="Context Name", max_length=255, null=True, blank=True, help_text="SNMP context name." )
    snmp_securityname    = models.CharField( verbose_name="Security Name", max_length=255, default="{$SNMPV3_USER}", help_text="SNMP security name." )
    snmp_securitylevel   = models.IntegerField( verbose_name="Security Level", choices=SNMPSecurityLevelChoices, default=SNMPSecurityLevelChoices.authPriv, help_text="SNMP security level." )
    snmp_authprotocol    = models.IntegerField( verbose_name="Authentication Protocol", choices=SNMPAuthProtocolChoices, default=SNMPAuthProtocolChoices.SHA1, help_text="SNMP authentication protocol." )
    snmp_authpassphrase  = models.CharField( verbose_name="Authentication Passphrase", max_length=255, default="{$SNMPV3_AUTHPASS}", help_text="SNMP authentication passphrase." )
    snmp_privprotocol    = models.IntegerField( verbose_name="Privacy Protocol", choices=SNMPPrivProtocolChoices, default=SNMPPrivProtocolChoices.AES128, help_text="SNMP privacy protocol." )
    snmp_privpassphrase  = models.CharField( verbose_name="Privacy Passphrase", max_length=255, default="{$SNMPV3_PRIVPASS}", help_text="SNMP privacy passphrase." )
    
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
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return self.name


    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:setting", args=[self.pk] )

    
    def save(self, *args, **kwargs):
        """
        Save the Setting instance to the database.
        
        This method currently does not implement additional logic beyond
        the standard model save behavior, but it can be overridden
        for future pre-save or post-save processing.
        
        Args:
            *args: Positional arguments passed to the model save method.
            **kwargs: Keyword arguments passed to the model save method.
        """
        super().save(*args, **kwargs)


# ------------------------------------------------------------------------------
# Template
# ------------------------------------------------------------------------------


class Template(NetBoxModel):
    """
    Represents a Zabbix template.
    
    Attributes:
        name (str): Template name.
        templateid (str): Template ID from Zabbix.
        last_synced (datetime): Last sync timestamp.
        parents (ManyToMany): Parent templates for dependency management.
        dependencies (ManyToMany): Trigger dependencies.
        interface_type (int): Required interface type (Any, Agent, SNMP).
    """
    class Meta:
        verbose_name = "Template"
        verbose_name_plural = "Templates"
    
    name        = models.CharField( max_length=255 )
    templateid  = models.CharField( max_length=255 )
    last_synced = models.DateTimeField( blank=True, null=True )

    # Self-referential many-to-many for template dependencies
    parents = models.ManyToManyField( "self", 
                                     symmetrical=False, 
                                     related_name="children", 
                                     blank=True )

    # Self-referential many-to-many for trigger dependencies
    dependencies = models.ManyToManyField( "self", 
                                          symmetrical=False, 
                                          related_name="dependents", 
                                          blank=True )

    # Required interface type for this template - 
    interface_type = models.IntegerField( choices=InterfaceTypeChoices.choices, default=InterfaceTypeChoices.Any )


    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return self.name


    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:template", args=[self.pk] )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class Proxy(NetBoxModel):
    """Represents a Zabbix Proxy for host monitoring."""
    class Meta:
        verbose_name = "Proxy"
        verbose_name_plural = "Proxies"
    
    name          = models.CharField( verbose_name="Proxy", max_length=255, help_text="Name of the proxy." )
    proxyid       = models.CharField( verbose_name="Proxy ID", max_length=255, help_text="Proxy ID.")
    proxy_groupid = models.CharField( verbose_name="Proxy Group ID", max_length=255 , help_text="Proxy Group ID.")
    last_synced   = models.DateTimeField( blank=True, null=True )

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return self.name

    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:proxy", args=[self.pk] )


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------


class ProxyGroup(NetBoxModel):
    """Represents a Zabbix Host Group."""
    class Meta:
        verbose_name = "Proxy Group"
        verbose_name_plural = "Proxy Groups"
    
    name          = models.CharField( verbose_name="Proxy Group", max_length=255, help_text="Name of the proxy group." )
    proxy_groupid = models.CharField( verbose_name="Proxy Group ID", max_length=255, help_text="Proxy Group ID." )
    last_synced   = models.DateTimeField( blank=True, null=True )

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return self.name

    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:proxygroup", args=[self.pk] )


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------


class HostGroup(NetBoxModel):
    """Represents a Zabbix Host Group."""
    class Meta:
        verbose_name = "Hostgroup"
        verbose_name_plural = "Hostgroups"
    
    name        = models.CharField( max_length=255 )
    groupid     = models.CharField( max_length=255 )
    last_synced = models.DateTimeField( blank=True, null=True )

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return self.name

    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:hostgroup", args=[self.pk] )


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMapping(NetBoxModel):
    """
    Maps NetBox object fields to Zabbix tags.
    
    Attributes:
        object_type (str): 'device' or 'virtualmachine'.
        selection (list): List of field paths used as Zabbix tags.
    """
    class Meta:
        verbose_name = "Tag Mapping"
        verbose_name_plural = "Tag Mappings"
    
    OBJECT_TYPE_CHOICES = [
        ('device', 'Device'),
        ('virtualmachine', 'Virtual Machine'),
    ]

    object_type = models.CharField( max_length=20, choices=OBJECT_TYPE_CHOICES, unique=True )
    selection   = models.JSONField( default=list, help_text="List of field paths to use as Zabbix tags" )

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return f"Tag Mapping {self.object_type}"
    
    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:tagmapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMapping(NetBoxModel):
    """
    Maps NetBox object fields to Zabbix inventory items.
    
    Attributes:
        object_type (str): 'device' or 'virtualmachine'.
        selection (list): List of field paths used for Zabbix inventory.
    """
    class Meta:
        verbose_name = "Inventory Mapping"
        verbose_name_plural = "Inventory Mappings"
    
    OBJECT_TYPE_CHOICES = [
        ('device', 'Device'),
        ('virtualmachine', 'Virtual Machine'),
    ]

    object_type = models.CharField( max_length=20, choices=OBJECT_TYPE_CHOICES, unique=True )
    selection   = models.JSONField( default=list, help_text="List of field paths to use as Zabbix inventory" )

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return f"Inventory Mapping {self.object_type}"
    
    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:inventorymapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# Mapping Base Object
# ------------------------------------------------------------------------------


class Mapping(NetBoxModel):
    """
    Base mapping for hosts, templates, proxies, and filters.
    
    Attributes:
        name (str): Name of the mapping.
        description (str): Optional description.
        default (bool): Whether this mapping is the default.
        host_groups / templates (ManyToMany): Host groups and templates to match.
        proxy / proxy_group: Optional proxy configuration.
        interface_type (int): Limit mapping to a specific interface type.
        sites / roles / platforms: Filters for hosts to which this mapping applies.
    """
    name        = models.CharField( verbose_name="Name", max_length=255, help_text="Name of the mapping." )
    description = models.TextField( blank=True )
    default     = models.BooleanField( default=False )

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
        """
        Delete this mapping instance from the database.
        
        Raises:
            ValidationError: If the mapping is marked as default, it cannot be deleted.
        """
        if self.default == True:
            raise ValidationError( "Cannot delete default config" )
        super().delete(*args, **kwargs)


    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return self.name


    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return None


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMapping(Mapping):
    """
    Mapping for Device objects.
    
    Methods:
        get_matching_filter(device, interface_type): Returns the most specific mapping matching a device.
        get_matching_devices(): Returns Devices matched by this mapping, excluding devices handled by more specific mappings.
    """
    class Meta:
        verbose_name = "Device Mapping"
        verbose_name_plural = "Device Mappings"
    

    @classmethod
    def get_matching_filter(cls, device, interface_type=InterfaceTypeChoices.Any):
        """
        Return the most specific DeviceMapping that matches a device.
        
        Args:
            device (Device): Device instance to match.
            interface_type (int): Interface type to filter by.
        
        Returns:
            DeviceMapping: Matching mapping object.
        """
        filters = cls.objects.filter( default=False )
        matches = []
        for f in filters:
            if f.interface_type == interface_type:
                if (
                    (not f.sites.exists() or device.site in f.sites.all()) and
                    (not f.roles.exists() or device.role in f.roles.all()) and
                    (not f.platforms.exists() or device.platform in f.platforms.all())
                ):
                    matches.append( f )
        if matches:
            # Return the most specific filter (most fields defined/set)
            matches.sort( key=lambda f: (
                f.sites.count() > 0,
                f.roles.count() > 0,
                f.platforms.count() > 0
            ), reverse=True )
            return matches[0]
        
        # Fallback return the default mapping
        return cls.objects.get( default=True )


    def get_matching_devices(self):
        """
        Return queryset of Devices that match this mapping,
        excluding devices already covered by more specific mappings.
        
        Returns:
            QuerySet: Matching Device instances.
        """
        def mapping_fields(mapping):
            """
            Extract relevant filter fields from a mapping instance.
            
            Args:
                mapping (Mapping): A mapping instance.
            
            Returns:
                dict: Dictionary containing sets of IDs for 'sites', 'roles', and 'platforms'.
            """
            return {
                "sites":     set( mapping.sites.values_list( "pk", flat=True ) ),
                "roles":     set( mapping.roles.values_list( "pk", flat=True ) ),
                "platforms": set( mapping.platforms.values_list( "pk", flat=True ) ),
            }
    
        def count_fields(fields):
            """
            Count the number of non-empty filter fields.
            
            Args:
                fields (dict): Dictionary of filter sets (e.g., 'sites', 'roles', 'platforms').
            
            Returns:
                int: Number of fields that are non-empty.
            """
            return sum( bool( v ) for v in fields.values() )
    
        # Step 1: Precompute related IDs for this mapping (self)
        self_fields = mapping_fields( self )
        my_specificity = count_fields( self_fields )
    
        # Step 2: Load candidate mappings (more specific mappings only)
        candidates = (
            DeviceMapping.objects.exclude( pk=self.pk )
            .filter( default=False )
            .prefetch_related( "sites", "roles", "platforms" )
        )
    
        candidate_fields = {m.pk: mapping_fields(m) for m in candidates}
    
        # Keep only mappings strictly more specific than this mapping (self)
        candidates = [
            m for m in candidates
            if count_fields( candidate_fields[m.pk] ) > my_specificity
        ]
    
        # Step 3: Helper to compare specificity
        def is_more_specific(more_specific_fields, current_fields):
            """
            Determine if one mapping is more specific than another.
            
            A mapping is considered more specific if it has filters for
            sites, roles, or platforms that include all of the current mapping's filters.
            
            Args:
                more_specific_fields (dict): Filter sets of the candidate mapping.
                current_fields (dict): Filter sets of the current mapping.
            
            Returns:
                bool: True if candidate mapping is more specific, False otherwise.
            """
            for field in ["sites", "roles", "platforms"]:
                current_ids = current_fields[field]
                specific_ids = more_specific_fields[field]
    
                # If the current mapping doesn’t have a filter for the field, it allows everything.
                # In that case, the more specific mapping is ignored.
                if not current_ids:
                    continue
    
                # If the current mapping does have a filter for the field, then the more 
                # specific mapping must include all of those same values. 
                # If not, the more specific mapping isn’t actually more specific than the current mapping.
                if not specific_ids or not current_ids.issubset( specific_ids ):
                    return False
    
            return True
    
        # Step 4: Precompute Device sets per mapping
        all_devices = Device.objects.all().only( "pk", "site_id", "role_id", "platform_id" )
    
        device_sets = {}
        for m in candidates:
            fields = candidate_fields[m.pk]
            device_qs = all_devices
            if fields["sites"]:
                device_qs = device_qs.filter( site_id__in=fields["sites"] )
            if fields["roles"]:
                device_qs = device_qs.filter( role_id__in=fields["roles"] )
            if fields["platforms"]:
                device_qs = device_qs.filter( platform_id__in=fields["platforms"] )
            device_sets[m.pk] = set( device_qs.values_list( "pk", flat=True ) )
    
        # Step 5: Exclude all Devices covered by more specific mappings
        exclude_ids = set()
        for m in candidates:
            if is_more_specific(candidate_fields[m.pk], self_fields):
                exclude_ids.update(device_sets[m.pk])
    
        # Step 6: Compute self’s Device
        qs = all_devices
        if self_fields["sites"]:
            qs = qs.filter(site_id__in=self_fields["sites"])
        if self_fields["roles"]:
            qs = qs.filter(role_id__in=self_fields["roles"])
        if self_fields["platforms"]:
            qs = qs.filter(platform_id__in=self_fields["platforms"])
    
        if exclude_ids:
            qs = qs.exclude(pk__in=exclude_ids)
    
        return qs


    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:devicemapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMapping(Mapping):
    """
    Mapping for VirtualMachine objects.
    
    Methods:
        get_matching_filter(virtual_machine, interface_type): Returns the most specific mapping for a VM.
        get_matching_virtual_machines(): Returns VMs matched by this mapping, excluding those handled by more specific mappings.
    """
    class Meta:
        verbose_name = "Virtual Machine Mapping"
        verbose_name_plural = "Virtual Machine Mappings"
    
    @classmethod
    def get_matching_filter(cls, virtual_machine, interface_type=InterfaceTypeChoices.Any):
        """
        Return the most specific VMMapping that matches a virtual machine.
        
        Args:
            virtual_machine (VirtualMachine): VM instance to match.
            interface_type (int): Interface type to filter by.
        
        Returns:
            VMMapping: Matching mapping object.
        """
        filters = cls.objects.filter( default=False )
        matches = []
        for f in filters:
            if f.interface_type == interface_type:
                if (
                    (not f.sites.exists() or virtual_machine.site in f.sites.all()) and
                    (not f.roles.exists() or virtual_machine.role in f.roles.all()) and
                    (not f.platforms.exists() or virtual_machine.platform in f.platforms.all())
                ):
                    matches.append( f )
        if matches:
            # Return the most specific filter (most field defined/set)
            matches.sort( key=lambda f: (
                f.sites.count() > 0,
                f.roles.count() > 0,
                f.platforms.count() > 0
            ), reverse=True )
            return matches[0]

        # Fallback return the default mapping
        return cls.obejcts.get( default=True )


    def get_matching_virtual_machines(self):
        """
        Return queryset of VirtualMachines that match this mapping,
        excluding VMs covered by more specific mappings.
        
        Returns:
            QuerySet: Matching VirtualMachine instances.
        """
        def mapping_fields(mapping):
            """
            Extract relevant filter fields from a VMMapping instance.
            
            Args:
                mapping (VMMapping): A VMMapping instance.
            
            Returns:
                dict: Dictionary containing sets of IDs for 'sites', 'roles', and 'platforms'.
            """
            return {
                "sites":     set( mapping.sites.values_list( "pk", flat=True ) ),
                "roles":     set( mapping.roles.values_list( "pk", flat=True ) ),
                "platforms": set( mapping.platforms.values_list( "pk", flat=True ) ),
            }
    
        def count_fields(fields):
            """
            Count the number of non-empty filter fields for VMMapping.
            
            Args:
                fields (dict): Dictionary of filter sets (e.g., 'sites', 'roles', 'platforms').
            
            Returns:
                int: Number of fields that are non-empty.
            """
            return sum( bool( v ) for v in fields.values() )
    
        # Step 1: Precompute related IDs for this mapping (self)
        self_fields = mapping_fields( self )
        my_specificity = count_fields( self_fields )
    
        # Step 2: Load candidate mappings (more specific mappings only)
        candidates = (
            VMMapping.objects.exclude( pk=self.pk )
            .filter( default=False )
            .prefetch_related( "sites", "roles", "platforms" )
        )
    
        candidate_fields = {m.pk: mapping_fields(m) for m in candidates}
    
        # Keep only mappings strictly more specific than this mapping (self)
        candidates = [
            m for m in candidates
            if count_fields( candidate_fields[m.pk] ) > my_specificity
        ]
    
        # Step 3: Helper to compare specificity
        def is_more_specific(more_specific_fields, current_fields):
            """
            Determine if one VM mapping is more specific than another.
            
            A VM mapping is considered more specific if it has filters for
            sites, roles, or platforms that include all of the current mapping's filters.
            
            Args:
                more_specific_fields (dict): Filter sets of the candidate VM mapping.
                current_fields (dict): Filter sets of the current VM mapping.
            
            Returns:
                bool: True if candidate VM mapping is more specific, False otherwise.
            """
            for field in ["sites", "roles", "platforms"]:
                current_ids = current_fields[field]
                specific_ids = more_specific_fields[field]
    
                # If the current mapping doesn’t have a filter for the field, it allows everything.
                # In that case, the more specific mapping is ignored.
                if not current_ids:
                    continue
    
                # If the current mapping does have a filter for the field, then the more 
                # specific mapping must include all of those same values. 
                # If not, the more specific mapping isn’t actually more specific than the current mapping.
                if not specific_ids or not current_ids.issubset( specific_ids ):
                    return False
    
            return True
    
        # Step 4: Precompute VM sets per mapping
        all_vms = VirtualMachine.objects.all().only( "pk", "site_id", "role_id", "platform_id" )
    
        vm_sets = {}
        for m in candidates:
            fields = candidate_fields[m.pk]
            vm_qs = all_vms
            if fields["sites"]:
                vm_qs = vm_qs.filter( site_id__in=fields["sites"] )
            if fields["roles"]:
                vm_qs = vm_qs.filter( role_id__in=fields["roles"] )
            if fields["platforms"]:
                vm_qs = vm_qs.filter( platform_id__in=fields["platforms"] )
            vm_sets[m.pk] = set( vm_qs.values_list( "pk", flat=True ) )
    
        # Step 5: Exclude all VMs covered by more specific mappings
        exclude_ids = set()
        for m in candidates:
            if is_more_specific(candidate_fields[m.pk], self_fields):
                exclude_ids.update(vm_sets[m.pk])
    
        # Step 6: Compute self’s VMs
        qs = all_vms
        if self_fields["sites"]:
            qs = qs.filter(site_id__in=self_fields["sites"])
        if self_fields["roles"]:
            qs = qs.filter(role_id__in=self_fields["roles"])
        if self_fields["platforms"]:
            qs = qs.filter(platform_id__in=self_fields["platforms"])
    
        if exclude_ids:
            qs = qs.exclude(pk__in=exclude_ids)
    
        return qs
    

    def get_absolute_url(self):
        """
        Return the canonical URL for this object within the plugin UI.
        This is used for linking to the object's detail page in NetBox.
        
        Returns:
            str: Absolute URL as a string. Can be None if not applicable.
        """
        return reverse( "plugins:netbox_zabbix:vmmapping", args=[self.pk] )


# ------------------------------------------------------------------------------
# Host Config
# ------------------------------------------------------------------------------


class HostConfig(NetBoxModel, JobsMixin):
    """
    Represents a host configuration in Zabbix.
    
    Attributes:
        name (str): Host name.
        hostid (int): Zabbix host ID.
        status (int): Host monitoring status.
        host_groups / templates: Assigned groups and templates.
        monitored_by (int): Monitoring source (server, proxy, etc.).
        proxy / proxy_group: Assigned proxies.
        content_type / object_id: Generic relation to Device or VirtualMachine.
    
    Properties:
        has_agent_interface: True if an AgentInterface exists.
        has_snmp_interface: True if an SNMPInterface exists.
    
    Methods:
        get_sync_status(): Check if the host is in sync with Zabbix.
        get_sync_diff(): Returns differences between NetBox and Zabbix.
    """
    class Meta:
        verbose_name = "Host Config"
        verbose_name_plural = "Host Configs"

    name            = models.CharField( max_length=200, unique=True, blank=True, null=True, help_text="Name for this host configuration." )
    hostid          = models.PositiveIntegerField( unique=True, blank=True, null=True, help_text="Zabbix Host ID." )
    status          = models.IntegerField( choices=StatusChoices.choices, default=StatusChoices.ENABLED, help_text="Host monitoring status." )
    host_groups     = models.ManyToManyField( HostGroup, help_text="Assigned Host Groups." )
    templates       = models.ManyToManyField( Template,  help_text="Assgiend Tempalates.", blank=True )
    monitored_by    = models.IntegerField( choices=MonitoredByChoices, default=MonitoredByChoices.ZabbixServer, help_text="Monitoring source for the host." )
    proxy           = models.ForeignKey( Proxy, on_delete=models.CASCADE, blank=True, null=True, help_text="Assigned Proxy." )
    proxy_group     = models.ForeignKey( ProxyGroup, on_delete=models.CASCADE, blank=True, null=True, help_text="Assigned Proxy Group." )
    description     = models.TextField( blank=True, null=True, help_text="Optional description." )
    content_type    = models.ForeignKey( ContentType, on_delete=models.CASCADE, limit_choices_to={ "model__in": ["device", "virtualmachine"] }, related_name="host_config")
    object_id       = models.PositiveIntegerField()
    assigned_object = GenericForeignKey( "content_type", "object_id" )


    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return f"{self.name}"


    @property
    def has_agent_interface(self):
        """Return True if this host has at least one AgentInterface assigned."""
        return self.agent_interfaces.exists()


    @property
    def has_snmp_interface(self):
        """Return True if this host has at least one SNMPInterface assigned."""
        return self.snmp_interfaces.exists()


    @property
    def zabbix_tags(self):
        """Return tags for this host configuration suitable for templates."""
        from netbox_zabbix.jobs import get_tags
        return get_tags( self.assigned_object )


    @property
    def active_maintenances(self):
        """
        Return all active Maintenance objects that include this HostConfig
        (either directly or indirectly through sites, host groups, proxy groups, or clusters).
        """
        from netbox_zabbix.models import Maintenance  # avoid circular import
        now = timezone.now()
    
        # Start with active maintenance windows
        maintenances = Maintenance.objects.filter(
            start_time__lte=now,
            end_time__gte=now
        )
    
        # Filter to those that include this host
        result = []
        for m in maintenances:
            if self in m.get_matching_host_configs():
                result.append(m)
        return result


    @property
    def in_maintenance(self):
        """Return True if this host is currently under any maintenance window."""
        return bool( self.active_maintenances )


    def get_sync_status(self):
        """
        Check if the host is in sync with Zabbix.
        
        Returns:
            bool: True if host differs from Zabbix configuration, False otherwise.
        """
        from netbox_zabbix.utils import compare_host_config_with_zabbix_host
        try:
            result = compare_host_config_with_zabbix_host( self )
            return result.get( "differ", False )
        except:
            return False


    def get_sync_icon(self):
          """
          Returns a checkmark or cross to indicate if the Host Config is in Sync with the Zabbix host.
          """
          return mark_safe('<span style="color:red;">✘</span>') if self.get_sync_status() else mark_safe('<span style="color:green;">✔</span>')


    def get_sync_diff(self):
        """
        Get differences between NetBox host and Zabbix host configuration.
        
        Returns:
            dict: JSON-like dictionary describing differences.
        """
        from netbox_zabbix.utils import compare_host_config_with_zabbix_host
        try:
            return compare_host_config_with_zabbix_host( self )
        except:
            return {}

    def save(self, *args, **kwargs):
        """
        Save the HostConfig instance to the database.
        
        If no name is provided, automatically generate one using the
        assigned object's name with a 'z-' prefix.
        
        Args:
            *args: Positional arguments passed to the model save method.
            **kwargs: Keyword arguments passed to the model save method.
        """
        # Add default name if no name is  provided
        if not self.name and self.assigned_object:
            self.name = f"z-{self.assigned_object.name}"
        super().save( *args, **kwargs )


# ------------------------------------------------------------------------------
# Base Interface
# ------------------------------------------------------------------------------


class BaseInterface(NetBoxModel):
    """
    Base class for Zabbix host interfaces (Agent or SNMP).
    
    Attributes:
        name (str): Interface name.
        hostid / interfaceid (int): IDs from Zabbix.
        useip (int): Use IP or DNS for connection.
        main (int): Whether this is the main interface.
    """
    class Meta:
        abstract = True
    
    # Name of the zabbix config interface in NetBox
    name = models.CharField( verbose_name="Name", max_length=255, blank=False, null=False, help_text="Name for the interface in NetBox." )

    # Zabbix Host ID - This is collected from Zabbix
    hostid = models.IntegerField( blank=True, null=True )

    # Zabbix Interface ID - This is collected from Zabbix
    interfaceid = models.IntegerField( blank=True, null=True )

    # Whether a connection to the monitoried 'host' should be made via IP or DNS.
    useip = models.IntegerField( verbose_name="Use IP", choices=UseIPChoices, default=UseIPChoices.IP, help_text="Whether the connection should be made via IP or DNS." )

    # Whether the interface is used as default on the host.
    # Only one interface of some type can be set as default on a host.
    main = models.IntegerField( verbose_name="Main Interface", choices=MainChoices, default=MainChoices.YES, help_text="Whether the interface is used as default on the host. Only one interface of some type can be set as default on a host." )

    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return f"{self.name}"
    

    def _get_primary_ip(self):
        """
        Return the primary IP from the host_config, or None if not available.
        
        Returns:
            IPAddress or None
        """
        if self.host_config.assigned_object:
            return self.host_config.assigned_object.primary_ip4
        return None
    

    @property
    def resolved_dns_name(self):
        """
        Return DNS name for this interface based on the plugin IP assignment method.
        
        Returns:
            str or None
        """
        setting = Setting.objects.first()
        primary_ip = self._get_primary_ip()
        if setting.ip_assignment_method == 'primary' and primary_ip == self.ip_address:
            primary_ip = self._get_primary_ip()
            return primary_ip.dns_name if primary_ip else None
        else:
            return self.ip_address.dns_name if self.ip_address else None

    @property
    def resolved_ip_address(self):
        """
        Return IP address for this interface based on the plugin IP assignment method.
        
        Returns:
            IPAddress or None
        """
        setting = Setting.objects.first()
        primary_ip = self._get_primary_ip()
        if setting.ip_assignment_method == 'primary' and primary_ip == self.ip_address:
            return self._get_primary_ip()
        else:
            return self.ip_address
    
    def clean(self):
        """
        Validate that the assigned IP address matches the interface.
        
        Raises:
            ValidationError: If IP does not belong to the selected interface.
        """
        super().clean()
    
        interface  = self.interface
        ip_address = self.ip_address
    
        # Validate interface/IP match
        if ip_address and interface:
            if ip_address.assigned_object != interface:
                raise ValidationError({ "ip_address": "The selected IP address is not assigned to the selected interface." })


# ------------------------------------------------------------------------------
# Agent Interface
# ------------------------------------------------------------------------------


class AgentInterface(BaseInterface):
    """Represents an agent interface linked to a HostConfig."""
    host_config    = models.ForeignKey( to="HostConfig", on_delete=models.CASCADE, related_name="agent_interfaces" )
    interface_type = models.ForeignKey( ContentType, on_delete=models.CASCADE, limit_choices_to={"model__in": ["interface", "vminterface"]} )
    interface_id   = models.PositiveIntegerField()
    interface      = GenericForeignKey( "interface_type", "interface_id" )
    ip_address     = models.ForeignKey( "ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="agent_interface" )

    # Interface type - The user doens't have to set this.
    type = models.IntegerField( choices=TypeChoices, default=TypeChoices.AGENT )
    
    # Port number used by the interface.
    port = models.IntegerField( default=10050, help_text="IP address used by the interface." )


    def save(self, *args, **kwargs):
        """
        Ensure only one main AgentInterface exists per host_config and validate the instance.
        
        Raises:
            ValidationError: If the model is invalid.
        """
        self.full_clean()

        # Ensure that only one agent interface at a time is the the main interface.
        if self.main == MainChoices.YES:
            existing_mains = self.host_config.agent_interfaces.filter( main=MainChoices.YES ).exclude( pk=self.pk )
            if existing_mains.exists():
                existing_mains.update( main=MainChoices.NO )

        return super().save(*args, **kwargs)


# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterface(BaseInterface):
    """Represents an SNMP interface linked to a HostConfig."""
    host_config    = models.ForeignKey( to="HostConfig", on_delete=models.CASCADE, related_name="snmp_interfaces" )
    interface_type = models.ForeignKey( ContentType, on_delete=models.CASCADE, limit_choices_to={"model__in": ["interface", "vminterface"]} )
    interface_id   = models.PositiveIntegerField()
    interface      = GenericForeignKey( "interface_type", "interface_id" )
    ip_address     = models.ForeignKey( "ipam.IPAddress", on_delete=models.SET_NULL, blank=True, null=True, related_name="snmp_interface" )

    # Interface type - The user doens't have to set this.
    type = models.IntegerField( choices=TypeChoices, default=TypeChoices.SNMP )
    
    # Port number used by the interface
    port = models.IntegerField( verbose_name="Port", default=161, help_text="IP address used by the interface." )
    
    # SNMP interface version - The user doesn't have to set this.
    version = models.IntegerField( choices=SNMPVersionChoices, default=SNMPVersionChoices.SNMPv3, blank=True, null=True )
    
    # Whether to use bulk SNMP requests
    bulk = models.IntegerField( verbose_name="Bulk", choices=SNMPBulkChoices, default=1, blank=True, null=True, help_text="Whether to use bulk SNMP requests." )
    
    # Max repetition value for native SNMP bulk requests
    max_repetitions = models.IntegerField( verbose_name="Max Repetitions", default=10, blank=True, null=True, help_text="Max repetition value for native SNMP bulk requests." )
    
    # SNMP context name.
    contextname = models.CharField( verbose_name="Contex Name", max_length=255, blank=True, null=True, help_text="SNMP context name." )
    
    # SNMP security name 
    securityname = models.CharField( verbose_name="Secuity Name", max_length=255, default="{$SNMPV3_USER}", blank=True, null=True, help_text="SNMP security name." )
    
    # SNMP Secuirty level
    securitylevel = models.IntegerField( verbose_name="Security Level", choices=SNMPSecurityLevelChoices, default=SNMPSecurityLevelChoices.authPriv, blank=True, null=True, help_text="SNMP security level." )
    
    # SNMP authentication protocol
    authprotocol = models.IntegerField( verbose_name="Authentication Protocol", choices=SNMPAuthProtocolChoices, default=SNMPAuthProtocolChoices.SHA1, blank=True, null=True, help_text="SNMP authentication protocol." )
    
    # SNMP authentication passphrase
    authpassphrase = models.CharField( verbose_name="Authentication Passphrase", max_length=255, default="{$SNMPV3_AUTHPASS}", blank=True, null=True, help_text="SNMP authentication passphrase." )
    
    # SNMP privacy protocol.
    privprotocol = models.IntegerField( verbose_name="Privacy Protocol", choices=SNMPPrivProtocolChoices, default=SNMPPrivProtocolChoices.AES128, blank=True, null=True, help_text="SNMP privacy protocol." )
    
    # SNMP privacy passphrase
    privpassphrase = models.CharField( verbose_name="Privacy Passphrase", max_length=255, default="{$SNMPV3_PRIVPASS}", blank=True, null=True, help_text="SNMP privacy passphrase."  )


    def save(self, *args, **kwargs):
        """
        Ensure only one main SNMPInterface exists per host_config and validate the instance.
        
        Raises:
            ValidationError: If the model is invalid.
        """
        self.full_clean()
    
        # Ensure that only one SNMP interface at a time is the the main interface.
        if self.main == MainChoices.YES:
            existing_mains = self.host_config.agent_interfaces.filter( main=MainChoices.YES ).exclude( pk=self.pk )
            if existing_mains.exists():
                existing_mains.update( main=MainChoices.NO )
    
        return super().save(*args, **kwargs)


# ------------------------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------------------------

from django.utils import timezone
from django.db.models import Q
from virtualization.models import Cluster


class Maintenance(NetBoxModel):
    """
    Represents a scheduled maintenance window for Zabbix hosts.

    This object defines a time period during which one or more hosts are put
    into maintenance mode in Zabbix. The maintenance can target hosts derived
    from Sites, HostGroups, ProxyGroups, or Clusters.

    Attributes:
        name (str): Name of the maintenance.
        description (str): Optional descriptive text.
        start_time (datetime): When maintenance begins.
        end_time (datetime): When maintenance ends.
        disable_data_collection (bool): If True, disables item collection during maintenance.
        host_config: (ManyToMany): Releated Host Configurtions that is part of the maintenance.
        sites (ManyToMany): Related Sites whose hosts will be included.
        host_groups (ManyToMany): Related Zabbix host groups.
        proxies (ManyToMany): Related Zabbix proxies.
        proxy_groups (ManyToMany): Related Zabbix proxy groups.
        clusters (ManyToMany): Related Clusters whose VMs will be included.
        zabbix_id (str): ID of the maintenance in Zabbix.
        status (str): Current lifecycle status (pending, active, expired).
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active',  'Active'),
        ('expired', 'Expired'),
        ('failed',  'Failed'),
    ]

    name       = models.CharField( max_length=200, help_text="Name of the maintenance window." )
    start_time = models.DateTimeField( default=timezone.now, help_text="Maintenence start time." )
    end_time   = models.DateTimeField( help_text="Maintenence end time.")

    disable_data_collection = models.BooleanField(
        default=False,
        help_text="Disable data collection in Zabbix during maintenance."
    )

    host_configs = models.ManyToManyField( HostConfig, blank=True, related_name="zabbix_maintenances", help_text="Host configurations that will be included in this maintenance." )
    sites        = models.ManyToManyField( Site, blank=True, related_name="zabbix_maintenances", help_text="Sites whose hosts will be included in this maintenance." )
    host_groups  = models.ManyToManyField( HostGroup, blank=True, related_name="zabbix_maintenances" , help_text="Host groups whose hosts will be included in this maintenance." )
    proxies      = models.ManyToManyField( Proxy, blank=True, related_name="zabbix_maintenances", help_text="Proxy whose hosts will be included in this maintenance." )
    proxy_groups = models.ManyToManyField( ProxyGroup, blank=True, related_name="zabbix_maintenances", help_text="Proxy groups whose hosts will be included in this maintenance." )
    clusters     = models.ManyToManyField( Cluster, blank=True, related_name="zabbix_maintenances", help_text="Clusters whose hosts will be included in this maintenance." )

    zabbix_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Unique maintenance ID assigned by Zabbix (if synchronized)."
    )

    status = models.CharField( max_length=20, choices=STATUS_CHOICES, default='pending', help_text="Current status of the maintenance (Pending, Active, Expired, or Failed)." )
    description = models.TextField( blank=True, help_text="Optional detailed description of the maintenance purpose or scope." )
    
    
    class Meta:
        verbose_name = "Zabbix Maintenance"
        verbose_name_plural = "Zabbix Maintenances"
        ordering = ['-start_time']

    def __str__(self):
        local_time = timezone.localtime(self.start_time)
        return f"{self.name} ({local_time:%Y-%m-%d %H:%M:%S})"


    @property
    def is_active(self):
        """Return True if the maintenance is currently active."""
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    @property
    def disable_data_collection_value(self):
        return  mark_safe('<span style="color:green;">✔</span>') if self.disable_data_collection else mark_safe('<span style="color:red;">✘</span>')

    def get_matching_host_configs(self):
        qs = HostConfig.objects.all()
        combined_filter = Q()
    
        if self.sites.exists():
            # Get ContentType objects for Device and VirtualMachine
            device_ct = ContentType.objects.get_for_model( Device )
            vm_ct = ContentType.objects.get_for_model( VirtualMachine )
    
            # Get PKs of devices and VMs in the selected sites
            device_pks = Device.objects.filter( site__in=self.sites.all() ).values_list( 'pk', flat=True )
            vm_pks = VirtualMachine.objects.filter( site__in=self.sites.all() ).values_list( 'pk', flat=True )
    
            site_filter = Q(
                content_type=device_ct,
                object_id__in=device_pks
            ) | Q(
                content_type=vm_ct,
                object_id__in=vm_pks
            )
    
            combined_filter &= site_filter
    
        if self.host_groups.exists():
            combined_filter |= Q( host_groups__in=self.host_groups.all() )
    
        if self.proxies.exists():
            combined_filter |= Q( proxy__in=self.proxies.all() )

        if self.proxy_groups.exists():
            combined_filter |= Q( proxy_group__in=self.proxy_groups.all() )

        if self.host_configs.exists():
            combined_filter |= Q( id__in=self.host_configs.all() )

        if self.clusters.exists():
            cluster_vms = VirtualMachine.objects.filter( cluster__in=self.clusters.all() ).values_list( 'pk', flat=True )
            vm_ct = ContentType.objects.get_for_model( VirtualMachine )
            
            cluster_filter = Q(
                content_type=vm_ct,
                object_id__in=cluster_vms
            )
            combined_filter |= cluster_filter

        if combined_filter:
            qs = qs.filter( combined_filter ).distinct()

        return qs




#    def sync_to_zabbix(self):
#        from netbox_zabbix.zabbix import create_maintenance, update_maintenance
#
#        hostids = [hc.hostid for hc in self.get_matching_host_configs() if hc.hostid]
#    
#        params = {
#            "name":          self.name,
#            "active_since":  int(self.start_time.timestamp()),
#            "active_till":   int(self.end_time.timestamp()),
#            "hostids":       hostids,
#            "description":   self.description or "",
#            "tags_evaltype": 0,
#            "timeperiods": [{
#                "timeperiod_type": 0,  # One-time only
#                "start_date":      int(self.start_time.timestamp()),
#                "period":          int((self.end_time - self.start_time).total_seconds())
#            }],
#        }
#    
#        if not hostids:
#            raise ValueError("No hosts found to include in maintenance window.")
#    
#        if self.zabbix_id:
#            
#            update_maintenance({ "maintenanceid": self.zabbix_id, **params })
#            self.status = "active"
#            logger.info( f"hostids {hostids}" )
#
#        else:
#            result = create_maintenance(params)
#            self.zabbix_id = result["maintenanceids"][0]
#            self.status = "active"
#    
#        super().save( update_fields=["zabbix_id", "status"] )
#
#
#    def save(self, *args, **kwargs):
#        super().save(*args, **kwargs)
#    
#        try:
#            self.sync_to_zabbix()
#        except Exception as e:
#            logger.exception(f"Failed to sync maintenance '{self.name}' to Zabbix: {e}")
#            self.status = "failed"
#            super().save(update_fields=["status"])
#
#
#    def delete(self, *args, **kwargs):
#        from netbox_zabbix.zabbix import delete_maintenance
#        if self.zabbix_id:
#            from netbox_zabbix.api import zabbix_api_client
#            try:
#                delete_maintenance( self.zabbix_id )
#            except Exception as e:
#                logger.warning(f"Failed to delete maintenance {self.name} ({self.zabbix_id}) from Zabbix: {e}")
#        super().delete(*args, **kwargs)


# ------------------------------------------------------------------------------
# Events
# ------------------------------------------------------------------------------


class EventLog(NetBoxModel):
    """
    Logs plugin events.
    
    Attributes:
        name (str): Event name.
        job (Job): Associated job.
        signal_id / message / exception / data / pre_data / post_data: Event details.
        created (datetime): Timestamp.
    
    Methods:
        get_job_status_color(): Returns a color code based on job status.
    """
    name      = models.CharField( verbose_name="Name", max_length=256, help_text="Event name." )
    job       = models.ForeignKey( Job, on_delete=models.CASCADE, null=True, related_name='logs', help_text="Job reference." )
    signal_id = models.TextField( verbose_name="Signal ID", blank=True, default="", help_text="Signal ID." )
    message   = models.TextField( verbose_name="Message", blank=True, default="", help_text="Event message." )
    exception = models.TextField( verbose_name="Exception", blank=True, default="", help_text="Exception." )
    data      = models.JSONField( verbose_name="Data", null=True, blank=True, default=dict, help_text="Event data." )
    pre_data  = models.JSONField( verbose_name="Pre-Change Data", null=True, blank=True, default=dict, help_text="Pre-change data." )
    post_data = models.JSONField( verbose_name="Post-Change Data", null=True, blank=True, default=dict, help_text="Post-change data." )
    
    created   = models.DateTimeField( verbose_name="Created", auto_now_add=True )

    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        """
        Return a human-readable string representation of the object.
        Typically returns the `name` field or another identifying attribute.
        
        Returns:
            str: Human-readable name of the object.
        """
        return f"{self.name}"

    def get_absolute_url(self):
       """
       Return the canonical URL for this object within the plugin UI.
       This is used for linking to the object's detail page in NetBox.
       
       Returns:
           str: Absolute URL as a string. Can be None if not applicable.
       """
       return reverse( 'plugins:netbox_zabbix:eventlog', args=[self.pk] )

    def get_job_status_color(self):
        """
        Return a color representing the status of the associated job.
        
        Returns:
            str: Hex color or name (e.g., 'red').
        """
        if self.job:
            return self.job.get_status_color()
        return 'red'


# ------------------------------------------------------------------------------
# PROXY MODELS
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Un-assgiend Hosts
# ------------------------------------------------------------------------------


class UnAssignedHosts(Device):
    """Proxy model for unassigned Device objects."""
    class Meta:
        proxy = True


# ------------------------------------------------------------------------------
# Un-assigned Agent Interfaces
# ------------------------------------------------------------------------------


class UnAssignedAgentInterfaces(Interface):
    """Proxy model for unassigned agent interfaces."""
    class Meta:
        proxy = True


# ------------------------------------------------------------------------------
# Un-assigned SNMP Interfaces
# ------------------------------------------------------------------------------


class UnAssignedSNMPInterfaces(Interface):
    """Proxy model for unassigned SNMP interfaces."""
    class Meta:
        proxy = True


# ------------------------------------------------------------------------------
# Un-assigned Host Interfaces
# ------------------------------------------------------------------------------


class UnAssignedHostInterfaces(Interface):
    """Proxy model for unassigned host interfaces."""
    class Meta:
        proxy = True


# ------------------------------------------------------------------------------
# Un-assigned Host IP  Addresses
# ------------------------------------------------------------------------------


class UnAssignedHostIPAddresses(IPAddress):
    """Proxy model for unassigned IP addresses."""
    class Meta:
        proxy = True




# end