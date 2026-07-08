/**
 * 本地办公工作台 - 前端交互脚本
 * 包含所有模块的API调用和UI交互
 */

// ==================== API基础配置 ====================
const API_BASE = '/api';

// ==================== 认证状态管理 ====================
let isAuthenticated = false;

async function checkAuth() {
    const result = await apiRequest('/check_auth');
    if (result.code === 0 && result.authenticated) {
        isAuthenticated = true;
    } else {
        isAuthenticated = false;
    }
    return isAuthenticated;
}

async function login(password) {
    const result = await apiRequest('/login', 'POST', { password });
    if (result.code === 0) {
        isAuthenticated = true;
        showMessage('登录成功', 'success');
        location.reload();
    } else {
        showMessage(result.message || '登录失败', 'error');
    }
}

async function logout() {
    const result = await apiRequest('/logout', 'POST');
    if (result.code === 0) {
        isAuthenticated = false;
        location.href = '/login';
    }
}

async function changePassword(oldPassword, newPassword) {
    const result = await apiRequest('/change_password', 'POST', { old_password: oldPassword, new_password: newPassword });
    if (result.code === 0) {
        showMessage('密码修改成功', 'success');
        closeAllModals();
    } else {
        showMessage(result.message || '修改失败', 'error');
    }
}

function openChangePasswordModal() {
    openModal('changePasswordModal');
}

function handleChangePassword(e) {
    e.preventDefault();
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (newPassword !== confirmPassword) {
        showMessage('两次输入的密码不一致', 'error');
        return;
    }
    
    if (newPassword.length < 6) {
        showMessage('密码长度不能少于6位', 'error');
        return;
    }
    
    changePassword(oldPassword, newPassword);
}

// ==================== 工具函数 ====================
/**
 * 发送API请求
 */
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(API_BASE + url, options);
        const result = await response.json();
        
        if (result.code === 401) {
            isAuthenticated = false;
            location.href = '/login';
            return { code: 401, message: '未授权' };
        }
        
        return result;
    } catch (error) {
        console.error('API请求错误:', error);
        return { code: 1, message: '网络请求失败' };
    }
}

/**
 * 格式化日期时间
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * 格式化日期
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN');
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 获取标签样式类
 */
function getTagClass(tag) {
    const tagMap = {
        '紧急': 'tag-urgent',
        '重要': 'tag-important',
        '一般': 'tag-normal'
    };
    return tagMap[tag] || 'tag-normal';
}

/**
 * 获取状态样式类
 */
function getStatusClass(status) {
    const statusMap = {
        '未开始': 'status-pending',
        '进行中': 'status-progress',
        '完成': 'status-completed',
        '延期': 'status-delayed',
        '未完成': 'status-pending',
        '已完成': 'status-completed'
    };
    return statusMap[status] || 'status-pending';
}

/**
 * 显示提示消息
 */
function showMessage(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 24px;
        border-radius: 6px;
        color: #fff;
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    
    const colors = {
        success: '#48bb78',
        error: '#f56565',
        info: '#4299e1',
        warning: '#ed8936'
    };
    toast.style.background = colors[type] || colors.info;
    
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== 模态框管理 ====================
let currentModal = null;

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        currentModal = modal;
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        currentModal = null;
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.classList.remove('active');
    });
    currentModal = null;
}

