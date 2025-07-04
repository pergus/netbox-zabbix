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


def get_auto_validate_importables():
    """
    Retrieve the current setting for automatic validation of importable devices and VMs.
    
    Returns:
        bool: True if automatic validation is enabled; False otherwise.
    """
    return get_config().auto_validate_importables


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


def get_monitored_by():
    """
    Retrieves the default monitored_by value from the configuration.
    
    Returns:
        The default monitored_by value as specified in the configuration.
    """
    return get_config().monitored_by


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

def get_inventory_mode():
    """
    Retrieves the inventory mode from the configuration.

    Returns:
        The inventory mode as specified in the configuration.
    """
    return get_config().inventory_mode


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

def get_event_log_enabled():
    """
    Retrieves the event log enabled  from the configuration.
    
    Returns:
        The event log enabled as specified in the configuration.
    """

    return get_config().event_log_enabled