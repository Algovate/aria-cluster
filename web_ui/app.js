// Aria2c Cluster Manager - Application Logic

// Configuration
let config = {
    apiUrl: localStorage.getItem('dispatcherUrl') || 'http://localhost:8000',
    apiKey: localStorage.getItem('apiKey') || '',
    refreshInterval: parseInt(localStorage.getItem('refreshInterval') || '5', 10),
    darkMode: localStorage.getItem('darkMode') === 'true'
};

// Global variables
let refreshTimerId = null;
let currentTaskId = null;
let currentSection = 'dashboard'; // Track which section is currently active
let lastRefreshTime = 0;
let workerRpcPorts = new Map(); // Map of worker IDs to their RPC ports

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    loadUserPreferences();

    // Check if API key is needed
    if (config.apiKey === '') {
        showApiKeyModal();
    } else {
        // Start loading data
        await refreshData();
        startAutoRefresh();
    }
});

// Event listeners setup
function setupEventListeners() {
    // Navigation
    document.getElementById('dashboard-link').addEventListener('click', () => switchSection('dashboard'));
    document.getElementById('tasks-link').addEventListener('click', () => switchSection('tasks'));
    document.getElementById('workers-link').addEventListener('click', () => switchSection('workers'));
    document.getElementById('direct-control-link').addEventListener('click', () => switchSection('direct-control'));
    document.getElementById('settings-link').addEventListener('click', () => switchSection('settings'));

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', refreshData);

    // New task button
    document.getElementById('new-task-btn').addEventListener('click', () => {
        document.getElementById('newTaskForm').reset();
        const newTaskModal = new bootstrap.Modal(document.getElementById('newTaskModal'));
        newTaskModal.show();
    });

    // Create task
    document.getElementById('submitTask').addEventListener('click', createNewTask);

    // API key modal
    document.getElementById('save-api-key').addEventListener('click', saveApiKey);

    // Settings
    document.getElementById('toggleApiKey').addEventListener('click', toggleApiKeyVisibility);
    document.getElementById('saveSettings').addEventListener('click', saveSettings);
    document.getElementById('saveUiSettings').addEventListener('click', saveUiSettings);
    document.getElementById('darkModeSwitch').addEventListener('change', toggleDarkMode);

    // Task filter
    document.getElementById('task-search').addEventListener('input', filterTasks);
    document.getElementById('task-status-filter').addEventListener('change', filterTasks);

    // Delete task
    document.getElementById('deleteTask').addEventListener('click', deleteCurrentTask);

    // Direct Control
    document.getElementById('openRpcModal').addEventListener('click', showRpcModal);
    document.getElementById('executeRpc').addEventListener('click', executeRpcCommand);
    document.getElementById('rpcMethod').addEventListener('change', handleRpcMethodChange);

    // Quick Actions
    document.querySelectorAll('.quick-action').forEach(button => {
        button.addEventListener('click', (e) => {
            const action = e.currentTarget.getAttribute('data-action');
            executeQuickAction(action);
        });
    });

    // RPC Method change handler
    document.getElementById('rpcMethod').addEventListener('change', function () {
        const customMethodContainer = document.getElementById('customMethodContainer');
        customMethodContainer.style.display = this.value === 'custom' ? 'block' : 'none';
    });
}

// Function to switch active section
function switchSection(sectionName) {
    // Update current section tracking
    currentSection = sectionName;

    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active-section');
    });

    // Show the selected section
    document.getElementById(`${sectionName}-section`).classList.add('active-section');

    // Update the page title
    document.getElementById('page-title').textContent = sectionName.charAt(0).toUpperCase() + sectionName.slice(1);

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.getElementById(`${sectionName}-link`).classList.add('active');

    // Refresh data for the new section
    refreshData();
}

// Load user preferences
function loadUserPreferences() {
    // Set field values from config
    document.getElementById('apiKeyInput').value = config.apiKey;
    document.getElementById('dispatcherUrl').value = config.apiUrl;
    document.getElementById('refreshInterval').value = config.refreshInterval;
    document.getElementById('darkModeSwitch').checked = config.darkMode;

    // Apply dark mode if enabled
    if (config.darkMode) {
        document.body.classList.add('dark-mode');
    }
}

// API Key Modal
function showApiKeyModal() {
    const apiKeyModal = new bootstrap.Modal(document.getElementById('apiKeyModal'));
    apiKeyModal.show();
}

// Save API Key
function saveApiKey() {
    const apiKey = document.getElementById('apiKey').value.trim();
    config.apiKey = apiKey;
    localStorage.setItem('apiKey', apiKey);

    // Close the modal
    const apiKeyModal = bootstrap.Modal.getInstance(document.getElementById('apiKeyModal'));
    apiKeyModal.hide();

    // Start loading data
    refreshData();
    startAutoRefresh();
}

