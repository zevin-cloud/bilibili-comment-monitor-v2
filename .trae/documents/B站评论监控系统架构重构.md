# B站评论监控系统架构重构计划

## 重构目标

将系统从"视频中心"架构重构为"用户中心"架构，实现自动发现、精准过滤、统一管理。

## 第一阶段：核心架构搭建（高优先级）

### 1.1 创建目录结构

```
core/
├── __init__.py
├── monitor_engine.py      # 监控引擎（核心调度器）
├── activity_manager.py    # 活动管理器
├── comment_filter.py     # 评论过滤器
├── user_manager.py        # 用户管理器
└── scheduler.py           # 调度管理器

models/
├── __init__.py
├── activity.py           # 活动模型（基类+子类）
└── user.py              # 用户模型

api/
├── __init__.py
├── bilibili_api.py      # B站API统一封装
└── wbi_manager.py       # WBI签名管理器

config/
├── __init__.py
└── settings.py          # 统一配置管理
```

### 1.2 实现核心模块

* **MonitorEngine**: 用户驱动的监控循环

* **ActivityManager**: 统一管理视频/动态/专栏

* **CommentFilter**: 实现UP主本人高亮过滤

* **Activity模型**: 多态设计支持不同活动类型

## 第二阶段：数据库重构（高优先级）

### 2.1 创建统一活动表

* `activities` 表替代分散的 videos/monitored\_dynamics

* `activity_comments` 表统一评论存储

* 增强 monitored\_users 表（last\_activity\_id字段）

### 2.2 数据迁移脚本

* 将现有 videos 表数据迁移到 activities

* 将现有 monitored\_dynamics 数据迁移

* 迁移 seen\_comments 到 activity\_comments

## 第三阶段：代码重构（中优先级）

### 3.1 消除冗余代码

* 提取重复的评论检查逻辑到 ActivityManager

* 统一 WBI 签名逻辑到 WBIManager

* 合并 main.py 和 auto\_monitor.py 的重复代码

### 3.2 重构 main.py

* 使用 MonitorEngine 替代现有监控循环

* 简化为只负责用户交互和启动引擎

### 3.3 重构 auto\_monitor.py

* 直接调用 MonitorEngine

* 移除重复逻辑

## 第四阶段：功能增强（中优先级）

### 4.1 实现断点续传

* 使用 last\_activity\_id 避免重复处理

* 支持程序重启后继续监控

### 4.2 增强通知系统

* 区分高优先级（UP主本人）和普通评论

* 支持不同通知渠道（Webhook/邮件/微信）

### 4.3 Web界面更新

* 适配新的数据库结构

* 添加活动管理界面

* 显示UP主本人评论高亮

## 第五阶段：优化和测试（低优先级）

### 5.1 性能优化

* 添加缓存机制

* 优化数据库查询

* 减少API调用频率

### 5.2 测试覆盖

* 单元测试

* 集成测试

* 压力测试

## 重构收益

| 指标     | 重构前     | 重构后     | 提升     |
| ------ | ------- | ------- | ------ |
| 代码行数   | \~2000行 | \~1500行 | -25%   |
| 重复代码   | \~400行  | \~50行   | -87%   |
| 模块耦合度  | 高       | 低       | 显著降低   |
| <br /> | <br />  | <br />  | <br /> |

