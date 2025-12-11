# NetBox Zabbix Plugin Programmer's Guide

## Overview

This guide is designed for Developers and Programmers who need to understand the internal workings of the NetBox Zabbix plugin, extend its functionality, or integrate it with other systems. It covers the code structure, models, jobs, APIs, and extension points.

## System Architecture Overview

The plugin follows a modular architecture with clear separation of concerns that promotes maintainability and extensibility. This design enables developers to understand, modify, and extend specific components without requiring deep knowledge of the entire system.

### Core Components

The plugin's codebase is organized into several key directories, each serving a specific purpose:

```
netbox_zabbix/
├── models.py          # Data models and database schema
├── views.py           # User interface views and handlers
├── forms.py           # Form definitions and validation
├── urls.py            # URL routing configuration
├── jobs/              # Background job implementations
├── zabbix/            # Zabbix API integration and utilities
├── mapping/           # NetBox to Zabbix mapping logic
├── provisioning/      # Host creation and management workflows
├── signals/           # Django signal handlers
├── api/               # REST API endpoints
└── management/        # Django management commands
```

**Models Layer**: Django models in `models.py` represent Zabbix objects and configurations, providing the data structure foundation for the entire plugin.

**Jobs System**: Background task processing is implemented using NetBox's job framework through files in the `jobs/` directory, handling asynchronous operations efficiently.

**Zabbix API Integration**: Zabbix API interactions are wrapped in classes located in the `zabbix/` directory, abstracting complex API calls into manageable functions.

**NetBox Integration**: Views, forms, and UI components connect with NetBox through `views.py` and `forms.py`, ensuring seamless user experience.

**Mapping Engine**: Logic for translating NetBox objects to Zabbix configurations resides in the `mapping/` directory, automating the conversion process.

**Provisioning System**: The orchestration of Zabbix host creation and updating is managed through files in the `provisioning/` directory, handling end-to-end provisioning workflows.

## Data Models

### Settings Model

The Settings Model manages global plugin configuration and Zabbix connection parameters within `models.py`. This central configuration point controls fundamental plugin behavior and integration characteristics.

Key fields include `name` which provides a configuration identifier, `api_endpoint` specifying the Zabbix API endpoint URL, `web_address` defining the Zabbix web interface URL, `_encrypted_token` storing the encrypted Zabbix API token securely, `ip_assignment_method` determining how IP addresses are assigned to interfaces, and various configuration flags and intervals that control plugin behavior.

Essential methods include `get_client()` which returns an authenticated Zabbix API client through helper functions, and automatic token encryption/decryption capabilities that protect sensitive credentials while maintaining usability.

### HostConfig Model

The HostConfig Model represents a Zabbix host configuration linked to a NetBox object in `models.py`. This model forms the core connection between infrastructure asset management and monitoring configuration.

Critical fields encompass `content_type` linking to Device or VirtualMachine models, `object_id` storing the ID of the linked NetBox object, `hostid` containing the Zabbix host identifier, `status` tracking monitoring status as enabled or disabled, `in_sync` indicating synchronization status with Zabbix, `last_sync_update` recording when sync status was last refreshed, and relationships to templates, host groups, proxy, and proxy_group for comprehensive configuration management.

Important properties include `has_agent_interface` returning true when an AgentInterface exists, `has_snmp_interface` returning true when an SNMPInterface exists, `assigned_object` providing access to the linked Device or VirtualMachine, and `in_maintenance` indicating when the host is under active maintenance.

The HostConfig model can be associated with AgentInterface or SNMPInterface models that define how Zabbix communicates with the monitored host. AgentInterface represents Zabbix agent communication parameters, while SNMPInterface contains SNMP-specific configuration details.

### Mapping Models

Base `Mapping` class with `DeviceMapping` and `VMMapping` subclasses in `models.py` provides flexible configuration translation between NetBox objects and Zabbix monitoring setups.

