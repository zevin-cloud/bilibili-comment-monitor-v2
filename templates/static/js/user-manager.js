/**
 * 用户管理模块
 */
class UserManager {
    constructor() {
        this.container = document.getElementById('userList');
        this.searchResults = document.getElementById('searchResults');
        this.searchSelect = document.getElementById('searchResultSelect');
    }

    async loadUsers() {
        try {
            UIComponents.showLoading('userList');
            const users = await api.getUsers();
            stateManager.setUsers(users);
            this.render(users);
        } catch (error) {
            console.error('加载用户失败:', error);
            this.render([]);
            UIComponents.showMessage('加载用户失败', 'error');
        } finally {
            UIComponents.hideLoading('userList');
        }
    }

    render(users) {
        if (!this.container) return;

        if (users.length === 0) {
            this.container.innerHTML = UIComponents.createEmptyState('暂无用户');
            return;
        }

        this.container.innerHTML = users.map(user => `
            <div class="list-item">
                <div class="list-item-info">
                    <div class="list-item-title">
                        ${UIComponents.escapeHtml(user.uname || '未知')}
                        ${user.monitor_comments ? UIComponents.createBadge('comments', '评论') : ''}
                        ${user.monitor_dynamic ? UIComponents.createBadge('dynamic', '动态') : ''}
                    </div>
                    <div class="list-item-subtitle">UID: ${UIComponents.escapeHtml(user.mid)}</div>
                </div>
                <div class="list-item-actions">
                    <button class="btn-small danger" onclick="userManager.deleteUser('${user.mid}')">删除</button>
                </div>
            </div>
        `).join('');
    }

    async searchUser(keyword) {
        if (!keyword) {
            UIComponents.showMessage('请输入搜索关键词', 'error');
            return;
        }

        try {
            UIComponents.showLoading('searchBtn');
            const result = await api.searchUser(keyword);
            
            if (result.success && result.users.length > 0) {
                this.renderSearchResults(result.users);
                UIComponents.showMessage(`找到 ${result.users.length} 个用户`, 'success');
            } else {
                UIComponents.showMessage('未找到用户', 'error');
                this.hideSearchResults();
            }
        } catch (error) {
            UIComponents.showMessage(`搜索失败: ${error.message}`, 'error');
        } finally {
            UIComponents.hideLoading('searchBtn', '🔍 搜索');
        }
    }

    renderSearchResults(users) {
        if (!this.searchSelect) return;

        this.searchSelect.innerHTML = '<option value="">-- 选择用户 --</option>';
        users.forEach(user => {
            this.searchSelect.innerHTML += `<option value="${user.mid}" data-uname="${user.uname}">${user.uname} (UID: ${user.mid})</option>`;
        });
        
        if (this.searchResults) {
            this.searchResults.style.display = 'block';
        }
    }

    hideSearchResults() {
        if (this.searchResults) {
            this.searchResults.style.display = 'none';
        }
    }

    selectSearchResult() {
        const selectedOption = this.searchSelect.options[this.searchSelect.selectedIndex];
        if (selectedOption && selectedOption.value) {
            document.getElementById('userMid').value = selectedOption.value;
            document.getElementById('userName').value = selectedOption.getAttribute('data-uname');
        }
    }

    async addUser() {
        const mid = document.getElementById('userMid').value.trim();
        const uname = document.getElementById('userName').value.trim();
        const monitorComments = document.getElementById('monitorComments').checked;
        const monitorDynamic = document.getElementById('monitorDynamic').checked;

        if (!mid) {
            UIComponents.showMessage('请输入UID', 'error');
            return;
        }

        try {
            UIComponents.showLoading('addUserBtn');
            const result = await api.addUser({ mid, uname, monitor_comments: monitorComments, monitor_dynamic: monitorDynamic });
            
            if (result.success) {
                UIComponents.showMessage(`添加成功${result.uname ? `: ${result.uname}` : ''}`, 'success');
                this.clearForm();
                await this.loadUsers();
            } else {
                UIComponents.showMessage(result.error || '添加失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`添加失败: ${error.message}`, 'error');
        } finally {
            UIComponents.hideLoading('addUserBtn', '➕ 添加用户');
        }
    }

    async deleteUser(mid) {
        if (!UIComponents.confirm('确定删除这个用户吗？')) return;

        try {
            const result = await api.deleteUser(mid);
            
            if (result.success) {
                UIComponents.showMessage('删除成功', 'success');
                await this.loadUsers();
            } else {
                UIComponents.showMessage(result.error || '删除失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`删除失败: ${error.message}`, 'error');
        }
    }

    clearSearch() {
        document.getElementById('userMid').value = '';
        document.getElementById('userName').value = '';
        document.getElementById('searchKeyword').value = '';
        this.hideSearchResults();
    }

    async refreshUsers() {
        await this.loadUsers();
    }
}

const userManager = new UserManager();
