"""

NetBox Zabbix Plugin — Custom exception classes for the NetBox-Zabbix integration.

Defines specialized exception types that carry additional contextual data to aid
in debugging and error handling throughout the integration components.
"""


class ExceptionWithData(Exception):
    """
    A custom exception class that carries additional structured data alongside 
    the error message.
    
    This is useful in scenarios where simply raising an exception with a string 
    is not enough, and additional context (such as a failed API payload, 
    validation results, or debug metadata) needs to be passed along with the 
    error.  
    
    The additional data can be consumed by higher-level handlers (e.g. job 
    runners or UI code) to provide richer error reporting, troubleshooting 
    output, or rollback logic.
    
    Attributes:
        data (Any): Arbitrary structured data associated with the exception.
    
    Example:
        >>> payload = {"host": "router1", "status": "failed"}
        >>> raise ExceptionWithData("Failed to create host in Zabbix", payload)
    
        try:
            ...
        except ExceptionWithData as e:
            print(e)        # Output: Failed to create host in Zabbix
            print(e.data)   # Output: {'host': 'router1', 'status': 'failed'}
    """
    def __init__(self, message, data=None, pre_data=None, post_data=None):
        """
        Intialize ExceptionWithData
        """
        super().__init__( message )
        self.data = data
        self.pre_data = pre_data
        self.post_data = post_data

