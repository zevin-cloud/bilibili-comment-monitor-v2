/**
 * Cookie 和登录模块
 */
class AuthManager {
    constructor() {
        this.cookieCheckInterval = null;
        this.loginPollInterval = null;
        this.loginPollCount = 0;
        this.maxLoginPollCount = 45; // 45次 * 2秒 = 90秒超时
    }

    async checkCookieStatus() {
        try {
            const data = await api.getCookieStatus();
            stateManager.setCookieStatus(data);
            
            const el = document.getElementById('cookieStatus');
            if (el) {
                if (data.valid) {
                    el.textContent = `✅ ${data.user_info?.uname || '有效'}`;
                    el.style.color = '#51cf66';
                } else {
                    el.textContent = '❌ 无效';
                    el.style.color = '#ff6b6b';
                }
            }
        } catch (error) {
            console.error('检查Cookie失败:', error);
        }
    }

    async updateCookie(cookie) {
        try {
            const result = await api.updateCookie(cookie);
            
            if (result.success) {
                UIComponents.showMessage('Cookie更新成功', 'success');
                await this.checkCookieStatus();
            } else {
                UIComponents.showMessage(result.error || '更新失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`更新失败: ${error.message}`, 'error');
        }
    }

    async showLoginModal() {
        UIComponents.showModal('loginModal');
        document.getElementById('qrcodeContainer').innerHTML = '<p>生成二维码...</p>';
        document.getElementById('loginStatus').textContent = '';
        
        try {
            const result = await api.generateLoginQrcode();
            
            if (result.success) {
                document.getElementById('qrcodeContainer').innerHTML = `<img src="${result.img_path}?t=${Date.now()}" style="max-width: 200px;">`;
                this.startLoginPolling();
            } else {
                document.getElementById('qrcodeContainer').innerHTML = `<p style="color:red">${result.error}</p>`;
            }
        } catch (error) {
            document.getElementById('qrcodeContainer').innerHTML = `<p style="color:red">错误: ${error.message}</p>`;
        }
    }

    startLoginPolling() {
        if (this.loginPollInterval) {
            clearInterval(this.loginPollInterval);
        }
        
        this.loginPollCount = 0;
        this.loginPollInterval = setInterval(() => {
            this.loginPollCount++;
            
            if (this.loginPollCount > this.maxLoginPollCount) {
                this.stopLoginPolling();
                document.getElementById('loginStatus').textContent = '超时';
                return;
            }
            
            api.pollLoginStatus().then(result => {
                if (result.success) {
                    this.stopLoginPolling();
                    document.getElementById('loginStatus').textContent = '✅ 登录成功';
                    setTimeout(() => {
                        this.closeLoginModal();
                        this.checkCookieStatus().then(() => {
                            UIComponents.showMessage('登录成功', 'success');
                        });
                    }, 1000);
                } else if (result.status === 'scanned') {
                    document.getElementById('loginStatus').textContent = '已扫描,请确认';
                }
            }).catch(() => {});
        }, 2000);
    }

    stopLoginPolling() {
        if (this.loginPollInterval) {
            clearInterval(this.loginPollInterval);
            this.loginPollInterval = null;
        }
    }

    closeLoginModal() {
        this.stopLoginPolling();
        UIComponents.hideModal('loginModal');
        api.cancelLogin().catch(() => {});
    }

    startAutoCheck() {
        if (this.cookieCheckInterval) {
            clearInterval(this.cookieCheckInterval);
        }
        this.cookieCheckInterval = setInterval(() => {
            this.checkCookieStatus();
        }, 60000); // 每分钟检查一次
    }

    stopAutoCheck() {
        if (this.cookieCheckInterval) {
            clearInterval(this.cookieCheckInterval);
            this.cookieCheckInterval = null;
        }
    }
}

const authManager = new AuthManager();