// Toggle API Key visibility
function toggleApiKeyVisibility() {
    const apiKeyInput = document.getElementById('apiKeyInput');
    const toggleButton = document.getElementById('toggleApiKey').querySelector('i');

    if (apiKeyInput.type === 'password') {
        apiKeyInput.type = 'text';
        toggleButton.classList.remove('bi-eye');
        toggleButton.classList.add('bi-eye-slash');
    } else {
        apiKeyInput.type = 'password';
        toggleButton.classList.remove('bi-eye-slash');
        toggleButton.classList.add('bi-eye');
    }
}

// Save API settings
function saveSettings() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const apiUrl = document.getElementById('dispatcherUrl').value.trim();

    config.apiKey = apiKey;
    config.apiUrl = apiUrl;

    localStorage.setItem('apiKey', apiKey);
    localStorage.setItem('dispatcherUrl', apiUrl);

    showToast('Settings saved successfully');
    refreshData();
}

// Save UI settings
function saveUiSettings() {
    const refreshInterval = parseInt(document.getElementById('refreshInterval').value, 10);
    const darkMode = document.getElementById('darkModeSwitch').checked;

    config.refreshInterval = refreshInterval;
    config.darkMode = darkMode;

    localStorage.setItem('refreshInterval', refreshInterval.toString());
    localStorage.setItem('darkMode', darkMode.toString());

    // Restart auto-refresh with new interval
    stopAutoRefresh();
    startAutoRefresh();

    showToast('UI Settings saved successfully');
}

// Toggle dark mode
function toggleDarkMode() {
    const darkMode = document.getElementById('darkModeSwitch').checked;

    if (darkMode) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }

    config.darkMode = darkMode;
    localStorage.setItem('darkMode', darkMode.toString());
}

// Auto-refresh functionality
function startAutoRefresh() {
    if (refreshTimerId) {
        clearInterval(refreshTimerId);
    }

    refreshTimerId = setInterval(refreshData, config.refreshInterval * 1000);
}

function stopAutoRefresh() {
    if (refreshTimerId) {
        clearInterval(refreshTimerId);
        refreshTimerId = null;
    }
}

