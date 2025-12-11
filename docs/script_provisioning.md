# Script Provisioning Guide for NetBox Zabbix Plugin

## Overview

This guide explains how to provision Zabbix agents and SNMP hosts programmatically from NetBox scripts using the NetBox Zabbix plugin. This approach is valuable for automating large-scale deployments or integrating with external provisioning systems that require programmatic control over monitoring setup.

The plugin's script provisioning capabilities enable developers and automation engineers to programmatically create, configure, and manage Zabbix monitoring for NetBox infrastructure assets. This functionality bridges the gap between infrastructure-as-code practices and monitoring-as-code approaches, allowing organizations to maintain consistent, reproducible monitoring configurations that align with their infrastructure provisioning workflows.

## Prerequisites

Before implementing provisioning scripts, several foundational elements must be properly configured to ensure successful execution. The NetBox Zabbix plugin must be correctly installed and operational within the NetBox environment, with all necessary dependencies satisfied and database migrations completed. Plugin connectivity to the Zabbix server requires validation through the Settings interface, confirming that API endpoints are accessible and authentication credentials are valid.

Script execution necessitates appropriate permissions for both NetBox data access and Zabbix host creation operations. Users running provisioning scripts must possess sufficient privileges to read target NetBox objects and create corresponding Zabbix configurations. The existence of appropriate DeviceMapping and VMMapping configurations is essential for automatic configuration assignment during provisioning. These mappings determine which templates, host groups, and proxies are applied to newly created hosts, ensuring consistent monitoring policies across infrastructure components.

API access requirements include proper authentication tokens and network connectivity between the NetBox server and Zabbix API endpoints. Scripts must be able to reach the Zabbix server over the network, with any required firewall rules or security groups configured to permit API communication.

## Basic Script Structure

NetBox provisioning scripts inherit from the `Script` base class, following standard NetBox scripting conventions while incorporating plugin-specific functionality. This inheritance provides access to built-in logging capabilities, parameter handling, and execution control mechanisms that integrate seamlessly with the NetBox scripting framework.

The fundamental script structure includes metadata definition through the Meta class, which specifies the script name, description, and default commit behavior. The run method serves as the primary execution entry point, receiving data parameters and commit flags that control script behavior. This method orchestrates the provisioning workflow, iterating through target objects and applying appropriate configuration based on organizational requirements.

Error handling within scripts should leverage the built-in logging mechanisms to provide informative feedback about provisioning operations. Successful operations, skipped objects, and failed attempts should all be appropriately logged to facilitate troubleshooting and audit tracking. The commit flag enables dry-run functionality, allowing administrators to preview provisioning operations before executing actual changes.

## Provisioning Agents

### Simple Agent Provisioning

Agent provisioning scripts begin by identifying target devices that require Zabbix agent monitoring, typically filtering by platform, role, or other relevant characteristics. The provisioning process involves creating HostConfig objects that establish the connection between NetBox infrastructure assets and Zabbix monitoring configurations.

Before creating new host configurations, scripts should verify that existing configurations do not already exist for target objects to prevent duplication. This validation step ensures idempotent behavior, allowing scripts to be safely re-run without creating unwanted duplicates. When committing changes, scripts create HostConfig objects with appropriate associations to NetBox devices or virtual machines, then trigger provisioning jobs that handle the actual Zabbix host creation process.

The ProvisionAgent job class orchestrates the end-to-end agent provisioning workflow, automatically applying appropriate templates, host groups, and proxy assignments based on configured mappings. This automation eliminates manual configuration steps while ensuring consistent application of organizational monitoring policies.

#### Example: Provisioning a Single Agent Host

```python
from django.utils.text import slugify
from dcim.models import Device
from netbox_zabbix.jobs.provision import ProvisionAgent
from extras.scripts import Script, ObjectVar

class ProvisionSingleAgentHost(Script):
    class Meta:
        name = "Provision Single Agent Host"
        description = "Provision a single device with Zabbix agent monitoring"
        commit_default = True

    device = ObjectVar(
        description="Device to provision with Zabbix agent",
        queryset=Device.objects.all()
    )

    def run(self, data, commit):
        device = data['device']

        # Check if already provisioned
        from netbox_zabbix.models import HostConfig
        from django.contrib.contenttypes.models import ContentType

        existing_config = HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model(device),
            object_id=device.id
        ).first()

        if existing_config:
            self.log_info(f"Device {device.name} is already provisioned with HostConfig {existing_config.name}")
            return

        # Provision the agent
        if commit:
            job = ProvisionAgent.run_job(
                instance=device,
                request=self.request
            )
            self.log_success(f"Started provisioning job for {device.name} (Job ID: {job.id})")
        else:
            self.log_info(f"Would provision agent for {device.name} (dry run)")
```