// ==================== 待办任务模块 ====================
const TodoModule = {
    tasks: [],
    currentTaskId: null,
    
    /**
     * 初始化模块
     */
    init() {
        this.loadTasks();
        this.bindEvents();
    },
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 搜索和筛选
        document.getElementById('searchInput')?.addEventListener('input', () => this.filterTasks());
        document.getElementById('filterTag')?.addEventListener('change', () => this.filterTasks());
        document.getElementById('filterTeam')?.addEventListener('change', () => this.filterTasks());
        document.getElementById('filterPerson')?.addEventListener('change', () => this.filterTasks());
        document.getElementById('filterStatus')?.addEventListener('change', () => this.filterTasks());
        document.getElementById('filterSort')?.addEventListener('change', () => this.filterTasks());
        
        // 表单提交
        document.getElementById('taskForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveTask();
        });
        
        // 关闭模态框
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => closeAllModals());
        });
    },
    
    /**
     * 加载任务列表
     */
    async loadTasks() {
        const result = await apiRequest('/tasks');
        if (result.code === 0) {
            this.tasks = result.data;
            this.renderTasks();
            this.loadFilterOptions();
        }
    },
    
    /**
     * 渲染任务列表（紧凑布局）
     */
    renderTasks() {
        const container = document.getElementById('taskList');
        if (!container) return;
        
        if (this.tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <div class="empty-state-text">暂无待办任务</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.tasks.map(task => `
            <div class="card task-card compact" data-id="${task.id}" onclick="toggleCollapse(${task.id})">
                <div class="card-body">
                    <div class="task-header">
                        <div class="task-main">
                            <span class="tag ${getTagClass(task.tag)}">${task.tag || '一般'}</span>
                            <span class="tag ${getStatusClass(task.status)}">${task.status}</span>
                            <span class="task-summary">${task.summary}</span>
                        </div>
                        <div class="task-meta">
                            ${task.deadline ? `<span class="task-deadline">${formatDate(task.deadline)}</span>` : ''}
                            <span class="expand-icon">▶</span>
                            <div class="btn-group btn-group-sm">
                                ${task.status === '未完成' ? `<button class="btn btn-success btn-sm" onclick="event.stopPropagation(); TodoModule.completeTask(${task.id})">完成</button>` : ''}
                                <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); TodoModule.editTask(${task.id})">编辑</button>
                                <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); TodoModule.deleteTask(${task.id})">删除</button>
                            </div>
                        </div>
                    </div>
                    <div class="collapse-content" id="collapse-${task.id}">
                        ${task.detail_content ? `<p><strong>详细内容：</strong>${task.detail_content}</p>` : ''}
                        ${task.deadline ? `<p><strong>截止时间：</strong>${formatDateTime(task.deadline)}</p>` : ''}
                        ${task.assigned_team ? `<p><strong>指派团队：</strong>${task.assigned_team}</p>` : ''}
                        ${task.assigned_person ? `<p><strong>指派个人：</strong>${task.assigned_person}</p>` : ''}
                        ${task.progress_note ? `<p><strong>进度备注：</strong>${task.progress_note}</p>` : ''}
                        <p class="text-muted" style="font-size: 12px;">创建时间：${formatDateTime(task.created_at)}</p>
                        <div class="mt-2">
                            <strong>附件：</strong>
                            <div id="attachments-${task.id}"></div>
                            <input type="file" id="file-${task.id}" style="display:none" onchange="TodoModule.uploadAttachment(${task.id}, this)">
                            <button class="btn btn-secondary btn-sm mt-1" onclick="event.stopPropagation(); document.getElementById('file-${task.id}').click()">上传附件</button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        // 加载附件
        this.tasks.forEach(task => this.loadAttachments(task.id));
    },
    
    /**
     * 加载附件列表
     */
    async loadAttachments(taskId) {
        const result = await apiRequest(`/tasks/${taskId}/attachments`);
        const container = document.getElementById(`attachments-${taskId}`);
        if (container && result.code === 0) {
            container.innerHTML = result.data.map(att => `
                <div class="attachment-item">
                    <span>
                        <span class="attachment-name" onclick="startRenameAttachment(${att.id}, this)">${att.file_name}</span>
                        <span class="attachment-size">(${formatFileSize(att.file_size)})</span>
                    </span>
                    <span>
                        <button class="btn btn-secondary btn-sm" onclick="downloadFile(${att.id})">下载</button>
                        <button class="btn btn-secondary btn-sm" onclick="startRenameAttachment(${att.id}, document.querySelector('[data-att-id="${att.id}"]'))">重命名</button>
                        <button class="btn btn-danger btn-sm" onclick="TodoModule.deleteAttachment(${att.id}, ${taskId})">删除</button>
                    </span>
                </div>
            `).join('') || '<span class="text-muted">无附件</span>';
        }
    },
    
    /**
     * 上传附件
     */
    async uploadAttachment(taskId, input) {
        const file = input.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE}/tasks/${taskId}/attachments`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.code === 0) {
                showMessage('附件上传成功', 'success');
                this.loadAttachments(taskId);
            } else {
                showMessage(result.message || '上传失败', 'error');
            }
        } catch (error) {
            showMessage('上传失败', 'error');
        }
        
        input.value = '';
    },
    
    /**
     * 删除附件
     */
    async deleteAttachment(attId, taskId) {
        if (!confirm('确定要删除此附件吗？')) return;
        
        const result = await apiRequest(`/attachments/${attId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadAttachments(taskId);
        }
    },
    
    /**
     * 加载筛选选项
     */
    async loadFilterOptions() {
        const result = await apiRequest('/config');
        if (result.code === 0) {
            const configs = result.data;
            
            // 填充标签选项
            const tagSelect = document.getElementById('filterTag');
            if (tagSelect) {
                const tags = configs.filter(c => c.config_type === 'task_tag');
                tagSelect.innerHTML = '<option value="">全部标签</option>' + 
                    tags.map(t => `<option value="${t.config_value}">${t.config_value}</option>`).join('');
            }
            
            // 填充团队选项
            const teamSelect = document.getElementById('filterTeam');
            if (teamSelect) {
                const teams = configs.filter(c => c.config_type === 'team');
                teamSelect.innerHTML = '<option value="">全部团队</option>' + 
                    teams.map(t => `<option value="${t.config_value}">${t.config_value}</option>`).join('');
            }
            
            // 填充人员选项
            const personSelect = document.getElementById('filterPerson');
            if (personSelect) {
                const persons = configs.filter(c => c.config_type === 'person');
                personSelect.innerHTML = '<option value="">全部人员</option>' + 
                    persons.map(p => `<option value="${p.config_value}">${p.config_value}</option>`).join('');
            }
        }
    },
    
    /**
     * 筛选任务
     */
    async filterTasks() {
        const params = new URLSearchParams();
        
        const keyword = document.getElementById('searchInput')?.value;
        const tag = document.getElementById('filterTag')?.value;
        const team = document.getElementById('filterTeam')?.value;
        const person = document.getElementById('filterPerson')?.value;
        const status = document.getElementById('filterStatus')?.value;
        const sort = document.getElementById('filterSort')?.value;
        
        if (keyword) params.append('keyword', keyword);
        if (tag) params.append('tag', tag);
        if (team) params.append('team', team);
        if (person) params.append('person', person);
        if (status) params.append('status', status);
        if (sort) params.append('sort', sort);
        
        const result = await apiRequest(`/tasks?${params.toString()}`);
        if (result.code === 0) {
            this.tasks = result.data;
            this.renderTasks();
        }
    },
    
    /**
     * 打开新建任务模态框
     */
    openCreateModal() {
        this.currentTaskId = null;
        document.getElementById('taskForm')?.reset();
        document.getElementById('modalTitle').textContent = '新建任务';
        this.loadFormOptions();
        openModal('taskModal');
    },
    
    /**
     * 编辑任务
     */
    async editTask(taskId) {
        this.currentTaskId = taskId;
        const task = this.tasks.find(t => t.id === taskId);
        
        if (!task) return;
        
        await this.loadFormOptions();
        
        document.getElementById('taskSummary').value = task.summary || '';
        document.getElementById('taskDetail').value = task.detail_content || '';
        document.getElementById('taskDeadline').value = task.deadline ? task.deadline.replace(' ', 'T').substring(0, 16) : '';
        document.getElementById('taskTeam').value = task.assigned_team || '';
        document.getElementById('taskPerson').value = task.assigned_person || '';
        document.getElementById('taskProgress').value = task.progress_note || '';
        document.getElementById('taskTag').value = task.tag || '一般';
        
        document.getElementById('modalTitle').textContent = '编辑任务';
        openModal('taskModal');
    },
    
    /**
     * 加载表单选项
     */
    async loadFormOptions() {
        const result = await apiRequest('/config');
        if (result.code === 0) {
            const configs = result.data;
            
            // 标签
            const tagSelect = document.getElementById('taskTag');
            if (tagSelect) {
                const tags = configs.filter(c => c.config_type === 'task_tag');
                tagSelect.innerHTML = tags.map(t => `<option value="${t.config_value}">${t.config_value}</option>`).join('');
            }
            
            // 团队
            const teamSelect = document.getElementById('taskTeam');
            if (teamSelect) {
                const teams = configs.filter(c => c.config_type === 'team');
                teamSelect.innerHTML = '<option value="">请选择团队</option>' + 
                    teams.map(t => `<option value="${t.config_value}">${t.config_value}</option>`).join('');
            }
            
            // 人员
            const personSelect = document.getElementById('taskPerson');
            if (personSelect) {
                const persons = configs.filter(c => c.config_type === 'person');
                personSelect.innerHTML = '<option value="">请选择人员</option>' + 
                    persons.map(p => `<option value="${p.config_value}">${p.config_value}</option>`).join('');
            }
        }
    },
    
    /**
     * 保存任务
     */
    async saveTask() {
        const data = {
            summary: document.getElementById('taskSummary').value,
            detail_content: document.getElementById('taskDetail').value,
            deadline: document.getElementById('taskDeadline').value ? 
                document.getElementById('taskDeadline').value.replace('T', ' ') + ':00' : null,
            assigned_team: document.getElementById('taskTeam').value,
            assigned_person: document.getElementById('taskPerson').value,
            progress_note: document.getElementById('taskProgress').value,
            tag: document.getElementById('taskTag').value
        };
        
        if (!data.summary) {
            showMessage('请输入任务摘要', 'warning');
            return;
        }
        
        let result;
        if (this.currentTaskId) {
            result = await apiRequest(`/tasks/${this.currentTaskId}`, 'PUT', data);
        } else {
            result = await apiRequest('/tasks', 'POST', data);
        }
        
        if (result.code === 0) {
            showMessage(this.currentTaskId ? '更新成功' : '创建成功', 'success');
            closeAllModals();
            this.loadTasks();
        } else {
            showMessage(result.message || '操作失败', 'error');
        }
    },
    
    /**
     * 完成任务
     */
    async completeTask(taskId) {
        if (!confirm('确定要将此任务标记为已完成吗？')) return;
        
        const result = await apiRequest(`/tasks/${taskId}/complete`, 'POST');
        if (result.code === 0) {
            showMessage('任务已完成', 'success');
            this.loadTasks();
        }
    },
    
    /**
     * 删除任务
     */
    async deleteTask(taskId) {
        if (!confirm('确定要删除此任务吗？相关附件也将被删除。')) return;
        
        const result = await apiRequest(`/tasks/${taskId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadTasks();
        }
    }
};

