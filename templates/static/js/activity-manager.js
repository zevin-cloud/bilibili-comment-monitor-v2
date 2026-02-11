/**
 * 活动管理模块（新架构）
 */
class ActivityManager {
    constructor() {
        this.container = document.getElementById('dynamicList');
    }

    async loadActivities() {
        try {
            UIComponents.showLoading('dynamicList');
            const activities = await api.getActivities();
            stateManager.setActivities(activities);
            this.render(activities);
        } catch (error) {
            console.error('加载活动失败:', error);
            this.render([]);
            UIComponents.showMessage('加载活动失败', 'error');
        } finally {
            UIComponents.hideLoading('dynamicList');
        }
    }

    render(activities) {
        if (!this.container) return;

        if (activities.length === 0) {
            this.container.innerHTML = UIComponents.createEmptyState('暂无动态<br><small>添加用户并启用动态监控后会自动获取</small>');
            return;
        }

        const typeNames = {
            video: '📹',
            dynamic: '📝',
            article: '📰'
        };

        this.container.innerHTML = activities.map(activity => `
            <div class="list-item">
                <div class="list-item-info">
                    <div class="list-item-title">
                        ${UIComponents.escapeHtml(activity.owner_name)} ${typeNames[activity.activity_type] || ''}
                    </div>
                    <div class="list-item-subtitle">
                        ${activity.content ? UIComponents.escapeHtml(activity.content.substring(0, 50)) + '...' : '无内容'}
                    </div>
                </div>
                <div class="list-item-actions">
                    <button class="btn-small danger" onclick="activityManager.deleteActivity('${activity.id}')">删除</button>
                </div>
            </div>
        `).join('');
    }

    async refreshDynamics() {
        try {
            UIComponents.showLoading('refreshDynamicsBtn');
            const result = await api.checkDynamicVideos();
            
            if (result.success) {
                UIComponents.showMessage(result.message, 'success');
                await this.loadActivities();
            } else {
                UIComponents.showMessage(result.error || '刷新失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`刷新失败: ${error.message}`, 'error');
        } finally {
            UIComponents.hideLoading('refreshDynamicsBtn', '🔄 刷新动态');
        }
    }

    async deleteActivity(activityId) {
        if (!UIComponents.confirm('确定删除这个活动监控吗？')) return;

        try {
            const result = await api.deleteActivity(activityId);
            
            if (result.success) {
                UIComponents.showMessage('删除成功', 'success');
                await this.loadActivities();
            } else {
                UIComponents.showMessage(result.error || '删除失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`删除失败: ${error.message}`, 'error');
        }
    }
}

const activityManager = new ActivityManager();
