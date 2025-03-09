# Aria Cluster

A distributed system for managing and dispatching download tasks across multiple aria2c instances running on different machines. The system consists of a central dispatcher server, worker nodes, and a modern web interface for easy management.

## Features

### Core Features

- Central task dispatcher server with RESTful API
- Distributed worker nodes running aria2c instances
- Automatic task distribution based on worker load
- Fault tolerance and task recovery
- Real-time status monitoring
- Tag-based worker assignment for task categorization

### Web Interface

- Modern, responsive web UI for system management
- Real-time dashboard with system metrics
- Task and worker management interface
- Dark mode support
- Mobile-friendly design

## Project Structure

```
aria_cluster/
├── dispatcher/         # Central dispatcher server
├── worker/            # Worker node client
├── web_ui/           # Web interface
├── common/           # Shared code and utilities
├── config/           # Configuration files
└── scripts/          # Utility scripts
```

## Quick Start

The easiest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/yourusername/aria_cluster.git
cd aria_cluster

# Create necessary directories
mkdir -p data downloads/worker1 downloads/worker2

# Build and start the containers
docker-compose up -d

# Access the web interface
open http://localhost:8080
```

## Documentation

- [Running Guide](docs/RUNNING.md) - Detailed instructions for running the system
- [Web UI Guide](web_ui/README.md) - Web interface documentation
- [Worker Tagging](docs/tagging.md) - Guide to using tag-based worker assignment
- API Documentation (see below)

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
2. Configure the system:

   - Edit `config/dispatcher.json` for the central server
   - Edit `config/worker.json` for each worker node
3. Start the components:

   ```bash
   # Start the dispatcher
   python -m scripts.run_dispatcher

   # Start worker nodes
   python -m scripts.run_worker
   ```

## API Documentation

The dispatcher provides a RESTful API:

- `GET /status` - System status
- `GET /tasks` - List all tasks
- `POST /tasks` - Create new task
- `GET /tasks/{task_id}` - Task details
- `DELETE /tasks/{task_id}` - Cancel task
- `GET /workers` - List workers

## Command Line Interface

The client script provides a CLI for system interaction:

```bash
# System status
./scripts/client.py status

# Create download task
./scripts/client.py create https://example.com/file.zip --out myfile.zip

# List tasks
./scripts/client.py tasks

# List workers
./scripts/client.py workers
```

## Monitoring

Monitor the system through:

1. Web Interface (Recommended):

   ```
   http://localhost:8080
   ```
2. API Endpoint:

   ```
   http://localhost:8000/status
   ```
3. Docker logs:

   ```bash
   docker-compose logs -f
   ```

## License

MIT
