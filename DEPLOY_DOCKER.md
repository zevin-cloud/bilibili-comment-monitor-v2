# Docker 部署指南 (Docker Deployment Guide)

本指南详细介绍了如何在新服务器上使用 Docker 和 Docker Compose 快速安装和运行 B站评论监控系统。

---

## 🛠️ 前置要求

在开始部署前，请确保您的目标服务器已安装以下软件：
- **Docker**: [官方安装指南](https://docs.docker.com/get-docker/) (推荐 20.10 及以上版本)
- **Docker Compose**: [官方安装指南](https://docs.docker.com/compose/install/) (推荐 v2 及以上版本)

---

## 🚀 部署步骤

### 1. 克隆代码仓库
首先，将项目代码克隆到您的新服务器上：
```bash
git clone https://github.com/zevin-cloud/bilibili-comment-monitor-v2.git
cd bilibili-comment-monitor-v2
```

### 2. 预先创建数据卷映射文件 (关键步骤 ⚠️)
由于 `docker-compose.yml` 采用了文件挂载 (Bind Mount) 的方式将配置和数据库挂载到宿主机，**如果在启动容器前这些文件不存在，Docker 可能会自动创建同名的文件夹**，从而导致挂载失败或程序运行异常。

请在项目根目录下执行以下命令预先创建空文件和必要目录：
```bash
# 创建数据存放目录
mkdir -p data

# 创建空白的 Cookie 配置文件
touch bili_cookie.txt

# 创建空白的 Webhook 配置文件
touch webhook_config.txt

# 创建空白的 SQLite 数据库文件
touch bilibili_monitor.db
```

### 3. 检查配置 (`docker-compose.yml`)
确认 `docker-compose.yml` 的端口和路径挂载是否符合需求。默认配置如下：
```yaml
version: '3.8'

services:
  bilibili-monitor:
    build: .
    container_name: bilibili-comment-monitor
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data
      - ./bili_cookie.txt:/app/bili_cookie.txt
      - ./webhook_config.txt:/app/webhook_config.txt
      - ./bilibili_monitor.db:/app/bilibili_monitor.db
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
```
*如需修改外部访问端口，可将 `ports` 下的 `"5001:5001"` 改为 `"新端口:5001"`*。

### 4. 构建并启动容器
在项目根目录下运行以下命令，Docker 将自动读取 `Dockerfile` 构建镜像，并以后台模式启动服务：
```bash
docker-compose up -d --build
```

### 5. 访问 Web 界面进行初始化
服务启动后，可在浏览器中访问：
```text
http://<您的服务器IP>:5001
```

- **完成登录**: 访问 Web 页面后，点击右上角的 **"登录B站"**，系统将自动生成二维码。使用B站 App 扫码登录，Cookie 会自动写入并同步保存至主机的 `./bili_cookie.txt`。
- **配置通知**: 如果需要启用 Webhook 推送通知，可以直接在 Web 页面中配置 Webhook 地址，其内容会自动保存至宿主机的 `./webhook_config.txt`。

---

## 💾 备份与数据持久化
项目中所有重要的数据都已映射到服务器本地：
- **`bilibili_monitor.db`**: 监控的视频、用户列表以及扫描过的评论记录数据库。
- **`bili_cookie.txt`**: B站的登录凭证。
- **`webhook_config.txt`**: Webhook 通知接口地址。
- **`data/`**: 用于存储运行时生成的临时文件（如登录二维码等）。

> [!TIP]
> 迁移或备份服务时，只需要完整备份这几个文件 and 目录，在新服务器上解压并使用相同的 Docker 命令启动即可实现无缝迁移。

---

## 🔧 常用 Docker 维护命令

- **查看运行状态**:
  ```bash
  docker-compose ps
  ```
- **查看实时运行日志**:
  ```bash
  docker-compose logs -f
  ```
- **重启监控服务**:
  ```bash
  docker-compose restart
  ```
- **停止服务并销毁容器**:
  ```bash
  docker-compose down
  ```
- **热更新（代码有修改时重新构建镜像）**:
  ```bash
  docker-compose up -d --build
  ```
