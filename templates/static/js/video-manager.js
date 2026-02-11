/**
 * 视频管理模块
 */
class VideoManager {
    constructor() {
        this.container = document.getElementById('videoList');
    }

    async loadVideos() {
        try {
            UIComponents.showLoading('videoList');
            const videos = await api.getVideos();
            stateManager.setVideos(videos);
            this.render(videos);
        } catch (error) {
            console.error('加载视频失败:', error);
            this.render([]);
            UIComponents.showMessage('加载视频失败', 'error');
        } finally {
            UIComponents.hideLoading('videoList');
        }
    }

    render(videos) {
        if (!this.container) return;

        if (videos.length === 0) {
            this.container.innerHTML = UIComponents.createEmptyState('暂无视频');
            return;
        }

        this.container.innerHTML = videos.map(video => `
            <div class="list-item">
                <div class="list-item-info">
                    <div class="list-item-title">${UIComponents.escapeHtml(video.title)}</div>
                    <div class="list-item-subtitle">${UIComponents.escapeHtml(video.bv_id)}</div>
                </div>
                <div class="list-item-actions">
                    <button class="btn-small danger" onclick="videoManager.deleteVideo('${video.oid}')">删除</button>
                </div>
            </div>
        `).join('');
    }

    async addVideo(bvId) {
        if (!bvId) {
            UIComponents.showMessage('请输入BV号', 'error');
            return;
        }

        try {
            UIComponents.showLoading('addVideoBtn');
            const result = await api.addVideo(bvId);
            
            if (result.success) {
                UIComponents.showMessage(result.message, 'success');
                document.getElementById('videoBvId').value = '';
                await this.loadVideos();
            } else {
                UIComponents.showMessage(result.error || '添加失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`添加失败: ${error.message}`, 'error');
        } finally {
            UIComponents.hideLoading('addVideoBtn', '➕ 添加视频');
        }
    }

    async deleteVideo(oid) {
        if (!UIComponents.confirm('确定删除这个视频吗？')) return;

        try {
            const result = await api.deleteVideo(oid);
            
            if (result.success) {
                UIComponents.showMessage('删除成功', 'success');
                await this.loadVideos();
            } else {
                UIComponents.showMessage(result.error || '删除失败', 'error');
            }
        } catch (error) {
            UIComponents.showMessage(`删除失败: ${error.message}`, 'error');
        }
    }
}

const videoManager = new VideoManager();
