# 币安 Alpha 监控 2.0

一个用于监控 Twitter/X 币安中文官方账号（默认 `@binancezh`）最新推文的轻量工具。支持：
- 无需官方 API 的 Nitter 抓取（Playwright 无头浏览器 + 解析）
- 可选 Twitter 官方 API（需自备凭据）
- 关键词过滤（全部命中才推送）
- 邮件通知（SMTP，支持 465/587）
- 企业微信群机器人通知（可配置多个 webhook）
- 去重与节流（避免重复/过频推送）
- 图形化配置面板 `gui.py`

请使用示例配置 `config.example.ini` 自行填写到本地 `config.ini`。

## 目录结构
```
alpha_watcher/
  config_loader.py   # 读取/校验配置、日志与统计
  fetchers.py        # Nitter 与 Twitter API 抓取
  notifier.py        # SMTP 邮件 + 企业微信机器人通知
  scheduler.py       # 智能调度（安静/高峰/普通/关键时段）
  deduper.py         # 去重（ID + 文本指纹）
  utils.py           # UA 列表、时区、ID 规范化等
  singleton.py       # 单实例运行
watcher.py           # 后台监控主循环
gui.py               # 图形化配置与一键启动/停止
config.example.ini   # 示例配置（安全）
requirements.txt     # 依赖列表
watcher.spec         # 后端打包脚本（PyInstaller）
watcher-gui.spec     # GUI 打包脚本（PyInstaller）
```

## 环境要求
- Python 3.10+（推荐 3.10/3.11/3.12）
- Windows 10/11（其他系统需自行适配 Playwright 浏览器安装路径）

## 安装
```bash
pip install -r requirements.txt
# 首次使用 Playwright 需安装浏览器内核
playwright install
```

## 配置
复制示例文件并填写本地配置（不要提交到仓库）：
```bash
cp config.example.ini config.ini
# Windows PowerShell 可用： Copy-Item config.example.ini config.ini
```
编辑 `config.ini`：
- [Email]
  - `smtp_server`: 默认 `smtp.qq.com`
  - `smtp_port`: `465`(SSL) 或 `587`(STARTTLS)
  - `sender_email`: 发件人邮箱
  - `sender_password`: 邮箱授权码或密码（推荐授权码）
  - `receiver_email`: 收件人邮箱
- [WeCom]
  - `webhook_urls`: 企业微信群机器人 webhook 列表（支持多个，用逗号或换行分隔）。
    - 形如：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx-xxxx-xxxx`
    - 消息体为文本，自动截断到 2048 字符以内。
- [Scraper]
  - `nitter_instances`: 每行一个 Nitter 实例，末尾加 `/binancezh`
  - `keywords`: 以逗号分隔，必须全部命中才发送
- [TWITTER]（可选）
  - `target_username`: 默认 `binancezh`
  - `user_id`: 对应用户 ID（使用 API 时建议填）
  - `api_key`、`api_secret_key`、`bearer_token`: 官方 API 凭据（自备）
- [Schedule]
  - `quiet_start/quiet_end`: 安静时间段，暂停到 `quiet_end`
  - `high_start/high_end`: 高峰时间段
  - `critical_minutes`: 整点前后关键分钟数
  - `critical_interval/high_interval/normal_interval`: 对应检查间隔秒数

> 若未配置 Twitter API，程序将仅使用 Nitter 抓取。

## 运行方式
- 命令行运行（后台循环）
  ```bash
  python watcher.py
  ```
- 图形化配置面板
  ```bash
  python gui.py
  ```
![微信图片_20250809230513_38](https://github.com/user-attachments/assets/1e72b64a-892b-46c1-a6e0-f025fd90f4e7)

  - 支持保存配置、健康检查提示
  - 一键启动/停止后台监控（Windows，采用进程与 PID 文件管理）

## 去重与节流
- 去重依据：规范化推文 ID + 文本指纹（小写化+空白合并后 SHA1）
- 窗口大小、TTL、最小推送间隔可在 `watcher.py` 中构造 `Deduper` 时调整（默认：`max_history=300`，`ttl=7天`，`min_push_interval=90秒`）

## 日志与统计
- 日志文件：`watcher.log`
- 统计文件：`stats.json`
- 去重状态：`dedup_state.json`
- GUI 中“最近日志”页可快速查看抓取与推送相关日志片段

## 打包发布（可选）
打包前确保本地 `config.ini` 不含敏感信息（或仅在发布 zip 中放置 `config.example.ini`）：
```powershell
python -m pip install pyinstaller playwright
playwright install
pyinstaller watcher.spec
pyinstaller watcher-gui.spec
```
产物位于 `dist/` 目录：
- `dist/watcher/` 后台监控可执行文件
- `dist/watcher-gui/` GUI 可执行文件

> `watcher.spec` 默认将 `config.ini` 打入包内。若要只打包示例：请改 spec 的 `datas` 为 `('config.example.ini', '.')` 并在运行时检测不存在 `config.ini` 时引导用户复制。

## 安全与开源注意
- 仓库已移除所有邮箱与 Twitter/X 凭据；请不要提交真实 `config.ini`、日志与构建产物。
- `.gitignore` 已包含：`config.ini`、`*.log`、`*.pid`、`*.lock`、`stats.json`、`dedup_state.json`、`dist/`、`build/`、`*.spec`。
- 若历史提交包含敏感信息，建议使用 `git filter-repo` 或 BFG 清理并强制推送（详见仓库 issue 或常见做法）。

## 常见问题（FAQ）
- Q: Playwright 提示未安装浏览器？
  - A: 执行 `playwright install`。
- Q: Twitter API 429 或失败？
  - A: 受额度或权限限制。可仅使用 Nitter 抓取，或在开发者平台提升权限/更换 token。
- Q: 邮件发送失败（认证错误）？
  - A: 确认 `smtp_server`、端口与授权码是否正确，QQ 邮箱建议使用授权码而非明文密码。
- Q: 重复推送或过频？
  - A: 调整 `[Schedule]` 或 `Deduper` 参数，确保 `min_push_interval_seconds` 足够长。
- Q: GUI 显示“未配置 Nitter 且 Twitter API 未就绪”？
  - A: 至少配置一项：填写 Nitter 实例或提供 `bearer_token + user_id`。

## 结语f
- 整个项目以vibe coding为主，可能存在很多问题没有测试到，尽请各位大佬提出建议
- 这算是一次大更新，相比原来的代码尝试修复了过量提醒的问题，并添加gui界面和企业微信提醒功能
- 另外希望大家支持这些nitter的提供方






