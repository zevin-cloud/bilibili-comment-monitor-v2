import notifier

# 测试发送Webhook通知
test_comments = [
    {
        'user': '测试用户',
        'type': '主评论',
        'message': '这是一条测试评论',
        'time': __import__('datetime').datetime.now()
    }
]

print('正在发送测试通知到企业微信...')
notifier.send_webhook_notification('测试视频', test_comments)
print('测试完成！')
