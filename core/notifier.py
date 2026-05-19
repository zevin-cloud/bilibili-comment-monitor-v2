# filename: notifier.py
import requests
import os

# 定义配置文件的名称
WEBHOOK_CONFIG_FILE = 'webhook_config.txt'


def check_webhook_configured():
    """检查 Webhook 配置文件是否存在且包含至少一个有效的URL。"""
    if not os.path.exists(WEBHOOK_CONFIG_FILE):
        return False
    try:
        with open(WEBHOOK_CONFIG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 过滤掉空白行
            valid_urls = [line.strip() for line in lines if line.strip()]
            return len(valid_urls) > 0
    except Exception:
        return False


def send_webhook_notification(video_title, new_comments):
    """
    格式化新评论信息并将其发送到配置的 Webhook URL。
    支持简单的文本格式，兼容 Discord, Slack, 飞书, 钉钉等多种平台。
    """
    # 再次检查配置，这是一个安全措施
    if not check_webhook_configured():
        return

    with open(WEBHOOK_CONFIG_FILE, 'r', encoding='utf-8') as f:
        webhook_urls = [line.strip() for line in f.readlines() if line.strip()]

    # 格式化通知内容
    # 这种格式在大多数平台上都表现良好
    message_lines = [
        f"🔥 **【{video_title}】发现 {len(new_comments)} 条新评论！**",
        "--------------------------------------"
    ]
    for comment in new_comments:
        user = comment['user'].replace('`', '').replace('*', '')
        message = comment['message'].replace('`', '').replace('*', '')
        
        comment_time = comment['time']
        if hasattr(comment_time, 'strftime'):
            comment_time = comment_time.strftime('%Y-%m-%d %H:%M:%S')

        # 构建直达链接
        link_str = ""
        if 'bv_id' in comment and comment.get('bv_id'):
            bv_id = comment['bv_id']
            rpid = comment.get('rpid', '')
            if rpid:
                link_str = f"https://www.bilibili.com/video/{bv_id}#reply{rpid}"
            else:
                link_str = f"https://www.bilibili.com/video/{bv_id}"
        elif 'dynamic_id' in comment and comment.get('dynamic_id'):
            dynamic_id = comment['dynamic_id']
            rpid = comment.get('rpid', '')
            if rpid:
                link_str = f"https://t.bilibili.com/{dynamic_id}#reply{rpid}"
            else:
                link_str = f"https://t.bilibili.com/{dynamic_id}"

        comment_block = (
            f"**用户:** {user}\n"
            f"**类型:** {comment['type']}\n"
            f"**内容:** {message}\n"
            f"**时间:** {comment_time}"
        )
        if link_str:
            comment_block += f"\n**链接:** {link_str}"
        message_lines.append(comment_block)
        message_lines.append("--------------------------------------")

    full_message = "\n".join(message_lines)

    # 遍历所有 Webhook URL 发送请求
    for webhook_url in webhook_urls:
        try:
            payload = build_webhook_payload(webhook_url, f"发现新评论", full_message)
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"  - [通知] Webhook 通知已成功发送至 {webhook_url[:30]}...")
        except requests.exceptions.RequestException as e:
            print(f"  - [错误] 发送 Webhook 通知到 {webhook_url[:30]}... 失败: {e}")


def build_webhook_payload(webhook_url, title, markdown_content):
    """
    智能判定 Webhook 类型（钉钉、企业微信、飞书、其他），
    构建最适合的富文本/Markdown Payload 以获得最佳展示效果（例如渲染图片和加粗文字）。
    """
    if "oapi.dingtalk.com" in webhook_url:
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_content
            }
        }
    elif "qyapi.weixin.qq.com" in webhook_url:
        # 企业微信机器人在个人微信端中展示时，不支持 markdown 格式（会显示“暂不支持此消息类型”）
        # 为了完美的微信端兼容性，企业微信一律使用 "text" 消息类型，文字中的图片链接在微信里依然可以点击打开
        return {
            "msgtype": "text",
            "text": {
                "content": markdown_content
            }
        }
    elif "feishu.cn" in webhook_url or "larksuite.com" in webhook_url:
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    }
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": markdown_content
                    }
                ]
            }
        }
    else:
        # 默认回退为普通文本消息，保持良好兼容性
        return {
            "msgtype": "text",
            "text": {
                "content": markdown_content
            }
        }


def send_new_dynamic_notification(uname, dynamic_type, content, pub_ts=None, images=None):
    """
    发送新动态通知到 Webhook。
    
    Args:
        uname: 用户名
        dynamic_type: 动态类型（图片/文字/专栏/视频）
        content: 动态内容
        pub_ts: 动态发布的原始时间戳
        images: 动态附带的图片 URL 列表
    """
    if not check_webhook_configured():
        return

    with open(WEBHOOK_CONFIG_FILE, 'r', encoding='utf-8') as f:
        webhook_urls = [line.strip() for line in f.readlines() if line.strip()]

    import datetime
    if pub_ts:
        try:
            display_time = datetime.datetime.fromtimestamp(int(pub_ts)).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            display_time = str(pub_ts)
    else:
        display_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    message_lines = [
        f"🆕 **【{uname}】发布了新动态！**",
        "--------------------------------------",
        f"**类型:** {dynamic_type}",
        f"**时间:** {display_time}",
        f"**内容:**",
        content,
        "--------------------------------------"
    ]

    # 如果有图片，将图片渲染及图片超链接追加到内容中
    if images and isinstance(images, list):
        message_lines.append("**附带图片:**")
        for idx, img_url in enumerate(images, 1):
            # 自动为图片链接套接全球高速免费图片代理 wsrv.nl 以完美突破 B站 的防盗链规则，
            # 从而在任何浏览器或微信环境中都能直接无阻查看图片
            clean_url = img_url.replace("http://", "").replace("https://", "")
            proxy_url = f"https://wsrv.nl/?url={clean_url}"
            
            message_lines.append(f"![图片 {idx}]({proxy_url})")
            message_lines.append(f"图片 {idx} 链接 (直达免防盗链): {proxy_url}")
            message_lines.append(f"图片 {idx} 原始链接: {img_url}")
        message_lines.append("--------------------------------------")

    full_message = "\n".join(message_lines)

    for webhook_url in webhook_urls:
        try:
            title = f"🆕 【{uname}】发布了新动态！"
            payload = build_webhook_payload(webhook_url, title, full_message)
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"  - [通知] 新动态 Webhook 通知已成功发送至 {webhook_url[:30]}...")
        except requests.exceptions.RequestException as e:
            print(f"  - [错误] 发送新动态 Webhook 通知到 {webhook_url[:30]}... 失败: {e}")

