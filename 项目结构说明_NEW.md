# 📁 SMS PUBLISHER - 重新整理后的项目结构

## 🎯 整理后的目录结构

```
SMS PUBLISHER/
├── 📁 src/                          # 源代码目录
│   ├── 📁 frontend/                 # 前端文件
│   │   ├── main_app.html           # 主应用界面
│   │   ├── main_app.js             # 主应用逻辑
│   │   ├── login.html              # 登录页面
│   │   └── login.js                # 登录逻辑
│   ├── 📁 backend/                  # 后端服务
│   │   ├── api_server.py           # Flask API服务器
│   │   └── rpa_server.js           # Node.js RPA服务器
│   └── 📁 rpa/                      # RPA自动化脚本
│       ├── send_sms_firebase.py    # Firebase版RPA脚本
│       └── send_sms_once.py        # 独立版RPA脚本
├── 📁 config/                       # 配置文件
│   └── 📁 firebase/                # Firebase配置
│       ├── firebase.js             # Firebase初始化
│       ├── api_manager.js          # API管理器
│       ├── firestore.rules         # Firestore规则
│       └── firestore-dev.rules     # 开发环境规则
├── 📁 assets/                       # 静态资源
│   └── 📁 styles/                  # CSS样式文件
│       ├── main_app.css            # 主应用样式
│       └── login.css               # 登录页样式
├── 📁 scripts/                      # 启动脚本
│   └── start_rpa_server.bat        # RPA服务器启动脚本
├── 📁 docs/                         # 项目文档
│   ├── firebase_multi_company_design.md
│   ├── multi_company_architecture.md
│   ├── DEPLOYMENT.md               # 部署指南
│   ├── PROJECT_SUMMARY.md          # 项目总结
│   ├── README_Firebase版本.md      # Firebase版本说明
│   ├── 完整集成使用指南.md
│   ├── 界面简化说明.md
│   └── firestore_rules_fix.md
├── 📁 temp/                         # 临时文件
│   ├── 📁 chrome_user_data/        # Chrome浏览器数据
│   ├── firebase_init.html          # Firebase初始化页面
│   └── firebase_company_init.html  # 公司初始化页面
├── 📁 node_modules/                 # Node.js依赖（自动生成）
├── package.json                     # Node.js项目配置
├── package-lock.json               # 依赖锁定文件
├── .gitignore                      # Git忽略规则
└── 项目结构说明_NEW.md             # 本文件
```

## 🚀 快速启动指南

### 1. 前端应用

```bash
# 直接打开浏览器访问
src/frontend/login.html        # 登录页面
src/frontend/main_app.html     # 主应用（需要先登录）
```

### 2. 后端服务

```bash
# 启动API服务器
cd src/backend
python api_server.py

# 启动RPA服务器
cd src/backend
node rpa_server.js
# 或使用批处理文件
scripts/start_rpa_server.bat
```

### 3. RPA 脚本执行

```bash
# Firebase版本（推荐）
cd src/rpa
python send_sms_firebase.py

# 独立版本
cd src/rpa
python send_sms_once.py
```

## 📝 文件说明

### 🎨 前端文件

- **login.html/js**: 用户登录界面，支持 Firebase 认证
- **main_app.html/js**: 主应用界面，包含账户设置、SMS 配置、RPA 执行

### ⚙️ 后端服务

- **api_server.py**: Flask API 服务器，处理 HTTP 请求
- **rpa_server.js**: Node.js 服务器，管理 RPA 进程

### 🤖 RPA 脚本

- **send_sms_firebase.py**: 集成 Firebase 的 RPA 脚本，支持多用户
- **send_sms_once.py**: 独立 RPA 脚本，使用环境变量配置

### 🔧 配置文件

- **firebase/**: Firebase 相关配置和规则
- **styles/**: CSS 样式文件

### 📚 文档

- **docs/**: 项目文档、部署指南、架构说明

## 🔄 迁移后的路径更新

由于文件移动，需要更新以下引用路径：

### HTML 文件中的 CSS 引用

```html
<!-- 更新前 -->
<link rel="stylesheet" href="styles/main_app.css" />

<!-- 更新后 -->
<link rel="stylesheet" href="../../assets/styles/main_app.css" />
```

### JavaScript 文件中的引用

```javascript
// 更新前
import "./firebase/firebase.js";

// 更新后
import "../../config/firebase/firebase.js";
```

## 🎯 优化建议

1. **✅ 已完成**: 文件分类整理
2. **📋 待处理**: 更新文件间的引用路径
3. **🔧 建议**: 创建统一的启动脚本
4. **📦 建议**: 配置 webpack 或类似工具管理前端资源

---

_整理时间: 2025 年 9 月 2 日_
_整理目的: 提高项目可维护性和开发效率_
