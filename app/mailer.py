"""众肯会服务号 v2 - 管理员邮件通知（QQ 邮箱 SMTP SSL）"""
import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText

from .config import settings

logger = logging.getLogger("zhongkenhui")


def send_notification(subject: str, body: str) -> bool:
    """同步发送邮件；调用方应放在后台任务里，避免阻塞请求。"""
    if not settings.MAIL_ENABLED or not settings.SMTP_USER or not settings.ADMIN_EMAIL:
        logger.info("邮件通知未启用，跳过: %s", subject)
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(f"【众肯会】{subject}", "utf-8")
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ADMIN_EMAIL
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
            smtp.sendmail(settings.SMTP_USER, [settings.ADMIN_EMAIL], msg.as_string())
        logger.info("邮件通知已发送: %s", subject)
        return True
    except Exception:
        logger.exception("邮件发送失败: %s", subject)
        return False
