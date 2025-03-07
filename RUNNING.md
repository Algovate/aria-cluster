# Running the Aria2c Cluster

This document provides instructions for running the aria2c cluster task dispatcher.

## Running with Docker Compose

The easiest way to run the entire system is using Docker Compose:

```bash
# Create necessary directories
mkdir -p data downloads/worker1 downloads/worker2

# Build and start the containers
docker-compose up -d

# Check the logs
docker-compose logs -f
```

This will start:
- 1 dispatcher server
- 2 worker nodes

## Running Manually

### Prerequisites

- Python 3.8 or higher
- aria2c installed on each worker machine

### Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the system:
   - Edit `config/dispatcher.json` for the central server
   - Edit `config/worker.json` for each worker node

### Running the Dispatcher

```bash
python -m scripts.run_dispatcher
```

Or use the executable script:

```bash
./scripts/run_dispatcher.py
```

### Running a Worker

```bash
python -m scripts.run_worker
```

Or use the executable script:

```bash
./scripts/run_worker.py
```

## Using the Client

The client script provides a command-line interface for interacting with the dispatcher:

```bash
# Get system status
./scripts/client.py status

# List all tasks
./scripts/client.py tasks

# Create a new download task
./scripts/client.py create https://example.com/file.zip --out myfile.zip

# Get task details
./scripts/client.py task task-123456

# Delete a task
./scripts/client.py delete task-123456

# List all workers
./scripts/client.py workers

# Get worker details
./scripts/client.py worker worker-123456
```

## Monitoring

You can monitor the system by:

1. Checking the dispatcher API:
   ```
   http://localhost:8000/status
   ```

2. Viewing the logs:
   ```bash
   # Docker logs
   docker-compose logs -f

   # Or individual service logs
   docker-compose logs -f dispatcher
   docker-compose logs -f worker1
   ``` 