"""众肯会服务号 v2 - 配置（从 .env 读取）"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # 微信服务号
    WX_TOKEN: str = os.getenv("WX_TOKEN", "zonken2025")
    WX_APPID: str = os.getenv("WX_APPID", "wxe8f700245a3d2af7")
    WX_APPSECRET: str = os.getenv("WX_APPSECRET", "")

    # 数据库（分量字段，避免密码特殊字符在 URL 中出问题）
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "zhongkenhui")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "zhongkenhui")

    # SMTP 邮件通知
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.qq.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    MAIL_ENABLED: bool = os.getenv("MAIL_ENABLED", "1") == "1"

    # 站点
    PUBLIC_BASE: str = os.getenv("PUBLIC_BASE", "http://wx.zk550.cn")
    LOG_FILE: str = os.getenv("LOG_FILE", "/var/log/zhongkenhui/app.log")

    # OAuth 网页授权（需在公众平台配置「网页授权域名」后才能开启）
    OAUTH_ENABLED: bool = os.getenv("OAUTH_ENABLED", "0") == "1"


settings = Settings()
