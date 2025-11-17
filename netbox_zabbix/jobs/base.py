"""
NetBox Zabbix Plugin — Job Utility Helpers

This module provides shared helper functions for NetBox Zabbix plugin 
jobs, focusing on argument validation and instance retrieval.

Responsibilities:
- Validate that required keyword arguments are provided to job functions.
- Simplify common checks and repetitive logic across background jobs.
- Serve as a central location for lightweight, reusable job utilities.

Example Usage:
    from netbox_zabbix.jobs.helpers import require_kwargs

    kwargs = {"device": device, "user": user}
    device, user = require_kwargs(kwargs, "device", "user")
"""


def require_kwargs(kwargs, *required):
    """
    Ensures that required keyword arguments are present.
    
    Args:
        kwargs (dict): Dictionary of keyword arguments.
        *required (str): Names of required arguments.
    
    Returns:
        Single value if one argument requested, else tuple of values.
    
    Raises:
        ValueError: If a required argument is missing or None.
    """
    values = []
    for arg in required:
        if arg not in kwargs or kwargs[arg] is None:
            raise ValueError(f"Missing required argument '{arg}'.")
        values.append(kwargs[arg])
    
    if len(values) == 1:
        return values[0]
    return tuple(values)


