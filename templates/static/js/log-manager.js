/**
 * 日志管理模块
 */
class LogManager {
    constructor() {
        this.container = document.getElementById('logsContainer');
        this.refreshInterval = null;
        this.refreshIntervalMs = 10000;
    }

    async loadLogs() {
        try {
            const data = await api.getLogs();
            stateManager.setLogs(data.logs || []);
            this.render(data.logs || []);
        } catch (error) {
            console.error('加载日志失败:', error);
            this.render([]);
        }
    }

    render(logs) {
        if (!this.container) return;

        if (!logs || logs.length === 0) {
            this.container.innerHTML = UIComponents.createEmptyState('暂无日志');
            return;
        }

        this.container.innerHTML = logs.map(line => `
            <div>${UIComponents.escapeHtml(line)}</div>
        `).join('');
        
        // 自动滚动到底部
        this.container.scrollTop = this.container.scrollHeight;
    }

    async refreshLogs() {
        await this.loadLogs();
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.refreshInterval = setInterval(() => {
            this.refreshLogs().catch(() => {});
        }, this.refreshIntervalMs);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

const logManager = new LogManager();
