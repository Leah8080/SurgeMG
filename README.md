# 🚀 Surge 部署交互工具

基于 Python 和 `rich` 库打造的 Surge 增强版 CLI 工具。通过美观的交互界面，简化 Surge 项目的查看、部署、管理及外链生成。

## ✨ 核心特性

- **智能部署**：
  - 自动检测项目目录下的 `CNAME` 文件并提取域名。
  - 部署前提供二次确认面板，防止误操作。
  - 对于没有 `CNAME` 的项目，部署成功后会自动创建并保存。
- **项目管理**：支持交互式删除项目（Teardown），包含安全确认。
- **外链生成**：扫描项目目录并生成 Markdown 格式的文件列表及对应 Surge 链接。
- **工具集成**：内置 Surge 安装、更新及卸载快捷入口。

## 📂 目录结构

```text
surge/
├── main.py            # 程序启动入口
├── .env               # 环境变量配置文件 (可选)
├── .env.example       # 环境变量配置示例
├── src/               # 源码目录
│   ├── ui.py          # 交互逻辑与菜单显示
│   └── logic.py       # 核心业务逻辑（链接生成等）
├── links/             # 生成的 Markdown 链接文件存放处
├── pyproject.toml     # 项目依赖配置文件 (uv)
└── .surge-url.json    # 图标及忽略规则配置文件
```

## ⚙️ 环境变量配置 (.env)

为了方便在不同电脑上操作，你可以创建一个 `.env` 文件（参考 `.env.example`）来配置以下内容：

- **Surge 认证**：
  - `SURGE_LOGIN`: 你的 Surge 账号邮箱。
  - `SURGE_TOKEN`: 你的 Surge Token（登录后可通过 `surge token` 命令获取）。

*注意：工具本身的图标及忽略规则配置仍通过 `.surge-url.json` 进行管理。*

## 🚀 快速开始

### 前提条件
1. 安装 [Python 3.13+](https://www.python.org/)
2. 安装 [uv](https://github.com/astral-sh/uv) (推荐的 Python 包管理工具)
3. 安装 [Node.js](https://nodejs.org/) (Surge 运行环境)

### 安装与运行

1. **同步依赖**：
   ```bash
   uv sync
   ```

2. **启动工具**：
   ```bash
   uv run main.py
   ```

## 🛠️ 常用功能说明

- **部署项目**：输入本地路径即可开始。如果目录下有 `CNAME`，工具会自动识别并使用。
- **生成链接**：为本地静态资源项目生成在线访问链接列表。
- **工具管理**：在这里可以快速更新全局 `surge` 命令行工具。

---

*注意：请确保您已在终端通过 `surge login` 登录您的账号，本工具将直接使用您的全局登录状态。*
