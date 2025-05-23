
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