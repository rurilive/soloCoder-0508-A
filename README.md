# URL 缩短服务

一个采用螺旋模型开发的现代化 URL 缩短服务项目，使用 Python (FastAPI) 作为后端，React + Vite 作为前端。

## 项目特性

- **URL 缩短**: 将长链接转换为 6 位短码
- **LRU 替换策略**: 当短码池满时，自动替换最少使用的短码
- **实时统计**: 查看短码池使用情况
- **前后端分离**: 现代化的前后端架构

## 技术栈

### 后端
- **FastAPI**: 高性能 Python Web 框架
- **SQLAlchemy**: ORM 数据库框架
- **SQLite**: 轻量级数据库
- **Uvicorn**: ASGI 服务器

### 前端
- **React 19**: 用户界面库
- **Vite**: 构建工具
- **React Router**: 路由管理

## 项目结构

```
.
├── backend/                    # 后端代码
│   └── app/
│       ├── main.py            # FastAPI 应用入口
│       ├── config/            # 配置模块
│       │   └── settings.py    # 配置项
│       ├── database/          # 数据库模块
│       │   └── connection.py  # 数据库连接
│       ├── models/            # ORM 模型
│       │   └── url.py         # URL 映射模型
│       ├── schemas/           # Pydantic 模型
│       │   └── url.py         # 请求/响应模型
│       ├── routers/           # 路由定义
│       │   └── url.py         # URL 相关路由
│       ├── services/          # 业务逻辑
│       │   └── url_service.py # URL 服务
│       └── utils/             # 工具函数
│           └── short_code.py  # 短码生成
├── public/                    # 静态资源
├── src/                       # 前端代码
│   ├── main.jsx              # 入口文件
│   ├── App.jsx               # 应用组件
│   ├── App.css               # 应用样式
│   ├── index.css             # 全局样式
│   └── pages/                # 页面组件
│       ├── Home.jsx          # 主页
│       └── Home.css          # 主页样式
├── main.py                    # 后端启动入口
├── pyproject.toml            # Python 依赖配置
├── package.json              # Node.js 依赖配置
└── vite.config.js            # Vite 配置
```

## 快速开始

### 环境要求
- Python >= 3.12
- Node.js >= 18
- npm 或 yarn

### 安装依赖

#### 后端依赖
```bash
uv sync
```

#### 前端依赖
```bash
npm install
```

### 运行项目

#### 启动后端
```bash
uv run python main.py
```
后端服务将在 `http://localhost:1111` 启动

#### 启动前端
```bash
npm run dev
```
前端应用将在 `http://localhost:3000` 启动

### 访问应用
- **前端界面**: http://localhost:3000
- **后端 API**: http://localhost:1111
- **API 文档**: http://localhost:1111/docs

## API 接口

### 1. 缩短 URL
```
POST /shorten
Content-Type: application/json

{
  "url": "https://example.com/very/long/url"
}

Response:
{
  "short_code": "abc123",
  "original_url": "https://example.com/very/long/url",
  "is_reused": false,
  "replaced_url": null
}
```

### 2. 重定向到原始 URL
```
GET /{short_code}

Redirect: 302 到原始 URL
```

### 3. 获取统计数据
```
GET /stats

Response:
{
  "total_pool": 56800235584,
  "used_count": 10,
  "available_count": 56800235574,
  "usage_percent": 0.00002,
  "oldest_accessed": "2026-05-11T10:00:00",
  "newest_accessed": "2026-05-11T11:00:00"
}
```

## 短码策略

- **短码长度**: 6 位
- **字符集**: 大小写字母 + 数字 (62 个字符)
- **总容量**: 62^6 = 56,800,235,584 个短码
- **替换策略**: LRU (Least Recently Used) - 当短码池满时，替换最少使用的短码

## 开发说明

### 螺旋模型迭代

本项目采用螺旋模型进行开发，每次迭代都会增加新功能并改进现有功能。

#### 当前版本 (v1.1.0)
- 项目结构工程化
- 前端界面开发
- API 文档完善

#### 下一版本规划
- 用户认证系统
- 自定义短码
- 过期时间设置
- 访问统计
- 批量缩短

### 代码规范

- **后端**: 遵循 PEP 8 规范
- **前端**: 使用 ESLint 进行代码检查
- **提交**: 小步提交，保持原子性

## 许可证

MIT License
