
import sys
import socket

from django.core.management.base import BaseCommand
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from cryptography.fernet import Fernet
from netbox_zabbix.jobs.imports import ImportZabbixSettings
from netbox_zabbix.models import (
    Setting, 
    Template,
    HostGroup,
    Proxy,
    ProxyGroup,
    DeviceMapping, 
    VMMapping
)


class Command(BaseCommand):
    help = "Setup NetBox Zabbix plugin"

    def handle(self, *args, **options):
        console = Console()
        try:
            # Part 1 - Setup Zabbix connection
            path = self.part_1(console)

            # Part 2 - Configure Device and VM mappings
            self.part_2(console)


            # Show instruction to configure FERNET_KEY_PATH
            console.print("\n[bold]Next Required Step[/bold]")
            console.print(
                "You must add the path to your [bold]fernet.key[/bold] file in the "
                "PLUGINS_CONFIG section of your NetBox configuration.\n"
            )
            
            config_snippet = f'''
            PLUGINS_CONFIG = {{
                'netbox_zabbix': {{
                    "FERNET_KEY_PATH": "{path}"
                }}
            }}
            '''.strip()
            
            from rich.syntax import Syntax
            console.print(Syntax(config_snippet, "python", word_wrap=True))
            console.print( "\n[green]Copy and paste the above into your NetBox configuration.py file.[/green]" )

        except KeyboardInterrupt:
            console.print("\n[red]Setup aborted by user (Ctrl+C).[/]")
            sys.exit(1)

    # ---------------------- PART 1 METHODS ---------------------- #

    def prompt_zabbix_settings(self, console):
        config_name = Prompt.ask("Enter the name of the setting instance", default="config")

        hostname = socket.getfqdn()
        host = Prompt.ask("Enter the Zabbix host", default=f"{hostname}")
        api_url = Prompt.ask("Enter the Zabbix API URL", default=f"https://{host}/api_jsonrpc.php")
        web_url = Prompt.ask("Enter the Zabbix Web URL", default=f"https://{host}")

        token = ""
        while not token.strip():
            token = Prompt.ask("Enter the Zabbix API token", password=True)
            if not token.strip():
                console.print("[red]Token cannot be empty![/red]")

        plugin_dir = Path(__file__).resolve().parent.parent.parent
        default_fernet_path = plugin_dir / "fernet.key"
        fernet_path = Prompt.ask("Path to Fernet key file", default=str(default_fernet_path))

        return config_name, api_url, web_url, token, Path(fernet_path)

    def get_or_create_fernet(self, console, fernet_path: Path):
        """Load or generate a Fernet key and return a Fernet instance."""
        if fernet_path.exists():
            key = fernet_path.read_text().strip()
            console.print(f"[green]Loaded existing Fernet key from {fernet_path}[/green]")
        else:
            key = Fernet.generate_key().decode()
            fernet_path.write_text(key)
            console.print(f"[green]Generated new Fernet key and stored at {fernet_path}[/green]")
        return Fernet(key.encode())

    def save_zabbix_setting(self, name, api_url, web_url, encrypted_token):
        setting, created = Setting.objects.get_or_create(name=name)
        setting.api_endpoint = api_url
        setting.web_address = web_url
        setting._encrypted_token = encrypted_token
        setting.save()
        return setting, created

    def show_setting_summary(self, console, setting):
        table = Table(title="Zabbix Setting Summary")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_row("Name", setting.name)
        table.add_row("API URL", setting.api_endpoint)
        table.add_row("Web URL", setting.web_address)
        table.add_row("Encrypted Token", setting._encrypted_token[:8] + "..." if setting._encrypted_token else "")
        console.print(table)

    def style_success_part1(self, created, config_name):
        if created:
            return f"A new Zabbix Setting instance '{config_name}' was created."
        return "Existing Zabbix Setting updated."

    def part_1(self, console):
        console.print("\n[bold]Part 1 - Setup Zabbix connection[/bold]")
        config_name, api_url, web_url, token, fernet_path = self.prompt_zabbix_settings(console)
        fernet = self.get_or_create_fernet(console, fernet_path)
        encrypted_token = fernet.encrypt(token.encode()).decode()
        
        setting, created = self.save_zabbix_setting(config_name, api_url, web_url, encrypted_token)
        self.show_setting_summary(console, setting)
        console.print(self.style_success_part1(created, config_name))
        
        # Import Zabbix settings
        with console.status("[bold green]Loading Templates, Host Groups etc. from Zabbix..[/bold green]", spinner="dots") as status:
            try:
                ImportZabbixSettings.run_now()
            except Exception as e:
                console.print(f"[red]Failed to import settings from Zabbix: {e}[/red]")
                return

        return fernet_path

    # ---------------------- PART 2 METHODS ---------------------- #

    def configure_device_vm_mappings(self, console):
        console.print("\n[bold]Part 2 - Configure Device and VM Mappings[/bold]")

        # Load templates and host groups from DB
        templates   = Template.objects.all()
        host_groups = HostGroup.objects.all()
        proxy       = Proxy.objects.all()
        proxy_group = ProxyGroup.objects.all()
        
        template    = self.prompt_choice(console, "Enter Default Template", templates, default_name="ICMP Ping")
        host_group  = self.prompt_choice(console, "Enter Default Host Group", host_groups, default_name=None)
        proxy       = self.prompt_choice(console, "Enter Default Proxy", proxy, default_name=None, required=False)
        proxy_group = self.prompt_choice(console, "Enter Default Proxy Group", proxy_group, default_name=None, required=False)
        

        # Display summary table
        table = Table(title="Device/VM Mapping Defaults")
        table.add_column("Mapping")
        table.add_column("Value")
        table.add_row("Default Template", template.name if template else "")
        table.add_row("Default Host Group", host_group.name if host_group else "")
        table.add_row("Default Proxy", proxy.name if proxy else "")
        table.add_row("Default Proxy Group", proxy_group.name if proxy_group else "")
        
        console.print(table)

        try:
            # Save or update Device Mapping
            device_mapping, created = DeviceMapping.objects.update_or_create(
                name="Default Device Mapping",
                defaults={
                    "proxy": proxy,
                    "proxy_group": proxy_group,
                }
            )
            device_mapping.templates.set([template] if template else [])
            device_mapping.host_groups.set([host_group] if host_group else [])
            # Save or update VM Mapping
            vm_mapping, created = VMMapping.objects.update_or_create(
                name="Default VM Mapping",
                defaults={
                    "proxy": proxy,
                    "proxy_group": proxy_group,
                }
            )
            vm_mapping.templates.set([template] if template else [])
            vm_mapping.host_groups.set([host_group] if host_group else [])

            console.print("[green]Device and VM mappings saved successfully![/green]")

        except Exception as e:
               console.print(f"[bold red]Error saving Device/VM mappings:[/bold red] {e}")

    def prompt_choice( self, console, prompt_text, queryset, default_name=None, required=True ):
        """
        Display a numbered list of choices from a queryset and prompt the user to select one.
    
        Args:
            console (Console): Rich console.
            prompt_text (str): Text to show before prompting.
            queryset (QuerySet): Django queryset of objects with `name` attribute.
            default_name (str, optional): Name of the default choice.
            required (bool): If False, user can press Enter to select None.
    
        Returns:
            Selected object from queryset or None.
        """
        if not queryset.exists():
            console.print(f"[yellow]No options available for {prompt_text}[/yellow]")
            return None
    
        # Build table of choices
        table = Table(title=prompt_text)
        table.add_column("#", justify="right")
        table.add_column("Name")
    
        choices = list(queryset)
        default_index = None
    
        for i, obj in enumerate(choices, start=1):
            table.add_row(str(i), obj.name)
            if default_name and obj.name == default_name:
                default_index = i
    
        console.print(table)
    
        while True:
            prompt_msg = f"Select a number [1-{len(choices)}]"
            if not required:
                prompt_msg += " (Enter to skip)"
            try:
                choice_str = Prompt.ask(
                    prompt_msg,
                    default=str(default_index) if default_index else None
                )
                choice_str = choice_str or ""  # Convert None to empty string
                if not choice_str.strip() and not required:
                    return None
                choice_index = int(choice_str)
                if 1 <= choice_index <= len(choices):
                    return choices[choice_index - 1]
            except (ValueError, IndexError):
                console.print(f"[red]Invalid selection. Please choose a number between 1 and {len(choices)}.[/red]")
    
    
    def part_2(self, console):
        self.configure_device_vm_mappings(console)
