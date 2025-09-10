# config.py
from netbox_zabbix.models import Config
from netbox_zabbix.logger import logger

class ZabbixConfigNotFound(Exception):
    """Raised when the required Zabbix configuration is not present in the database."""
    pass


def get_config():
    """
    Retrieve the first Zabbix Config object from the database.
    
    Raises:
        ZabbixConfigNotFound: If no configuration is found.
    
    Returns:
        Config: The Zabbix configuration object.
    """
    cfg = Config.objects.first()
    if not cfg:
        msg = "Missing Zabbix Configuration"
        logger.error( msg )
        raise ZabbixConfigNotFound( msg )
    return cfg


# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------


def get_auto_validate_importables():
    """
    Retrieve the current setting for automatic validation of importable devices and VMs.
    
    Returns:
        bool: True if automatic validation is enabled; False otherwise.
    """
    return get_config().auto_validate_importables


def get_event_log_enabled():
    """
    Retrieves the event log enabled  from the configuration.
    
    Returns:
        The event log enabled as specified in the configuration.
    """

    return get_config().event_log_enabled


# ------------------------------------------------------------------------------
# Background Job(s)
# ------------------------------------------------------------------------------


def get_max_deletions():
    """
    Retrieves the max deletions from the configuration.

    Returns:
        The max deletions as specified in the configuration.
    """
    return get_config().max_deletions


def get_max_success_notifications():
    """
    Retrieves the max success notifications from the configuration.

    Returns:
        The max success notifications as specified in the configuration.
    """
    return get_config().max_success_notifications


# ------------------------------------------------------------------------------
# Zabbix Server
# ------------------------------------------------------------------------------


def get_zabbix_api_endpoint():
    """
    Retrieve the Zabbix API endpoint from the configuration.
    
    Returns:
        str: The Zabbix API endpoint URL.
    """
    return get_config().api_endpoint


def get_zabbix_web_address():
    """
    Retrieve the Zabbix web interface URL from the configuration.
    
    Returns:
        str: The Zabbix web interface URL.
    """
    return get_config().web_address


def get_zabbix_token():
    """
    Retrieve the Zabbix API token from the configuration.
    
    Returns:
        str: The Zabbix API token.
    """
    return get_config().token


def get_default_cidr():
    """
    Retrieve the default CIDR suffix configured for Zabbix interface IP lookups.
    
    This value is used to append a CIDR (e.g., /24) to Zabbix IP addresses
    when querying NetBox for matching IP addresses, since NetBox requires CIDR notation.
    
    Returns:
        str: The default CIDR suffix (e.g., '/24')
    """
    return get_config().default_cidr


def set_version( version ):
    """
    Update the stored Zabbix version in the configuration.
    
    Args:
        version (str): The Zabbix version string to store.
    """
    cfg = get_config()
    cfg.version = version
    cfg.save()


def set_connection( status ):
    """
    Update the connection status in the configuration.
    
    Args:
        status (bool): True if connection is successful, False otherwise.
    """
    cfg = get_config()
    cfg.connection = status
    cfg.save()


def set_last_checked( timestamp ):
    """
    Update the timestamp for the last successful configuration check.
    
    Args:
        timestamp (datetime): A datetime object representing the check time.
    """    
    cfg = get_config()
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
    return get_config().delete_setting


def get_graveyard():
    """
    Retrieves the graveyard (host group) value from the configuration.
    
    Returns:
        The graveyard value as specified in the configuration.
    """
    return get_config().graveyard


def get_graveyard_suffix():
    """
    Retrieves the graveyard suffix value from the configuration.
    
    Returns:
        The graveyard suffix value as specified in the configuration.
    """
    return get_config().graveyard_suffix



# ------------------------------------------------------------------------------
# Common Defaults
# ------------------------------------------------------------------------------


def get_monitored_by():
    """
    Retrieves the default monitored_by value from the configuration.
    
    Returns:
        The default monitored_by value as specified in the configuration.
    """
    return get_config().monitored_by


def get_inventory_mode():
    """
    Retrieves the inventory mode from the configuration.

    Returns:
        The inventory mode as specified in the configuration.
    """
    return get_config().inventory_mode


