# NetBox Zabbix Plugin User Guide

Welcome to the NetBox Zabbix Plugin User Guide. This guide will help you understand how to install, configure, and use the NetBox Zabbix plugin to integrate your NetBox infrastructure data with Zabbix monitoring.

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Initial Configuration](#initial-configuration)
5. [Core Concepts](#core-concepts)
6. [Setting Up Monitoring](#setting-up-monitoring)
7. [Managing Hosts](#managing-hosts)
8. [Working with Templates](#working-with-templates)
9. [Using Proxies and Proxy Groups](#using-proxies-and-proxy-groups)
10. [Organizing with Host Groups](#organizing-with-host-groups)
11. [Configuring Maintenance Windows](#configuring-maintenance-windows)
12. [Advanced Features](#advanced-features)
13. [Troubleshooting](#troubleshooting)
14. [Best Practices](#best-practices)

## Introduction

The NetBox Zabbix plugin bridges the gap between your NetBox infrastructure data and Zabbix monitoring system. It allows you to:

- Automatically synchronize NetBox devices and virtual machines with Zabbix hosts
- Apply monitoring templates based on device characteristics
- Manage Zabbix configurations directly from NetBox
- Organize hosts using NetBox data (sites, roles, platforms)
- Schedule maintenance windows for planned outages
- Monitor synchronization status between systems

This integration helps maintain consistency between your infrastructure documentation and monitoring configuration.

## Prerequisites

Before installing the plugin, ensure you have:

1. **NetBox Installation**: Version 3.0 or higher
2. **Zabbix Server**: Version 5.0 or higher with API access enabled
3. **Python**: Version 3.8 or higher
4. **Network Connectivity**: Between NetBox server and Zabbix server
5. **Zabbix API Token**: With appropriate permissions for host management
6. **Database Access**: Permissions to create tables in NetBox database

## Installation

### Step 1: Install the Plugin

Install the plugin using pip:

```bash
pip install netbox-zabbix-plugin
```

Or clone the repository and install locally:

```bash
git clone <repository-url>
cd netbox-zabbix-plugin
pip install -e .
```

### Step 2: Enable the Plugin

Add the plugin to your NetBox configuration file (`configuration.py`):

```python
PLUGINS = ['netbox_zabbix']

PLUGINS_CONFIG = {
    'netbox_zabbix': {
        'tag_mappings': {
            'device': [
                ('Site', 'site.name'),
                ('Role', 'role.name'),
                ('Platform', 'platform.name'),
            ],
            'virtualmachine': [
                ('Site', 'site.name'),
                ('Role', 'role.name'),
                ('Platform', 'platform.name'),
            ],
        },
        'inventory_mapping': {
            'device': [
                ["Name", "name", ["name"]],
                ["Platform", "os", ["platform.name"]],
            ],
            'virtualmachine': [
                ["Name", "name", ["name"]],
                ["Platform", "os", ["platform.name"]],
            ]
        },
        'FERNET_KEY_PATH': '/path/to/fernet.key',
    }
}
```

### Step 3: Run Migrations

Apply the database migrations:

```bash
python manage.py migrate
```

### Step 4: Collect Static Files

Collect static files for the plugin:

```bash
python manage.py collectstatic
```

### Step 5: Restart Services

Restart your NetBox services:

```bash
sudo systemctl restart netbox
sudo systemctl restart netbox-rq
```

## Initial Configuration

### Step 1: Generate Fernet Key

Create a Fernet key for encrypting sensitive data:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > /path/to/fernet.key
```

Ensure the NetBox service user has read access to this file.

### Step 2: Configure Plugin Settings

Navigate to the NetBox web interface and go to:
**Plugins → Zabbix → Settings**

Configure the following essential settings:

1. **API Endpoint**: Your Zabbix API URL (e.g., `https://zabbix.example.com/api_jsonrpc.php`)
2. **Web Address**: Your Zabbix web interface URL
3. **API Token**: Your Zabbix API token
4. **Connection Test**: Verify the connection works

### Step 3: Configure Default Mappings

Set up default Device and VM mappings:
**Plugins → Zabbix → Device Mappings** and **VM Mappings**

Create a default mapping that will apply to all devices/VMs not matched by specific rules.

## Core Concepts

### Host Configuration

Each NetBox device or virtual machine can have a corresponding HostConfig object that defines its Zabbix monitoring configuration. This includes:

- Host groups the host belongs to
- Templates applied to the host
- Proxy or proxy group responsible for monitoring
- Interface configuration (Agent or SNMP)
- Status (enabled/disabled)

### Mappings

Mappings determine how NetBox objects are translated to Zabbix configurations:

- **Device Mappings**: Rules for NetBox devices
- **VM Mappings**: Rules for NetBox virtual machines
- **Tag Mappings**: How NetBox fields become Zabbix tags
- **Inventory Mappings**: How NetBox fields populate Zabbix inventory

Mappings can be filtered by site, role, and platform to apply different configurations to different types of devices.

### Synchronization

The plugin maintains synchronization between NetBox and Zabbix:

- **Import Jobs**: Regularly import data from Zabbix
- **Sync Jobs**: Ensure NetBox configurations match Zabbix
- **Sync Status**: Track whether configurations are in sync

## Setting Up Monitoring

### Step 1: Create Host Groups

Organize your monitoring by creating host groups:
**Plugins → Zabbix → Host Groups**

Common host groups might include:
- Linux Servers
- Windows Servers
- Network Devices
- Database Servers
- Web Servers

### Step 2: Import Templates

Import existing Zabbix templates:
**Plugins → Zabbix → Templates**

Templates define what metrics to collect and how to monitor hosts.

### Step 3: Configure Mappings

Create mappings to automatically assign configurations to devices:
**Plugins → Zabbix → Device Mappings**

Example mapping for Linux servers:
- **Name**: Linux Servers
- **Host Groups**: Linux Servers
- **Templates**: Template OS Linux by Zabbix agent
- **Filters**: Platform = Ubuntu, Role = Server

### Step 4: Create Host Configurations

For individual devices, you can create specific host configurations:
**Plugins → Zabbix → Host Configs**

## Managing Hosts

### Automatic Host Creation

When a NetBox device or VM matches a mapping rule, a HostConfig is automatically created. The host can then be synchronized with Zabbix.

### Manual Host Management

You can manually create, edit, or delete host configurations:

1. **Create**: Define custom monitoring for specific devices
2. **Edit**: Modify host groups, templates, or proxy assignments
3. **Delete**: Remove monitoring for decommissioned devices

### Host Status

Monitor the status of your hosts:
- **Enabled**: Host is being monitored
- **Disabled**: Host monitoring is paused
- **Sync Status**: Whether NetBox and Zabbix configurations match

### Interface Configuration

Configure how Zabbix communicates with your hosts:

**Agent Interfaces**:
- Port: Usually 10050
- Connection: IP or DNS
- Main Interface: Primary interface for monitoring

**SNMP Interfaces**:
- Port: Usually 161
- Version: SNMPv1, SNMPv2c, or SNMPv3
- Security settings for SNMPv3

## Working with Templates

### Template Management

View and manage Zabbix templates:
**Plugins → Zabbix → Templates**

Templates can have:
- **Parent-Child Relationships**: Hierarchical template organization
- **Dependencies**: Templates that require others
- **Interface Types**: Agent or SNMP requirement

### Applying Templates

Templates are applied through mappings or directly to host configurations:

1. **Via Mappings**: Automatically applied based on device characteristics
2. **Direct Assignment**: Manually assigned to specific hosts

### Template Synchronization

Templates are synchronized between NetBox and Zabbix to ensure consistency.

## Using Proxies and Proxy Groups

### Proxies

Proxies collect monitoring data and send it to the Zabbix server:

**Types**:
- **Active**: Proxy connects to agents
- **Passive**: Agents connect to proxy

**Configuration**:
- Network settings (IP, port)
- Encryption settings (TLS/SSL)
- Timeout configurations

### Proxy Groups

Proxy groups provide high availability for monitoring:

- **Failover**: Automatic switching if a proxy fails
- **Load Distribution**: Spread monitoring across multiple proxies
- **Minimum Online**: Ensure enough proxies are available

### Assigning Proxies

Assign proxies through:
1. **Mappings**: Apply to groups of devices
2. **Host Configurations**: Apply to individual hosts
3. **Proxy Groups**: Apply high availability configurations

## Organizing with Host Groups

### Creating Host Groups

Create logical groupings of hosts:
**Plugins → Zabbix → Host Groups**

Examples:
- By Environment: Production, Staging, Development
- By Function: Web Servers, Database Servers, Load Balancers
- By Location: Datacenter A, Datacenter B

### Managing Group Membership

Hosts can belong to multiple groups:
- **Automatic Assignment**: Through mappings
- **Manual Assignment**: Direct host configuration
- **Dynamic Assignment**: Based on device characteristics

### Group Benefits

Host groups enable:
- **Permissions**: Control who can view/modify hosts
- **Maintenance**: Apply maintenance windows to groups
- **Dashboards**: Create group-specific monitoring views
- **Reporting**: Generate reports by group

## Configuring Maintenance Windows

### Creating Maintenance

Schedule maintenance for planned outages:
**Plugins → Zabbix → Maintenances**

Options:
- **Start/End Time**: Maintenance period
- **Data Collection**: Enable/disable during maintenance
- **Targets**: Which hosts are affected

### Targeting Options

Apply maintenance to:
- **Individual Hosts**: Specific devices
- **Host Groups**: All hosts in groups
- **Sites**: All hosts at locations
- **Proxies**: All hosts monitored by proxies
- **Clusters**: All VMs in clusters

### Maintenance Status

Track maintenance windows:
- **Pending**: Scheduled but not active
- **Active**: Currently in progress
- **Expired**: Past the scheduled time
- **Failed**: Errors occurred

## Advanced Features

### Tag Mapping

Automatically create Zabbix tags from NetBox data:
**Plugins → Zabbix → Tag Mappings**

Example tags:
- Site name
- Device role
- Platform type
- Tenant information

### Inventory Mapping

Populate Zabbix inventory fields:
**Plugins → Zabbix → Inventory Mappings**

Inventory items:
- Hardware information
- Location data
- Contact details
- Asset information

### Event Logging

Monitor plugin activities:
**Plugins → Zabbix → Event Logs**

Logs include:
- Synchronization events
- Configuration changes
- Error conditions
- API interactions

### Custom Fields Integration

Exclude devices from monitoring using custom fields:
- Configure exclusion field name in settings
- Enable exclusion field checking
- Devices with field set are skipped

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Zabbix API
**Solution**:
1. Verify API endpoint URL
2. Check API token validity
3. Confirm network connectivity
4. Verify Zabbix API is enabled

### Synchronization Problems

**Problem**: Host configurations out of sync
**Solution**:
1. Check sync status indicators
2. Run manual sync jobs
3. Review configuration differences
4. Force resynchronization

### Proxy Configuration

**Problem**: Hosts not being monitored
**Solution**:
1. Verify proxy connectivity
2. Check proxy status in Zabbix
3. Confirm proxy assignments
4. Review proxy logs

### Template Issues

**Problem**: Missing templates or metrics
**Solution**:
1. Verify template synchronization
2. Check template dependencies
3. Confirm template assignments
4. Review Zabbix template configuration

## Best Practices

### Configuration Management

1. **Use Descriptive Names**: Clear naming for all objects
2. **Document Changes**: Maintain records of configuration updates
3. **Test Changes**: Validate in non-production environments
4. **Backup Configurations**: Regular export of important settings

### Monitoring Strategy

1. **Tiered Monitoring**: Different templates for different importance levels
2. **Regular Reviews**: Periodic assessment of monitoring effectiveness
3. **Alert Tuning**: Minimize false positives and negatives
4. **Capacity Planning**: Monitor resource usage trends

### Security Considerations

1. **API Token Security**: Limit permissions and rotate regularly
2. **Network Security**: Secure communication between systems
3. **Access Control**: Restrict plugin access to authorized users
4. **Audit Logging**: Monitor configuration changes

### Performance Optimization

1. **Proxy Usage**: Distribute monitoring load appropriately
2. **Template Efficiency**: Avoid overly complex templates
3. **Sync Scheduling**: Balance sync frequency with system load
4. **Resource Monitoring**: Watch NetBox and Zabbix performance

## Conclusion

The NetBox Zabbix plugin provides powerful integration between your infrastructure documentation and monitoring systems. By following this guide, you can effectively set up and manage your monitoring environment while maintaining consistency with your NetBox data.

For additional help, refer to the model-specific documentation in the docs directory or consult the NetBox and Zabbix official documentation.

---

*This user guide was generated for NetBox Zabbix Plugin version 2.0.0*