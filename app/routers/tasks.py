{% extends "base.html" %}

{% block title %}Task Processing - TaskFlow{% endblock %}
{% block page_title %}Task Processing{% endblock %}

{% block content %}
<div class="space-y-6" x-data="taskProcessingData()" x-init="init()">
    
    <!-- Action Bar -->
    <div class="flex justify-between items-center">
        <div class="flex space-x-3">
            <button @click="showExtractModal = true" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                <span>AI Extract Tasks</span>
            </button>
            <button @click="showCreateModal = true" class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                <span>Create Task</span>
            </button>
        </div>
        
        <div class="flex space-x-2">
            <select x-model="filterStatus" @change="fetchTasks()" class="border border-gray-300 rounded-lg px-3 py-2">
                <option value="">All Status</option>
                <option value="enabled">Enabled</option>
                <option value="disabled">Disabled</option>
            </select>
            
            <input x-model="searchQuery" @input="filterTasks()" type="text" placeholder="Search tasks..." class="border border-gray-300 rounded-lg px-3 py-2">
        </div>
    </div>
    
    <!-- Tasks Table -->
    <div class="bg-white rounded-xl shadow-sm overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Task Name</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Schedule</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Run</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                <template x-for="task in filteredTasks" :key="task.id">
                    <tr class="hover:bg-gray-50">
                        <td class="px-6 py-4">
                            <div class="text-sm font-medium text-gray-900" x-text="task.name"></div>
                            <div class="text-sm text-gray-500" x-text="task.description?.substring(0, 100) + '...'"></div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="px-2 py-1 text-xs font-medium rounded-full"
                                  :class="{
                                      'bg-blue-100 text-blue-800': task.task_type === 'http',
                                      'bg-purple-100 text-purple-800': task.task_type === 'shell',
                                      'bg-orange-100 text-orange-800': task.task_type === 'python',
                                      'bg-teal-100 text-teal-800': task.task_type === 'backup'
                                  }"
                                  x-text="task.task_type">
                            </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="task.cron_expression"></td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="px-2 py-1 text-xs font-medium rounded-full"
                                  :class="{
                                      'bg-green-100 text-green-800': task.is_enabled && !task.is_running,
                                      'bg-yellow-100 text-yellow-800': task.is_running,
                                      'bg-gray-100 text-gray-800': !task.is_enabled
                                  }"
                                  x-text="task.is_running ? 'Running' : (task.is_enabled ? 'Enabled' : 'Disabled')">
                            </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="formatDate(task.last_run_at)"></td>
                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button @click="runTask(task.id)" class="text-indigo-600 hover:text-indigo-900 mr-3">Run</button>
                            <button @click="editTask(task)" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                            <button @click="deleteTask(task.id)" class="text-red-600 hover:text-red-900">Delete</button>
                        </td>
                    </tr>
                </template>
                
                <tr x-show="filteredTasks.length === 0">
                    <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                        No tasks found. Use "AI Extract Tasks" to extract from messages or "Create Task" to add manually.
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <!-- AI Extract Tasks Modal -->
    <div x-show="showExtractModal" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center" x-cloak>
        <div class="bg-white rounded-xl shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" @click.away="closeExtractModal()">
            <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h3 class="text-lg font-semibold">AI Extract Tasks from Messages</h3>
                <button @click="closeExtractModal()" class="text-gray-400 hover:text-gray-600">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            
            <div class="p-6 space-y-4">
                <!-- Unprocessed Messages List -->
                <div>
                    <h4 class="font-medium text-gray-900 mb-3">Select Messages to Process</h4>
                    <div class="space-y-2 max-h-64 overflow-y-auto">
                        <template x-for="msg in unprocessedMessages" :key="msg.id">
                            <div class="flex items-start space-x-3 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                                 @click="toggleMessageSelection(msg.id)"
                                 :class="selectedMessages.includes(msg.id) ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'">
                                <input type="checkbox" :checked="selectedMessages.includes(msg.id)" class="mt-1 h-4 w-4 text-indigo-600">
                                <div class="flex-1">
                                    <div class="font-medium text-sm" x-text="msg.subject"></div>
                                    <div class="text-xs text-gray-500" x-text="msg.organization + ' - ' + msg.contact_person"></div>
                                </div>
                            </div>
                        </template>
                        
                        <div x-show="unprocessedMessages.length === 0" class="text-center text-gray-500 py-4">
                            No unprocessed messages. <a href="/messages" class="text-indigo-600 hover:underline">Import messages first</a>.
                        </div>
                    </div>
                </div>
                
                <!-- Extract Button -->
                <div class="flex justify-center">
                    <button @click="extractTasks()" 
                            :disabled="selectedMessages.length === 0 || isExtracting"
                            class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2">
                        <svg x-show="isExtracting" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span x-text="isExtracting ? 'Extracting...' : 'Extract Tasks with AI'"></span>
                    </button>
                </div>
                
                <!-- Extracted Tasks Preview -->
                <div x-show="extractedTasks.length > 0" class="border-t border-gray-200 pt-4">
                    <h4 class="font-medium text-gray-900 mb-3">Extracted Tasks Preview</h4>
                    <div class="space-y-3">
                        <template x-for="(task, index) in extractedTasks" :key="index">
                            <div class="p-4 border rounded-lg bg-gray-50">
                                <div class="flex justify-between items-start">
                                    <div>
                                        <div class="font-medium" x-text="task.name"></div>
                                        <div class="text-sm text-gray-600 mt-1" x-text="task.description?.substring(0, 150) + '...'"></div>
                                        <div class="flex space-x-2 mt-2">
                                            <span class="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded" x-text="task.task_type"></span>
                                            <span class="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded" x-text="task.priority"></span>
                                        </div>
                                    </div>
                                    <button @click="removeExtractedTask(index)" class="text-red-500 hover:text-red-700">
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                                    </button>
                                </div>
                            </div>
                        </template>
                    </div>
                    
                    <div class="flex justify-end space-x-3 mt-4">
                        <button @click="closeExtractModal()" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">Cancel</button>
                        <button @click="createExtractedTasks()" :disabled="isCreating" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                            Create All Tasks
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Create/Edit Task Modal -->
    <div x-show="showCreateModal || showEditModal" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center" x-cloak>
        <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4" @click.away="closeModal()">
            <div class="px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-semibold" x-text="editingId ? 'Edit Task' : 'Create Task'"></h3>
            </div>
            
            <div class="p-6 space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">Task Name</label>
                    <input x-model="form.name" type="text" class="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2">
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700">Description</label>
                    <textarea x-model="form.description" class="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2" rows="3"></textarea>
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700">Task Type</label>
                    <select x-model="form.task_type" class="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2">
                        <option value="http">HTTP Request</option>
                        <option value="shell">Shell Command</option>
                        <option value="python">Python Script</option>
                        <option value="backup">File Backup</option>
                    </select>
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700">Cron Expression</label>
                    <input x-model="form.cron_expression" type="text" placeholder="*/5 * * * *" class="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2">
                </div>
                
                <div class="flex items-center">
                    <input x-model="form.is_enabled" type="checkbox" class="h-4 w-4 text-indigo-600 border-gray-300 rounded">
                    <label class="ml-2 block text-sm text-gray-900">Enable Task</label>
                </div>
            </div>
            
            <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                <button @click="closeModal()" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">Cancel</button>
                <button @click="saveTask()" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Save</button>
            </div>
        </div>
    </div>
