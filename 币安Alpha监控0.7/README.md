# 币安华语推特 Alpha 监控器

这是一个Python脚本，用于监控币安华语推特账户 (`@binancezh`) 的更新，当检测到包含特定关键词组合（如 "币安", "Alpha", "空投" 等）的新推文时，会通过邮件立即通知您。

## 主要功能

- **实时监控**: 自动从多个 Nitter 镜像源获取最新的推文。
- **关键词匹配**: 仅在推文内容**同时包含**所有预设关键词时发送通知，精准过滤重要信息。
- **邮件提醒**: 一旦发现符合条件的推文，立即发送邮件到您的指定邮箱。
- **智能休眠**: 在不同时间段采用不同的刷新频率，在关键时间（如整点前后）提高检查频率，在深夜自动暂停，节省资源。
- **自动切换源**: 如果某个 Nitter 实例无法访问，程序会自动尝试下一个，保证稳定性。
- **首次使用自动配置**: 第一次运行脚本时，程序会引导您在命令行中输入邮箱和Nitter实例等信息，自动生成配置文件。

## 环境与依赖

本项目正常运行需要以下环境和库的支持：

*   **Python 3**: 建议使用 Python 3.7 或更高版本。
*   **第三方库**:
    *   `requests`: 用于进行HTTP通信。
    *   `beautifulsoup4`: 用于解析从Nitter获取的HTML页面。
    *   `pytz`: 用于处理带时区的日期和时间。
    *   `playwright`: 核心依赖，一个强大的浏览器自动化工具，用于模拟浏览器行为，获取动态加载的推文内容并绕过Cloudflare等网站防护。
*   **Playwright 浏览器驱动**: Playwright 库本身并不包含浏览器。在安装完Python库后，需要单独下载它所控制的浏览器核心文件（如Chromium）。

## 安装指南

**步骤一：克隆或下载项目**

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

**步骤二：安装 Python 依赖库**

运行以下命令来安装所有在 `requirements.txt` 中声明的库：

```bash
pip install -r requirements.txt
```

**步骤三：安装 Playwright 浏览器驱动**

这是**非常关键**的一步。您需要运行以下命令来下载 Playwright 所需的浏览器驱动（只需要在首次配置环境时执行一次）。

```bash
playwright install
```
这个过程会下载一些浏览器文件，请耐心等待。

## 使用方法

**1. 运行脚本**

直接运行 `watcher.py` 即可启动监控。

```bash
python watcher.py
```

**2. 首次配置**

如果您是第一次运行，程序会检测到没有配置信息，并提示您输入：
- **发件人邮箱地址**: 用于发送通知邮件的邮箱（推荐使用QQ邮箱，程序已内置其服务器配置）。
- **邮箱授权码**: **注意！这不是邮箱的登录密码！** 而是邮箱服务商提供的一个专门用于第三方客户端登录的密码。您需要登录您的邮箱网页版，在设置中找到 "POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务" 并生成授权码。
- **收件人邮箱地址**: 接收提醒邮件的地址（可以是您自己）。
- **Nitter实例地址**: 用于抓取推特信息的Nitter服务地址，例如 `https://nitter.net/binancezh`。您可以提供多个，每行一个，程序会轮流使用。

输入完成后，程序会自动创建并保存 `config.ini` 文件，然后开始监控。

**3. 后续运行**

配置完成后，未来再次运行 `python watcher.py` 就会直接加载 `config.ini` 文件并开始监控，无需重复输入。

如果您需要修改配置（例如增删Nitter实例或更换邮箱），可以直接编辑项目根目录下的 `config.ini` 文件。

## 配置文件 (`config.ini`) 说明

- `[Email]`
  - `smtp_server`: 邮件服务器地址 (默认为 `smtp.qq.com`)。
  - `smtp_port`: 邮件服务器端口 (默认为 `465`, SSL)。
  - `sender_email`: 你的发件人邮箱。
  - `sender_password`: 你的邮箱授权码。
  - `receiver_email`: 你的收件人邮箱。
- `[Scraper]`
  - `nitter_instances`: Nitter 实例列表，每行一个。
  - `keywords`: 需要匹配的关键词，用英文逗号 `,` 分隔。 