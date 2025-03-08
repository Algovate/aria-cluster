# Aria2c Cluster Manager Web UI

A modern web interface for managing the Aria2c Cluster Task Dispatcher. This web UI provides a user-friendly way to interact with the RESTful API exposed by the dispatcher server.

## Features

- Dashboard with real-time system status
- Task management (create, view, update, delete)
- Worker monitoring
- Dark mode support
- Responsive design for desktop and mobile devices

## Installation

1. Copy the `web_ui` directory to your web server's document root, or serve it using any static file server.

2. No build step is required as the UI uses vanilla JavaScript and is loaded directly in the browser.

## Usage

### Accessing the UI

Open your web browser and navigate to the URL where you've hosted the web UI files.

### Configuration

On first load, you'll be prompted to enter your API key if the dispatcher requires authentication. You can also configure:

- Dispatcher URL (default: http://localhost:8000)
- Refresh interval (default: 5 seconds)
- Dark/light mode preference

All settings are stored in your browser's local storage.

### Dashboard

The dashboard provides an overview of your Aria2c Cluster:

- Active workers count
- Active downloads count
- Completed downloads count
- System load percentage
- Recent tasks table
- Worker status table

### Tasks Management

The Tasks page allows you to:

- View all download tasks
- Filter tasks by status
- Search tasks by URL or ID
- Create new download tasks
- View detailed task information
- Delete tasks

### Workers Management

The Workers page displays information about all worker nodes in the cluster:

- Worker status (online, busy, offline, error)
- Running tasks count
- Available download slots
- Worker load percentage
- Last heartbeat time

## API Interaction

The web UI communicates with the dispatcher server through its RESTful API. The following endpoints are used:

- `GET /status` - Fetch system status
- `GET /tasks` - List all tasks
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task details
- `DELETE /tasks/{task_id}` - Delete a task
- `GET /workers` - List all workers

## Customization

### Styling

The UI uses Bootstrap 5 for styling, with additional custom CSS in `styles.css`. You can modify the appearance by editing this file.

### Functionality

The core application logic is in `app.js`. All API interactions and UI updates are handled in this file.

## Browser Compatibility

The web UI is compatible with modern browsers:

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development

To extend or modify the UI:

1. Edit the HTML, CSS, and JavaScript files as needed
2. Test your changes in a browser
3. Deploy the updated files to your web server

## License

MIT 