</div>

<script>
function taskProcessingData() {
    return {
        tasks: [],
        filteredTasks: [],
        searchQuery: '',
        filterStatus: '',
        
        // Extract modal
        showExtractModal: false,
        unprocessedMessages: [],
        selectedMessages: [],
        extractedTasks: [],
        isExtracting: false,
        isCreating: false,
        
        // Create/Edit modal
        showCreateModal: false,
        showEditModal: false,
        editingId: null,
        form: {
            name: '',
            description: '',
            task_type: 'shell',
            cron_expression: '0 0 * * *',
            is_enabled: true,
            config: {}
        },
        
        init() {
            this.fetchTasks();
            this.fetchUnprocessedMessages();
        },
        
        async fetchTasks() {
            try {
                const response = await fetch('/api/tasks/');
                this.tasks = await response.json();
                this.filterTasks();
            } catch (error) {
                console.error('Failed to fetch tasks:', error);
            }
        },
        
        async fetchUnprocessedMessages() {
            try {
                const response = await fetch('/api/messages/?is_processed=false');
                this.unprocessedMessages = await response.json();
            } catch (error) {
                console.error('Failed to fetch messages:', error);
            }
        },
        
        filterTasks() {
            let filtered = this.tasks;
            
            if (this.filterStatus === 'enabled') {
                filtered = filtered.filter(t => t.is_enabled);
            } else if (this.filterStatus === 'disabled') {
                filtered = filtered.filter(t => !t.is_enabled);
            }
            
            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                filtered = filtered.filter(t => 
                    t.name.toLowerCase().includes(query) ||
                    (t.description && t.description.toLowerCase().includes(query))
                );
            }
            
            this.filteredTasks = filtered;
        },
        
        toggleMessageSelection(msgId) {
            const index = this.selectedMessages.indexOf(msgId);
            if (index > -1) {
                this.selectedMessages.splice(index, 1);
            } else {
                this.selectedMessages.push(msgId);
            }
        },
        
        async extractTasks() {
            if (this.selectedMessages.length === 0) return;
            
            this.isExtracting = true;
            this.extractedTasks = [];
            
            try {
                for (const msgId of this.selectedMessages) {
                    const msg = this.unprocessedMessages.find(m => m.id === msgId);
                    if (!msg) continue;
                    
                    const response = await fetch('/api/ai/extract-tasks-from-message', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: msg })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success && data.tasks) {
                        this.extractedTasks.push(...data.tasks);
                    }
                }
            } catch (error) {
                console.error('Failed to extract tasks:', error);
                alert('Extraction failed. Please try again.');
            } finally {
                this.isExtracting = false;
            }
        },
        
        removeExtractedTask(index) {
            this.extractedTasks.splice(index, 1);
        },
        
        async createExtractedTasks() {
            this.isCreating = true;
            
            try {
                for (const task of this.extractedTasks) {
                    await fetch('/api/tasks/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(task)
                    });
                }
                
                // Mark messages as processed
                for (const msgId of this.selectedMessages) {
                    await fetch(`/api/messages/${msgId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ is_processed: true })
                    });
                }
                
                this.closeExtractModal();
                this.fetchTasks();
                this.fetchUnprocessedMessages();
                alert(`Created ${this.extractedTasks.length} tasks successfully!`);
                
            } catch (error) {
                console.error('Failed to create tasks:', error);
                alert('Failed to create some tasks.');
            } finally {
                this.isCreating = false;
            }
        },
        
        async saveTask() {
            const url = this.editingId ? `/api/tasks/${this.editingId}` : '/api/tasks/';
            const method = this.editingId ? 'PUT' : 'POST';
            
            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.form)
                });
                
                if (response.ok) {
                    this.closeModal();
                    this.fetchTasks();
                } else {
                    alert('Save failed');
                }
            } catch (error) {
                console.error('Failed to save task:', error);
            }
        },
        
        async runTask(id) {
            try {
                await fetch(`/api/tasks/${id}/run`, { method: 'POST' });
                alert('Task started');
            } catch (error) {
                console.error('Failed to run task:', error);
            }
        },
        
        editTask(task) {
            this.editingId = task.id;
            this.form = { ...task };
            this.showEditModal = true;
        },
        
        async deleteTask(id) {
            if (!confirm('Delete this task?')) return;
            
            try {
                await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
                this.fetchTasks();
            } catch (error) {
                console.error('Failed to delete task:', error);
            }
        },
        
        closeModal() {
            this.showCreateModal = false;
            this.showEditModal = false;
            this.editingId = null;
            this.form = {
                name: '',
                description: '',
                task_type: 'shell',
                cron_expression: '0 0 * * *',
                is_enabled: true,
                config: {}
            };
        },
        
        closeExtractModal() {
            this.showExtractModal = false;
            this.selectedMessages = [];
            this.extractedTasks = [];
        },
        
        formatDate(dateStr) {
            if (!dateStr) return 'Never';
            return new Date(dateStr).toLocaleString();
        }
    }
}
</script>

<style>
[x-cloak] { display: none !important; }
</style>
{% endblock %}
