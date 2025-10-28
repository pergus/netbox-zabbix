# config.py

from netbox_zabbix.models import Setting
from netbox_zabbix.logger import logger

class ZabbixSettingNotFound(Exception):
    """Raised when a required Zabbix setting is not present in the database."""
    pass


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


# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------


def get_auto_validate_importables():
    """
    Retrieve the current setting for automatic validation of importable devices and VMs.
    
    Returns:
        bool: True if automatic validation is enabled; False otherwise.
    """
    return get_settings().auto_validate_importables


def get_auto_validate_quick_add():
    """
    Retrieve the current setting for automatic validation of quick add devices and VMs.
    
    Returns:
        bool: True if automatic validation is enabled; False otherwise.
    """
    return get_settings().auto_validate_quick_add


def get_event_log_enabled():
    """
    Retrieves the event log enabled from the configuration.
    
    Returns:
        The event log enabled as specified in the configuration.
    """

    return get_settings().event_log_enabled


# ------------------------------------------------------------------------------
# Background Job(s)
# ------------------------------------------------------------------------------


def get_max_deletions():
    """
    Retrieves the max deletions from the configuration.

    Returns:
        The max deletions as specified in the configuration.
    """
    return get_settings().max_deletions


def get_max_success_notifications():
    """
    Retrieves the max success notifications from the configuration.

    Returns:
        The max success notifications as specified in the configuration.
    """
    return get_settings().max_success_notifications


# ------------------------------------------------------------------------------
# Zabbix Server
# ------------------------------------------------------------------------------


def get_zabbix_api_endpoint():
    """
    Retrieve the Zabbix API endpoint from the configuration.
    
    Returns:
        str: The Zabbix API endpoint URL.
    """
    return get_settings().api_endpoint


def get_zabbix_web_address():
    """
    Retrieve the Zabbix web interface URL from the configuration.
    
    Returns:
        str: The Zabbix web interface URL.
    """
    return get_settings().web_address


def get_zabbix_token():
    """
    Retrieve the Zabbix API token from the configuration.
    
    Returns:
        str: The Zabbix API token.
    """
    return get_settings().token


def set_version( version ):
    """
    Update the stored Zabbix version in the configuration.
    
    Args:
        version (str): The Zabbix version string to store.
    """
    cfg = get_settings()
    cfg.version = version
    cfg.save()


def set_connection( status ):
    """
    Update the connection status in the configuration.
    
    Args:
        status (bool): True if connection is successful, False otherwise.
    """
    cfg = get_settings()
    cfg.connection = status
    cfg.save()


def set_last_checked( timestamp ):
    """
    Update the timestamp for the last successful configuration check.
    
    Args:
        timestamp (datetime): A datetime object representing the check time.
    """    
    cfg = get_settings()
    cfg.last_checked_at = timestamp
    cfg.save()


# ------------------------------------------------------------------------------
# Delete Settings
# ------------------------------------------------------------------------------


def get_delete_setting():
    """
    Retrieves the delete setting value from the configuration.
    
    Returns:
        The delete setting value as specified in the configuration.
    """
    return get_settings().delete_setting


def get_graveyard():
    """
    Retrieves the graveyard (host group) value from the configuration.
    
    Returns:
        The graveyard value as specified in the configuration.
    """
    return get_settings().graveyard


def get_graveyard_suffix():
    """
    Retrieves the graveyard suffix value from the configuration.
    
    Returns:
        The graveyard suffix value as specified in the configuration.
    """
    return get_settings().graveyard_suffix


# ------------------------------------------------------------------------------
# Additional Settings
# ------------------------------------------------------------------------------

def get_exclude_custom_field_name():
    """
    Retrieves the exclude custom field name from the configuration.
    
    Returns:
        The exclude custom field name as specified in the configuration.
    """
    
    return get_settings().exclude_custom_field_name


def get_exclude_custom_field_enabled():
    """
    Retrieves the exclude custom field enabled from the configuration.
    
    Returns:
        The exclude custom field enabled as specified in the configuration.
    """
    
    return get_settings().exclude_custom_field_enabled


# ------------------------------------------------------------------------------
# Common Defaults
# ------------------------------------------------------------------------------


def get_monitored_by():
    """
    Retrieves the default monitored_by value from the configuration.
    
    Returns:
        The default monitored_by value as specified in the configuration.
    """
    return get_settings().monitored_by