def get_tls_connect():
    """
    Retrieves the default TLS connection type from the configuration.
    
    Returns:
        The default TLS connection type as specified in the configuration.
    """
    return get_config().tls_connect


def get_tls_accept():
    """
     Retrieves the default TLS accept type from the configuration.
    
     Returns:
         The default TLS accept type as specified in the configuration.
     """
    return get_config().tls_accept


def get_tls_psk_identity():
    """
    Retrieves the default TLS PSK identity from the configuration.
    
    Returns:
        The default TLS PSK identity as specified in the configuration.
    """
    return get_config().tls_psk_identity


def get_tls_psk():
    """
    Retrieves the default TLS PSK from the configuration.
    
    Returns:
        The default TLS PSK as specified in the configuration.
    """
    return get_config().tls_psk


# ------------------------------------------------------------------------------
# Agent Specific Defaults
# ------------------------------------------------------------------------------

def get_agent_port():
    """
    Retrieves the default agent port from the configuration.
    
    Returns:
        The default agent port as specified in the configuration.
    """
    return get_config().agent_port
    

# ------------------------------------------------------------------------------
# SNMPv3 Specific Defaults
# ------------------------------------------------------------------------------

def get_snmpv3_port():
    """
    Retrieves the default snmpv3 port from the configuration.
    
    Returns:
        The default snmpv3 port as specified in the configuration.
    """
    return get_config().snmpv3_port


def get_snmpv3_bulk():
    """
    Retrieves the default snmpv3 bulk from the configuration.
    
    Returns:
        The default snmpv3 bulk as specified in the configuration.
    """
    return get_config().snmpv3_bulk


def get_snmpv3_max_repetitions():
    """
    Retrieves the default snmpv3 max_repetitions from the configuration.
    
    Returns:
        The default snmpv3 max_repetitions as specified in the configuration.
    """
    return get_config().snmpv3_max_repetitions


def get_snmpv3_contextname():
    """
    Retrieves the default snmpv3 context name from the configuration.
    
    Returns:
        The default snmpv3 context name as specified in the configuration.
    """
    return get_config().snmpv3_contextname


def get_snmpv3_securityname():
    """
    Retrieves the default snmpv3 security name from the configuration.
    
    Returns:
        The default snmpv3 security name as specified in the configuration.
    """
    return get_config().snmpv3_securityname


def get_snmpv3_securitylevel():
    """
    Retrieves the default snmpv3 security level from the configuration.
    
    Returns:
        The default snmpv3 security level as specified in the configuration.
    """
    return get_config().snmpv3_securitylevel


def get_snmpv3_authprotocol():
    """
    Retrieves the default snmpv3 auth protocol from the configuration.
    
    Returns:
        The default snmpv3 auth protocol as specified in the configuration.
    """
    return get_config().snmpv3_authprotocol


def get_snmpv3_authpassphrase():
    """
    Retrieves the default snmpv3 auth passphrase from the configuration.
    
    Returns:
        The default snmpv3 auth passphrase as specified in the configuration.
    """
    return get_config().snmpv3_authpassphrase


def get_snmpv3_privprotocol():
    """
    Retrieves the default snmpv3 priv protocol from the configuration.
    
    Returns:
        The default snmpv3 priv protocol as specified in the configuration.
    """
    return get_config().snmpv3_privprotocol


def get_snmpv3_privpassphrase():
    """
    Retrieves the default snmpv3 priv passphrase from the configuration.
    
    Returns:
        The default snmpv3 priv passphrase as specified in the configuration.
    """
    return get_config().snmpv3_privpassphrase


# ------------------------------------------------------------------------------
# Tags
# ------------------------------------------------------------------------------


def get_default_tag():
    """
    Retrieves the default tag from the configuration.
    
    Returns:
        The default tag as specified in the configuration.
    """
    return get_config().default_tag or ""


def get_tag_prefix():
    """
    Retrieves the tag prefix from the configuration.
    
    Returns:
        The tag prefix as specified in the configuration.
    """
    prefix = get_config().tag_prefix
    return prefix or ""


def get_tag_name_formatting():
    """
    Retrieves the tag name formatting from the configuration.
    
    Returns:
        The tag name formatting as specified in the configuration.
    """
    return get_config().tag_name_formatting

