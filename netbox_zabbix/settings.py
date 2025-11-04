"""
NetBox Zabbix Plugin — Configuration Utilities

This module provides helpers for retrieving and managing the Zabbix
Settings object stored in the database. It also defines related
custom exceptions and provides safe accessors for plugin code.
"""

# NetBox Zabbix plugin imports
from netbox_zabbix.models import Setting
from netbox_zabbix.logger import logger
from netbox_zabbix.models import (
    DeleteSettingChoices,
    MonitoredByChoices,
    InventoryModeChoices,
    TLSConnectChoices,
    SNMPBulkChoices,
    SNMPSecurityLevelChoices,
    SNMPAuthProtocolChoices,
    SNMPPrivProtocolChoices,
    TagNameFormattingChoices
)


# ------------------------------------------------------------------------------
# Custom exception definitions for Zabbix-related errors
# ------------------------------------------------------------------------------

class ZabbixSettingNotFound(Exception):
    """Raised when a required Zabbix setting is not present in the database."""
    pass


# ------------------------------------------------------------------------------
# Get Setting instance
# ------------------------------------------------------------------------------


def get_settings():
    """
    Retrieve the first Zabbix Settings object from the database.
    
    Raises:
        ZabbixSettingNotFound: If no setting is found.
    
    Returns:
        Setting: The Zabbix setting object.
    """
    setting = Setting.objects.first()
    if not setting:
        msg = "Missing Zabbix Configuration"
        logger.error( msg )
        raise ZabbixSettingNotFound( msg )
    return setting


def get_settings_safe(default=None):
    """
    Safely retrieve the first Zabbix Setting object from the database.
    If no Setting is found or an error occurs, the provided default value is returned instead.

    Args:
        default (Any, optional): Value to return if no setting is found or if a database error occurs.
    
    Returns:
        Setting | Any: The retrieved Setting object, or the default value if unavailable.
    """
    try:
        return Setting.objects.first() or default
    except Exception:
        logger.warning("Failed to retrieve Zabbix Setting from database")
        return default


def safe_setting(default=None):
    """
    Decorator that ensures safe access to Zabbix settings functions.
    
    Wraps a function so that it receives the current Setting instance, or a default
    value if the Setting is not available. This avoids repetitive exception handling.
    
    Args:
        default (Any, optional): Value returned when the Setting is missing.
    
    Returns:
        function: A decorator that wraps the target function.
    """
    def decorator(func):
        """
        Decorator function that wraps the target function to provide safe Settings access.
        
        Args:
            func (function): The function to wrap, which expects a Setting instance.
        
        Returns:
            function: A wrapped function that passes the current Setting or default value.
        """
        def wrapper(*args, **kwargs):
            """
            Wrapper function that executes the target function safely.
            
            Retrieves the current Setting instance via `get_settings_safe()`. If no
            Setting is available, returns the provided `default` value. Otherwise,
            calls the original function with the Setting instance.
            
            Args:
                *args: Positional arguments to pass to the wrapped function.
                **kwargs: Keyword arguments to pass to the wrapped function.
            
            Returns:
                Any: The result of the wrapped function, or the `default` value if
                Settings are missing.
            """
            s = get_settings_safe()
            if s is None:
                return default
            return func( s, *args, **kwargs )
        return wrapper
    return decorator


# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------


@safe_setting(False)
def get_auto_validate_importables(s):
    """
    Retrieve the current setting for automatic validation of importable devices and VMs.
    
    Returns:
        bool: True if automatic validation is enabled, False otherwise.
    """
    return s.auto_validate_importables


@safe_setting(False)
def get_auto_validate_quick_add(s):
    """
    Retrieve the current setting for automatic validation of quick add devices and VMs.
    
    Returns:
        bool: True if automatic validation is enabled, False otherwise.
    """
    return s.auto_validate_quick_add


@safe_setting(False)
def get_event_log_enabled(s):
    """
    Retrieves the event log enabled from the configuration.
    
    Returns:
        bool: True if the event log enabled, False otherwise.
    """
    return s.event_log_enabled


# ------------------------------------------------------------------------------
# Background Job(s)
# ------------------------------------------------------------------------------


@safe_setting(3)
def get_max_deletions(s):
    """
    Retrieves the max deletions from the configuration.

    Returns:
        The max deletions as specified in the configuration.
    """
    return s.max_deletions


