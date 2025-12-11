# NetBox Zabbix Plugin User Guide

## Overview

This guide is intended for users who work with the NetBox Zabbix plugin via the NetBox web interface. It describes daily operations for managing monitoring configurations and explains how the plugin integrates Zabbix host management into NetBox.

## Getting Started

### Accessing the Plugin

Once installed and configured, the plugin seamlessly integrates into the NetBox interface. Users will find new menu options that allow interaction with Zabbix hosts, interfaces, importable hosts, NetBox-only hosts, and maintenance windows.

### Core Concepts

Before diving into operations, it is useful to understand several key concepts:

* **Host Configuration** represents a Zabbix host linked to a NetBox device or virtual machine, encapsulating all monitoring settings.
* **Mappings** define rules that determine how NetBox objects are translated into Zabbix host configurations, including template assignments and proxy selections.
* **Jobs** are background processes that ensure synchronization and other tasks occur without blocking the user interface.
* **Sync Status** indicates whether a host configuration accurately reflects its corresponding Zabbix host.
* **Interfaces** define how Zabbix communicates with monitored hosts, either through Agent or SNMP protocols.


## Managing Hosts


### Host Configuration Concept

A Host Configuration is the core component that connects a NetBox device or virtual machine to its corresponding Zabbix host. It acts as a bridge between asset management and monitoring, defining how each infrastructure element should be monitored.

Each host configuration contains all the information needed to create and maintain the Zabbix host. This includes the associated NetBox device or VM, selected monitoring templates, assigned host groups, and proxy or proxy group assignments for distributed monitoring. The configuration also specifies the interface type (Agent, SNMPv3), host status, and descriptive information. This centralized approach ensures consistent monitoring, simplifies management, and provides clear traceability between NetBox and Zabbix.



### Creating Host Configurations

Creating a new host configuration begins in the **Hosts** menu of the plugin. After selecting “Add,” the user fills in a form specifying the host name, the type of object (device or virtual machine), and the specific device or VM to associate. The interface type must also be chosen, defining whether communication will occur via Agent, SNMP, or both.

Templates and host groups are pre-populated based on the mappings that match the selected device or VM. Proxy or proxy group assignment is similarly determined, although users can override these defaults if necessary. Additional fields include host status, monitoring preferences, and optional descriptions. Upon saving the configuration, a background job is automatically queued to create the corresponding host in Zabbix, ensuring that the system remains in sync with NetBox.

### Viewing Host Details

The details page for a host configuration presents a comprehensive overview of the host’s monitoring setup. Users can examine the current synchronization status, assigned templates, host groups, and interface configurations. Information regarding monitoring state, the last sync timestamp, associated Zabbix host ID, and proxy assignment is also displayed. By centralizing this information, users can quickly understand the status and relationships of each host configuration.

### Updating Hosts

Although background jobs maintain automatic synchronization, users can manually update host configurations when needed. Editing a host configuration and saving the changes queues a background job to propagate updates to Zabbix, ensuring consistency between systems.

### Deleting Hosts

To remove a host from Zabbix, the user deletes the corresponding Host Configuration object in NetBox. Depending on the system’s settings, this action either performs a soft delete—moving the host to a graveyard—or a hard delete, permanently removing the host from Zabbix. Deletion is managed through background jobs to ensure that all related Zabbix records are correctly updated.

### Host Sync Operations

The plugin supports multiple synchronization approaches. Users may trigger synchronization for all hosts at once through the **Sync All** button, or synchronize individual host configurations via the detail view. Background jobs periodically monitor and update synchronization status, keeping NetBox and Zabbix aligned without requiring user intervention.


## Working with Interfaces

### Agent Interfaces

Agent interfaces define how the Zabbix server communicates with hosts using the Zabbix agent protocol. Creating a new Agent Interface involves selecting the host configuration that requires the interface, providing a descriptive name, selecting the NetBox network interface, and specifying the IP address for communication. Default values for port, connection method (IP or DNS), and primary interface designation are automatically populated. Once created, users can modify the port, connection type, or primary status, while the interface name and IP address remain fixed. The DNS name is derived automatically from the chosen IP address. Deletion is allowed only if template dependencies are not affected. If an interface is removable, it is indicated by the "removable" column in the table and detailed view, helping you understand which interfaces can be safely deleted without affecting template dependencies.


### SNMP Interfaces

SNMP interfaces provide configuration for monitoring hosts via the Simple Network Management Protocol. Users create SNMP interfaces by specifying a name, selecting the NetBox interface, and assigning an IP address. Default SNMP port, connection method, bulk request settings, and maximum repetitions are applied automatically. SNMP interfaces can be edited for protocol parameters, but the interface name and IP remain immutable. The interface supports only SNMPv3. Deletion is allowed only if template dependencies are not affected. If an interface is removable, it is indicated by the "removable" column in the table and detailed view, helping you understand which interfaces can be safely deleted without affecting template dependencies.


## Understanding Mappings

Mappings are the rules that decide how NetBox devices and virtual machines are set up in Zabbix. Instead of manually configuring each host, administrators define mapping policies that automatically apply to matching infrastructure components.

