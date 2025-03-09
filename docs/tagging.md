# Worker and Task Tagging

This guide explains how to use the tag-based worker assignment strategy for organizing and categorizing tasks and workers in the Aria2c Cluster.

## Overview

The tag-based strategy allows you to assign tasks to specific workers based on matching key-value pairs. This enables you to:

- Dedicate specific workers to specific types of tasks
- Organize downloads by purpose or category
- Create specialized workers for different download types
- Implement simple access control for resources

## Configuration

### 1. Enable Tag-Based Assignment

In the `config/dispatcher.json` file, set the task assignment strategy to "tags":

```json
{
    "task_assignment": {
        "strategy": "tags",
        "max_retries": 3,
        "retry_delay": 300
    }
}
```

### 2. Configure Worker Tags

In each worker's configuration (`config/worker.json`), add tags to the capabilities:

```json
{
    "worker": {
        "name": "worker-1",
        "max_tasks": 5,
        "capabilities": {
            "disk_space": "100G",
            "bandwidth": "100M",
            "supports_bt": true,
            "supports_metalink": true,
            "tags": {
                "purpose": "multimedia",
                "location": "us-west",
                "priority": "high",
                "content_type": "video"
            }
        }
    }
}
```

## Using Tags in Tasks

When creating a new task, include the tags in the options:

### Using the API

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/large-file.zip",
    "options": {
      "tags": {
        "purpose": "multimedia",
        "content_type": "video"
      }
    }
  }'
```

### Using the Client

```bash
./scripts/client.py create https://example.com/large-file.zip --options '{"tags": {"purpose": "multimedia", "content_type": "video"}}'
```

### Using the Web UI

In the web interface, when creating a new task, you can specify tags in the advanced options section.

## How Tag Matching Works

1. When a task is submitted with tags, the dispatcher looks for workers with matching tags
2. A worker is considered a match if it has all the tags specified in the task
3. Workers don't need to have exactly the same tags - they can have additional tags not in the task
4. If multiple workers match, the task is assigned to the least loaded worker
5. If no workers match, the task falls back to the least loaded worker

## Examples

### Example 1: Content Type Categorization

Workers:
- Worker 1: `{"tags": {"content_type": "video"}}`
- Worker 2: `{"tags": {"content_type": "documents"}}`

Tasks:
- Video download: `{"tags": {"content_type": "video"}}` → Goes to Worker 1
- Document download: `{"tags": {"content_type": "documents"}}` → Goes to Worker 2

### Example 2: Location-Based Assignment

Workers:
- Worker 1: `{"tags": {"location": "us-west", "bandwidth": "high"}}`
- Worker 2: `{"tags": {"location": "eu-central", "bandwidth": "high"}}`

Tasks:
- US download: `{"tags": {"location": "us-west"}}` → Goes to Worker 1
- EU download: `{"tags": {"location": "eu-central"}}` → Goes to Worker 2

## Best Practices

1. Keep tag names consistent across your configuration
2. Use descriptive tag names and values
3. Don't overuse tags - focus on meaningful categorization
4. Consider using standardized tag values (e.g., "high/medium/low" for priority)
5. Document your tagging scheme for team members 
noteId: "c5c6bea0fca311ef9ffaffd33dc20838"
tags: []

---

 