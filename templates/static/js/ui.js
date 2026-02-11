/**
 * UI 组件 - 可复用的 UI 组件
 */
class UIComponents {
    static showMessage(text, type = 'info', duration = 3000) {
        const container = document.getElementById('message');
        if (!container) return;

        container.textContent = text;
        container.className = `message ${type}`;
        
        setTimeout(() => {
            container.className = 'message';
        }, duration);
    }

    static showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<span class="loading"></span>';
        }
    }

    static hideLoading(elementId, defaultText = '') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = defaultText;
        }
    }

    static createEmptyState(message = '暂无数据') {
        return `<div class="empty-state">${message}</div>`;
    }

    static createBadge(type, text) {
        const badges = {
            comments: { class: 'comments', icon: '💬' },
            dynamic: { class: 'dynamic', icon: '📝' },
            video: { class: 'video', icon: '📹' },
            article: { class: 'article', icon: '📰' }
        };
        
        const badge = badges[type] || { class: '', icon: '' };
        return `<span class="badge ${badge.class}">${badge.icon} ${text}</span>`;
    }

    static confirm(message) {
        return window.confirm(message);
    }

    static showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    static hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    static updateStatusDot(running) {
        const dot = document.getElementById('statusDot');
        if (dot) {
            if (running) {
                dot.classList.add('running');
            } else {
                dot.classList.remove('running');
            }
        }
    }

    static updateStatusText(text) {
        const textElement = document.getElementById('statusText');
        if (textElement) {
            textElement.textContent = text;
        }
    }

    static toggleButtonState(startBtnId, stopBtnId, running) {
        const startBtn = document.getElementById(startBtnId);
        const stopBtn = document.getElementById(stopBtnId);
        
        if (startBtn && stopBtn) {
            if (running) {
                startBtn.style.display = 'none';
                stopBtn.style.display = 'inline-block';
            } else {
                startBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
            }
        }
    }

    static formatDate(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    static formatActivityType(type) {
        const types = {
            video: '📹 视频',
            dynamic: '📝 动态',
            article: '📰 专栏'
        };
        return types[type] || type;
    }

    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
