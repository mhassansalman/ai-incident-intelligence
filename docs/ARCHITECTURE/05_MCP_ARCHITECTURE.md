# MCP Architecture

## Purpose

MCP standardizes how agents access operational tools and systems.

It is not the reasoning layer.

```text
Agent
  ↓
MCP Client
  ↓
MCP Server
  ↓
Tool
  ↓
Operational System
```

## Build order

Do not start with MCP.

Recommended sequence:

```text
plain Python function
    ↓
stable interface
    ↓
tests
    ↓
wrap/expose through MCP
```

This keeps MCP from hiding basic implementation problems.

## Tool interface boundary

Agents should call stable functions such as:

```text
search_logs(...)
get_metrics(...)
get_service_health(...)
get_recent_commits(...)
get_deployments(...)
```

Agents should not directly know:

```text
C:\logs\catalog.log
docker logs catalog
Prometheus query language
GitHub REST endpoints
```

## Future MCP servers

### Observability MCP

```text
search_logs
get_metrics
get_trace
get_service_health
```

### Engineering MCP

```text
get_commits
get_diff
get_pull_request
get_deployments
```

### Infrastructure MCP

```text
get_containers
get_container_health
get_pods
get_cloud_events
get_network_health
```

### Database MCP

```text
get_connection_stats
get_query_latency
get_database_health
```

### Remediation MCP

Later only:

```text
restart_service
rollback_deployment
scale_service
```

Write-capable tools require approval controls.

## Local now vs MCP later

### Now

```text
Log Investigator
    ↓
search_logs()
    ↓
LocalLogProvider
    ↓
local file
```

### Later

```text
Log Investigator
    ↓
MCP Client
    ↓
Observability MCP Server
    ↓
Prometheus / OpenTelemetry / log backend
```

The investigator should need minimal or no architectural change.
