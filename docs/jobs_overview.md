# NetBox Zabbix Plugin - Jobs Overview

## Overview

The NetBox Zabbix plugin uses a comprehensive job system to handle asynchronous operations between NetBox and Zabbix. These jobs are implemented using NetBox's RQ-based job framework and provide transactional execution, error handling, and event logging capabilities.

Jobs in the plugin are categorized into several types:
- **Validation Jobs**: Validate synchronization status between NetBox and Zabbix
- **Import Jobs**: Import data from Zabbix into NetBox
- **Provisioning Jobs**: Create new host configurations in Zabbix
- **Interface Jobs**: Manage Zabbix interfaces for existing hosts
- **Host Management Jobs**: Create, update, and delete Zabbix hosts
- **System Jobs**: Recurring background tasks for maintenance and synchronization

All jobs inherit from the `AtomicJobRunner` base class, which ensures transactional execution and proper error propagation.

## Job Categories

### Validation Jobs

Jobs that validate the synchronization status between NetBox and Zabbix.

#### ValidateHost

Validates a Zabbix host configuration for a given NetBox Device or VirtualMachine, raising exceptions on validation failures or misconfigured instances.

### Import Jobs

Jobs that import data from Zabbix into NetBox.

#### ImportZabbixSettings

Synchronizes global Zabbix entities such as templates, proxies, proxy groups, and host groups into NetBox models.

#### ImportHost

Imports a single Zabbix host into NetBox, creating or updating a corresponding HostConfig for a Device or VirtualMachine.

### Provisioning Jobs

Jobs that create new host configurations in Zabbix.

#### ProvisionAgent

Provisions a Zabbix host using an Agent interface. This job creates a Host Configuration using the Agent interface model and registers it in Zabbix.

#### ProvisionSNMP

Provisions a Zabbix host using an SNMP interface. This job creates a Host configuration using the SNMP interface model and registers it in Zabbix.

### Interface Jobs

Jobs that manage Zabbix interfaces for existing hosts.

#### BaseZabbixInterfaceJob

Abstract base class providing shared enqueue logic for interface jobs.

#### CreateZabbixInterface

Creates missing interfaces in Zabbix for a HostConfig.

#### UpdateZabbixInterface

Synchronizes existing interfaces in Zabbix for a HostConfig.

### Host Management Jobs

Jobs that create, update, and delete Zabbix hosts.

#### CreateZabbixHost

Creates a new Zabbix host from a HostConfig.

#### UpdateZabbixHost

Updates an existing Zabbix host using HostConfig.

#### DeleteZabbixHost

Deletes a Zabbix host, supporting both soft and hard deletion.

### System Jobs

Recurring background tasks for maintenance and synchronization.

#### SyncHostsNow

Synchronizes all NetBox HostConfig objects with their corresponding hosts in Zabbix immediately.

#### SystemJobImportZabbixSettings

Periodically imports Zabbix settings into NetBox on a configurable recurring interval.

#### SystemJobHostConfigSyncRefresh

Refreshes HostConfig sync status on a recurring interval.

#### SystemJobMaintenanceCleanup

Cleans up expired Zabbix Maintenance windows from both NetBox and Zabbix.

## Base Classes

### AtomicJobRunner

JobRunner that ensures transactional execution and propagates exceptions. This class provides enhanced error handling, transactional integrity, and event logging capabilities for all plugin jobs.