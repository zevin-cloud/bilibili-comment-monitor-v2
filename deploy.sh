#!/bin/bash

# 部署脚本 - 在远程服务器上运行

# 配置
REPO_URL="https://github.com/wy3057/bilibili-comment.git"
PROJECT_DIR="/opt/bilibili-comment"
PORT="5000"

echo "=== B站评论监控系统部署脚本 ==="

# 1. 安装Docker和Docker Compose（如果未安装）
if ! command -v docker &> /dev/null; then
    echo "正在安装Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    echo "正在安装Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 2. 克隆或更新代码
if [ -d "$PROJECT_DIR" ]; then
    echo "更新代码..."
    cd $PROJECT_DIR
    git pull
else
    echo "克隆代码..."
    git clone $REPO_URL $PROJECT_DIR
    cd $PROJECT_DIR
fi

# 3. 创建必要的文件
echo "创建配置文件..."
touch bili_cookie.txt
touch webhook_config.txt

# 4. 构建并启动容器
echo "启动Docker容器..."
docker-compose down
docker-compose up -d --build

# 5. 检查状态
echo "检查容器状态..."
docker-compose ps

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://192.168.123.185:$PORT"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo "重启服务: docker-compose restart"
