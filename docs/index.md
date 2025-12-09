# NetBox Zabbix Plugin Documentation

## Introduction

The NetBox Zabbix Plugin provides seamless integration between NetBox, a leading infrastructure resource modeling (IRM) tool, and Zabbix, a powerful enterprise-class monitoring solution. This plugin bridges the gap between your infrastructure documentation and monitoring systems, enabling automated synchronization of devices, virtual machines, and their monitoring configurations.

With this plugin, you can:
- Automatically synchronize NetBox devices and virtual machines with Zabbix hosts
- Apply monitoring templates based on device characteristics
- Manage Zabbix configurations directly from NetBox
- Organize hosts using NetBox data (sites, roles, platforms)
- Schedule maintenance windows for planned outages
- Monitor synchronization status between systems

This integration helps maintain consistency between your infrastructure documentation and monitoring configuration, reducing manual effort and minimizing configuration errors.

## Documentation Overview

This documentation provides comprehensive information for both users and developers working with the NetBox Zabbix plugin. It covers installation, configuration, core concepts, and detailed reference material for all plugin components.

## Table of Contents

### Getting Started
- [User Guide](userguide.md) - Complete guide to installing, configuring, and using the plugin

### Core Models
- [Settings Model](settings_model.md) - Plugin configuration and settings management
- [HostConfig and Interface Models](hostconfig_models.md) - Host configurations and network interfaces
- [Template Model](template_model.md) - Zabbix template management
- [Proxy Model](proxy_model.md) - Zabbix proxy configuration
- [ProxyGroup Model](proxygroup_model.md) - Zabbix proxy group management
- [HostGroup Model](hostgroup_model.md) - Host group organization
- [Mapping Models](mapping_models.md) - Device and VM mapping configurations
- [TagMapping Model](tagmapping_model.md) - Tag mapping configurations
- [InventoryMapping Model](inventorymapping_model.md) - Inventory mapping configurations
- [Maintenance Model](maintenance_model.md) - Maintenance window management

### Background Jobs
- [Jobs Summary](jobs_summary.md) - Overview of the job system
- [System/Recurring Jobs (Programmer)](jobs_programmer_system.md) - Automated recurring jobs
- [Host Management Jobs (Programmer)](jobs_programmer_host.md) - Individual host operations
- [Sync Jobs (Programmer)](jobs_programmer_sync.md) - Bulk synchronization operations
- [Jobs User Guide](jobs_user_guide.md) - User guide for job management

## Key Features

### Automated Synchronization
The plugin maintains continuous synchronization between NetBox and Zabbix through:
- Automatic import of Zabbix configuration objects (templates, proxies, host groups)
- Real-time sync status monitoring for host configurations
- Scheduled cleanup of expired maintenance windows

### Flexible Mapping System
Intelligent mapping rules allow you to:
- Automatically assign templates based on device characteristics
- Organize hosts into groups using NetBox data
- Configure monitoring through proxy or proxy groups
- Apply different configurations to different device types

### Comprehensive Host Management
Full lifecycle management for Zabbix hosts:
- Automatic creation of hosts from NetBox devices and VMs
- Interface configuration for agent and SNMP monitoring
- Template and host group assignment
- Status management (enabled/disabled)
- Sync status tracking

### Maintenance Window Management
Robust maintenance scheduling capabilities:
- Target by individual hosts, host groups, sites, or clusters
- Flexible scheduling with start/end times
- Option to disable data collection during maintenance
- Automatic cleanup of expired windows

### Advanced Configuration Options
- Tag mapping from NetBox fields to Zabbix tags
- Inventory mapping for detailed host information
- Custom field integration for exclusion control
- Event logging for audit and troubleshooting

## Architecture Overview

The plugin follows a modular architecture with clear separation of concerns:

1. **Models Layer**: Defines the data structures and relationships
2. **Jobs System**: Handles background operations and synchronization
3. **Zabbix API Integration**: Communicates with Zabbix server
4. **NetBox Integration**: Integrates with NetBox UI and data models
5. **Mapping Engine**: Translates NetBox objects to Zabbix configurations

## Getting Help

For issues, questions, or contributions:
- Check the official NetBox and Zabbix documentation
- Review the model-specific documentation in this directory
- Consult the user guide for operational instructions
- Examine the jobs documentation for background task information

---

*This documentation was generated for NetBox Zabbix Plugin*