When provisioning a new host, the plugin checks all available mappings and applies the first one that matches the NetBox object. This evaluation considers site membership, roles, platforms, and custom fields to select the appropriate monitoring configuration.

Two mapping types handle different infrastructure components: Device Mappings for physical hardware like servers and network equipment, and VM Mappings for virtual machines. Both share the same structure but operate independently, allowing different monitoring strategies for physical and virtual infrastructure.

Each mapping has two parts: filter criteria that determine which objects it applies to, and configuration settings that define the monitoring elements. Filters can include sites, roles, platforms, and tags for precise targeting. For example, a mapping might target all database servers at a specific location or all Linux VMs.

Configuration settings specify the Zabbix elements applied to matching objects, including templates for metrics collection, host groups for organization, proxy assignments for distributed monitoring, and interface types for communication methods.

Every mapping system requires one default mapping for devices and one for VMs. This catch-all mapping applies to any object not matched by specific mappings, ensuring all infrastructure gets basic monitoring coverage. Default mappings cannot have restrictive filters and must apply universally.

Mappings are predictive, letting users see how any NetBox object will be configured in Zabbix before creating the host. By reviewing mapping criteria, users can determine which templates, host groups, proxies, and interface types will be applied.

The plugin enforces validation rules when creating mappings, ensuring only one default mapping exists per object type, non-default mappings include filter criteria, and selected templates are compatible with interface types. These validations maintain mapping integrity and prevent configuration errors.


## Importable and NetBox Only Hosts


### Importable Hosts

The Importable Hosts section displays Zabbix hosts that already exist in the Zabbix monitoring system but do not yet have corresponding host configurations in NetBox. This functionality enables organizations to bring existing monitoring configurations under centralized NetBox management, bridging the gap between established Zabbix monitoring and NetBox infrastructure documentation.

For a host to appear in this table, the Zabbix host must have the exact same name as an existing NetBox device or virtual machine. This name-based matching ensures that only relevant hosts are presented for import, preventing accidental duplication or mismatched entries.

The table presents essential information about each importable host to help users make informed decisions about which hosts to import:

**Name** shows the hostname as configured in Zabbix, which should match the corresponding NetBox object name. This column provides immediate identification of the host to be imported.

**Type** indicates whether the importable host corresponds to a physical Device or a VirtualMachine in NetBox, helping users understand the nature of the infrastructure component.

**Site** displays the NetBox site associated with the matching NetBox object, providing geographical or organizational context for the host.

**Status** shows the current operational status of the NetBox object, such as "Active," "Offline," or "Planned," giving users insight into the object's current state.

**Role** displays the functional role assigned to the NetBox object, such as "server," "switch," or "firewall," which often influences how the object should be managed and monitored.

**Valid** indicates whether the host passes automated validation checks for import into NetBox. When validation succeeds, this field confirms that the system has verified the host can be successfully imported without conflicts. Failed validation signals potential issues that need to be addressed before proceeding with the import.

**Invalid Reason** provides detailed explanations when validation fails, describing specific issues such as naming conflicts with existing NetBox objects, IP address conflicts, missing site associations, or unsupported characters in hostnames. This information guides users in resolving obstacles before importing.

Each row in the table represents a Zabbix host ready for import into NetBox. Users can select one or multiple hosts using the checkboxes provided in the first column, then apply bulk operations.

When the plugin administrator has enabled the **Auto Validate Importables** option in the Settings, the Valid and Invalid Reason fields are automatically populated for all displayed hosts without user intervention. This automatic validation continuously checks import readiness and provides immediate feedback on potential issues.

However, when automatic validation is disabled or when users want to refresh validation status after making configuration changes, the **Validate** button becomes essential. By selecting one or more hosts and clicking Validate, users can manually trigger the validation process for those specific hosts. The system then evaluates each selected host against import requirements, populating the Valid and Invalid Reason columns with current status information.

To import validated hosts into NetBox, users select the desired hosts using checkboxes and click the **Import** button. This action initiates the import process, creating corresponding Device or VirtualMachine objects in NetBox with appropriate attributes derived from Zabbix host information. The system establishes relationships between the imported objects and existing NetBox entities such as sites, roles, and IP addresses, while preserving the original Zabbix monitoring configuration. Background jobs handle the technical aspects of the import process, ensuring that NetBox accurately reflects the imported infrastructure while maintaining the existing monitoring setup in Zabbix.


### NetBox Only Hosts

The NetBox Only Hosts section displays devices and virtual machines that exist in NetBox but do not yet have corresponding Zabbix host configurations. This view serves as a provisioning queue, enabling administrators to quickly identify and add NetBox-managed infrastructure to Zabbix monitoring.

The table presents key information about each NetBox object to help users make informed provisioning decisions:

**Name** shows the hostname as configured in NetBox, providing immediate identification of the object.

**Type** indicates whether each entry is a physical Device or a VirtualMachine, helping users understand the nature of the infrastructure component.

**Site** displays the NetBox site where the object is physically or logically located, offering geographical or organizational context.