// ==================== 工作备忘录模块 ====================
const MemoModule = {
    memos: [],
    currentMemoId: null,
    
    init() {
        this.loadMemos();
        this.bindEvents();
    },
    
    bindEvents() {
        document.getElementById('memoSearchInput')?.addEventListener('input', () => this.filterMemos());
        document.getElementById('memoTagFilter')?.addEventListener('change', () => this.filterMemos());
        document.getElementById('memoForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveMemo();
        });
    },
    
    async loadMemos() {
        const result = await apiRequest('/memos');
        if (result.code === 0) {
            this.memos = result.data;
            this.renderMemos();
        }
    },
    
    renderMemos() {
        const container = document.getElementById('memoList');
        if (!container) return;
        
        if (this.memos.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <div class="empty-state-text">暂无备忘录</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.memos.map(memo => `
            <div class="card memo-card" data-id="${memo.id}">
                <div class="card-header">
                    <h3>${memo.title}</h3>
                    <div class="btn-group">
                        <button class="btn btn-secondary btn-sm" onclick="MemoModule.editMemo(${memo.id})">编辑</button>
                        <button class="btn btn-danger btn-sm" onclick="MemoModule.deleteMemo(${memo.id})">删除</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="text-muted mb-1" style="font-size: 12px;">
                        标签：${memo.tags || '无'} | 创建时间：${formatDateTime(memo.created_at)}
                    </div>
                    <div style="white-space: pre-wrap; max-height: 100px; overflow: hidden;">
                        ${memo.content ? memo.content.substring(0, 200) + (memo.content.length > 200 ? '...' : '') : '无内容'}
                    </div>
                    <div class="mt-2">
                        <div id="memo-attachments-${memo.id}"></div>
                        <input type="file" id="memo-file-${memo.id}" style="display:none" onchange="MemoModule.uploadAttachment(${memo.id}, this)">
                        <button class="btn btn-secondary btn-sm" onclick="document.getElementById('memo-file-${memo.id}').click()">上传附件</button>
                    </div>
                </div>
            </div>
        `).join('');
        
        this.memos.forEach(memo => this.loadAttachments(memo.id));
    },
    
    async loadAttachments(memoId) {
        const result = await apiRequest(`/memos/${memoId}/attachments`);
        const container = document.getElementById(`memo-attachments-${memoId}`);
        if (container && result.code === 0) {
            container.innerHTML = result.data.length > 0 ? result.data.map(att => `
                <div class="attachment-item">
                    <span>
                        <span class="attachment-name" onclick="startRenameAttachment(${att.id}, this)">${att.file_name}</span>
                        <span class="attachment-size">(${formatFileSize(att.file_size)})</span>
                    </span>
                    <span>
                        <button class="btn btn-secondary btn-sm" onclick="downloadFile(${att.id})">下载</button>
                        <button class="btn btn-secondary btn-sm" onclick="startRenameAttachment(${att.id})">重命名</button>
                        <button class="btn btn-danger btn-sm" onclick="MemoModule.deleteAttachment(${att.id}, ${memoId})">删除</button>
                    </span>
                </div>
            `).join('') : '';
        }
    },
    
    async uploadAttachment(memoId, input) {
        const file = input.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE}/memos/${memoId}/attachments`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.code === 0) {
                showMessage('附件上传成功', 'success');
                this.loadAttachments(memoId);
            } else {
                showMessage(result.message || '上传失败', 'error');
            }
        } catch (error) {
            showMessage('上传失败', 'error');
        }
        
        input.value = '';
    },
    
    async deleteAttachment(attId, memoId) {
        if (!confirm('确定要删除此附件吗？')) return;
        
        const result = await apiRequest(`/attachments/${attId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadAttachments(memoId);
        }
    },
    
    async filterMemos() {
        const params = new URLSearchParams();
        const keyword = document.getElementById('memoSearchInput')?.value;
        const tags = document.getElementById('memoTagFilter')?.value;
        
        if (keyword) params.append('keyword', keyword);
        if (tags) params.append('tags', tags);
        
        const result = await apiRequest(`/memos?${params.toString()}`);
        if (result.code === 0) {
            this.memos = result.data;
            this.renderMemos();
        }
    },
    
    openCreateModal() {
        this.currentMemoId = null;
        document.getElementById('memoForm')?.reset();
        document.getElementById('memoModalTitle').textContent = '新建备忘录';
        openModal('memoModal');
    },
    
    async editMemo(memoId) {
        this.currentMemoId = memoId;
        const memo = this.memos.find(m => m.id === memoId);
        
        if (!memo) return;
        
        document.getElementById('memoTitle').value = memo.title || '';
        document.getElementById('memoContent').value = memo.content || '';
        document.getElementById('memoTags').value = memo.tags || '';
        
        document.getElementById('memoModalTitle').textContent = '编辑备忘录';
        openModal('memoModal');
    },
    
    async saveMemo() {
        const data = {
            title: document.getElementById('memoTitle').value,
            content: document.getElementById('memoContent').value,
            tags: document.getElementById('memoTags').value
        };
        
        if (!data.title) {
            showMessage('请输入标题', 'warning');
            return;
        }
        
        let result;
        if (this.currentMemoId) {
            result = await apiRequest(`/memos/${this.currentMemoId}`, 'PUT', data);
        } else {
            result = await apiRequest('/memos', 'POST', data);
        }
        
        if (result.code === 0) {
            showMessage(this.currentMemoId ? '更新成功' : '创建成功', 'success');
            closeAllModals();
            this.loadMemos();
        } else {
            showMessage(result.message || '操作失败', 'error');
        }
    },
    
    async deleteMemo(memoId) {
        if (!confirm('确定要删除此备忘录吗？相关附件也将被删除。')) return;
        
        const result = await apiRequest(`/memos/${memoId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadMemos();
        }
    }
};

// ==================== 重点关注看板模块 ====================
const FocusModule = {
    areas: [],
    items: [],
    currentItemId: null,
    currentAreaId: null,
    
    init() {
        this.loadData();
        this.bindEvents();
    },
    
    bindEvents() {
        document.getElementById('focusSearchInput')?.addEventListener('input', () => this.filterItems());
        document.getElementById('focusStatusFilter')?.addEventListener('change', () => this.filterItems());
        document.getElementById('areaForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveArea();
        });
        document.getElementById('itemForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveItem();
        });
    },
    
    async loadData() {
        await this.loadAreas();
        await this.loadKanban();
    },
    
    async loadAreas() {
        const result = await apiRequest('/focus/areas');
        if (result.code === 0) {
            this.areas = result.data;
            this.renderAreaOptions();
        }
    },
    
    async loadKanban() {
        const result = await apiRequest('/focus/kanban');
        if (result.code === 0) {
            this.renderKanban(result.data);
        }
    },
    
    renderKanban(areas) {
        const container = document.getElementById('kanbanBoard');
        if (!container) return;
        
        if (areas.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <div class="empty-state-text">暂无关注领域，请先创建领域</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = areas.map(area => `
            <div class="kanban-column">
                <div class="kanban-column-header">
                    <span>${area.name}</span>
                    <div class="btn-group">
                        <button class="btn btn-secondary btn-sm" onclick="FocusModule.openEditAreaModal(${area.id}, '${area.name}', '${area.description || ''}')">编辑</button>
                        <button class="btn btn-danger btn-sm" onclick="FocusModule.deleteArea(${area.id})">删除</button>
                    </div>
                </div>
                <div class="kanban-items">
                    ${area.items.map(item => `
                        <div class="kanban-item" onclick="FocusModule.openEditItemModal(${item.id})">
                            <div class="kanban-item-title">${item.title}</div>
                            <div class="kanban-item-meta">
                                <span class="tag ${getStatusClass(item.status)}">${item.status}</span>
                                <span>${item.planned_date ? '计划: ' + formatDate(item.planned_date) : ''}</span>
                            </div>
                        </div>
                    `).join('')}
                    <button class="btn btn-secondary btn-sm" style="width: 100%; margin-top: 10px;" onclick="FocusModule.openCreateItemModal(${area.id})">+ 添加事项</button>
                </div>
            </div>
        `).join('');
    },
    
    renderAreaOptions() {
        const select = document.getElementById('itemArea');
        if (select) {
            select.innerHTML = this.areas.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
        }
    },
    
    async filterItems() {
        const params = new URLSearchParams();
        const keyword = document.getElementById('focusSearchInput')?.value;
        const status = document.getElementById('focusStatusFilter')?.value;
        
        if (keyword) params.append('keyword', keyword);
        if (status) params.append('status', status);
        
        const result = await apiRequest(`/focus/items?${params.toString()}`);
        if (result.code === 0) {
            this.items = result.data;
            // 简单列表视图
            const container = document.getElementById('focusItemList');
            if (container) {
                container.innerHTML = this.items.map(item => `
                    <div class="card">
                        <div class="card-body">
                            <h4>${item.title}</h4>
                            <p class="text-muted">${item.note || '无备注'}</p>
                            <span class="tag ${getStatusClass(item.status)}">${item.status}</span>
                        </div>
                    </div>
                `).join('');
            }
        }
    },
    
    openCreateAreaModal() {
        this.currentAreaId = null;
        document.getElementById('areaForm')?.reset();
        document.getElementById('areaModalTitle').textContent = '新建关注领域';
        openModal('areaModal');
    },
    
    openEditAreaModal(areaId, name, description) {
        this.currentAreaId = areaId;
        document.getElementById('areaName').value = name;
        document.getElementById('areaDescription').value = description;
        document.getElementById('areaModalTitle').textContent = '编辑关注领域';
        openModal('areaModal');
    },
    
    async saveArea() {
        const data = {
            name: document.getElementById('areaName').value,
            description: document.getElementById('areaDescription').value
        };
        
        if (!data.name) {
            showMessage('请输入领域名称', 'warning');
            return;
        }
        
        let result;
        if (this.currentAreaId) {
            result = await apiRequest(`/focus/areas/${this.currentAreaId}`, 'PUT', data);
        } else {
            result = await apiRequest('/focus/areas', 'POST', data);
        }
        
        if (result.code === 0) {
            showMessage(this.currentAreaId ? '更新成功' : '创建成功', 'success');
            closeAllModals();
            this.loadData();
        }
    },
    
    async deleteArea(areaId) {
        if (!confirm('确定要删除此领域吗？相关事项也将被删除。')) return;
        
        const result = await apiRequest(`/focus/areas/${areaId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadData();
        }
    },
    
    openCreateItemModal(areaId) {
        this.currentItemId = null;
        document.getElementById('itemForm')?.reset();
        document.getElementById('itemArea').value = areaId || (this.areas[0]?.id || '');
        document.getElementById('itemModalTitle').textContent = '新建关注事项';
        openModal('itemModal');
    },
    
    async openEditItemModal(itemId) {
        this.currentItemId = itemId;
        
        const result = await apiRequest(`/focus/items`);
        if (result.code === 0) {
            const item = result.data.find(i => i.id === itemId);
            if (item) {
                await this.loadAreas();
                document.getElementById('itemArea').value = item.area_id || '';
                document.getElementById('itemTitle').value = item.title || '';
                document.getElementById('itemNote').value = item.note || '';
                document.getElementById('itemPlannedDate').value = item.planned_date || '';
                document.getElementById('itemStatus').value = item.status || '未开始';
                
                document.getElementById('itemModalTitle').textContent = '编辑关注事项';
                openModal('itemModal');
            }
        }
    },
    
    async saveItem() {
        const data = {
            area_id: document.getElementById('itemArea').value,
            title: document.getElementById('itemTitle').value,
            note: document.getElementById('itemNote').value,
            planned_date: document.getElementById('itemPlannedDate').value,
            status: document.getElementById('itemStatus').value
        };
        
        if (!data.title) {
            showMessage('请输入事项标题', 'warning');
            return;
        }
        
        if (data.title.length > 40) {
            showMessage('标题不能超过40个字符', 'warning');
            return;
        }
        
        let result;
        if (this.currentItemId) {
            result = await apiRequest(`/focus/items/${this.currentItemId}`, 'PUT', data);
        } else {
            result = await apiRequest('/focus/items', 'POST', data);
        }
        
        if (result.code === 0) {
            showMessage(this.currentItemId ? '更新成功' : '创建成功', 'success');
            closeAllModals();
            this.loadData();
        }
    },
    
    async deleteItem(itemId) {
        if (!confirm('确定要删除此事项吗？')) return;
        
        const result = await apiRequest(`/focus/items/${itemId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadData();
        }
    }
};

// ==================== 部门报告库模块 ====================
const ReportModule = {
    reports: [],
    currentReportId: null,
    
    init() {
        this.loadReports();
        this.loadReportCategories();
        this.bindEvents();
    },
    
    bindEvents() {
        document.getElementById('reportSearchInput')?.addEventListener('input', () => this.filterReports());
        document.getElementById('reportCategoryFilter')?.addEventListener('change', () => this.filterReports());
        document.getElementById('reportTagFilter')?.addEventListener('input', () => this.filterReports());
        document.getElementById('reportForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveReport();
        });
    },
    
    async loadReportCategories() {
        const result = await apiRequest('/report_categories');
        if (result.code === 0) {
            const categories = result.data;
            const filterSelect = document.getElementById('reportCategoryFilter');
            const formSelect = document.getElementById('reportCategory');
            
            if (filterSelect) {
                filterSelect.innerHTML = '<option value="">全部分类</option>' +
                    categories.map(cat => `<option value="${cat.name}">${cat.name}</option>`).join('');
            }
            
            if (formSelect) {
                formSelect.innerHTML = '<option value="">请选择分类</option>' +
                    categories.map(cat => `<option value="${cat.name}">${cat.name}</option>`).join('');
            }
        }
    },
    
    async loadReports() {
        const result = await apiRequest('/reports');
        if (result.code === 0) {
            this.reports = result.data;
            this.renderReports();
        }
    },
    
    renderReports() {
        const container = document.getElementById('reportList');
        if (!container) return;
        
        if (this.reports.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📄</div>
                    <div class="empty-state-text">暂无报告</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.reports.map(report => `
            <div class="card report-card" data-id="${report.id}">
                <div class="card-header">
                    <h3>${report.title}</h3>
                    <div class="btn-group">
                        <button class="btn btn-secondary btn-sm" onclick="ReportModule.viewReport(${report.id})">查看</button>
                        <button class="btn btn-secondary btn-sm" onclick="ReportModule.editReport(${report.id})">编辑</button>
                        <button class="btn btn-danger btn-sm" onclick="ReportModule.deleteReport(${report.id})">删除</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="text-muted mb-1" style="font-size: 12px;">
                        分类：${report.category || '未分类'} | 标签：${report.tags || '无'} | 创建时间：${formatDateTime(report.created_at)}
                    </div>
                    <div style="white-space: pre-wrap; max-height: 80px; overflow: hidden;">
                        ${report.content ? report.content.substring(0, 150) + (report.content.length > 150 ? '...' : '') : '无内容'}
                    </div>
                    <div class="mt-2">
                        <div id="report-attachments-${report.id}"></div>
                        <input type="file" id="report-file-${report.id}" style="display:none" onchange="ReportModule.uploadAttachment(${report.id}, this)">
                        <button class="btn btn-secondary btn-sm" onclick="document.getElementById('report-file-${report.id}').click()">上传附件</button>
                    </div>
                </div>
            </div>
        `).join('');
        
        this.reports.forEach(report => this.loadAttachments(report.id));
    },
    
    async loadAttachments(reportId) {
        const result = await apiRequest(`/reports/${reportId}/attachments`);
        const container = document.getElementById(`report-attachments-${reportId}`);
        if (container && result.code === 0) {
            container.innerHTML = result.data.length > 0 ? result.data.map(att => `
                <div class="attachment-item">
                    <span>
                        <span class="attachment-name" onclick="startRenameAttachment(${att.id}, this)">${att.file_name}</span>
                        <span class="attachment-size">(${formatFileSize(att.file_size)})</span>
                    </span>
                    <span>
                        <button class="btn btn-secondary btn-sm" onclick="downloadFile(${att.id})">下载</button>
                        <button class="btn btn-secondary btn-sm" onclick="startRenameAttachment(${att.id})">重命名</button>
                        <button class="btn btn-danger btn-sm" onclick="ReportModule.deleteAttachment(${att.id}, ${reportId})">删除</button>
                    </span>
                </div>
            `).join('') : '';
        }
    },
    
    async uploadAttachment(reportId, input) {
        const file = input.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE}/reports/${reportId}/attachments`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.code === 0) {
                showMessage('附件上传成功', 'success');
                this.loadAttachments(reportId);
            } else {
                showMessage(result.message || '上传失败', 'error');
            }
        } catch (error) {
            showMessage('上传失败', 'error');
        }
        
        input.value = '';
    },
    
    async deleteAttachment(attId, reportId) {
        if (!confirm('确定要删除此附件吗？')) return;
        
        const result = await apiRequest(`/attachments/${attId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadAttachments(reportId);
        }
    },
    
    async filterReports() {
        const params = new URLSearchParams();
        const keyword = document.getElementById('reportSearchInput')?.value;
        const category = document.getElementById('reportCategoryFilter')?.value;
        const tags = document.getElementById('reportTagFilter')?.value;
        
        if (keyword) params.append('keyword', keyword);
        if (category) params.append('category', category);
        if (tags) params.append('tags', tags);
        
        const result = await apiRequest(`/reports?${params.toString()}`);
        if (result.code === 0) {
            this.reports = result.data;
            this.renderReports();
        }
    },
    
    openCreateModal() {
        this.currentReportId = null;
        document.getElementById('reportForm')?.reset();
        document.getElementById('reportModalTitle').textContent = '新建报告';
        openModal('reportModal');
    },
    
    viewReport(reportId) {
        const report = this.reports.find(r => r.id === reportId);
        if (!report) return;
        
        document.getElementById('viewReportTitle').textContent = report.title;
        document.getElementById('viewReportCategory').textContent = report.category || '未分类';
        document.getElementById('viewReportTags').textContent = report.tags || '无';
        document.getElementById('viewReportTime').textContent = formatDateTime(report.created_at);
        document.getElementById('viewReportContent').textContent = report.content || '无内容';
        
        openModal('viewReportModal');
    },
    
    editReport(reportId) {
        this.currentReportId = reportId;
        const report = this.reports.find(r => r.id === reportId);
        
        if (!report) return;
        
        document.getElementById('reportTitle').value = report.title || '';
        document.getElementById('reportCategory').value = report.category || '';
        document.getElementById('reportTags').value = report.tags || '';
        document.getElementById('reportContent').value = report.content || '';
        
        document.getElementById('reportModalTitle').textContent = '编辑报告';
        openModal('reportModal');
    },
    
    async saveReport() {
        const data = {
            title: document.getElementById('reportTitle').value,
            category: document.getElementById('reportCategory').value,
            tags: document.getElementById('reportTags').value,
            content: document.getElementById('reportContent').value
        };
        
        if (!data.title) {
            showMessage('请输入报告标题', 'warning');
            return;
        }
        
        let result;
        if (this.currentReportId) {
            result = await apiRequest(`/reports/${this.currentReportId}`, 'PUT', data);
        } else {
            result = await apiRequest('/reports', 'POST', data);
        }
        
        if (result.code === 0) {
            showMessage(this.currentReportId ? '更新成功' : '创建成功', 'success');
            closeAllModals();
            this.loadReports();
        }
    },
    
    async deleteReport(reportId) {
        if (!confirm('确定要删除此报告吗？')) return;
        
        const result = await apiRequest(`/reports/${reportId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadReports();
        }
    }
};

