/**
 * 主应用入口
 */
class App {
    constructor() {
        this.currentSection = 'dashboard';
    }

    async init() {
        await this.loadAllData();
        this.startAutoRefresh();
    }

    async loadAllData() {
        await Promise.all([
            videoManager.loadVideos(),
            userManager.loadUsers(),
            activityManager.loadActivities(),
            this.loadSchedules(),
            monitorController.checkStatus(),
            logManager.loadLogs(),
            this.loadCurrentInterval(),
            authManager.checkCookieStatus()
        ]);
        this.updateStats();
    }

    switchSection(sectionName) {
        this.currentSection = sectionName;
        
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.section === sectionName) {
                item.classList.add('active');
            }
        });
        
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        
        const targetSection = document.getElementById(`section-${sectionName}`);
        if (targetSection) {
            targetSection.classList.add('active');
        }
    }

    async loadSchedules() {
        try {
            const schedules = await api.getSchedules();
            stateManager.setSchedules(schedules);
            this.renderSchedules(schedules);
        } catch (error) {
            console.error('加载时间段失败:', error);
        }
    }

    renderSchedules(schedules) {
        const container = document.getElementById('scheduleList');
        if (!container) return;

        if (schedules.length === 0) {
            container.innerHTML = UIComponents.createEmptyState('暂无配置');
            return;
        }

        const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
        container.innerHTML = schedules.map(schedule => {
            const days = schedule.days_of_week.split(',').map(d => weekDays[parseInt(d)]).join(',');
            return `
                <div class="list-item">
                    <div class="list-item-main">
                        <div class="list-item-title">${UIComponents.escapeHtml(schedule.name)}</div>
                        <div class="list-item-subtitle">
                            ${schedule.start_time} - ${schedule.end_time} | ${days} | ${schedule.interval_seconds}秒
                        </div>
                    </div>
                    <div class="list-item-actions">
                        <button class="btn-sm btn-danger" onclick="app.deleteSchedule(${schedule.id})">删除</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async addSchedule() {
        const name = document.getElementById('scheduleName').value.trim();
        const startTime = document.getElementById('scheduleStart').value;
        const endTime = document.getElementById('scheduleEnd').value;
        const interval = parseInt(document.getElementById('scheduleInterval').value);
        const daysSelect = document.getElementById('scheduleDays');
        const days = Array.from(daysSelect.selectedOptions).map(o => o.value).join(',');

        if (!name || !startTime || !endTime || !interval || !days) {
            UIComponents.showMessage('请填写所有字段', 'error');
            return;
        }

        try {
            const result = await api.addSchedule({
                name,
                start_time: startTime,
                end_time: endTime,
                days_of_week: days,
                interval_seconds: interval
            });

            if (result.success) {
                UIComponents.showMessage('添加成功', 'success');
                document.getElementById('scheduleName').value = '';
                await this.loadSchedules();
                await this.loadCurrentInterval();
            } else {
                UIComponents.showMessage(result.error || '添加失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`添加失败: ${error.message}`, 'error');
        }
    }

    async deleteSchedule(id) {
        if (!UIComponents.confirm('确定删除这个时间段配置吗？')) return;

        try {
            const result = await api.deleteSchedule(id);

            if (result.success) {
                UIComponents.showMessage('删除成功', 'success');
                await this.loadSchedules();
                await this.loadCurrentInterval();
            } else {
                UIComponents.showMessage(result.error || '删除失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`删除失败: ${error.message}`, 'error');
        }
    }

    async loadCurrentInterval() {
        try {
            const data = await api.getCurrentInterval();
            stateManager.setCurrentInterval(data);
            document.getElementById('intervalValue').textContent = `${data.schedule_name} (${data.interval_seconds}秒)`;
        } catch (error) {
            console.error('刷新间隔失败:', error);
        }
    }

    async refreshCurrentInterval() {
        await this.loadCurrentInterval();
    }

    updateStats() {
        const stats = stateManager.getStats();
        
        const userCount = document.getElementById('statUserCount');
        if (userCount) userCount.textContent = stats.userCount;
        
        const videoCount = document.getElementById('statVideoCount');
        if (videoCount) videoCount.textContent = stats.videoCount;
        
        const activityCount = document.getElementById('statActivityCount');
        if (activityCount) activityCount.textContent = stats.activityCount;
        
        const scheduleCount = document.getElementById('statScheduleCount');
        if (scheduleCount) scheduleCount.textContent = stats.scheduleCount;
    }

    startAutoRefresh() {
        monitorController.startAutoCheck();
        authManager.startAutoCheck();
        logManager.startAutoRefresh();
    }

    stopAutoRefresh() {
        monitorController.stopAutoCheck();
        authManager.stopAutoCheck();
        logManager.stopAutoRefresh();
    }
}

const app = new App();