@safe_setting(3)
def get_max_success_notifications(s):
    """
    Retrieves the max success notifications from the configuration.

    Returns:
        The max success notifications as specified in the configuration.
    """
    return s.max_success_notifications


# ------------------------------------------------------------------------------
# Zabbix Server
# ------------------------------------------------------------------------------


@safe_setting("")
def get_zabbix_api_endpoint(s):
    """
    Retrieve the Zabbix API endpoint from the configuration.
    
    Returns:
        str: The Zabbix API endpoint URL, or empty string if not set.
    """
    return s.api_endpoint


@safe_setting("")
def get_zabbix_web_address(s):
    """
    Retrieve the Zabbix web interface URL from the configuration.
    
    Returns:
        str: The Zabbix web interface URL, or empty string if not set.
    """
    return s.web_address


@safe_setting("")
def get_zabbix_token(s):
    """
    Retrieve the Zabbix API token from the configuration.
    
    Returns:
        str: The Zabbix API token, or empty string if not set.
    """
    return s.token


@safe_setting( "" )
def set_version( s, version ):
    """
    Update the stored Zabbix version in the configuration.
    
    Args:
        s (Setting): The Zabbix Setting object.
        version (str): The Zabbix version string to store.
    
    Returns:
        None
    """
    s.version = version
    s.save()


@safe_setting( False )
def set_connection( s, status ):
    """
    Update the connection status in the configuration.
    
    Args:
        s (Setting): The Zabbix Setting object.
        status (bool): True if connection is successful, False otherwise.
    
    Returns:
        None
    """
    s.connection = status
    s.save()


@safe_setting( None )
def set_last_checked( s, timestamp ):
    """
    Update the timestamp for the last successful configuration check.
    
    Args:
        s (Setting): The Zabbix Setting object.
        timestamp (datetime): A datetime object representing the check time.
    
    Returns:
        None
    """
    s.last_checked_at = timestamp
    s.save()



# ------------------------------------------------------------------------------
# Delete Settings
# ------------------------------------------------------------------------------


@safe_setting(DeleteSettingChoices.SOFT)
def get_delete_setting(s):
    """
    Retrieves the delete setting value from the configuration.
    
    Returns:
        The delete setting value as specified in the configuration.
    """
    return s.delete_setting


@safe_setting("graveyard")
def get_graveyard(s):
    """
    Retrieves the graveyard (host group) value from the configuration.
    
    Returns:
        The graveyard value as specified in the configuration.
    """
    return s.graveyard


@safe_setting("_archived")
def get_graveyard_suffix(s):
    """
    Retrieves the graveyard suffix value from the configuration.
    
    Returns:
        The graveyard suffix value as specified in the configuration.
    """
    return s.graveyard_suffix


# ------------------------------------------------------------------------------
# Additional Settings
# ------------------------------------------------------------------------------


@safe_setting("")
def get_exclude_custom_field_name(s):
    """
    Retrieves the exclude custom field name from the configuration.
    
    Returns:
        The exclude custom field name as specified in the configuration.
    """
    
    return s.exclude_custom_field_name


@safe_setting(False)
def get_exclude_custom_field_enabled(s):
    """
    Retrieves the exclude custom field enabled from the configuration.
    
    Returns:
        bool: True if exclude custom field is enabled is True, False otherwise.
    """
    
    
    return s.exclude_custom_field_enabled


# ------------------------------------------------------------------------------
# Common Defaults
# ------------------------------------------------------------------------------


@safe_setting(MonitoredByChoices.ZabbixServer)
def get_monitored_by(s):
    """
    Retrieves the default monitored_by value from the configuration.
    
    Returns:
        The default monitored_by value as specified in the configuration.
    """
    return s.monitored_by


@safe_setting(InventoryModeChoices.MANUAL)
def get_inventory_mode(s):
    """
    Retrieves the inventory mode from the configuration.

    Returns:
        The inventory mode as specified in the configuration.
    """
    return s.inventory_mode


@safe_setting(TLSConnectChoices.PSK)
def get_tls_connect(s):
    """
    Retrieves the default TLS connection type from the configuration.
    
    Returns:
        The default TLS connection type as specified in the configuration.
    """
    return s.tls_connect


@safe_setting(TLSConnectChoices.PSK)
def get_tls_accept(s):
    """
     Retrieves the default TLS accept type from the configuration.
    
     Returns:
         The default TLS accept type as specified in the configuration.
     """
    return s.tls_accept


