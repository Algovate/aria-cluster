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
     "worker_timeout": 30
   }
   ```

2. Worker configuration (`config/worker.json`):
   ```json
   {
     "dispatcher_url": "http://localhost:8000",
     "download_dir": "./downloads",
     "max_concurrent_downloads": 3
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

## Health Checks

1. Check system status:
   ```bash
   curl http://localhost:8000/status
   ```

2. List workers:
   ```bash
   curl http://localhost:8000/workers
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

2. If downloads fail:
   - Verify aria2c installation
   - Check download directory permissions
   - Review worker logs for errors

3. If web UI can't connect:
   - Verify dispatcher URL configuration
   - Check CORS settings if needed
   - Clear browser cache

For more details about using the system, see [README.md](README.md) and the [Web UI Guide](web_ui/README.md). 