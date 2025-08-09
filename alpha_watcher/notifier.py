import logging
import smtplib
import ssl
from email.message import EmailMessage

import requests


def send_email(subject: str, content: str, config) -> None:
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


def send_wecom(text: str, config) -> None:
    """
    将文本通过企业微信群机器人推送。
    读取 [WeCom] 配置段的 webhook_urls（支持多行或逗号分隔多个 URL）。
    """
    try:
        if 'WeCom' not in config:
            logging.debug("未配置 WeCom 段，跳过企业微信推送。")
            return
        cfg = config['WeCom']
        raw = cfg.get('webhook_urls', '').strip()
        if not raw:
            logging.debug("WeCom.webhook_urls 为空，跳过企业微信推送。")
            return
        # 支持多行或逗号分隔
        urls: list[str] = [u.strip() for u in raw.replace(',', '\n').splitlines() if u.strip()]
        if not urls:
            logging.debug("未解析到有效的企业微信 webhook URL，跳过推送。")
            return

        payload = {"msgtype": "text", "text": {"content": text[:2048]}}
        headers = {"Content-Type": "application/json"}
        for url in urls:
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json() if resp.headers.get('Content-Type', '').startswith('application/json') else {}
                    if isinstance(data, dict) and data.get('errcode') == 0:
                        logging.info("企业微信机器人推送成功。")
                    else:
                        logging.warning(f"企业微信推送返回异常: {data}")
                else:
                    logging.error(f"企业微信推送失败，HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logging.error(f"企业微信推送请求异常: {e}")
    except Exception as e:
        logging.error(f"企业微信推送发生未处理错误: {e}") 