@safe_setting("")
def get_tls_psk_identity(s):
    """
    Retrieves the default TLS PSK identity from the configuration.
    
    Returns:
        The default TLS PSK identity as specified in the configuration.
    """
    return s.tls_psk_identity


@safe_setting("")
def get_tls_psk(s):
    """
    Retrieves the default TLS PSK from the configuration.
    
    Returns:
        The default TLS PSK as specified in the configuration.
    """
    return s.tls_psk


# ------------------------------------------------------------------------------
# Agent Specific Defaults
# ------------------------------------------------------------------------------


@safe_setting(10050)
def get_agent_port(s):
    """
    Retrieves the default agent port from the configuration.
    
    Returns:
        The default agent port as specified in the configuration.
    """
    return s.agent_port


# ------------------------------------------------------------------------------
# SNMP Specific Defaults
# ------------------------------------------------------------------------------


@safe_setting(161)
def get_snmp_port(s):
    """
    Retrieves the default snmp port from the configuration.
    
    Returns:
        The default snmp port as specified in the configuration.
    """
    return s.snmp_port


@safe_setting(SNMPBulkChoices.YES)
def get_snmp_bulk(s):
    """
    Retrieves the default snmp bulk from the configuration.
    
    Returns:
        The default snmp bulk as specified in the configuration.
    """
    return s.snmp_bulk


@safe_setting(10)
def get_snmp_max_repetitions(s):
    """
    Retrieves the default snmp max_repetitions from the configuration.
    
    Returns:
        The default snmp max_repetitions as specified in the configuration.
    """
    return s.snmp_max_repetitions


@safe_setting("")
def get_snmp_contextname(s):
    """
    Retrieves the default snmp context name from the configuration.
    
    Returns:
        The default snmp context name as specified in the configuration.
    """
    return s.snmp_contextname


@safe_setting("{$SNMPV3_USER}")
def get_snmp_securityname(s):
    """
    Retrieves the default snmp security name from the configuration.
    
    Returns:
        The default snmp security name as specified in the configuration.
    """
    return s.snmp_securityname


@safe_setting(SNMPSecurityLevelChoices.authPriv)
def get_snmp_securitylevel(s):
    """
    Retrieves the default snmp security level from the configuration.
    
    Returns:
        The default snmp security level as specified in the configuration.
    """
    return s.snmp_securitylevel


@safe_setting(SNMPAuthProtocolChoices.SHA1)
def get_snmp_authprotocol(s):
    """
    Retrieves the default snmp auth protocol from the configuration.
    
    Returns:
        The default snmp auth protocol as specified in the configuration.
    """
    return s.snmp_authprotocol


@safe_setting("{$SNMPV3_AUTHPASS}")
def get_snmp_authpassphrase(s):
    """
    Retrieves the default snmp auth passphrase from the configuration.
    
    Returns:
        The default snmp auth passphrase as specified in the configuration.
    """
    return s.snmp_authpassphrase


@safe_setting(SNMPPrivProtocolChoices.AES128)
def get_snmp_privprotocol(s):
    """
    Retrieves the default snmp priv protocol from the configuration.
    
    Returns:
        The default snmp priv protocol as specified in the configuration.
    """
    return s.snmp_privprotocol


@safe_setting("{$SNMPV3_PRIVPASS}")
def get_snmp_privpassphrase(s):
    """
    Retrieves the default snmp priv passphrase from the configuration.
    
    Returns:
        The default snmp priv passphrase as specified in the configuration.
    """
    return s.snmp_privpassphrase


# ------------------------------------------------------------------------------
# Tags
# ------------------------------------------------------------------------------


@safe_setting("")
def get_default_tag(s):
    """
    Retrieves the default tag from the configuration.
    
    Returns:
        The default tag as specified in the configuration.
    """
    return s.default_tag


@safe_setting("")
def get_tag_prefix(s):
    """
    Retrieves the tag prefix from the configuration.
    
    Returns:
        The tag prefix as specified in the configuration.
    """
    return s.tag_prefix


@safe_setting(TagNameFormattingChoices.KEEP)
def get_tag_name_formatting(s):
    """
    Retrieves the tag name formatting from the configuration.
    
    Returns:
        The tag name formatting as specified in the configuration.
    """
    return s.tag_name_formatting

