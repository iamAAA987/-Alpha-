import logging
import smtplib
import ssl
from email.message import EmailMessage


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