# NetBox Zabbix Plugin - Jobs Documentation Summary

## Overview

This document provides an overview of all job-related documentation for the NetBox Zabbix plugin. Jobs are background tasks that handle synchronization and management operations between NetBox and Zabbix.

## Documentation Files

### Programmer Documentation

1. **[System/Recurring Jobs](jobs_programmer_system.md)**
   - Detailed documentation for system jobs that run at configurable intervals
   - Covers ImportZabbixSettings, HostConfigSyncRefresh, and MaintenanceCleanup jobs
   - Implementation details for the job registration and scheduling system

2. **[Host Management Jobs](jobs_programmer_host.md)**
   - Documentation for jobs that manage individual host lifecycles
   - Covers CreateZabbixHost, UpdateZabbixHost, and DeleteZabbixHost jobs
   - Implementation details for job enqueuing and error handling

3. **[Sync Jobs](jobs_programmer_sync.md)**
   - Documentation for bulk synchronization operations
   - Covers SyncHostsNow job for full synchronization
   - Implementation details for transactional execution and error resilience

### User Guide

4. **[Jobs User Guide](jobs_user_guide.md)**
   - Comprehensive guide for users working with jobs
   - Instructions for monitoring, configuring, and running jobs
   - Best practices and troubleshooting guidance

## Job Categories

### System/Recurring Jobs
These jobs maintain ongoing synchronization between NetBox and Zabbix:
- **ImportZabbixSettings**: Imports Zabbix configuration objects
- **HostConfigSyncRefresh**: Updates sync status for host configurations
- **MaintenanceCleanup**: Removes expired maintenance windows

### Host Management Jobs
These jobs handle individual host operations:
- **CreateZabbixHost**: Creates new hosts in Zabbix
- **UpdateZabbixHost**: Updates existing hosts in Zabbix
- **DeleteZabbixHost**: Removes hosts from Zabbix

### Sync Jobs
These jobs handle bulk operations:
- **SyncHostsNow**: Synchronizes all host configurations

## Related Documentation

This job documentation complements other plugin documentation:

- **[User Guide](userguide.md)**: General plugin usage and configuration
- **[Settings Model](settings_model.md)**: Configuration options including job intervals
- **[HostConfig Model](hostconfig_models.md)**: Host configuration objects managed by jobs
- **[Maintenance Model](maintenance_model.md)**: Maintenance windows affected by cleanup jobs

## Getting Started

For users:
1. Start with the [Jobs User Guide](jobs_user_guide.md) for operational instructions
2. Refer to the [User Guide](userguide.md) for general plugin configuration

For developers:
1. Review the programmer documentation for each job category:
   - [System/Recurring Jobs](jobs_programmer_system.md)
   - [Host Management Jobs](jobs_programmer_host.md)
   - [Sync Jobs](jobs_programmer_sync.md)
2. Consult related model documentation for data structure details