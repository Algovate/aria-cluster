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
- Multiple database backends (in-memory and SQLite)
- API key authentication for security

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
├── scripts/          # Utility scripts
├── data/             # Database and persistent data
└── downloads/        # Download directories for workers
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
- [Database Configuration](docs/database.md) - Database options and migration
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

The dispatcher provides a RESTful API (requires API key authentication):

- `GET /api/status` - System status
- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{task_id}` - Task details
- `DELETE /api/tasks/{task_id}` - Cancel task
- `GET /api/workers` - List workers
- `GET /api/workers/{worker_id}` - Worker details

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
   http://localhost:8000/api/status
   ```
3. Docker logs:

   ```bash
   docker-compose logs -f
   ```

## Database Migration

To migrate between database types:

```bash
# Migrate from memory to SQLite
python scripts/migrate_database.py --source memory --target sqlite

# Migrate from SQLite to memory
python scripts/migrate_database.py --source sqlite --target memory
```

## License

MIT