// API Interaction Functions
async function fetchWithAuth(endpoint, options = {}) {
    const url = `${config.apiUrl}${endpoint}`;

    // Default headers with API key
    const headers = {
        'Content-Type': 'application/json',
        ...(config.apiKey ? { 'X-API-Key': config.apiKey } : {})
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...headers,
                ...(options.headers || {})
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                showApiKeyModal();
                throw new Error('Authentication required');
            }
            throw new Error(`API error: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showToast(`API request failed: ${error.message}`, 'error');
        throw error;
    }
}

// Handle RPC method change
function handleRpcMethodChange() {
    const method = document.getElementById('rpcMethod').value;
    const customMethodContainer = document.getElementById('customMethodContainer');
    const paramsInput = document.getElementById('rpcParams');

    // Show/hide custom method input
    customMethodContainer.style.display = method === 'custom' ? 'block' : 'none';

    // Set default parameters based on method
    switch (method) {
        case 'aria2.tellWaiting':
        case 'aria2.tellStopped':
            paramsInput.value = '[0, 100]';
            break;
        case 'aria2.getGlobalOption':
        case 'aria2.getGlobalStat':
        case 'aria2.tellActive':
        case 'aria2.purgeDownloadResult':
            paramsInput.value = '[]';
            break;
        case 'aria2.changeGlobalOption':
            paramsInput.value = '[{"max-concurrent-downloads": "5"}]';
            break;
        default:
            if (method !== 'custom') {
                paramsInput.value = '[]';
            }
    }
}

// Data refreshing function
async function refreshData() {
    try {
        // Get system status
        const status = await fetchWithAuth('/status');
        updateDashboardStatus(status);

        // Get recent tasks
        const tasks = await fetchWithAuth('/tasks');
        updateRecentTasks(tasks);

        // Get worker status
        const workers = await fetchWithAuth('/workers');
        updateWorkerStatus(workers);

        // Update active downloads
        await updateActiveDownloads();

        // Update current section
        if (currentSection === 'tasks') {
            updateAllTasks(tasks);
        } else if (currentSection === 'workers') {
            updateAllWorkers(workers);
        } else if (currentSection === 'settings') {
            // Update task assignment strategy display
            updateTaskAssignmentStrategy(status.config?.task_assignment?.strategy || 'least_loaded');
        }

        // Hide loading indicator
        document.getElementById('loading-indicator').style.display = 'none';
    } catch (error) {
        console.error('Error refreshing data:', error);
        showToast('Error refreshing data', 'error');
    }
}

// Update dashboard status cards
function updateDashboardStatus(status) {
    document.getElementById('active-workers-count').textContent = status.active_workers;
    document.getElementById('active-downloads-count').textContent = status.tasks_by_status.downloading || 0;
    document.getElementById('completed-count').textContent = status.tasks_by_status.completed || 0;
    document.getElementById('system-load').textContent = `${status.system_load.toFixed(1)}%`;

    // If we're on the settings page, update the task assignment strategy
    if (currentSection === 'settings') {
        updateTaskAssignmentStrategy(status.config?.task_assignment?.strategy || 'least_loaded');
    }
}

// Update task assignment strategy display
function updateTaskAssignmentStrategy(strategy) {
    const strategyElement = document.getElementById('currentStrategy');
    const descriptionElement = document.getElementById('strategyDescription');

    strategyElement.textContent = strategy;

    // Set description based on strategy
    switch (strategy) {
        case 'least_loaded':
            descriptionElement.textContent = 'Assigns tasks to workers with the lowest load percentage';
            break;
        case 'round_robin':
            descriptionElement.textContent = 'Assigns tasks in sequence, rotating through available workers';
            break;
        case 'random':
            descriptionElement.textContent = 'Randomly selects a worker from available ones';
            break;
        case 'tags':
            descriptionElement.textContent = 'Matches tasks and workers based on matching key-value tags';
            break;
        default:
            descriptionElement.textContent = '';
    }

    // Highlight the current strategy in the list
    const listItems = document.querySelectorAll('.list-group-item');
    listItems.forEach(item => {
        if (item.textContent.includes(strategy)) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// Update recent tasks table on dashboard
function updateRecentTasks(tasks) {
    const table = document.getElementById('recent-tasks-table').querySelector('tbody');
    table.innerHTML = '';

    // Sort tasks by created_at (newest first) and take only the first 5
    const recentTasks = tasks
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5);

    if (recentTasks.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = 'No tasks available';
        cell.className = 'text-center';
        return;
    }

    recentTasks.forEach(task => {
        const row = table.insertRow();
        row.insertCell().textContent = task.id.substring(0, 8);

        const urlCell = row.insertCell();
        urlCell.textContent = formatUrl(task.url);
        urlCell.title = task.url;

        const statusCell = row.insertCell();
        statusCell.textContent = task.status;
        statusCell.className = `status-${task.status}`;

        const progressCell = row.insertCell();
        progressCell.innerHTML = `
            <div class="progress">
                <div class="progress-bar" role="progressbar" style="width: ${task.progress}%"></div>
            </div>
            <small>${task.progress.toFixed(1)}%</small>
        `;

        // Add click event to show task details
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => showTaskDetails(task.id));
    });
}

// Update worker status table on dashboard
function updateWorkerStatus(workers) {
    const table = document.getElementById('workers-table').querySelector('tbody');
    table.innerHTML = '';

    // Update worker RPC ports map
    workerRpcPorts.clear();
    workers.forEach(worker => {
        workerRpcPorts.set(worker.id, worker.port);
    });

    if (workers.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = 'No workers available';
        cell.className = 'text-center';
        return;
    }

    workers.forEach(worker => {
        const row = table.insertRow();
        row.insertCell().textContent = worker.hostname;

        const statusCell = row.insertCell();
        statusCell.textContent = worker.status;
        statusCell.className = `worker-${worker.status}`;

        row.insertCell().textContent = `${worker.used_slots}/${worker.total_slots}`;
        row.insertCell().textContent = `${worker.load_percentage.toFixed(1)}%`;

        // Add click event to show worker details
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => showWorkerDetails(worker.id));
    });

    // Update active downloads worker filter
    const workerFilter = document.getElementById('activeDownloadsWorkerFilter');
    if (workerFilter) {
        const currentValue = workerFilter.value;
        workerFilter.innerHTML = '<option value="all">All Workers</option>';
        workers.forEach(worker => {
            const option = document.createElement('option');
            option.value = worker.id;
            option.textContent = worker.hostname;
            workerFilter.appendChild(option);
        });
        if (currentValue && Array.from(workerFilter.options).some(opt => opt.value === currentValue)) {
            workerFilter.value = currentValue;
        }
    }
}

// Update all tasks table on tasks section
function updateAllTasks(tasks) {
    const table = document.getElementById('all-tasks-table').querySelector('tbody');
    table.innerHTML = '';

    if (tasks.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 8;
        cell.textContent = 'No tasks available';
        cell.className = 'text-center';
        return;
    }

    // Sort tasks by created_at (newest first)
    const sortedTasks = tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    sortedTasks.forEach(task => {
        const row = table.insertRow();
        row.setAttribute('data-task-id', task.id);
        row.setAttribute('data-task-status', task.status);
        row.setAttribute('data-task-url', task.url);

        row.insertCell().textContent = task.id.substring(0, 8);

        const urlCell = row.insertCell();
        urlCell.textContent = formatUrl(task.url);
        urlCell.title = task.url;

        const statusCell = row.insertCell();
        statusCell.textContent = task.status;
        statusCell.className = `status-${task.status}`;

        row.insertCell().textContent = task.worker_id ? task.worker_id.substring(0, 8) : '-';

        const progressCell = row.insertCell();
        progressCell.innerHTML = `
            <div class="progress">
                <div class="progress-bar ${task.status === 'failed' ? 'bg-danger' : ''}" role="progressbar" style="width: ${task.progress}%"></div>
            </div>
            <small>${task.progress.toFixed(1)}%</small>
        `;

        const speedCell = row.insertCell();
        speedCell.textContent = task.download_speed ? formatSpeed(task.download_speed) : '-';

        const createdCell = row.insertCell();
        createdCell.textContent = formatDate(task.created_at);
        createdCell.title = new Date(task.created_at).toLocaleString();

        const actionsCell = row.insertCell();
        actionsCell.className = 'action-buttons';
        actionsCell.innerHTML = `
            <button class="btn btn-sm btn-outline-info view-task" data-task-id="${task.id}">
                <i class="bi bi-eye"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger delete-task" data-task-id="${task.id}">
                <i class="bi bi-trash"></i>
            </button>
        `;

        // Add event listeners for action buttons
        actionsCell.querySelector('.view-task').addEventListener('click', (e) => {
            e.stopPropagation();
            showTaskDetails(task.id);
        });

        actionsCell.querySelector('.delete-task').addEventListener('click', (e) => {
            e.stopPropagation();
            confirmDeleteTask(task.id);
        });

        // Add click event to show task details
        row.addEventListener('click', () => showTaskDetails(task.id));
    });

    // Apply current filter
    filterTasks();
}

// Update all workers table on workers section
function updateAllWorkers(workers) {
    const table = document.getElementById('all-workers-table').querySelector('tbody');
    table.innerHTML = '';

    // Update worker RPC ports map
    workerRpcPorts.clear();
    workers.forEach(worker => {
        workerRpcPorts.set(worker.id, worker.port);
    });

    if (workers.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 8;
        cell.textContent = 'No workers available';
        cell.className = 'text-center';
        return;
    }

    workers.forEach(worker => {
        const row = table.insertRow();

        row.insertCell().textContent = worker.id.substring(0, 8);
        row.insertCell().textContent = worker.hostname;
        row.insertCell().textContent = worker.address;

        const statusCell = row.insertCell();
        statusCell.textContent = worker.status;
        statusCell.className = `worker-${worker.status}`;

        row.insertCell().textContent = worker.current_tasks.length;
        row.insertCell().textContent = worker.available_slots;
        row.insertCell().textContent = `${worker.load_percentage.toFixed(1)}%`;

        const heartbeatCell = row.insertCell();
        heartbeatCell.textContent = worker.last_heartbeat ? formatDate(worker.last_heartbeat) : '-';
        heartbeatCell.title = worker.last_heartbeat ? new Date(worker.last_heartbeat).toLocaleString() : '';

        // Add click event to show worker details
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => showWorkerDetails(worker.id));
    });

    // Update active downloads worker filter
    const workerFilter = document.getElementById('activeDownloadsWorkerFilter');
    if (workerFilter) {
        const currentValue = workerFilter.value;
        workerFilter.innerHTML = '<option value="all">All Workers</option>';
        workers.forEach(worker => {
            const option = document.createElement('option');
            option.value = worker.id;
            option.textContent = worker.hostname;
            workerFilter.appendChild(option);
        });
        if (currentValue && Array.from(workerFilter.options).some(opt => opt.value === currentValue)) {
            workerFilter.value = currentValue;
        }
    }
}

// Filter tasks based on search and status filter
function filterTasks() {
    const searchValue = document.getElementById('task-search').value.toLowerCase();
    const statusFilter = document.getElementById('task-status-filter').value;

    const rows = document.getElementById('all-tasks-table').querySelectorAll('tbody tr');

    rows.forEach(row => {
        const taskId = row.getAttribute('data-task-id') || '';
        const taskStatus = row.getAttribute('data-task-status') || '';
        const taskUrl = row.getAttribute('data-task-url') || '';

        const matchesSearch = taskId.toLowerCase().includes(searchValue) ||
            taskUrl.toLowerCase().includes(searchValue);

        const matchesStatus = statusFilter === 'all' || taskStatus === statusFilter;

        if (matchesSearch && matchesStatus) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Show task details modal
async function showTaskDetails(taskId) {
    try {
        currentTaskId = taskId;
        const task = await fetchWithAuth(`/tasks/${taskId}`);

        const modalContent = document.getElementById('taskDetailContent');

        // Format created and updated dates
        const createdDate = new Date(task.created_at).toLocaleString();
        const updatedDate = new Date(task.updated_at).toLocaleString();

        // Build HTML content
        let html = `
            <div class="row">
                <div class="col-md-6">
                    <p class="task-detail-label">Task ID:</p>
                    <p class="task-detail-value">${task.id}</p>
                </div>
                <div class="col-md-6">
                    <p class="task-detail-label">Status:</p>
                    <p class="task-detail-value status-${task.status}">${task.status}</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-12">
                    <p class="task-detail-label">URL:</p>
                    <p class="task-detail-value"><a href="${task.url}" target="_blank">${task.url}</a></p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <p class="task-detail-label">Created:</p>
                    <p class="task-detail-value">${createdDate}</p>
                </div>
                <div class="col-md-6">
                    <p class="task-detail-label">Last Updated:</p>
                    <p class="task-detail-value">${updatedDate}</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <p class="task-detail-label">Worker:</p>
                    <p class="task-detail-value">${task.worker_id || '-'}</p>
                </div>
                <div class="col-md-6">
                    <p class="task-detail-label">aria2 GID:</p>
                    <p class="task-detail-value">${task.aria2_gid || '-'}</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-12">
                    <p class="task-detail-label">Progress:</p>
                    <div class="progress mb-2">
                        <div class="progress-bar ${task.status === 'failed' ? 'bg-danger' : ''}"
                             role="progressbar" style="width: ${task.progress}%"></div>
                    </div>
                    <p class="task-detail-value">${task.progress.toFixed(1)}%</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <p class="task-detail-label">Download Speed:</p>
                    <p class="task-detail-value">${task.download_speed ? formatSpeed(task.download_speed) : '-'}</p>
                </div>
            </div>
        `;

        // Add options if available
        if (task.options && Object.keys(task.options).length > 0) {
            // Extract tags for special display
            const tags = task.options.tags || {};
            const otherOptions = { ...task.options };
            delete otherOptions.tags;

            // Display tags if they exist
            if (Object.keys(tags).length > 0) {
                html += `
                    <div class="row">
                        <div class="col-md-12">
                            <p class="task-detail-label">Tags:</p>
                            <div class="task-detail-value">
                                ${Object.entries(tags).map(([key, value]) =>
                    `<span class="badge bg-info me-1">${key}: ${value}</span>`
                ).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }

            // Display other options
            if (Object.keys(otherOptions).length > 0) {
                html += `
                    <div class="row">
                        <div class="col-md-12">
                            <p class="task-detail-label">Options:</p>
                            <pre class="task-detail-value">${JSON.stringify(otherOptions, null, 2)}</pre>
                        </div>
                    </div>
                `;
            }
        }

        // Add error message if available
        if (task.error_message) {
            html += `
                <div class="row">
                    <div class="col-md-12">
                        <p class="task-detail-label">Error:</p>
                        <p class="task-detail-value text-danger">${task.error_message}</p>
                    </div>
                </div>
            `;
        }

        // Add result if available
        if (task.result) {
            html += `
                <div class="row">
                    <div class="col-md-12">
                        <p class="task-detail-label">Result:</p>
                        <pre class="task-detail-value">${JSON.stringify(task.result, null, 2)}</pre>
                    </div>
                </div>
            `;
        }

        modalContent.innerHTML = html;

        // Show delete button only for non-completed tasks
        const deleteButton = document.getElementById('deleteTask');
        if (task.status === 'completed') {
            deleteButton.style.display = 'none';
        } else {
            deleteButton.style.display = 'block';
        }

        // Show the modal
        const taskDetailModal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
        taskDetailModal.show();

    } catch (error) {
        console.error('Error fetching task details:', error);
        showToast('Error fetching task details', 'error');
    }
}