**Role** shows the functional role assigned to the object in NetBox, such as "server," "router," or "database," which often influences monitoring requirements.

**Platform** identifies the operating system or platform of the object, such as "Linux" or "Windows," which can affect template selection and monitoring approaches.

**Agent Mapping** displays the DeviceMapping or VMMapping that would be applied during Agent interface provisioning. This column shows which mapping rule matches the object's characteristics and what configuration would be used for Agent-based monitoring.

**SNMP Mapping** displays the DeviceMapping or VMMapping that would be applied during SNMP interface provisioning. Like the Agent Mapping column, this shows the matching rule and configuration that would be used for SNMP-based monitoring.

**Valid** indicates whether the object passes automated validation checks for provisioning. A positive validation means the system has confirmed that the object can be successfully provisioned to Zabbix, while a negative validation signals potential issues that require attention.

**Invalid Reason** provides specific details when validation fails, explaining issues such as missing primary IP addresses, absent matching mappings, or unavailable templates. This information guides users in resolving obstacles before provisioning.

Each row in the table represents a NetBox object ready for monitoring integration. Users can select one or multiple objects using the checkboxes provided in the first column, then apply bulk operations.

Above the table, the **Valid** button initiates validation for all currently displayed objects. When clicked, the system evaluates each selected object against provisioning requirements, populating the Valid and Invalid Reason columns with current status information. This is particularly useful when automatic validation is disabled in plugin settings, or when users want to refresh validation status after making configuration changes.

The **Quick Add Agent** button enables rapid provisioning of selected objects with Agent interfaces. When activated, the system applies Agent-specific mappings to create host configurations, automatically generating Agent interfaces using primary IP addresses, applying appropriate templates, assigning proxies as defined in mappings, and adding hosts to designated host groups. This feature requires that objects have primary IPv4 addresses and valid Agent mappings with available templates.

The **Quick Add SNMP** button provides equivalent functionality for SNMP interface provisioning. Activation triggers creation of host configurations using SNMP-specific mappings, automatic generation of SNMP interfaces with primary IP addresses, application of SNMP-appropriate templates, proxy assignments, host group memberships, and configuration of SNMP settings according to mapping definitions. Like Quick Add Agent, this requires valid SNMP mappings and available templates, along with properly configured primary IP addresses.

Both Quick Add features streamline the provisioning process by eliminating manual configuration steps while ensuring consistent application of organizational monitoring policies through predefined mappings. The system automatically queues background jobs to create corresponding hosts in Zabbix and establish the configured interfaces, maintaining synchronization between NetBox and Zabbix without requiring user intervention beyond the initial selection and button click.


## Maintenance Windows

Maintenance windows provide a mechanism for temporarily suspending monitoring activities during planned downtime or maintenance periods. This functionality prevents false alerts and monitoring noise when systems are intentionally offline for maintenance, upgrades, or repairs.

Creating a maintenance window requires several inputs: a descriptive name that identifies the maintenance activity, precise start and end times that define the maintenance period, target selections that determine which infrastructure components are affected, and an optional description that provides context about the maintenance work. The time-based scheduling ensures that monitoring suspension occurs automatically at the appropriate moments without requiring manual intervention.

You can target individual hosts for specific device maintenance, entire host groups for broader infrastructure work, sites for location-based maintenance activities or clusters for virtualization environment maintenance. This granular targeting ensures that only the relevant monitoring elements are suspended while maintaining visibility into unaffected infrastructure.

During an active maintenance period, the plugin enforces configuration restrictions to maintain the integrity of the maintenance window. Hosts under maintenance cannot have their configuration settings modified, including changes to templates, host groups, proxy assignments, or interface configurations. These restrictions prevent conflicts between ongoing maintenance activities and configuration changes that might interfere with the maintenance process or produce inconsistent monitoring states.


## Understanding Jobs

The plugin uses background jobs to perform tasks ensuring that time-consuming tasks don't block the user interface. 

There are two main types of jobs:

- System Jobs – Keep NetBox and Zabbix in sync. Examples include importing Zabbix settings, updating synchronization status, and cleaning up maintenance windows.
- Host Management Jobs – Handle individual hosts. This includes creating new hosts with Agent or SNMP interfaces, updating existing hosts, and removing hosts based on deletion rules.

#### Monitoring Jobs

You can track jobs and see their progress in several places:

* The **Jobs section** shows all background operations.
* Individual **host pages** display job-related information for that host.
* **Notifications** inform you when a job finishes or fails.

Each job shows details like progress, completion time, and error messages. This helps administrators confirm that operations completed successfully or quickly diagnose problems if they occur.

#### Common Job Issues

Some jobs may fail or get stuck. Common reasons include:

* **Configuration errors** – Incorrect settings prevent a job from completing.
* **Permission problems** – Zabbix API tokens may lack the needed privileges, or credentials may have expired.
* **Connectivity issues** – Network problems between NetBox and Zabbix can cause timeouts or failures.
* **Resource constraints** – Jobs may get stuck if the system doesn’t have enough resources.

*For administrative configuration details, see the Admin Guide. For developers and integrators, see the Programmer's Guide.*