// ==================== 系统配置模块 ====================
const ConfigModule = {
    configs: [],
    reportCategories: [],
    
    init() {
        this.loadConfigs();
        this.loadReportCategories();
        this.bindEvents();
    },
    
    bindEvents() {
        document.getElementById('configForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.addConfig();
        });
    },
    
    async loadConfigs() {
        const result = await apiRequest('/config');
        if (result.code === 0) {
            this.configs = result.data;
            this.renderConfigs();
        }
    },
    
    async loadReportCategories() {
        const result = await apiRequest('/report_categories');
        if (result.code === 0) {
            this.reportCategories = result.data;
            this.renderReportCategories();
        }
    },
    
    renderConfigs() {
        const types = {
            'task_tag': '任务标签',
            'team': '指派团队',
            'person': '指派人员',
            'focus_area': '关注领域'
        };
        
        Object.keys(types).forEach(type => {
            const container = document.getElementById(`config-${type}`);
            if (container) {
                const items = this.configs.filter(c => c.config_type === type);
                container.innerHTML = items.map(item => `
                    <div class="config-item" style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f7fafc; border-radius: 4px; margin-bottom: 8px;">
                        <span style="flex: 1;">${item.config_value}</span>
                        <button class="btn btn-danger btn-sm" onclick="ConfigModule.deleteConfig(${item.id}, '${type}')">删除</button>
                    </div>
                `).join('') || '<div class="text-muted">暂无配置项</div>';
            }
        });
    },
    
    renderReportCategories() {
        const container = document.getElementById('config-report_category');
        if (!container) return;
        
        if (this.reportCategories.length === 0) {
            container.innerHTML = '<div class="text-muted">暂无分类</div>';
            return;
        }
        
        container.innerHTML = this.reportCategories.map(cat => `
            <div class="config-item" style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f7fafc; border-radius: 4px; margin-bottom: 8px;">
                <span style="flex: 1;">${cat.name} ${cat.is_system ? '<span style="font-size:12px;color:#999">(系统默认)</span>' : ''}</span>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-secondary btn-sm" onclick="ConfigModule.editReportCategory(${cat.id}, '${cat.name}', ${cat.is_system})">编辑</button>
                    <button class="btn btn-danger btn-sm" ${cat.is_system ? 'disabled' : ''} onclick="ConfigModule.deleteReportCategory(${cat.id}, '${cat.name}')">删除</button>
                </div>
            </div>
        `).join('');
    },
    
    async addConfig() {
        const type = document.getElementById('configType').value;
        const value = document.getElementById('configValue').value;
        
        if (!value) {
            showMessage('请输入配置值', 'warning');
            return;
        }
        
        const result = await apiRequest('/config', 'POST', { config_type: type, config_value: value });
        if (result.code === 0) {
            showMessage('添加成功', 'success');
            document.getElementById('configValue').value = '';
            this.loadConfigs();
        }
    },
    
    async deleteConfig(configId, type) {
        if (!confirm('确定要删除此配置项吗？')) return;
        
        const result = await apiRequest(`/config/${configId}`, 'DELETE');
        if (result.code === 0) {
            showMessage('删除成功', 'success');
            this.loadConfigs();
        }
    },
    
    async addReportCategory() {
        const name = prompt('请输入新分类名称：');
        if (!name) return;
        
        const result = await apiRequest('/report_categories', 'POST', { name });
        if (result.code === 0) {
            showMessage('分类添加成功', 'success');
            this.loadReportCategories();
        } else {
            showMessage(result.message || '添加失败', 'error');
        }
    },
    
    async editReportCategory(categoryId, currentName, isSystem) {
        if (isSystem) {
            showMessage('系统默认分类不可修改', 'warning');
            return;
        }
        
        const newName = prompt('请输入新分类名称：', currentName);
        if (!newName || newName === currentName) return;
        
        const result = await apiRequest(`/report_categories/${categoryId}`, 'PUT', { name: newName });
        if (result.code === 0) {
            showMessage('分类修改成功', 'success');
            this.loadReportCategories();
        } else {
            showMessage(result.message || '修改失败', 'error');
        }
    },
    
    async deleteReportCategory(categoryId, categoryName) {
        if (!confirm(`确定要删除分类"${categoryName}"吗？删除后其下报告将转至"其他"分类。`)) return;
        
        const result = await apiRequest(`/report_categories/${categoryId}`, 'DELETE');
        if (result.code === 0) {
            showMessage(result.message || '删除成功', 'success');
            this.loadReportCategories();
        } else {
            showMessage(result.message || '删除失败', 'error');
        }
    }
};