// Show worker details
async function showWorkerDetails(workerId) {
    try {
        const worker = await fetchWithAuth(`/workers/${workerId}`);

        const modalContent = document.getElementById('workerDetailContent');

        // Format dates
        const connectedDate = worker.connected_at ? new Date(worker.connected_at).toLocaleString() : 'N/A';
        const lastHeartbeat = worker.last_heartbeat ? new Date(worker.last_heartbeat).toLocaleString() : 'N/A';

        // Build HTML content
        let html = `
            <div class="row">
                <div class="col-md-6">
                    <p class="worker-detail-label">Worker ID:</p>
                    <p class="worker-detail-value">${worker.id}</p>
                </div>
                <div class="col-md-6">
                    <p class="worker-detail-label">Status:</p>
                    <p class="worker-detail-value status-${worker.status.toLowerCase()}">${worker.status}</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <p class="worker-detail-label">Hostname:</p>
                    <p class="worker-detail-value">${worker.hostname}</p>
                </div>
                <div class="col-md-6">
                    <p class="worker-detail-label">Address:</p>
                    <p class="worker-detail-value">${worker.address}:${worker.port}</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <p class="worker-detail-label">Connected At:</p>
                    <p class="worker-detail-value">${connectedDate}</p>
                </div>
                <div class="col-md-6">
                    <p class="worker-detail-label">Last Heartbeat:</p>
                    <p class="worker-detail-value">${lastHeartbeat}</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <p class="worker-detail-label">Slots:</p>
                    <p class="worker-detail-value">${worker.used_slots} / ${worker.total_slots}</p>
                </div>
                <div class="col-md-6">
                    <p class="worker-detail-label">Load:</p>
                    <p class="worker-detail-value">${worker.load_percentage.toFixed(1)}%</p>
                </div>
            </div>
        `;

        // Add tags if available
        if (worker.capabilities && worker.capabilities.tags) {
            const tags = worker.capabilities.tags;
            html += `
                <div class="row">
                    <div class="col-md-12">
                        <p class="worker-detail-label">Tags:</p>
                        <div class="worker-detail-value">
                            ${Object.entries(tags).map(([key, value]) =>
                `<span class="badge bg-info me-1">${key}: ${value}</span>`
            ).join('')}
                        </div>
                    </div>
                </div>
            `;
        }

        // Add other capabilities
        if (worker.capabilities) {
            const otherCapabilities = { ...worker.capabilities };
            delete otherCapabilities.tags;

            if (Object.keys(otherCapabilities).length > 0) {
                html += `
                    <div class="row">
                        <div class="col-md-12">
                            <p class="worker-detail-label">Capabilities:</p>
                            <pre class="worker-detail-value">${JSON.stringify(otherCapabilities, null, 2)}</pre>
                        </div>
                    </div>
                `;
            }
        }

        // Add current tasks
        if (worker.current_tasks && worker.current_tasks.length > 0) {
            html += `
                <div class="row">
                    <div class="col-md-12">
                        <p class="worker-detail-label">Current Tasks:</p>
                        <ul class="worker-detail-value">
                            ${worker.current_tasks.map(taskId =>
                `<li><a href="#" class="task-link" data-task-id="${taskId}">${taskId}</a></li>`
            ).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }

        // Add health metrics
        if (worker.health_metrics) {
            html += `
                <div class="row">
                    <div class="col-md-12">
                        <p class="worker-detail-label">Health Metrics:</p>
                        <div class="row">
                            <div class="col-md-4">
                                <p>CPU: ${worker.health_metrics.cpu_usage.toFixed(1)}%</p>
                            </div>
                            <div class="col-md-4">
                                <p>Memory: ${worker.health_metrics.memory_usage.toFixed(1)}%</p>
                            </div>
                            <div class="col-md-4">
                                <p>Disk: ${worker.health_metrics.disk_usage.toFixed(1)}%</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        modalContent.innerHTML = html;

        // Add event listeners to task links
        const taskLinks = modalContent.querySelectorAll('.task-link');
        taskLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const taskId = link.getAttribute('data-task-id');
                // Close this modal
                const workerModal = bootstrap.Modal.getInstance(document.getElementById('workerDetailModal'));
                workerModal.hide();
                // Show task details
                showTaskDetails(taskId);
            });
        });

        // Show the modal
        const workerDetailModal = new bootstrap.Modal(document.getElementById('workerDetailModal'));
        workerDetailModal.show();

    } catch (error) {
        console.error('Error fetching worker details:', error);
        showToast('Error fetching worker details', 'error');
    }
}

