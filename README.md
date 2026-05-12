# 实时聊天室应用

一个基于 WebSocket 的实时聊天室应用，采用 Python + FastAPI 后端和 Jinja2 模板前端，具有扁平式科技感设计。

## 功能特性

- 🚀 **实时通信**: 基于 WebSocket 实现即时消息传递
- 💾 **消息存储**: 使用 SQLite 数据库持久化存储聊天记录
- 📜 **历史消息**: 新用户进入时自动显示最近 20 条历史消息
- 🎨 **科技感设计**: 扁平式深色主题，带有毛玻璃效果和渐变背景
- 👤 **用户昵称**: 支持自定义用户昵称
- 🌐 **多用户支持**: 所有在线用户实时接收消息广播

## 技术栈

- **后端**: FastAPI + WebSocket
- **前端**: Jinja2 模板 + 原生 JavaScript
- **数据库**: SQLite + SQLAlchemy
- **包管理**: uv
- **服务器**: Uvicorn

## 快速开始

### 1. 安装依赖

确保已安装 [uv](https://github.com/astral-sh/uv) 包管理器。

```bash
uv sync
```

### 2. 启动应用

```bash
uv run python -m chatroom.main
```

或者使用 uvicorn 直接启动：

```bash
uv run uvicorn chatroom.main:app --host 0.0.0.0 --port 1111 --reload
```

### 3. 访问应用

在浏览器中打开: `http://localhost:1111`

## 使用说明

1. 在左侧输入框中输入你的昵称（默认为 Anonymous）
2. 在右侧输入框中输入消息内容
3. 点击"发送"按钮或按 Enter 键发送消息
4. 所有在线用户将实时收到你的消息
5. 新用户加入时会自动加载最近 20 条历史记录

## 项目结构

```
.
├── chatroom/
│   ├── __init__.py
│   ├── main.py          # FastAPI 主应用和 WebSocket 处理
│   ├── database.py      # 数据库模型和操作
│   └── templates/
│       └── index.html   # Jinja2 前端模板
├── pyproject.toml       # 项目配置和依赖
├── .gitignore           # Git 忽略文件
└── README.md           # 项目文档
```

## API 端点

- `GET /` - 聊天室主页
- `WebSocket /ws` - WebSocket 连接端点

## 端口配置

默认绑定端口为 **1111**，如需修改可编辑 `chatroom/main.py` 中的端口配置。

## 许可证

MIT License