Essential fields include `name` and `description` for identification purposes, `default` flag indicating default mapping status, relationships to templates, host groups, proxy, and proxy_group for configuration inheritance, and filtering criteria covering sites, roles, platforms, cluster_types, cluster_groups, manufacturers, and device_types for precise targeting.

Core methods encompass `matches_object(obj)` which determines if a mapping applies to a specific NetBox object, and `get_configuration(obj)` which returns the appropriate Zabbix configuration for an object based on mapping rules.

### Proxy and Host Group Models

Proxy and Host Group Models represent Zabbix objects imported from the Zabbix server in `models.py`, maintaining synchronized representations of remote monitoring infrastructure.

Fundamental fields include `name` storing the object name in Zabbix, `zabbix_id` containing the identifier in Zabbix, and additional Zabbix-specific attributes that preserve remote object characteristics locally.

Primary methods consist of `sync_from_zabbix()` which updates local data from Zabbix information through import functions, and `to_zabbix_format()` which formats data appropriately for Zabbix API calls, ensuring seamless bidirectional synchronization.

## Job System

The plugin leverages NetBox's background job system based on Redis Queue (RQ) for asynchronous operations, preventing user interface blocking while processing time-consuming tasks.

### Job Types

Four distinct job categories handle different operational requirements. System Jobs perform recurring maintenance tasks in `jobs/system.py`, including `SystemJobImportZabbixSettings` for importing Zabbix objects, `SystemJobHostConfigSyncRefresh` for updating synchronization status, and `SystemJobMaintenanceCleanup` for removing expired maintenance windows. Host Management Jobs execute individual host operations in `jobs/host.py`, featuring `CreateZabbixHost` for Zabbix host creation, `UpdateZabbixHost` for Zabbix host updates, and `DeleteZabbixHost` for Zabbix host removal. Provisioning Jobs orchestrate host creation workflows in `jobs/provision.py`, comprising `ProvisionAgent` for hosts with Agent interfaces and `ProvisionSNMP` for hosts with SNMP interfaces. Sync Jobs handle bulk operations in `jobs/synchosts.py`, primarily `SyncHosts` for synchronizing multiple hosts simultaneously.

### Job Implementation

Jobs inherit from `AtomicJobRunner` which extends NetBox's `JobRunner` to provide transaction support and consistent error handling. This inheritance ensures that jobs execute within database transactions, automatically logging events when enabled, and properly handling exceptions with appropriate rollback mechanisms.

### Job Scheduling

System job scheduling occurs through multiple mechanisms including Django management commands for manual execution, NetBox's recurring job system for automated scheduling, and manual triggering through user interface actions or API calls for on-demand execution.

## APIs and Interfaces

### REST API Endpoints

The plugin exposes comprehensive REST API endpoints through Django REST Framework in the `api/` directory, enabling programmatic access to all plugin functionality.

Public endpoints include:

- `/api/plugins/netbox-zabbix/setting/` - Settings management
- `/api/plugins/netbox-zabbix/templates/` - Template management
- `/api/plugins/netbox-zabbix/proxy/` - Proxy management
- `/api/plugins/netbox-zabbix/proxy-group/` - Proxy group management
- `/api/plugins/netbox-zabbix/host-group/` - Host group management
- `/api/plugins/netbox-zabbix/tag-mapping/` - Tag mapping management
- `/api/plugins/netbox-zabbix/inventory-mapping/` - Inventory mapping management
- `/api/plugins/netbox-zabbix/device-mapping/` - Device mapping management
- `/api/plugins/netbox-zabbix/vm-mapping/` - VM mapping management
- `/api/plugins/netbox-zabbix/host-config/` - Host configuration management
- `/api/plugins/netbox-zabbix/agent-interface/` - Agent interface management
- `/api/plugins/netbox-zabbix/snmp-interface/` - SNMP interface management
- `/api/plugins/netbox-zabbix/event-log/` - Event log management
- `/api/plugins/netbox-zabbix/maintenance/` - Maintenance management

