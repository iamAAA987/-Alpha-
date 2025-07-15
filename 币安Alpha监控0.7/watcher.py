import configparser
import logging
import os
import random
import smtplib
import ssl
import sys
import time
from datetime import datetime, timedelta
from email.message import EmailMessage

import pytz
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def resource_path(relative_path):
    """ 获取资源的绝对路径，无论是从脚本运行还是从打包后的exe运行 """
    try:
        # PyInstaller 创建一个临时文件夹，并把路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- 全局配置 ---
CONFIG_FILE = resource_path('config.ini')
LOG_FILE = 'watcher.log'
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
]
# 设置北京时区
BJT = pytz.timezone('Asia/Shanghai')

def setup_logging():
    """配置日志记录，同时输出到文件和控制台"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_config():
    """加载配置文件，如果关键信息缺失则提示用户输入"""
    try:
        config = configparser.ConfigParser(allow_no_value=True)
        # 保留键的大小写
        config.optionxform = str

        if not os.path.exists(CONFIG_FILE):
            logging.error(f"错误：找不到配置文件 {CONFIG_FILE}。")
            logging.info("程序将为您创建一个新的配置文件...")
            # 创建一个空的config对象以便进行填充
            config['Email'] = {'smtp_server': 'smtp.qq.com', 'smtp_port': '465'}
            config['Scraper'] = {'keywords': '币安,Alpha,积分,用户,空投'}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
        
        config.read(CONFIG_FILE, encoding='utf-8')

        if 'Email' not in config or 'Scraper' not in config:
            logging.error("配置文件 config.ini 格式不正确，请确保包含 [Email] 和 [Scraper] 部分。")
            return None

        # 检查是否缺少必要的配置
        cfg_email = config['Email']
        cfg_scraper = config['Scraper']
        nitter_urls = [line.strip() for line in cfg_scraper.get('nitter_instances', '').split('\n') if line.strip()]

        if not all([cfg_email.get('sender_email'),
                    cfg_email.get('sender_password'),
                    cfg_email.get('receiver_email')]) or not nitter_urls:
            print("-" * 20)
            logging.warning("检测到配置信息不完整，需要进行首次设置。")
            prompt_and_save_config(config, CONFIG_FILE)
            # 重新加载配置以确保获取最新值
            config.read(CONFIG_FILE, encoding='utf-8')
            logging.info("配置完成。")
            print("-" * 20)

        return config
    except Exception as e:
        logging.error(f"处理配置文件时发生错误: {e}")
        return None

def prompt_and_save_config(config, config_file):
    """提示用户输入缺失的配置项并保存"""
    cfg_email = config['Email']
    cfg_scraper = config['Scraper']

    # 使用 get 获取现有值，如果不存在则提示输入
    if not cfg_email.get('sender_email'):
        cfg_email['sender_email'] = input("请输入您的发件人邮箱地址 (例如 12345@qq.com): ")
    if not cfg_email.get('sender_password'):
        cfg_email['sender_password'] = input("请输入您邮箱的授权码 (注意：这不是登录密码！): ")
    if not cfg_email.get('receiver_email'):
        cfg_email['receiver_email'] = input("请输入接收通知的邮箱地址: ")

    # 检查 Nitter 实例
    nitter_urls = [line.strip() for line in cfg_scraper.get('nitter_instances', '').split('\n') if line.strip()]
    if not nitter_urls:
        print("\n当前未配置Nitter实例。")
        print("请输入至少一个币安华语推特的Nitter实例地址 (例如 https://nitter.net/binancezh)。")
        print("您可以输入多个地址，每行一个，最后输入一个空行来结束输入。")
        new_instances = []
        while True:
            instance = input("> ")
            if not instance:
                break
            new_instances.append(instance.strip())
        # configparser 在写入多行值时，需要在后续行前加上缩进
        cfg_scraper['nitter_instances'] = '\n' + '\n'.join([f'    {url}' for url in new_instances])

    # 保存更新后的配置
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)

def send_email(subject, content, config):
    """发送邮件通知"""
    cfg_email = config['Email']
    smtp_port = int(cfg_email['smtp_port'])
    server = None

    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = f"币安Alpha监控 <{cfg_email['sender_email']}>"
        msg['To'] = cfg_email['receiver_email']

        context = ssl.create_default_context()

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(cfg_email['smtp_server'], smtp_port, context=context)
        elif smtp_port == 587:
            server = smtplib.SMTP(cfg_email['smtp_server'], smtp_port)
            server.starttls(context=context)
        else:
            logging.warning(f"不支持的SMTP端口: {smtp_port}，邮件可能无法发送。")
            return

        server.login(cfg_email['sender_email'], cfg_email['sender_password'])
        server.send_message(msg)
        logging.info("邮件已成功发送。")

    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP认证失败！请检查您的发件人邮箱和密码（授权码）是否正确。")
    except Exception as e:
        logging.error(f"发送邮件时发生错误: {e}")
    finally:
        if server:
            try:
                server.quit()
            except smtplib.SMTPServerDisconnected:
                logging.info("与邮件服务器的连接已关闭。")
            except Exception as e:
                logging.error(f"关闭服务器连接时发生错误: {e}")

def get_latest_tweet(p, nitter_instances):
    """
    使用 Playwright 从Nitter实例列表中获取最新的推文。
    轮询实例并在失败时自动切换，能处理JS挑战。
    """
    # 关键修复：告诉Playwright使用系统范围安装的浏览器，而不是在临时目录中寻找
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    
    # 每次尝试时都随机打乱实例顺序
    random.shuffle(nitter_instances)

    for instance in nitter_instances:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=random.choice(USER_AGENTS))
            
            logging.info(f"正在尝试从 {instance} 获取推文 (使用Playwright)...")
            page.goto(instance, timeout=30000)

            # 等待推文容器加载，这会给JS验证留出时间
            page.wait_for_selector('div.timeline-item', timeout=30000)

            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            latest_tweet_div = soup.find('div', class_='timeline-item')
            if not latest_tweet_div:
                logging.warning(f"在 {instance} 上找到timeline-item但无法解析。")
                browser.close()
                continue
            
            content_div = latest_tweet_div.find('div', class_='tweet-content')
            tweet_text = content_div.text.strip() if content_div else ""

            link_tag = latest_tweet_div.find('a', class_='tweet-link')
            tweet_id = link_tag['href'] if link_tag else ""

            browser.close()

            if tweet_text and tweet_id:
                logging.info(f"成功获取到最新推文 ID: {tweet_id}")
                return tweet_text, tweet_id
            else:
                logging.warning(f"在 {instance} 上解析推文内容或ID失败。")
                continue
        
        except PlaywrightTimeoutError:
            logging.error(f"访问 {instance} 超时，可能被验证码卡住或网络问题。")
        except Exception as e:
            logging.error(f"使用Playwright处理 {instance} 时发生未知错误: {e}")
        finally:
            if 'browser' in locals() and browser.is_connected():
                browser.close()

    logging.error("所有Nitter实例均无法访问，本次检查失败。")
    return None, None

def get_sleep_duration():
    """根据当前北京时间计算下一次检查前的休眠秒数"""
    now_bjt = datetime.now(BJT)
    hour = now_bjt.hour
    minute = now_bjt.minute

    # 晚上11:02到次日早上10:00，暂停
    if (hour == 23 and minute >= 2) or hour > 23 or hour < 10:
        pause_until = now_bjt.replace(hour=10, minute=0, second=0, microsecond=0)
        if now_bjt.hour >= 23:
            pause_until += timedelta(days=1)
        
        sleep_seconds = (pause_until - now_bjt).total_seconds()
        logging.info(f"现在是休眠时间，将暂停直到北京时间 {pause_until.strftime('%Y-%m-%d %H:%M:%S')}")
        return sleep_seconds

    # 下午3点到晚上11点 (15:00 - 23:01)
    if 15 <= hour < 23:
        # 整点前后 (xx:58 - yy:02)
        if minute >= 58 or minute <= 1:
            logging.info("处于关键时间段，30秒后检查。")
            return 30  # 30秒一次
        else:
            logging.info("处于普通高峰时段，1分钟后检查。")
            return 60  # 1分钟一次
    
    # 其他时间 (早上10:00 - 下午15:00)
    logging.info("处于普通时段，5分钟后检查。")
    return 300  # 5分钟一次

def main():
    """主函数"""
    setup_logging()
    logging.info("程序启动，开始监控币安华语推特...")
    
    config = load_config()
    if not config:
        logging.error("无法加载配置，程序退出。")
        return

    nitter_instances = [url.strip() for url in config['Scraper']['nitter_instances'].split('\n') if url.strip()]
    keywords = [kw.strip() for kw in config['Scraper']['keywords'].split(',')]
    
    if not nitter_instances or not keywords:
        logging.error("配置文件中缺少 Nitter 实例或关键词。")
        return

    logging.info(f"监控关键词: {keywords}")
    logging.info(f"使用的Nitter实例: {nitter_instances}")
    
    last_processed_tweet_id = None

    with sync_playwright() as p:
        while True:
            try:
                tweet_text, tweet_id = get_latest_tweet(p, nitter_instances)

                if tweet_text and tweet_id:
                    if tweet_id != last_processed_tweet_id:
                        logging.info(f"发现新推文: {tweet_text[:80]}...")
                        last_processed_tweet_id = tweet_id
                        
                        if all(keyword in tweet_text for keyword in keywords):
                            logging.warning(f"检测到符合所有关键词的推文！-> {tweet_text}")
                            subject = f"【重要提醒】币安Alpha新动态"
                            send_email(subject, tweet_text, config)
                        else:
                            logging.info("新推文内容不符合关键词组合，已忽略。")
                    else:
                        logging.info("未发现新推文。")

                sleep_duration = get_sleep_duration()
                time.sleep(sleep_duration)

            except KeyboardInterrupt:
                logging.info("程序被手动中断，正在退出。")
                break
            except Exception as e:
                logging.error(f"主循环发生未捕获的异常: {e}")
                logging.info("将在一分钟后重试...")
                time.sleep(60)

if __name__ == '__main__':
    main() 