# B站评论监控系统

一个用于监控Bilibili视频评论的自动化工具，支持实时监控、用户动态追踪和企业微信Webhook通知。

## 功能特性

- **视频评论监控**: 实时监控指定视频的评论区，检测新评论
- **用户动态追踪**: 自动获取监控用户的最新视频和动态
- **指定用户过滤**: 可选择只监控特定用户的评论
- **Webhook通知**: 支持企业微信、钉钉、飞书等平台的Webhook推送
- **Web管理界面**: 提供友好的可视化操作界面
- **自动登录**: 支持二维码扫码登录B站

## 项目结构

```
bilibili-comment/
├── auto_monitor.py      # 自动监控脚本（核心）
├── web_server.py        # Web服务器和API
├── main.py             # B站API交互模块
├── database.py         # 数据库操作
├── user_monitor.py     # 用户动态监控
├── notifier.py         # Webhook通知
├── cookie_checker.py   # Cookie验证
├── bvget.py           # BV号获取工具
├── templates/
│   └── index.html     # Web界面
├── Dockerfile         # Docker镜像构建文件
├── docker-compose.yml # Docker Compose配置
├── requirements.txt   # 依赖列表
├── .gitignore        # Git忽略文件
└── README.md         # 项目说明
```

## 安装部署

### 方式一：Docker部署（推荐）

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/bilibili-comment.git
cd bilibili-comment
```

#### 2. 配置环境

创建配置文件：

```bash
# 创建Cookie文件（先留空，启动后通过Web界面登录）
touch bili_cookie.txt

# 配置Webhook（可选）
echo "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key" > webhook_config.txt
```

#### 3. 启动容器

```bash
docker-compose up -d
```

#### 4. 访问Web界面

打开浏览器访问 `http://localhost:5001`

#### Docker常用命令

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新镜像后重新构建
docker-compose up -d --build
```

---

### 方式二：本地部署

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/bilibili-comment.git
cd bilibili-comment
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置Cookie

**方式一：自动登录（推荐）**
1. 启动Web服务器：`python web_server.py`
2. 访问 `http://localhost:5001`
3. 点击"登录B站"按钮，扫描二维码

**方式二：手动配置**
1. 浏览器登录B站
2. F12打开开发者工具 → Application/Storage → Cookies
3. 复制所有Cookie内容
4. 粘贴到 `bili_cookie.txt` 文件中

#### 4. 配置Webhook通知（可选）

创建 `webhook_config.txt` 文件，填入Webhook地址：

```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key_here
```

支持平台：
- 企业微信
- 钉钉
- 飞书
- Discord
- Slack

## 使用方法

### 启动Web界面

```bash
python web_server.py
```

访问 `http://localhost:5001` 打开管理界面

### 功能说明

#### 1. 添加监控视频
- 在"添加视频"区域输入BV号（如：`BV1mg4y13713`）
- 点击"添加视频"按钮

#### 2. 添加监控用户
- 在"添加用户"区域输入用户ID（MID）
- 可选择是否监控评论和动态
- 点击"添加用户"按钮

#### 3. 开始监控
- 点击"开始监控"按钮启动自动监控
- 系统会每30秒检查一次新评论
- 新评论会自动显示在日志区域

#### 4. 查看日志
- 日志区域实时显示监控状态
- 包括新评论、系统状态等信息

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/videos` | GET/POST/DELETE | 视频管理 |
| `/api/users` | GET/POST/DELETE | 用户管理 |
| `/api/monitor/start` | POST | 开始监控 |
| `/api/monitor/stop` | POST | 停止监控 |
| `/api/monitor/status` | GET | 监控状态 |
| `/api/logs` | GET | 获取日志 |
| `/api/cookie-status` | GET | Cookie状态 |
| `/api/login/qrcode` | POST | 获取登录二维码 |
| `/api/login/status` | GET | 登录状态 |

## 数据库说明

使用SQLite数据库，包含以下表：

- `monitored_videos`: 监控的视频列表
- `monitored_users`: 监控的用户列表
- `seen_comments`: 已记录的评论（避免重复通知）
- `dynamic_videos`: 从动态获取的视频
- `schedules`: 监控时间表配置

## 监控频率

支持按时间段自动调整监控频率：

- **工作日高峰时段**（9:00-21:00）: 30秒
- **工作日低峰时段**（21:00-9:00）: 5分钟
- **周末高峰时段**（10:00-22:00）: 30秒
- **周末低峰时段**（22:00-10:00）: 5分钟

## 注意事项

1. **Cookie有效期**: B站Cookie会过期，需要定期重新登录
2. **API限制**: 频繁请求可能导致IP被限制，请合理设置监控频率
3. **隐私安全**: 请勿将包含Cookie的配置文件上传到公开仓库

## 技术栈

- **后端**: Python + Flask
- **前端**: HTML + JavaScript (原生)
- **数据库**: SQLite
- **HTTP请求**: requests

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 免责声明

本项目仅供学习交流使用，请勿用于非法用途。使用本项目产生的任何后果由使用者自行承担。
