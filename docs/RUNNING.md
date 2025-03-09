---
noteId: "2d4c35a0fca411ef9ffaffd33dc20838"
tags: []

---

# Running the Aria2c Cluster

This guide provides detailed instructions for running the aria2c cluster task dispatcher system.

## Prerequisites

- Docker and Docker Compose (recommended)
- Or:
  - Python 3.8 or higher
  - aria2c installed on each worker machine
  - Required Python packages (see requirements.txt)

## Docker Compose Setup (Recommended)

The easiest way to run the entire system:

```bash
# Create necessary directories
mkdir -p data downloads/worker1 downloads/worker2

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f dispatcher
docker-compose logs -f worker1
```

This starts:
- 1 dispatcher server (port 8000)
- 2 worker nodes
- Web UI (port 8080)

## Manual Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Components

1. Dispatcher configuration (`config/dispatcher.json`):
   ```json
   {
     "host": "0.0.0.0",
     "port": 8000,
     "log_level": "info",
     "database": {
       "type": "memory",
       "path": "data/dispatcher.db"
     },
     "task_assignment": {
       "strategy": "least_loaded",
       "max_retries": 3,
       "retry_delay": 300
     },
     "worker_management": {
       "heartbeat_interval": 30,
       "heartbeat_timeout": 90,
       "auto_remove_offline": true,
       "offline_threshold": 300
     },
     "security": {
       "api_key_required": true,
       "api_keys": ["default-api-key-change-me"]
     }
   }
   ```

2. Worker configuration (`config/worker.json`):
   ```json
   {
     "dispatcher": {
       "url": "http://localhost:8000",
       "heartbeat_interval": 30,
       "api_key": "default-api-key-change-me"
     },
     "aria2": {
       "host": "0.0.0.0",
       "port": 6800,
       "rpc_secret": "",
       "rpc_path": "/jsonrpc",
       "download_dir": "downloads",
       "global_options": {
         "max-concurrent-downloads": 5,
         "max-connection-per-server": 16,
         "split": 8,
         "min-split-size": "1M",
         "continue": true,
         "max-overall-download-limit": "0",
         "max-overall-upload-limit": "0"
       }
     },
     "worker": {
       "name": "worker-1",
       "max_tasks": 5,
       "capabilities": {
         "disk_space": "100G",
         "bandwidth": "100M",
         "supports_bt": true,
         "supports_metalink": true
       }
     },
     "log_level": "info"
   }
   ```

### 3. Start Components

1. Start the dispatcher:
   ```bash
   python -m scripts.run_dispatcher
   ```

2. Start worker node(s):
   ```bash
   python -m scripts.run_worker
   ```

3. Start the web UI:
   ```bash
   cd web_ui
   python -m http.server 8080
   ```

## Component Access

- Web UI: http://localhost:8080
- Dispatcher API: http://localhost:8000
- Default download locations:
  - Worker 1: `./downloads/worker1`
  - Worker 2: `./downloads/worker2`

## API Authentication

The API requires authentication using an API key. You can:

1. Include the API key in the request header:
   ```
   X-API-Key: your-api-key-here
   ```

2. Or include it as a query parameter:
   ```
   http://localhost:8000/api/status?api_key=your-api-key-here
   ```

The default API key is set in the dispatcher configuration file.

## Database Configuration

The system supports two database backends:

1. In-memory database (default):
   - Fast but data is lost on restart
   - No configuration needed

2. SQLite database:
   - Persistent storage across restarts
   - Configure in `config/dispatcher.json`:
     ```json
     "database": {
       "type": "sqlite",
       "path": "data/dispatcher.db"
     }
     ```

See [Database Configuration](database.md) for more details.

## Health Checks

1. Check system status:
   ```bash
   curl -H "X-API-Key: default-api-key-change-me" http://localhost:8000/api/status
   ```

2. List workers:
   ```bash
   curl -H "X-API-Key: default-api-key-change-me" http://localhost:8000/api/workers
   ```

3. Monitor logs:
   ```bash
   # Docker setup
   docker-compose logs -f

   # Manual setup
   tail -f logs/dispatcher.log
   tail -f logs/worker.log
   ```

## Troubleshooting

1. If workers can't connect:
   - Check if dispatcher is running
   - Verify dispatcher URL in worker config
   - Check network connectivity
   - Verify API key matches between worker and dispatcher

2. If downloads fail:
   - Verify aria2c installation
   - Check download directory permissions
   - Review worker logs for errors

3. If web UI can't connect:
   - Verify dispatcher URL configuration
   - Check CORS settings if needed
   - Clear browser cache
   - Verify API key configuration

For more details about using the system, see [README.md](../README.md) and the [Web UI Guide](../web_ui/README.md). 