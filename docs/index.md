# NetBox Zabbix Plugin Documentation

## Introduction

The NetBox Zabbix Plugin connects NetBox with Zabbix, integrating your infrastructure documentation with your monitoring system. It automates the synchronization of devices, virtual machines, and their associated monitoring configurations, keeping both platforms aligned.


## Objectives

The plugin automates synchronization between NetBox and Zabbix, acting as a bridge between infrastructure documentation and monitoring. Its key goals include:

- Full lifecycle management for Zabbix hosts from NetBox including creation, configuration, and deletion
- Import existing Zabbix hosts into NetBox
- Automatically assigning settings to devices and VMs based on their type and role, including which templates, host groups, and proxies to use
- Managing proxies, proxy groups, and host groups directly from NetBox
- Scheduling and managing maintenance windows

## Non-Objectives

The plugin does not aim to replace or replicate core Zabbix functionality, nor does it provide direct management of Zabbix server configurations. The focus remains on data synchronization and integration rather than:

- Direct management of Zabbix server settings or configurations
- Replacement of Zabbix web interface for monitoring tasks
- Management of Zabbix user accounts or permissions
- Direct manipulation of Zabbix triggers, graphs, or dashboards
- Providing alerting mechanisms beyond what Zabbix natively offers

## Documentation Overview

This documentation is organized for three different audiences:

### 1. Users
If you're using the plugin through the NetBox web interface to manage your monitoring configurations, start with the **User Guide**. This section covers day-to-day operations like creating and managing hosts, understanding job statuses, and troubleshooting common issues.

### 2. Administrators
If you're responsible for configuring and maintaining the plugin, the **Admin Guide** provides detailed information about settings, mappings, proxies, and system configuration. This section builds on the User Guide and covers advanced administrative tasks.

### 3. Developers and Programmers
If you're extending the plugin, integrating it with other systems, or need to understand the internal workings, the **Programmer's Guide** provides technical documentation about the code structure, models, jobs, and APIs.

## Getting Started

Choose your poision below:

- [Installation](installation.md) - Plugin installation and initial setup
- [User Guide](user_guide.md) - For day-to-day use of the plugin
- [Admin Guide](admin_guide.md) - For plugin configuration and administration
- [Programmer's Guide](programmer_guide.md) - For developers and advanced customization