def get_inventory_mode():
    """
    Retrieves the inventory mode from the configuration.

    Returns:
        The inventory mode as specified in the configuration.
    """
    return get_settings().inventory_mode


def get_tls_connect():
    """
    Retrieves the default TLS connection type from the configuration.
    
    Returns:
        The default TLS connection type as specified in the configuration.
    """
    return get_settings().tls_connect


def get_tls_accept():
    """
     Retrieves the default TLS accept type from the configuration.
    
     Returns:
         The default TLS accept type as specified in the configuration.
     """
    return get_settings().tls_accept


def get_tls_psk_identity():
    """
    Retrieves the default TLS PSK identity from the configuration.
    
    Returns:
        The default TLS PSK identity as specified in the configuration.
    """
    return get_settings().tls_psk_identity


def get_tls_psk():
    """
    Retrieves the default TLS PSK from the configuration.
    
    Returns:
        The default TLS PSK as specified in the configuration.
    """
    return get_settings().tls_psk


# ------------------------------------------------------------------------------
# Agent Specific Defaults
# ------------------------------------------------------------------------------


def get_agent_port():
    """
    Retrieves the default agent port from the configuration.
    
    Returns:
        The default agent port as specified in the configuration.
    """
    return get_settings().agent_port


# ------------------------------------------------------------------------------
# SNMP Specific Defaults
# ------------------------------------------------------------------------------

def get_snmp_port():
    """
    Retrieves the default snmp port from the configuration.
    
    Returns:
        The default snmp port as specified in the configuration.
    """
    return get_settings().snmp_port


def get_snmp_bulk():
    """
    Retrieves the default snmp bulk from the configuration.
    
    Returns:
        The default snmp bulk as specified in the configuration.
    """
    return get_settings().snmp_bulk


def get_snmp_max_repetitions():
    """
    Retrieves the default snmp max_repetitions from the configuration.
    
    Returns:
        The default snmp max_repetitions as specified in the configuration.
    """
    return get_settings().snmp_max_repetitions


def get_snmp_contextname():
    """
    Retrieves the default snmp context name from the configuration.
    
    Returns:
        The default snmp context name as specified in the configuration.
    """
    return get_settings().snmp_contextname


def get_snmp_securityname():
    """
    Retrieves the default snmp security name from the configuration.
    
    Returns:
        The default snmp security name as specified in the configuration.
    """
    return get_settings().snmp_securityname


def get_snmp_securitylevel():
    """
    Retrieves the default snmp security level from the configuration.
    
    Returns:
        The default snmp security level as specified in the configuration.
    """
    return get_settings().snmp_securitylevel


def get_snmp_authprotocol():
    """
    Retrieves the default snmp auth protocol from the configuration.
    
    Returns:
        The default snmp auth protocol as specified in the configuration.
    """
    return get_settings().snmp_authprotocol


def get_snmp_authpassphrase():
    """
    Retrieves the default snmp auth passphrase from the configuration.
    
    Returns:
        The default snmp auth passphrase as specified in the configuration.
    """
    return get_settings().snmp_authpassphrase


def get_snmp_privprotocol():
    """
    Retrieves the default snmp priv protocol from the configuration.
    
    Returns:
        The default snmp priv protocol as specified in the configuration.
    """
    return get_settings().snmp_privprotocol


def get_snmp_privpassphrase():
    """
    Retrieves the default snmp priv passphrase from the configuration.
    
    Returns:
        The default snmp priv passphrase as specified in the configuration.
    """
    return get_settings().snmp_privpassphrase


# ------------------------------------------------------------------------------
# Tags
# ------------------------------------------------------------------------------


def get_default_tag():
    """
    Retrieves the default tag from the configuration.
    
    Returns:
        The default tag as specified in the configuration.
    """
    return get_settings().default_tag or ""


def get_tag_prefix():
    """
    Retrieves the tag prefix from the configuration.
    
    Returns:
        The tag prefix as specified in the configuration.
    """
    prefix = get_settings().tag_prefix
    return prefix or ""


def get_tag_name_formatting():
    """
    Retrieves the tag name formatting from the configuration.
    
    Returns:
        The tag name formatting as specified in the configuration.
    """
    return get_settings().tag_name_formatting