#### Example: Bulk Agent Provisioning

```python
from django.utils.text import slugify
from dcim.models import Device
from netbox_zabbix.jobs.provision import ProvisionAgent
from extras.scripts import Script, MultiObjectVar

class BulkProvisionAgentHosts(Script):
    class Meta:
        name = "Bulk Provision Agent Hosts"
        description = "Provision multiple devices with Zabbix agent monitoring"
        commit_default = True

    devices = MultiObjectVar(
        description="Devices to provision with Zabbix agents",
        queryset=Device.objects.all()
    )

    def run(self, data, commit):
        devices = data['devices']
        provisioned_count = 0
        skipped_count = 0

        for device in devices:
            # Check if already provisioned
            from netbox_zabbix.models import HostConfig
            from django.contrib.contenttypes.models import ContentType

            existing_config = HostConfig.objects.filter(
                content_type=ContentType.objects.get_for_model(device),
                object_id=device.id
            ).first()

            if existing_config:
                self.log_info(f"Skipping {device.name} - already provisioned")
                skipped_count += 1
                continue

            # Provision the agent
            if commit:
                try:
                    job = ProvisionAgent.run_job(
                        instance=device,
                        request=self.request
                    )
                    self.log_success(f"Started provisioning job for {device.name} (Job ID: {job.id})")
                    provisioned_count += 1
                except Exception as e:
                    self.log_failure(f"Failed to provision {device.name}: {e}")
            else:
                self.log_info(f"Would provision agent for {device.name} (dry run)")
                provisioned_count += 1

        self.log_info(f"Bulk provisioning complete: {provisioned_count} provisioned, {skipped_count} skipped")
```

### Advanced Agent Configuration

Advanced agent provisioning extends basic functionality by allowing explicit configuration of templates, host groups, and other monitoring parameters before triggering provisioning jobs. This approach provides fine-grained control over monitoring configurations for specific use cases that require deviations from standard mapping rules.

Scripts implementing advanced provisioning typically retrieve specific Zabbix objects such as templates and host groups by name or other identifiers, then associate these objects with newly created HostConfig instances. This explicit assignment overrides automatic mapping behavior, enabling specialized monitoring configurations for particular infrastructure components or environments.

Error handling in advanced provisioning scripts should account for missing Zabbix objects, ensuring that required templates and host groups exist before attempting provisioning operations. Comprehensive logging captures both successful operations and failures, providing administrators with detailed information about provisioning outcomes and facilitating troubleshooting when issues arise.

## Provisioning SNMP Hosts

### Basic SNMP Provisioning

SNMP provisioning follows similar patterns to agent provisioning but targets network infrastructure components that are typically monitored through SNMP protocols rather than Zabbix agents. These devices include network switches, routers, firewalls, and other infrastructure elements that support SNMP-based monitoring.

The provisioning workflow begins with identification of SNMP-capable devices through appropriate filtering criteria, such as device role, manufacturer, or platform characteristics. Scripts validate that target objects possess the necessary attributes for SNMP monitoring, including primary IP addresses and appropriate interface configurations.

HostConfig creation for SNMP devices follows the same patterns as agent provisioning, with the key difference being the use of ProvisionSNMP job classes instead of ProvisionAgent classes. This distinction ensures that appropriate interface types and configuration parameters are applied during the provisioning process, creating SNMP-specific monitoring configurations in Zabbix.

#### Example: Provisioning a Single SNMP Host

```python
from django.utils.text import slugify
from dcim.models import Device
from netbox_zabbix.jobs.provision import ProvisionSNMP
from extras.scripts import Script, ObjectVar

class ProvisionSingleSNMPHost(Script):
    class Meta:
        name = "Provision Single SNMP Host"
        description = "Provision a single device with SNMP monitoring"
        commit_default = True

    device = ObjectVar(
        description="Network device to provision with SNMP monitoring",
        queryset=Device.objects.all()
    )

    def run(self, data, commit):
        device = data['device']

        # Check if already provisioned
        from netbox_zabbix.models import HostConfig
        from django.contrib.contenttypes.models import ContentType

        existing_config = HostConfig.objects.filter(
            content_type=ContentType.objects.get_for_model(device),
            object_id=device.id
        ).first()

        if existing_config:
            self.log_info(f"Device {device.name} is already provisioned with HostConfig {existing_config.name}")
            return

        # Provision with SNMP
        if commit:
            job = ProvisionSNMP.run_job(
                instance=device,
                request=self.request
            )
            self.log_success(f"Started SNMP provisioning job for {device.name} (Job ID: {job.id})")
        else:
            self.log_info(f"Would provision SNMP for {device.name} (dry run)")
```