// Create a new task
async function createNewTask() {
    const url = document.getElementById('taskUrl').value.trim();
    const filename = document.getElementById('outputFilename').value.trim();
    const maxConnections = parseInt(document.getElementById('maxConnections').value, 10);
    const tagsInput = document.getElementById('taskTags').value.trim();
    const priority = parseInt(document.getElementById('taskPriority').value, 10);

    if (!url) {
        showToast('URL is required', 'error');
        return;
    }

    const options = {};

    if (filename) {
        options.out = filename;
    }

    options['max-connection-per-server'] = maxConnections;

    // Add priority
    options.priority = priority;

    // Parse and add tags if provided
    if (tagsInput) {
        try {
            const tags = JSON.parse(tagsInput);
            options.tags = tags;
        } catch (e) {
            showToast('Invalid JSON format for tags', 'error');
            return;
        }
    }

    try {
        const newTask = await fetchWithAuth('/tasks', {
            method: 'POST',
            body: JSON.stringify({
                url: url,
                options: options
            })
        });

        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('newTaskModal'));
        modal.hide();

        showToast('Task created successfully');

        // Refresh the tasks list
        await refreshData();

        // Show the task details
        showTaskDetails(newTask.id);

    } catch (error) {
        console.error('Error creating task:', error);
        showToast('Error creating task', 'error');
    }
}

