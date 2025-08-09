import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import configparser
import os
import sys
import subprocess

from alpha_watcher.config_loader import CONFIG_FILE, LOG_FILE


class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("币安Alpha监控 - 配置面板")
        self.geometry("760x820")
        self.resizable(False, False)

        self.config_parser = configparser.ConfigParser(interpolation=None)
        self._load_config()

        self._build_ui()
        self._refresh_running_status()
        self._update_warnings_banner()

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            messagebox.showerror("错误", f"配置文件不存在: {CONFIG_FILE}")
            self.config_parser['Email'] = {}
            self.config_parser['Scraper'] = {
                'nitter_instances': '',
                'keywords': '币安,Alpha,积分,用户,空投',
            }
            self.config_parser['TWITTER'] = {
                'target_username': 'binancezh',
                'user_id': '',
                'api_key': '',
                'api_secret_key': '',
                'bearer_token': '',
            }
            self.config_parser['Schedule'] = {}
            # 新增默认 WeCom 段
            self.config_parser['WeCom'] = {
                'webhook_urls': ''
            }
            return
        self.config_parser.read(CONFIG_FILE, encoding='utf-8')
        if 'Schedule' not in self.config_parser:
            self.config_parser['Schedule'] = {}
        # 确保存在 WeCom 段
        if 'WeCom' not in self.config_parser:
            self.config_parser['WeCom'] = {'webhook_urls': ''}

    def _build_ui(self):
        # 顶部健康检查横幅
        self.warn_var = tk.StringVar(value="")
        self.warn_label = tk.Label(self, textvariable=self.warn_var, fg="#b00020")
        self.warn_label.pack(fill=tk.X, padx=10, pady=(8, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 目标账号
        frame_account = ttk.Frame(notebook)
        notebook.add(frame_account, text="目标账号")
        self._build_account_tab(frame_account)

        # 关键词
        frame_keywords = ttk.Frame(notebook)
        notebook.add(frame_keywords, text="筛选关键词")
        self._build_keywords_tab(frame_keywords)

        # 定时设置
        frame_schedule = ttk.Frame(notebook)
        notebook.add(frame_schedule, text="时间与间隔")
        self._build_schedule_tab(frame_schedule)

        # 接口与通知（原名 接口与邮箱）
        frame_api_email = ttk.Frame(notebook)
        notebook.add(frame_api_email, text="接口与通知")
        self._build_api_email_tab(frame_api_email)

        # 最近日志
        frame_logs = ttk.Frame(notebook)
        notebook.add(frame_logs, text="最近日志")
        self._build_logs_tab(frame_logs)

        # 保存按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="检查配置", command=self._update_warnings_banner).pack(side=tk.RIGHT, padx=(0, 8))

        # 运行控制
        run_frame = ttk.LabelFrame(self, text="运行控制")
        run_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(run_frame, text="启动后台监控(静默)", command=self._start_background).grid(row=0, column=0, padx=6, pady=8, sticky=tk.W)
        ttk.Button(run_frame, text="停止后台监控", command=self._stop_background).grid(row=0, column=1, padx=6, pady=8, sticky=tk.W)
        self.lbl_status_var = tk.StringVar(value="状态: 未知")
        ttk.Label(run_frame, textvariable=self.lbl_status_var).grid(row=0, column=2, padx=12, pady=8, sticky=tk.W)

    def _build_account_tab(self, parent):
        twitter = self.config_parser['TWITTER']

        ttk.Label(parent, text="目标用户名（不含@）：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        self.var_username = tk.StringVar(value=twitter.get('target_username', 'binancezh'))
        ttk.Entry(parent, textvariable=self.var_username, width=40).grid(row=0, column=1, padx=5, pady=8)

        ttk.Label(parent, text="用户ID（可选）：").grid(row=1, column=0, sticky=tk.W, padx=5, pady=8)
        self.var_userid = tk.StringVar(value=twitter.get('user_id', ''))
        ttk.Entry(parent, textvariable=self.var_userid, width=40).grid(row=1, column=1, padx=5, pady=8)

        # 左侧文本编辑 Nitter
        ttk.Label(parent, text="Nitter 实例（每行一个，末尾加 /<username>）：").grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        nitter_text = self.config_parser['Scraper'].get('nitter_instances', '').strip()
        self.txt_nitter = tk.Text(parent, width=45, height=12)
        self.txt_nitter.grid(row=2, column=1, padx=5, pady=8, sticky=tk.NW)
        self.txt_nitter.insert('1.0', nitter_text)



    def _build_keywords_tab(self, parent):
        ttk.Label(parent, text="关键词（用逗号分隔，必须全部命中才推送）：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        kw = self.config_parser['Scraper'].get('keywords', '币安,Alpha,积分,用户,空投')
        self.var_keywords = tk.StringVar(value=kw)
        ttk.Entry(parent, textvariable=self.var_keywords, width=60).grid(row=0, column=1, padx=5, pady=8)

    def _build_schedule_tab(self, parent):
        schedule = self.config_parser['Schedule']
        # Quiet
        ttk.Label(parent, text="休眠开始 (HH:MM)：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_quiet_start = tk.StringVar(value=schedule.get('quiet_start', '23:02'))
        ttk.Entry(parent, textvariable=self.var_quiet_start, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=6)

        ttk.Label(parent, text="休眠结束 (HH:MM)：").grid(row=1, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_quiet_end = tk.StringVar(value=schedule.get('quiet_end', '10:00'))
        ttk.Entry(parent, textvariable=self.var_quiet_end, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=6)

        # High
        ttk.Label(parent, text="高峰开始 (HH:MM)：").grid(row=2, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_high_start = tk.StringVar(value=schedule.get('high_start', '15:00'))
        ttk.Entry(parent, textvariable=self.var_high_start, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=6)

        ttk.Label(parent, text="高峰结束 (HH:MM)：").grid(row=3, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_high_end = tk.StringVar(value=schedule.get('high_end', '23:00'))
        ttk.Entry(parent, textvariable=self.var_high_end, width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=6)

        # Intervals
        ttk.Label(parent, text="关键分钟数：").grid(row=4, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_critical_minutes = tk.StringVar(value=schedule.get('critical_minutes', '2'))
        ttk.Entry(parent, textvariable=self.var_critical_minutes, width=10).grid(row=4, column=1, sticky=tk.W, padx=5, pady=6)

        ttk.Label(parent, text="关键间隔(秒)：").grid(row=5, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_critical_interval = tk.StringVar(value=schedule.get('critical_interval', '30'))
        ttk.Entry(parent, textvariable=self.var_critical_interval, width=10).grid(row=5, column=1, sticky=tk.W, padx=5, pady=6)

        ttk.Label(parent, text="高峰间隔(秒)：").grid(row=6, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_high_interval = tk.StringVar(value=schedule.get('high_interval', '60'))
        ttk.Entry(parent, textvariable=self.var_high_interval, width=10).grid(row=6, column=1, sticky=tk.W, padx=5, pady=6)

        ttk.Label(parent, text="普通间隔(秒)：").grid(row=7, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_normal_interval = tk.StringVar(value=schedule.get('normal_interval', '300'))
        ttk.Entry(parent, textvariable=self.var_normal_interval, width=10).grid(row=7, column=1, sticky=tk.W, padx=5, pady=6)

    def _build_api_email_tab(self, parent):
        # Twitter API
        twitter = self.config_parser['TWITTER']
        twitter_frame = ttk.LabelFrame(parent, text="Twitter API 配置")
        twitter_frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(twitter_frame, text="API Key：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_api_key = tk.StringVar(value=twitter.get('api_key', ''))
        ttk.Entry(twitter_frame, textvariable=self.var_api_key, width=60).grid(row=0, column=1, padx=5, pady=6)

        ttk.Label(twitter_frame, text="API Secret Key：").grid(row=1, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_api_secret = tk.StringVar(value=twitter.get('api_secret_key', ''))
        ttk.Entry(twitter_frame, textvariable=self.var_api_secret, width=60).grid(row=1, column=1, padx=5, pady=6)

        ttk.Label(twitter_frame, text="Bearer Token：").grid(row=2, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_bearer = tk.StringVar(value=twitter.get('bearer_token', ''))
        ttk.Entry(twitter_frame, textvariable=self.var_bearer, width=60).grid(row=2, column=1, padx=5, pady=6)

        # Email 配置
        email = self.config_parser['Email'] if 'Email' in self.config_parser else {}
        email_frame = ttk.LabelFrame(parent, text="邮件通知配置")
        email_frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(email_frame, text="SMTP 服务器：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_smtp_server = tk.StringVar(value=(email.get('smtp_server', 'smtp.qq.com') if isinstance(email, dict) else email.get('smtp_server', 'smtp.qq.com')))
        ttk.Entry(email_frame, textvariable=self.var_smtp_server, width=30).grid(row=0, column=1, padx=5, pady=6, sticky=tk.W)

        ttk.Label(email_frame, text="SMTP 端口：").grid(row=0, column=2, sticky=tk.W, padx=5, pady=6)
        self.var_smtp_port = tk.StringVar(value=(email.get('smtp_port', '465') if isinstance(email, dict) else email.get('smtp_port', '465')))
        ttk.Entry(email_frame, textvariable=self.var_smtp_port, width=10).grid(row=0, column=3, padx=5, pady=6, sticky=tk.W)

        ttk.Label(email_frame, text="发件人邮箱：").grid(row=1, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_sender_email = tk.StringVar(value=(email.get('sender_email', '') if isinstance(email, dict) else email.get('sender_email', '')))
        ttk.Entry(email_frame, textvariable=self.var_sender_email, width=30).grid(row=1, column=1, padx=5, pady=6, sticky=tk.W)

        ttk.Label(email_frame, text="发件人密码/授权码：").grid(row=1, column=2, sticky=tk.W, padx=5, pady=6)
        self.var_sender_password = tk.StringVar(value=(email.get('sender_password', '') if isinstance(email, dict) else email.get('sender_password', '')))
        ttk.Entry(email_frame, textvariable=self.var_sender_password, show='*', width=20).grid(row=1, column=3, padx=5, pady=6, sticky=tk.W)

        ttk.Label(email_frame, text="收件人邮箱：").grid(row=2, column=0, sticky=tk.W, padx=5, pady=6)
        self.var_receiver_email = tk.StringVar(value=(email.get('receiver_email', '') if isinstance(email, dict) else email.get('receiver_email', '')))
        ttk.Entry(email_frame, textvariable=self.var_receiver_email, width=30).grid(row=2, column=1, padx=5, pady=6, sticky=tk.W)

        # 企业微信机器人配置
        wecom = self.config_parser['WeCom'] if 'WeCom' in self.config_parser else {'webhook_urls': ''}
        wecom_frame = ttk.LabelFrame(parent, text="企业微信机器人配置")
        wecom_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(wecom_frame, text="Webhook 列表（逗号或换行分隔）：").grid(row=0, column=0, sticky=tk.NW, padx=5, pady=6)
        self.txt_wecom = tk.Text(wecom_frame, width=60, height=4)
        self.txt_wecom.grid(row=0, column=1, padx=5, pady=6, sticky=tk.W)
        wecom_text = wecom.get('webhook_urls', '') if isinstance(wecom, dict) else wecom.get('webhook_urls', '')
        self.txt_wecom.insert('1.0', wecom_text)

    def _build_logs_tab(self, parent):
        # 最近 5 条与推文抓取相关的日志
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=6, pady=(8, 0))
        ttk.Button(toolbar, text="刷新", command=self._refresh_recent_logs).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="打开日志目录", command=self._open_log_dir).pack(side=tk.LEFT, padx=(8, 0))

        self.txt_logs = tk.Text(parent, width=100, height=26, state=tk.DISABLED)
        self.txt_logs.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._refresh_recent_logs()


    def _log_file_path(self) -> str:
        return os.path.join(self._exe_dir(), LOG_FILE)

    def _refresh_recent_logs(self):
        path = self._log_file_path()
        logs: list[str] = []
        if os.path.exists(path):
            try:
                # 只读取文件尾部，避免大日志卡 UI
                with open(path, 'rb') as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    back = min(size, 120_000)
                    f.seek(size - back, os.SEEK_SET)
                    data = f.read().decode('utf-8', errors='ignore')
                lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
                # 过滤抓取相关关键词
                keywords = ["推文", "tweet", "获取", "成功", "失败", "ID:"]
                filtered = [ln for ln in lines if any(k in ln for k in keywords)]
                logs = filtered[-5:] if len(filtered) >= 5 else filtered
            except Exception as e:
                logs = ["读取日志失败: {}".format(e)]
        else:
            logs = ["未找到 watcher.log，可能尚未运行过监控或日志路径不一致。"]

        self.txt_logs.config(state=tk.NORMAL)
        self.txt_logs.delete('1.0', tk.END)
        for entry in logs:
            self.txt_logs.insert(tk.END, entry + "\n")
        self.txt_logs.config(state=tk.DISABLED)

    def _open_log_dir(self):
        try:
            os.startfile(self._exe_dir())
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录: {e}")

    def _required_config_problems(self) -> list[str]:
        problems: list[str] = []
        # 通知通道检查：Email 或 WeCom 至少一个
        wecom_conf = self.config_parser['WeCom'] if 'WeCom' in self.config_parser else None
        wecom_raw = (wecom_conf.get('webhook_urls', '') if wecom_conf else '').strip()
        wecom_ok = any(ln.strip() for ln in wecom_raw.replace(',', '\n').splitlines()) if wecom_raw else False

        email = self.config_parser['Email'] if 'Email' in self.config_parser else None
        sender_email = email.get('sender_email') if email else ''
        sender_password = email.get('sender_password') if email else ''
        receiver_email = email.get('receiver_email') if email else ''
        email_ok = bool(sender_email and sender_password and receiver_email)

        if not (email_ok or wecom_ok):
            problems.append("未配置任何通知通道（Email 或 WeCom）")
        else:
            # 仅当 WeCom 未配置时，严格检查 Email 细项
            if not wecom_ok:
                if not sender_email or not sender_password:
                    problems.append("发件人邮箱或授权码未设置")
                if not receiver_email:
                    problems.append("收件人邮箱未设置")
                try:
                    int(email.get('smtp_port', '465') if email else '465')
                except ValueError:
                    problems.append("SMTP 端口不是有效数字")

        # 抓取来源检查：至少有其一
        nitter_text = self.config_parser['Scraper'].get('nitter_instances', '').strip()
        nitter_ok = any(ln.strip() for ln in nitter_text.splitlines())
        twitter = self.config_parser['TWITTER']
        twitter_ok = bool(twitter.get('bearer_token', '').strip()) and bool(twitter.get('user_id', '').strip())
        if not (nitter_ok or twitter_ok):
            problems.append("未配置 Nitter 实例，且 Twitter API 未就绪（bearer_token + user_id）")

        # 关键词
        if not self.config_parser['Scraper'].get('keywords', '').strip():
            problems.append("关键词未设置")

        return problems

    def _update_warnings_banner(self):
        problems = self._required_config_problems()
        if problems:
            self.warn_var.set("配置提醒：" + "；".join(problems))
        else:
            self.warn_var.set("")

    def save_config(self):
        # 写入账户与抓取
        self.config_parser['TWITTER']['target_username'] = self.var_username.get().strip()
        self.config_parser['TWITTER']['user_id'] = self.var_userid.get().strip()
        self.config_parser['Scraper']['nitter_instances'] = self.txt_nitter.get('1.0', tk.END).strip()
        self.config_parser['Scraper']['keywords'] = self.var_keywords.get().strip()

        # 写入 Twitter API
        self.config_parser['TWITTER']['api_key'] = self.var_api_key.get().strip()
        self.config_parser['TWITTER']['api_secret_key'] = self.var_api_secret.get().strip()
        self.config_parser['TWITTER']['bearer_token'] = self.var_bearer.get().strip()

        # 写入时间
        schedule = self.config_parser['Schedule']
        schedule['quiet_start'] = self.var_quiet_start.get().strip() or '23:02'
        schedule['quiet_end'] = self.var_quiet_end.get().strip() or '10:00'
        schedule['high_start'] = self.var_high_start.get().strip() or '15:00'
        schedule['high_end'] = self.var_high_end.get().strip() or '23:00'
        schedule['critical_minutes'] = self.var_critical_minutes.get().strip() or '2'
        schedule['critical_interval'] = self.var_critical_interval.get().strip() or '30'
        schedule['high_interval'] = self.var_high_interval.get().strip() or '60'
        schedule['normal_interval'] = self.var_normal_interval.get().strip() or '300'

        # 写入 Email 配置
        if 'Email' not in self.config_parser:
            self.config_parser['Email'] = {}
        self.config_parser['Email']['smtp_server'] = self.var_smtp_server.get().strip() or 'smtp.qq.com'
        self.config_parser['Email']['smtp_port'] = self.var_smtp_port.get().strip() or '465'
        self.config_parser['Email']['sender_email'] = self.var_sender_email.get().strip()
        self.config_parser['Email']['sender_password'] = self.var_sender_password.get().strip()
        self.config_parser['Email']['receiver_email'] = self.var_receiver_email.get().strip()

        # 写入 WeCom 配置
        if 'WeCom' not in self.config_parser:
            self.config_parser['WeCom'] = {}
        self.config_parser['WeCom']['webhook_urls'] = self.txt_wecom.get('1.0', tk.END).strip()

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            self.config_parser.write(f)

        # 更新提醒
        self._update_warnings_banner()

        # 如有关键配置缺失，弹窗提醒
        problems = self._required_config_problems()
        if problems:
            messagebox.showwarning("提醒", "仍有配置项未完成：\n- " + "\n- ".join(problems))
        else:
            messagebox.showinfo("成功", "配置已保存！")

    # ---------------- 运行控制逻辑 ----------------
    def _exe_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.abspath('.')

    def _watcher_path(self) -> str:
        base = self._exe_dir()
        exe_path = os.path.join(base, 'watcher.exe')
        if os.path.exists(exe_path):
            return exe_path
        # PyInstaller 默认目录结构: dist/watcher-gui/ 与 dist/watcher/
        sibling = os.path.normpath(os.path.join(base, '..', 'watcher', 'watcher.exe'))
        if os.path.exists(sibling):
            return sibling
        # dev fallback
        return os.path.join(base, 'watcher.py')

    def _pid_file(self) -> str:
        return os.path.join(self._exe_dir(), 'watcher.pid')

    def _is_running(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            # Windows: 查询 tasklist
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return str(pid) in result.stdout
        except Exception:
            return False

    def _refresh_running_status(self):
        pid = None
        pid_path = self._pid_file()
        if os.path.exists(pid_path):
            try:
                with open(pid_path, 'r', encoding='utf-8') as f:
                    pid = int(f.read().strip())
            except Exception:
                pid = None
        running = self._is_running(pid) if pid else False
        if not running and os.path.exists(pid_path):
            try:
                os.remove(pid_path)
            except Exception:
                pass
        status = f"状态: 后台运行中 (PID {pid})" if running else "状态: 未在运行"
        self.lbl_status_var.set(status)

    def _start_background(self):
        # 防重复启动
        pid = None
        if os.path.exists(self._pid_file()):
            try:
                with open(self._pid_file(), 'r', encoding='utf-8') as f:
                    pid = int(f.read().strip())
            except Exception:
                pid = None
        if pid and self._is_running(pid):
            messagebox.showinfo("提示", f"监控已在后台运行 (PID {pid})。")
            self._refresh_running_status()
            return

        target = self._watcher_path()
        if not os.path.exists(target):
            messagebox.showerror("错误", f"未找到监控程序: {target}")
            return

        try:
            if target.endswith('.exe'):
                proc = subprocess.Popen([target], creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
            else:
                # dev 模式
                proc = subprocess.Popen([sys.executable, target], creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
            with open(self._pid_file(), 'w', encoding='utf-8') as f:
                f.write(str(proc.pid))
            messagebox.showinfo("成功", "后台监控已启动并静默运行。")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {e}")
        finally:
            self._refresh_running_status()

    def _stop_background(self):
        pid_path = self._pid_file()
        if not os.path.exists(pid_path):
            messagebox.showinfo("提示", "未发现正在运行的后台监控。")
            self._refresh_running_status()
            return
        try:
            with open(pid_path, 'r', encoding='utf-8') as f:
                pid = int(f.read().strip())
        except Exception:
            pid = None
        if not pid or not self._is_running(pid):
            try:
                os.remove(pid_path)
            except Exception:
                pass
            messagebox.showinfo("提示", "后台监控已不在运行。")
            self._refresh_running_status()
            return
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                os.remove(pid_path)
            except Exception:
                pass
            messagebox.showinfo("成功", "已停止后台监控。")
        except Exception as e:
            messagebox.showerror("错误", f"停止失败: {e}")
        finally:
            self._refresh_running_status()


if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop() 