Internal endpoints (for UI use):

- `/api/plugins/netbox-zabbix/host-mapping/` - Host mapping management
- `/api/plugins/netbox-zabbix/unassigned-hosts/` - Unassigned hosts for selection
- `/api/plugins/netbox-zabbix/unassigned-agent-interfaces/` - Unassigned agent interfaces
- `/api/plugins/netbox-zabbix/unassigned-snmp-interfaces/` - Unassigned SNMP interfaces
- `/api/plugins/netbox-zabbix/unassigned-host-interfaces/` - Unassigned host interfaces
- `/api/plugins/netbox-zabbix/unassigned-host-ipaddresses/` - Unassigned host IP addresses

### Zabbix API Wrapper

The plugin provides comprehensive wrappers around the Zabbix API in the `zabbix/` directory, abstracting complex API interactions into simple function calls.

Low-level API client access enables direct Zabbix API interaction through the `ZabbixAPI` class, while higher-level convenience functions in modules like `zabbix.hosts` provide simplified operations for common tasks such as `create_zabbix_host` and `update_zabbix_host`.

### Internal APIs

Plugin-specific APIs offer convenient access to common operations including `netbox_zabbix.provisioning.handler.provision_zabbix_host()` for full provisioning orchestration, `netbox_zabbix.mapping.engine.apply_mapping()` for applying mapping logic to objects, and `netbox_zabbix.importing.import_zabbix_settings()` for importing Zabbix objects, reducing development complexity for extension projects.

## Signals

The plugin employs Django signals to automatically synchronize changes in NetBox with Zabbix through implementations in `signals/signals.py`, ensuring real-time consistency between systems.

### Signal Handlers

The plugin implements five primary signal handler categories that maintain synchronization integrity between NetBox and Zabbix systems:

| Signal Category | Model | Signal Type | Action | Purpose |
|----------------|-------|-------------|--------|---------|
| HostConfig | HostConfig | post_save | Trigger update job | Updates Zabbix when HostConfig changes |
| HostConfig | HostConfig | pre_delete | Record deletion | Prepares cleanup before HostConfig removal |
| HostConfig | HostConfig | post_delete | Clean up Zabbix | Removes Zabbix host based on delete settings |
| Interface | AgentInterface/SNMPInterface | post_save | Update Zabbix | Updates interface configuration in Zabbix |
| Interface | AgentInterface/SNMPInterface | post_delete | Remove from Zabbix | Deletes interface from Zabbix |
| IP Address | IPAddress | post_save | Update interface IPs | Updates interface IP addresses in Zabbix |
| IP Address | IPAddress | pre_delete | Handle IP removal | Prepares for IP address removal |
| Device/VM | Device/VirtualMachine | pre_save | Detect changes | Identifies name/IP changes requiring Zabbix updates |

Each signal category serves a specific purpose in maintaining synchronization between NetBox and Zabbix. HostConfig signals ensure that changes to host configurations trigger appropriate Zabbix updates or cleanup operations. Interface signals manage the lifecycle of agent and SNMP interfaces, ensuring that Zabbix interface configurations remain consistent with NetBox interface data. IP Address signals handle IP address changes that might affect monitoring connectivity. Device and VirtualMachine signals detect infrastructure changes that require corresponding updates in the monitoring system.

### Signal Suppression

Signal suppression capabilities provide flexibility for bulk operations and testing scenarios. Global disable functionality operates through the environment variable `DISABLE_NETBOX_ZABBIX_SIGNALS="1"`, while per-instance suppression works by setting `_skip_signal = True` on specific model instances.

### Custom Signal Handling

Developers can extend signal handling by connecting custom functions to existing signals in their application's `apps.py` ready() method, enabling additional business logic integration without modifying core plugin code.

### Management Commands

Custom management commands in the `management/commands/` directory provide administrative extensions that can be executed through standard Django management command interfaces.


*For user operations, see the User Guide. For administrative configuration, see the Admin Guide.*