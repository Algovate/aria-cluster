# Aria2c Cluster Task Dispatcher

A distributed system for managing and dispatching download tasks across multiple aria2c instances running on different machines.

## Features

- Central task dispatcher server
- Worker nodes that run aria2c instances
- RESTful API for task submission and management
- Real-time status monitoring
- Automatic task distribution based on worker load
- Fault tolerance and task recovery

## Project Structure

```
aria2c_cluster/
├── dispatcher/         # Central dispatcher server
├── worker/             # Worker node client
├── common/             # Shared code and utilities
├── config/             # Configuration files
└── scripts/            # Utility scripts
```

## Quick Start

The easiest way to get started is to use Docker Compose:

```bash
# Clone the repository
git clone https://github.com/yourusername/aria2c_cluster.git
cd aria2c_cluster

# Create necessary directories
python scripts/setup.py

# Build and start the containers
docker-compose up -d

# Check the logs
docker-compose logs -f
```

For more detailed instructions, see [RUNNING.md](RUNNING.md).

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure the system:
   - Edit `config/dispatcher.json` for the central server
   - Edit `config/worker.json` for each worker node

3. Start the dispatcher:
   ```
   python -m scripts.run_dispatcher
   ```

4. Start worker nodes:
   ```
   python -m scripts.run_worker
   ```

## API Documentation

The dispatcher exposes a RESTful API for task management:

- `POST /tasks` - Submit a new download task
- `GET /tasks` - List all tasks
- `GET /tasks/{task_id}` - Get task details
- `DELETE /tasks/{task_id}` - Cancel a task
- `GET /workers` - List all connected workers
- `GET /status` - Get system status

## Using the Client

The client script provides a command-line interface for interacting with the dispatcher:

```bash
# Get system status
./scripts/client.py status

# Create a new download task
./scripts/client.py create https://example.com/file.zip --out myfile.zip
```

## License

MIT 