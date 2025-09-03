# SMS Publisher - Vercel RPA 集成指南

## 🌟 概述

本项目实现了在 Vercel 无服务器环境中集成 RPA 功能的混合架构。由于 Vercel 的限制，我们采用了以下策略：

## 🏗️ 架构设计

### 1. 前端部署

- **位置**: Vercel 静态托管
- **文件**: `src/frontend/` 目录下的所有文件
- **功能**: 用户界面，Firebase 认证，API 调用

### 2. API 服务

- **位置**: Vercel 无服务器函数
- **文件**: `api/index.js`
- **功能**: 处理 RPA 请求，SMS 发送，配置管理

### 3. RPA 执行策略

由于 Vercel 不支持长时间运行的进程和浏览器自动化，RPA 功能通过以下方式实现：

#### 方案 A: 外部 RPA 服务器（推荐）

```
Vercel网页 → Vercel API → 外部RPA服务器 → 执行Python脚本
```

#### 方案 B: 任务队列系统

```
Vercel网页 → Vercel API → 云队列服务 → Worker处理RPA任务
```

#### 方案 C: Webhook 触发

```
Vercel网页 → Vercel API → 其他云服务 → 执行RPA逻辑
```

## 🚀 部署步骤

### 1. 准备部署

```bash
# 运行部署脚本
deploy-to-vercel.bat
```

### 2. Vercel 配置

- 连接 GitHub 仓库
- 选择分支: `给个人发短信的机能`
- 构建设置会自动从 `vercel.json` 读取

### 3. 环境变量设置

在 Vercel 仪表板中设置：

- `FIREBASE_PROJECT_ID`: Firebase 项目 ID
- `RPA_SERVER_URL`: 外部 RPA 服务器 URL（如果使用）

## 📡 API 端点

### 健康检查

```
GET /api/health
```

### RPA 控制

```
POST /api/rpa/start
Body: { "userUid": "user123", "mode": "1", "interval": 5 }

POST /api/rpa/stop
Body: { "userUid": "user123", "taskId": "task_xxx" }

GET /api/rpa/status?userUid=user123
```

### SMS 发送

```
POST /api/sms/send
Body: {
  "userUid": "user123",
  "phone": "1234567890",
  "message": "Hello World"
}
```

### 配置管理

```
POST /api/config/save
Body: { "userUid": "user123", "config": {...} }

GET /api/config/get?userUid=user123
```

## 🔧 RPA 实现选项

### 选项 1: 独立 RPA 服务器

1. 在 VPS 或云服务器上部署 RPA 脚本
2. 创建 API 接口接收 Vercel 请求
3. Vercel 通过 HTTP 请求控制 RPA

**优点**: 完全功能，稳定运行
**缺点**: 需要额外服务器成本

### 选项 2: GitHub Actions

1. 使用 GitHub Actions 作为 RPA 运行环境
2. Vercel 触发 GitHub API 启动 workflow
3. Actions 执行 Python RPA 脚本

**优点**: 免费，与代码仓库集成
**缺点**: 执行时间有限制

### 选项 3: 云函数服务

1. 使用 AWS Lambda、Azure Functions 等
2. 部署支持浏览器的云函数
3. Vercel 调用云函数执行 RPA

**优点**: 按需付费，扩展性好
**缺点**: 复杂度较高

## 💡 当前实现状态

- ✅ Vercel 前端界面部署
- ✅ 无服务器 API 端点
- ✅ 任务状态管理（内存中）
- 🔄 RPA 执行（Demo 模式）
- 📋 待实现：选择并配置 RPA 执行策略

## 🚀 下一步

1. **选择 RPA 执行方案**：根据需求和预算选择上述方案之一
2. **配置外部服务**：设置 RPA 服务器或云函数
3. **更新 API 代码**：连接真实的 RPA 执行服务
4. **测试完整流程**：验证从网页到 RPA 执行的完整链路

## 📝 使用说明

1. 访问 Vercel 部署的网站
2. 使用 Firebase 账户登录
3. 配置邮箱和 SMS 设置
4. 点击"启动 RPA"开始自动化流程
5. 在状态页面监控任务执行

## ⚠️ 注意事项

- Vercel 函数有 30 秒执行时间限制
- 不支持文件系统持久化
- 不能直接运行 Selenium 等浏览器自动化
- 需要外部服务支持完整 RPA 功能
