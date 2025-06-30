from django.core.management.base import BaseCommand

from rich.console import Console
from rich.table import Table
from netbox_zabbix.models import DeviceMapping


class Command(BaseCommand):
    help = "List Device and VM Mappings"

    def handle(self, *args, **kwargs):
        self.device_mappings()


    def device_mappings(self):
        console = Console()

        # 1) Gather mappings & their matched devices
        mappings = list( DeviceMapping.objects.all() )
        matched_lists = [mapping.get_matching_devices() for mapping in mappings]

        # 2) Compute how many rows we need (the longest device list)
        max_rows = max( len( devs ) for devs in matched_lists ) if matched_lists else 0

        # 3) Build the table, one column per mapping
        table = Table( title="Device Mappings" )
        for mapping in mappings:
            table.add_column(mapping.name, overflow="fold")

        # 4) Add rows: for each index, pull the device name or blank
        for i in range( max_rows ):
            row = [
                devs[i].name if i < len(devs) else ""
                for devs in matched_lists
            ]
            table.add_row( *row )

        console.print( table )