// ==================== 首页模块 ====================
const HomeModule = {
    init() {
        this.loadUpcomingTasks();
    },
    
    async loadUpcomingTasks() {
        const result = await apiRequest('/tasks/upcoming');
        if (result.code === 0) {
            this.renderUpcomingTasks(result.data);
        }
    },
    
    renderUpcomingTasks(tasks) {
        const container = document.getElementById('upcomingTasks');
        if (!container) return;
        
        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="alert-card info">
                    <div class="alert-title">暂无即将到期的任务</div>
                    <div class="alert-content">未来5天内没有待办任务到期</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="alert-card warning">
                <div class="alert-title">即将到期任务提醒</div>
                <div class="alert-content">以下任务将在未来5天内到期，请及时处理</div>
            </div>
            ${tasks.map(task => `
                <div class="card" style="margin-bottom: 12px; cursor: pointer;" onclick="HomeModule.viewTaskDetail(${task.id})">
                    <div class="card-body">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span class="tag ${getTagClass(task.tag)}">${task.tag || '一般'}</span>
                                <strong style="margin-left: 8px;">${task.summary}</strong>
                            </div>
                            <span class="text-danger">截止: ${formatDateTime(task.deadline)}</span>
                        </div>
                        ${task.assigned_person ? `<div class="text-muted mt-1">负责人: ${task.assigned_person}</div>` : ''}
                    </div>
                </div>
            `).join('')}
        `;
    },
    
    currentTaskId: null,
    
    async viewTaskDetail(taskId) {
        this.currentTaskId = taskId;
        const result = await apiRequest(`/tasks/${taskId}`);
        if (result.code === 0) {
            const task = result.data;
            document.getElementById('taskDetailBody').innerHTML = `
                <div class="form-group">
                    <label>任务摘要</label>
                    <input type="text" id="viewTaskSummary" class="form-control" value="${task.summary || ''}" disabled>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>标签</label>
                        <input type="text" id="viewTaskTag" class="form-control" value="${task.tag || ''}" disabled>
                    </div>
                    <div class="form-group">
                        <label>状态</label>
                        <input type="text" id="viewTaskStatus" class="form-control" value="${task.status || ''}" disabled>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>截止时间</label>
                        <input type="text" id="viewTaskDeadline" class="form-control" value="${task.deadline || ''}" disabled>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>指派团队</label>
                        <input type="text" id="viewTaskTeam" class="form-control" value="${task.assigned_team || ''}" disabled>
                    </div>
                    <div class="form-group">
                        <label>指派个人</label>
                        <input type="text" id="viewTaskPerson" class="form-control" value="${task.assigned_person || ''}" disabled>
                    </div>
                </div>
                <div class="form-group">
                    <label>详细内容</label>
                    <textarea id="viewTaskDetail" class="form-control" rows="4" disabled>${task.detail_content || ''}</textarea>
                </div>
                <div class="form-group">
                    <label>进度备注</label>
                    <textarea id="viewTaskProgress" class="form-control" rows="2" disabled>${task.progress_note || ''}</textarea>
                </div>
            `;
            
            document.getElementById('editTaskBtn').onclick = () => {
                this.editTask(taskId);
            };
            
            openModal('taskDetailModal');
        }
    },
    
    async editTask(taskId) {
        closeModal('taskDetailModal');
        window.location.href = `/todo`;
        setTimeout(() => {
            TodoModule.editTask(taskId);
        }, 500);
    }
};

// ==================== 数据导入导出 ====================
async function exportAllData() {
    showMessage('正在导出数据...', 'info');
    window.location.href = '/api/export/all';
}

async function importData() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.zip';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/import/all', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.code === 0) {
                showMessage('数据导入成功', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage(result.message || '导入失败', 'error');
            }
        } catch (error) {
            showMessage('导入失败', 'error');
        }
    };
    input.click();
}

async function exportAttachments() {
    showMessage('正在导出附件...', 'info');
    window.location.href = '/api/export/attachments';
}

async function exportTextSummary() {
    showMessage('正在导出文本汇总...', 'info');
    window.location.href = '/api/export/text_summary';
}

// ==================== 下载文件 ====================
function downloadFile(attachmentId) {
    window.location.href = `/api/attachments/${attachmentId}/download`;
}

// ==================== 重命名附件 ====================
function startRenameAttachment(attachmentId, element) {
    const nameElement = element || document.querySelector(`.attachment-item[data-att-id="${attachmentId}"] .attachment-name`);
    if (!nameElement) return;
    
    const currentName = nameElement.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentName;
    input.className = 'form-control';
    input.style.width = 'auto';
    input.style.display = 'inline-block';
    input.style.maxWidth = '200px';
    
    input.onkeydown = async (e) => {
        if (e.key === 'Enter') {
            await saveRename(attachmentId, input.value, nameElement);
        } else if (e.key === 'Escape') {
            nameElement.textContent = currentName;
        }
    };
    
    input.onblur = async () => {
        await saveRename(attachmentId, input.value, nameElement);
    };
    
    nameElement.innerHTML = '';
    nameElement.appendChild(input);
    input.focus();
    input.select();
}

async function saveRename(attachmentId, newName, nameElement) {
    newName = newName.trim();
    if (!newName) {
        showMessage('文件名不能为空', 'warning');
        return;
    }
    
    const result = await apiRequest(`/attachments/${attachmentId}/rename`, 'PUT', { file_name: newName });
    if (result.code === 0) {
        nameElement.textContent = newName;
    } else {
        showMessage(result.message || '重命名失败', 'error');
    }
}

// ==================== 折叠面板切换 ====================
function toggleCollapse(id) {
    const collapse = document.getElementById(`collapse-${id}`);
    if (collapse) {
        const cardBody = collapse.parentElement;
        cardBody.classList.toggle('open');
    }
}

// ==================== 打印功能 ====================
function printPage() {
    window.print();
}

// ==================== 页面初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    // 根据当前页面初始化对应模块
    const path = window.location.pathname;
    
    if (path === '/' || path === '/index') {
        HomeModule.init();
    } else if (path === '/todo') {
        TodoModule.init();
    } else if (path === '/memo') {
        MemoModule.init();
    } else if (path === '/focus') {
        FocusModule.init();
    } else if (path === '/report') {
        ReportModule.init();
    } else if (path === '/config') {
        ConfigModule.init();
    }
    
    // 点击模态框外部关闭
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeAllModals();
            }
        });
    });
});

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);