"""
NetBox Zabbix Plugin - Utilities

This module contains generic helper functions for performing operations
on NetBox models etc.
"""

def save_without_signals(instance, update_fields=None):
    """
    Validate and save a model instance while explicitly preventing any
    signal handlers from running.


    This function sets the internal `_skip_signal` attribute on the instance
    before saving. Signal receivers that support this convention should check
    for this flag and exit early, ensuring that the save operation does not
    trigger any signal-based side effects such as background jobs, automatic
    synchronization steps, or related updates.
    
    Args:
        instance (Model): Any Django model instance that honors the `_skip_signal` flag.
        update_fields (list[str] | None): Optional list of fields to update.
    """
    if update_fields is None:
        instance.full_clean()
    instance._skip_signal = True
    instance.save(update_fields=update_fields)