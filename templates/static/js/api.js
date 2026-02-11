/**
 * API 客户端 - 统一的 API 调用封装
 */
class ApiClient {
    constructor() {
        this.baseUrl = '/api';
    }

    async request(url, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${url}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '请求失败');
            }
            
            return data;
        } catch (error) {
            console.error('API 请求错误:', error);
            throw error;
        }
    }

    async get(url) {
        return this.request(url);
    }

    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // 视频相关 API
    async getVideos() {
        return this.get('/videos');
    }

    async addVideo(bvId) {
        return this.post('/videos', { bv_id: bvId });
    }

    async deleteVideo(oid) {
        return this.delete(`/videos/${oid}`);
    }

    // 用户相关 API
    async getUsers() {
        return this.get('/users');
    }

    async searchUser(keyword) {
        return this.get(`/users/search?keyword=${encodeURIComponent(keyword)}`);
    }

    async addUser(data) {
        return this.post('/users', data);
    }

    async deleteUser(mid) {
        return this.delete(`/users/${mid}`);
    }

    // 活动相关 API（新架构）
    async getActivities() {
        return this.get('/activities');
    }

    async deleteActivity(activityId) {
        return this.delete(`/activities/${activityId}`);
    }

    async checkDynamicVideos() {
        return this.post('/check-dynamic-videos');
    }

    // 时间段配置 API
    async getSchedules() {
        return this.get('/schedules');
    }

    async addSchedule(data) {
        return this.post('/schedules', data);
    }

    async deleteSchedule(id) {
        return this.delete(`/schedules/${id}`);
    }

    // 监控状态 API
    async getMonitorStatus() {
        return this.get('/monitor/status');
    }

    async startMonitor() {
        return this.post('/monitor/start');
    }

    async stopMonitor() {
        return this.post('/monitor/stop');
    }

    // Cookie 和登录 API
    async getCookieStatus() {
        return this.get('/cookie-status');
    }

    async updateCookie(cookie) {
        return this.put('/cookie', { cookie });
    }

    async generateLoginQrcode() {
        return this.post('/login/qrcode');
    }

    async pollLoginStatus() {
        return this.post('/login/poll');
    }

    async cancelLogin() {
        return this.post('/login/cancel');
    }

    // 系统配置 API
    async getCurrentInterval() {
        return this.get('/current-interval');
    }

    async getSettings() {
        return this.get('/settings');
    }

    async updateSetting(key, value) {
        return this.put(`/settings/${key}`, { value });
    }

    // 日志 API
    async getLogs() {
        return this.get('/logs');
    }
}

// 导出单例
const api = new ApiClient();
