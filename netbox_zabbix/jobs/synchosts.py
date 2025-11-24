
# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.jobs.system import SystemJobHostConfigSyncRefresh


class HostConfigSyncNow( AtomicJobRunner ):
    """
    Job to sync hosts in NetBox with hosts in Zabbix.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Runs the same logic as SystemJobHostConfigSyncRefresh but once.
        """
        cutoff = kwargs.get("cutoff", 5)  # default to 5 minutes if not provided
    
        return SystemJobHostConfigSyncRefresh.run( cutoff=cutoff )