// Delete task confirmation
function confirmDeleteTask(taskId) {
    if (confirm('Are you sure you want to delete this task?')) {
        deleteTask(taskId);
    }
}

// Delete current task from the task details modal
function deleteCurrentTask() {
    if (currentTaskId && confirm('Are you sure you want to delete this task?')) {
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('taskDetailModal'));
        modal.hide();

        // Delete the task
        deleteTask(currentTaskId);
    }
}

// Delete a task
async function deleteTask(taskId) {
    try {
        await fetchWithAuth(`/tasks/${taskId}`, {
            method: 'DELETE'
        });

        showToast('Task deleted successfully');

        // Refresh the tasks list
        await refreshData();

    } catch (error) {
        console.error('Error deleting task:', error);
        showToast('Error deleting task', 'error');
    }
}

// Utility functions
function formatUrl(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname + urlObj.pathname.substring(0, 20) + (urlObj.pathname.length > 20 ? '...' : '');
    } catch (e) {
        return url.substring(0, 30) + (url.length > 30 ? '...' : '');
    }
}

function formatSpeed(bytesPerSec) {
    if (!bytesPerSec) return '-';

    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let speed = bytesPerSec;
    let unitIndex = 0;

    while (speed >= 1024 && unitIndex < units.length - 1) {
        speed /= 1024;
        unitIndex++;
    }

    return `${speed.toFixed(1)} ${units[unitIndex]}`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) {
        return 'just now';
    } else if (diffMin < 60) {
        return `${diffMin}m ago`;
    } else if (diffHour < 24) {
        return `${diffHour}h ago`;
    } else if (diffDay < 7) {
        return `${diffDay}d ago`;
    } else {
        return date.toLocaleDateString();
    }
}

