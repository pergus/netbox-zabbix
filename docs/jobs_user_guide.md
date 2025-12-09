# NetBox Zabbix Plugin - Jobs User Guide

## Overview

The NetBox Zabbix plugin uses a background job system to handle various operations that synchronize data between NetBox and Zabbix. These jobs run asynchronously to prevent blocking the user interface and ensure smooth operation of both systems.

This guide explains the different types of jobs, how to monitor them, and how to use them effectively.

## Types of Jobs

### System/Recurring Jobs

These jobs run automatically at configurable intervals to maintain synchronization between NetBox and Zabbix:

1. **Zabbix Settings Import**: Imports templates, proxies, host groups, and other configuration objects from Zabbix
2. **Host Config Sync Refresh**: Checks and updates the synchronization status of host configurations
3. **Maintenance Cleanup**: Removes expired maintenance windows from both systems

### Host Management Jobs

These jobs handle individual host operations:

1. **Create Host**: Adds a new host to Zabbix based on a NetBox HostConfig
2. **Update Host**: Updates an existing host in Zabbix to match NetBox configuration
3. **Delete Host**: Removes a host from Zabbix (soft or hard delete based on settings)

### Sync Jobs

These jobs handle bulk operations:

1. **Sync All Hosts**: Immediately synchronizes all NetBox host configurations with Zabbix

## Monitoring Jobs

### Job Status Page

You can monitor all jobs through the NetBox interface:

1. Navigate to **Plugins → Zabbix → Jobs**
2. View the status of all jobs (running, completed, failed, scheduled)
3. Click on individual jobs to see detailed information

### Job Details

Each job displays:
- **Name**: Descriptive name of the job
- **Status**: Current state (Pending, Running, Completed, Failed, Scheduled)
- **Created**: When the job was created
- **Started**: When the job began execution
- **Completed**: When the job finished
- **Duration**: How long the job took to execute
- **User**: Who initiated the job (if applicable)
- **Results**: Summary of what the job accomplished

### Interpreting Job Results

#### Successful Jobs
Successful jobs show:
- Status: "Completed"
- Green checkmark icon
- Results summary with details about what was accomplished

#### Failed Jobs
Failed jobs show:
- Status: "Errored"
- Red exclamation mark icon
- Error message explaining what went wrong
- Detailed error information in the job data

## Configuring System Jobs

### Accessing Settings

1. Navigate to **Plugins → Zabbix → Settings**
2. Scroll to the "System Job(s)" section

### Available Intervals

System jobs can be configured with the following intervals:
- Minutely (1 minute)
- Every 5 minutes
- Every 15 minutes
- Every 30 minutes
- Hourly (60 minutes)
- Every 2-12 hours
- Daily (24 hours)
- Weekly (7 days)
- 30 Days

### Configuration Options

1. **Zabbix Import Interval**: How often to import Zabbix settings
2. **Host Config Sync Interval**: How often to check host synchronization status
3. **Host Config Sync Cutoff**: How far back to check for outdated hosts
4. **Maintenance Cleanup Interval**: How often to remove expired maintenances

### Applying Changes

After changing intervals:
1. The system automatically reschedules jobs with new intervals
2. Existing jobs with different intervals will be replaced
3. You can verify scheduling on the Jobs page

## Running Manual Jobs

### Creating Individual Hosts

1. Navigate to **Plugins → Zabbix → Host Configs**
2. Select a host configuration that doesn't have a Zabbix host ID
3. Click the "Create Host in Zabbix" button
4. Monitor the job progress on the Jobs page

### Updating Individual Hosts

1. Navigate to **Plugins → Zabbix → Host Configs**
2. Select a host configuration
3. Click the "Update Host in Zabbix" button
4. Monitor the job progress on the Jobs page

### Deleting Individual Hosts

1. Navigate to **Plugins → Zabbix → Host Configs**
2. Select a host configuration with a Zabbix host ID
3. Click the "Delete Host from Zabbix" button
4. Confirm the deletion when prompted
5. Monitor the job progress on the Jobs page

### Running Full Sync

1. Navigate to **Plugins → Zabbix → Host Configs**
2. Click the "Sync All Hosts Now" button
3. Confirm when prompted (this can affect many hosts)
4. Monitor the job progress on the Jobs page

## Troubleshooting Jobs

### Common Issues

#### Jobs Stuck in "Running" State
- Check if the worker processes are running
- Restart the NetBox RQ worker service if needed
- Examine job logs for clues about what's happening

#### Failed Jobs
1. Click on the failed job to see error details
2. Check the error message for specific information
3. Look at the job data for additional context
4. Verify Zabbix connectivity if it's a communication error

#### Jobs Not Starting
- Verify that system jobs are properly scheduled
- Check the plugin settings for correct intervals
- Ensure the NetBox worker service is running

### Checking Job Logs

1. Navigate to **Plugins → Zabbix → Event Logs**
2. Filter by job name or time range
3. Review log entries for detailed information

### Restarting Failed Jobs

1. Navigate to the failed job details page
2. Some jobs can be restarted using the "Retry" button
3. For host operations, you may need to trigger the operation again manually

## Best Practices

### Scheduling Recommendations

1. **Import Interval**: Set based on how frequently your Zabbix configuration changes
   - Small environments: Daily
   - Medium environments: Every 6-12 hours
   - Large environments: Every 2-4 hours

2. **Sync Interval**: Balance between freshness and system load
   - Critical environments: Every 30 minutes to 1 hour
   - Standard environments: Every 2-4 hours
   - Low-change environments: Daily

3. **Cleanup Interval**: Daily is usually sufficient for maintenance cleanup

### Monitoring Recommendations

1. **Regular Checks**: Check job status daily, especially after configuration changes
2. **Alerting**: Set up alerts for repeated job failures
3. **Log Review**: Regularly review event logs for warnings or errors
4. **Performance Monitoring**: Watch for jobs taking unusually long to complete

### Operational Guidelines

1. **Full Sync Usage**: Use sparingly and during maintenance windows
2. **Individual Operations**: Prefer targeted operations over bulk when possible
3. **Error Investigation**: Investigate failed jobs promptly to prevent cascading issues
4. **Resource Consideration**: Be mindful of the impact on both NetBox and Zabbix servers
5. **Backup Before Major Operations**: Consider backing up configurations before large sync operations

## Security Considerations

### Job Permissions

- Only users with appropriate permissions can initiate jobs
- Job results are only visible to authorized users
- Sensitive information in job data is handled securely

### Audit Trail

- All job operations are logged with user information
- Changes made by jobs are tracked in NetBox changelog
- Event logs provide additional audit information

## Performance Tips

### Optimizing Job Performance

1. **Interval Tuning**: Adjust intervals based on your environment size and change rate
2. **Batch Operations**: Use bulk operations when updating multiple similar hosts
3. **Off-Peak Scheduling**: Schedule resource-intensive jobs during low-usage periods
4. **Worker Scaling**: Ensure adequate worker capacity for your job volume

### Monitoring Performance

1. **Duration Tracking**: Watch for jobs taking progressively longer
2. **Failure Patterns**: Look for repeating failure patterns that might indicate systemic issues
3. **Resource Usage**: Monitor system resources during job execution
4. **API Limits**: Be aware of Zabbix API rate limits in high-volume scenarios

## Getting Help

If you encounter issues with jobs:

1. **Check Documentation**: Review this guide and the programmer documentation
2. **Review Logs**: Examine job logs and event logs for error details
3. **Verify Configuration**: Ensure plugin settings are correct
4. **Contact Support**: Reach out to your system administrator or support team
5. **Community Resources**: Check NetBox and Zabbix community forums for similar issues