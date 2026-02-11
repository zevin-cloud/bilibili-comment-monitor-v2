/**
 * 监控控制模块
 */
class MonitorController {
    constructor() {
        this.statusCheckInterval = null;
        this.statusCheckIntervalMs = 5000;
    }

    async checkStatus() {
        try {
            const status = await api.getMonitorStatus();
            stateManager.setMonitorStatus(status);
            
            UIComponents.updateStatusDot(status.running);
            UIComponents.updateStatusText(status.running ? `运行中 (PID: ${status.pid})` : '监控未运行');
            UIComponents.toggleButtonState('startBtn', 'stopBtn', status.running);
        } catch (error) {
            console.error('检查状态失败:', error);
        }
    }

    async startMonitor() {
        try {
            const result = await api.startMonitor();
            
            if (result.success) {
                UIComponents.showMessage('监控已启动', 'success');
                await this.checkStatus();
            } else {
                UIComponents.showMessage(result.error || '启动失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`启动失败: ${error.message}`, 'error');
        }
    }

    async stopMonitor() {
        try {
            const result = await api.stopMonitor();
            
            if (result.success) {
                UIComponents.showMessage('监控已停止', 'success');
                await this.checkStatus();
            } else {
                UIComponents.showMessage(result.error || '停止失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`停止失败: ${error.message}`, 'error');
        }
    }

    startAutoCheck() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }
        this.statusCheckInterval = setInterval(() => {
            this.checkStatus().catch(() => {});
        }, this.statusCheckIntervalMs);
    }

    stopAutoCheck() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
    }
}

const monitorController = new MonitorController();