// Toast notification
function showToast(message, type = 'success') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center ${type === 'error' ? 'text-bg-danger' : 'text-bg-success'}`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');

    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toastElement);

    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();

    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Direct Control Functions

// Show RPC Modal
function showRpcModal() {
    // Populate worker select
    const workerSelect = document.getElementById('workerSelect');
    workerSelect.innerHTML = '';

    // Add "All Workers" option for applicable commands
    const allWorkersOption = document.createElement('option');
    allWorkersOption.value = 'all';
    allWorkersOption.textContent = 'All Workers';
    workerSelect.appendChild(allWorkersOption);

    // Add individual workers
    workerRpcPorts.forEach((port, workerId) => {
        const option = document.createElement('option');
        option.value = workerId;
        option.textContent = `Worker ${workerId}`;
        workerSelect.appendChild(option);
    });

    const modal = new bootstrap.Modal(document.getElementById('directRpcModal'));
    modal.show();
}

// Execute RPC Command
async function executeRpcCommand() {
    const method = document.getElementById('rpcMethod').value === 'custom'
        ? document.getElementById('customMethod').value
        : document.getElementById('rpcMethod').value;

    let params;
    try {
        params = JSON.parse(document.getElementById('rpcParams').value || '[]');
    } catch (e) {
        showToast('Invalid JSON parameters', 'error');
        return;
    }

    const workerId = document.getElementById('workerSelect').value;

    try {
        let results;
        if (workerId === 'all') {
            // Execute on all workers
            results = await Promise.all(
                Array.from(workerRpcPorts.entries()).map(([id, port]) =>
                    sendRpcRequest(id, port, method, params)
                )
            );
        } else {
            // Execute on single worker
            results = await sendRpcRequest(workerId, workerRpcPorts.get(workerId), method, params);
        }

        showRpcResult(results);

    } catch (error) {
        console.error('RPC execution failed:', error);
        showToast('RPC execution failed: ' + error.message, 'error');
    }
}

// Send RPC Request
async function sendRpcRequest(workerId, port, method, params) {
    const rpcRequest = {
        jsonrpc: '2.0',
        id: Date.now(),
        method: method,
        params: params
    };

    try {
        const response = await fetch(`http://localhost:${port}/jsonrpc`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(rpcRequest)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        if (result.error) {
            throw new Error(result.error.message);
        }

        return {
            workerId: workerId,
            result: result.result
        };

    } catch (error) {
        console.error(`RPC request to worker ${workerId} failed:`, error);
        throw error;
    }
}

// Show RPC Result
function showRpcResult(results) {
    const resultModal = new bootstrap.Modal(document.getElementById('rpcResultModal'));
    const resultContent = document.getElementById('rpcResultContent');

    if (Array.isArray(results)) {
        // Multiple worker results
        resultContent.textContent = JSON.stringify(results, null, 2);
    } else {
        // Single worker result
        resultContent.textContent = JSON.stringify(results.result, null, 2);
    }

    resultModal.show();
}

