/**
 * 状态管理器 - 统一管理应用状态
 */
class StateManager {
    constructor() {
        this.state = {
            videos: [],
            users: [],
            activities: [],
            schedules: [],
            monitorStatus: { running: false, pid: null },
            cookieStatus: { valid: false, user_info: null },
            currentInterval: { interval_seconds: 300, schedule_name: '默认' },
            logs: []
        };
        
        this.listeners = [];
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notifyListeners();
    }

    getState() {
        return { ...this.state };
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    notifyListeners() {
        this.listeners.forEach(listener => listener(this.state));
    }

    // 状态更新方法
    setVideos(videos) {
        this.setState({ videos });
    }

    setUsers(users) {
        this.setState({ users });
    }

    setActivities(activities) {
        this.setState({ activities });
    }

    setSchedules(schedules) {
        this.setState({ schedules });
    }

    setMonitorStatus(status) {
        this.setState({ monitorStatus: status });
    }

    setCookieStatus(status) {
        this.setState({ cookieStatus: status });
    }

    setCurrentInterval(interval) {
        this.setState({ currentInterval: interval });
    }

    setLogs(logs) {
        this.setState({ logs });
    }

    addLog(log) {
        const newLogs = [...this.state.logs, log];
        if (newLogs.length > 100) {
            newLogs.shift();
        }
        this.setState({ logs: newLogs });
    }

    // 获取统计信息
    getStats() {
        return {
            videoCount: this.state.videos.length,
            userCount: this.state.users.length,
            activityCount: this.state.activities.length,
            scheduleCount: this.state.schedules.length,
            monitorRunning: this.state.monitorStatus.running,
            cookieValid: this.state.cookieStatus.valid
        };
    }
}

// 导出单例
const stateManager = new StateManager();