#### Example: Bulk SNMP Provisioning with Custom Parameters

```python
from django.utils.text import slugify
from dcim.models import Device
from netbox_zabbix.jobs.provision import ProvisionSNMP
from extras.scripts import Script, MultiObjectVar

class BulkProvisionSNMPHosts(Script):
    class Meta:
        name = "Bulk Provision SNMP Hosts"
        description = "Provision multiple network devices with SNMP monitoring"
        commit_default = True

    devices = MultiObjectVar(
        description="Network devices to provision with SNMP monitoring",
        queryset=Device.objects.all()
    )

    def run(self, data, commit):
        devices = data['devices']
        provisioned_count = 0
        skipped_count = 0

        for device in devices:
            # Check if already provisioned
            from netbox_zabbix.models import HostConfig
            from django.contrib.contenttypes.models import ContentType

            existing_config = HostConfig.objects.filter(
                content_type=ContentType.objects.get_for_model(device),
                object_id=device.id
            ).first()

            if existing_config:
                self.log_info(f"Skipping {device.name} - already provisioned")
                skipped_count += 1
                continue

            # Provision with SNMP
            if commit:
                try:
                    job = ProvisionSNMP.run_job(
                        instance=device,
                        request=self.request
                    )
                    self.log_success(f"Started SNMP provisioning job for {device.name} (Job ID: {job.id})")
                    provisioned_count += 1
                except Exception as e:
                    self.log_failure(f"Failed to provision SNMP for {device.name}: {e}")
            else:
                self.log_info(f"Would provision SNMP for {device.name} (dry run)")
                provisioned_count += 1

        self.log_info(f"Bulk SNMP provisioning complete: {provisioned_count} provisioned, {skipped_count} skipped")
```

## Bulk Operations

### Bulk Provisioning Script

Bulk provisioning scripts enable simultaneous provisioning of multiple devices and virtual machines, streamlining large-scale monitoring deployments. These scripts implement efficient iteration patterns that process hundreds or thousands of objects while maintaining performance and reliability.

The bulk provisioning approach includes safeguards such as processing limits and error handling mechanisms that prevent cascading failures when individual provisioning operations encounter issues. Statistics tracking provides visibility into provisioning outcomes, enabling administrators to understand the scope and success rate of bulk operations.

Resource management considerations include memory usage, database connection handling, and API rate limiting that may impact large-scale provisioning operations. Scripts should implement appropriate batching and throttling mechanisms to ensure reliable execution even when provisioning thousands of objects.

## Error Handling

### Robust Error Handling

Production-ready provisioning scripts implement comprehensive error handling that accounts for various failure scenarios including network connectivity issues, authentication failures, missing dependencies, and Zabbix API errors. This robust error handling ensures that script failures are graceful and informative, providing administrators with actionable information for troubleshooting.

Logging mechanisms capture detailed information about provisioning operations, including timestamps, object identifiers, and error details that facilitate debugging and audit tracking. Scripts should differentiate between recoverable errors that might be resolved through retries and fatal errors that require manual intervention.

Cleanup procedures handle partially completed operations, ensuring that failed provisioning attempts do not leave orphaned objects or inconsistent configurations. This cleanup functionality maintains system integrity even when provisioning operations encounter unexpected issues.

### Monitoring Provisioning Jobs

Job monitoring capabilities enable administrators to track the status and outcomes of provisioning operations, providing visibility into background processing that occurs after script execution completes. This monitoring includes checking job completion status, examining error details for failed operations, and correlating job outcomes with script execution logs.

Real-time job monitoring allows administrators to observe provisioning progress as operations execute, while historical job tracking provides audit trails for compliance and troubleshooting purposes. Integration with NetBox's built-in job management system ensures consistent monitoring experiences across all plugin operations.


*For general usage information, see the User Guide. For administrative configuration, see the Admin Guide.*