// Execute Quick Action
async function executeQuickAction(action) {
    const workerId = document.getElementById('activeDownloadsWorkerFilter').value;

    let method, params;
    switch (action) {
        case 'getGlobalStat':
            method = 'aria2.getGlobalStat';
            params = [];
            break;
        case 'tellActive':
            method = 'aria2.tellActive';
            params = [];
            break;
        case 'tellWaiting':
            method = 'aria2.tellWaiting';
            params = [0, 100];
            break;
        case 'tellStopped':
            method = 'aria2.tellStopped';
            params = [0, 100];
            break;
        case 'purgeDownloadResult':
            if (!confirm('Are you sure you want to purge download results?')) {
                return;
            }
            method = 'aria2.purgeDownloadResult';
            params = [];
            break;
        default:
            showToast('Unknown action', 'error');
            return;
    }

    try {
        let results;
        if (workerId === 'all') {
            results = await Promise.all(
                Array.from(workerRpcPorts.entries()).map(([id, port]) =>
                    sendRpcRequest(id, port, method, params)
                )
            );
        } else {
            results = await sendRpcRequest(workerId, workerRpcPorts.get(workerId), method, params);
        }

        showRpcResult(results);

        // Refresh active downloads table if needed
        if (['tellActive', 'purgeDownloadResult'].includes(action)) {
            await updateActiveDownloads();
        }

    } catch (error) {
        console.error('Quick action failed:', error);
        showToast('Quick action failed: ' + error.message, 'error');
    }
}

// Update Active Downloads Table
async function updateActiveDownloads() {
    const table = document.getElementById('active-downloads-table').querySelector('tbody');
    table.innerHTML = '';

    try {
        const activeDownloads = [];

        // Fetch active downloads from all workers
        await Promise.all(Array.from(workerRpcPorts.entries()).map(async ([workerId, port]) => {
            try {
                const result = await sendRpcRequest(workerId, port, 'aria2.tellActive', []);
                result.result.forEach(download => {
                    activeDownloads.push({
                        ...download,
                        workerId: workerId
                    });
                });
            } catch (error) {
                console.error(`Failed to fetch active downloads from worker ${workerId}:`, error);
            }
        }));

        if (activeDownloads.length === 0) {
            const row = table.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 7;
            cell.textContent = 'No active downloads';
            cell.className = 'text-center';
            return;
        }

        activeDownloads.forEach(download => {
            const row = table.insertRow();

            row.insertCell().textContent = download.gid;
            row.insertCell().textContent = download.files[0]?.path || 'N/A';
            row.insertCell().textContent = formatBytes(download.totalLength);

            const progressCell = row.insertCell();
            const progress = (download.completedLength / download.totalLength) * 100;
            progressCell.innerHTML = `
                <div class="progress">
                    <div class="progress-bar" role="progressbar" style="width: ${progress}%"></div>
                </div>
                <small>${progress.toFixed(1)}%</small>
            `;

            row.insertCell().textContent = formatSpeed(download.downloadSpeed);
            row.insertCell().textContent = download.workerId;

            const actionsCell = row.insertCell();
            actionsCell.className = 'action-buttons';
            actionsCell.innerHTML = `
                <button class="btn btn-sm btn-outline-warning pause-download" data-gid="${download.gid}" data-worker="${download.workerId}">
                    <i class="bi bi-pause"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger remove-download" data-gid="${download.gid}" data-worker="${download.workerId}">
                    <i class="bi bi-x"></i>
                </button>
            `;

            // Add event listeners for action buttons
            actionsCell.querySelector('.pause-download').addEventListener('click', (e) => {
                e.stopPropagation();
                pauseDownload(download.gid, download.workerId);
            });

            actionsCell.querySelector('.remove-download').addEventListener('click', (e) => {
                e.stopPropagation();
                removeDownload(download.gid, download.workerId);
            });
        });

    } catch (error) {
        console.error('Failed to update active downloads:', error);
        showToast('Failed to update active downloads', 'error');
    }
}

// Pause Download
async function pauseDownload(gid, workerId) {
    try {
        await sendRpcRequest(workerId, workerRpcPorts.get(workerId), 'aria2.pause', [gid]);
        showToast('Download paused successfully');
        await updateActiveDownloads();
    } catch (error) {
        console.error('Failed to pause download:', error);
        showToast('Failed to pause download: ' + error.message, 'error');
    }
}

// Remove Download
async function removeDownload(gid, workerId) {
    if (!confirm('Are you sure you want to remove this download?')) {
        return;
    }

    try {
        await sendRpcRequest(workerId, workerRpcPorts.get(workerId), 'aria2.remove', [gid]);
        showToast('Download removed successfully');
        await updateActiveDownloads();
    } catch (error) {
        console.error('Failed to remove download:', error);
        showToast('Failed to remove download: ' + error.message, 'error');
    }
}

// Format Bytes
function formatBytes(bytes) {
    if (!bytes) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = parseInt(bytes, 10);
    let unitIndex = 0;

    while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024;
        unitIndex++;
    }

    return `${value.toFixed(1)} ${units[unitIndex]}`;
}