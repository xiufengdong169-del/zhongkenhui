"""众肯会服务号 v2 - 微信回调处理（Token 验证 / 事件 / 消息 / OAuth 网页授权）"""
import hashlib
import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from . import db
from .config import settings
from .mailer import send_notification

logger = logging.getLogger("zhongkenhui")

WELCOME_TEXT = (
    "欢迎加入众肯会！\n\n"
    "我们致力于为您提供优质的信息系统工程咨询与监理服务。\n\n"
    "如有问题请直接留言，我们会尽快回复。"
)

DEFAULT_REPLY = "收到您的留言，我们会尽快处理。\n\n（如需人工服务请留下联系方式）"

SET_ADMIN_KEYWORD = "设置管理员"

# ---- access_token 内存缓存 ----
_token_cache = {"token": "", "expires_at": 0}


def get_access_token() -> str:
    """获取微信 access_token（带内存缓存）"""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={settings.WX_APPID}&secret={settings.WX_APPSECRET}"
    )
    try:
        resp = httpx.get(url, timeout=10).json()
        token = resp.get("access_token", "")
        expires_in = resp.get("expires_in", 7200)
        if token:
            _token_cache["token"] = token
            _token_cache["expires_at"] = now + expires_in
            logger.info("access_token 已刷新，有效期 %ss", expires_in)
        return token
    except Exception as e:
        logger.error("获取 access_token 失败: %s", e)
        return _token_cache.get("token", "")


def check_signature(signature: str, timestamp: str, nonce: str) -> bool:
    items = sorted([settings.WX_TOKEN, timestamp or "", nonce or ""])
    sha = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    return sha == signature


def _reply_text(to_user: str, from_user: str, content: str) -> str:
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


# ==================== OAuth 2.0 网页授权 ====================


def build_oauth_url(redirect_uri: str, scope: str = "snsapi_base", state: str = "") -> str:
    """构建微信 OAuth 2.0 网页授权 URL

    参数:
        redirect_uri: 回调地址（完整 URL）
        scope: snsapi_base（静默，仅 openid）或 snsapi_userinfo（弹窗，含昵称头像）
        state: 回调时原样返回，用于携带目标页面路径
    """
    return (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={settings.WX_APPID}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={urllib.parse.quote(state, safe='')}"
        "#wechat_redirect"
    )


def exchange_code(code: str) -> dict:
    """用 OAuth code 换取 access_token 和 openid

    返回:
        {"openid": "...", "access_token": "...", ...} 或 {}（失败）
    """
    url = (
        "https://api.weixin.qq.com/sns/oauth2/access_token"
        f"?appid={settings.WX_APPID}"
        f"&secret={settings.WX_APPSECRET}"
        f"&code={code}"
        f"&grant_type=authorization_code"
    )
    try:
        resp = httpx.get(url, timeout=10).json()
        if "errcode" in resp and resp["errcode"] != 0:
            logger.error("OAuth code 换 token 失败: %s", resp)
            return {}
        return resp
    except Exception as e:
        logger.error("OAuth code 换 token 异常: %s", e)
        return {}


def get_oauth_userinfo(oauth_access_token: str, openid: str) -> dict:
    """通过网页授权 access_token 获取用户信息（昵称、头像等）

    仅在 scope=snsapi_userinfo 时可用
    """
    url = (
        "https://api.weixin.qq.com/sns/userinfo"
        f"?access_token={oauth_access_token}&openid={openid}&lang=zh_CN"
    )
    try:
        resp = httpx.get(url, timeout=10).json()
        if "errcode" in resp:
            logger.warning("OAuth 获取用户信息失败: %s", resp)
            return {}
        return resp
    except Exception as e:
        logger.error("OAuth 获取用户信息异常: %s", e)
        return {}


# ==================== 用户信息（关注者） ====================


def get_user_info(openid: str) -> dict:
    """通过 OpenID 获取关注者信息（昵称、头像等）

    仅对已关注公众号的用户有效，需认证服务号
    """
    token = get_access_token()
    if not token:
        return {}
    url = (
        f"https://api.weixin.qq.com/cgi-bin/user/info"
        f"?access_token={token}&openid={openid}&lang=zh_CN"
    )
    try:
        resp = httpx.get(url, timeout=10).json()
        if resp.get("errcode"):
            logger.warning("获取用户信息失败: %s", resp)
            return {}
        return resp
    except Exception as e:
        logger.error("获取用户信息异常: %s", e)
        return {}


def _format_user_email(openid: str, user_info: dict, now: str) -> tuple:
    """根据用户信息构建邮件主题和正文"""
    nickname = user_info.get("nickname")

    if nickname:
        headimgurl = user_info.get("headimgurl", "")
        sex = user_info.get("sex", 0)
        sex_str = {1: "男", 2: "女"}.get(sex, "未知")
        city = user_info.get("city", "")
        province = user_info.get("province", "")
        country = user_info.get("country", "")
        location = ", ".join(filter(None, [country, province, city])) or "未知"

        email_body = (
            f"OpenID: {openid}\n"
            f"昵称: {nickname}\n"
            f"性别: {sex_str}\n"
            f"地区: {location}\n"
            f"头像: {headimgurl}\n"
            f"关注时间: {now}\n\n"
            f"请登录微信公众平台查看详情。"
        )
        subject = f"新用户关注 - {nickname}"
    else:
        email_body = (
            f"OpenID: {openid}\n"
            f"关注时间: {now}\n\n"
            f"未能获取用户详细信息。"
        )
        subject = "新用户关注"

    return subject, email_body


# ==================== 消息/事件处理 ====================


def handle_message(xml_body: bytes, background_tasks) -> str:
    """处理微信 POST 回调，返回被动回复 XML（或空串）。"""
    if not xml_body:
        return ""
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError:
        logger.warning("微信回调 XML 解析失败")
        return ""

    def _get(tag: str) -> str:
        el = root.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    from_user = _get("FromUserName")  # 用户 openid
    to_user = _get("ToUserName")      # 公众号 ghid
    msg_type = _get("MsgType")
    event = _get("Event")
    content = _get("Content")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.log_message(from_user, msg_type, event, content)

    # ---- 事件 ----
    if msg_type == "event":
        if event == "subscribe":
            logger.info("新用户关注: %s", from_user)
            user_info = get_user_info(from_user)
            subject, email_body = _format_user_email(from_user, user_info, now)
            background_tasks.add_task(
                send_notification,
                f"【众肯会】{subject}",
                email_body,
            )
            return _reply_text(from_user, to_user, WELCOME_TEXT)

        if event == "unsubscribe":
            logger.info("用户取消关注: %s", from_user)
            user_info = get_user_info(from_user)
            nickname = user_info.get("nickname")

            if nickname:
                subject = f"用户取消关注 - {nickname}"
                body = f"OpenID: {from_user}\n昵称: {nickname}\n取消时间: {now}"
            else:
                subject = "用户取消关注"
                body = f"OpenID: {from_user}\n取消时间: {now}"

            background_tasks.add_task(
                send_notification,
                f"【众肯会】{subject}",
                body,
            )
            return ""
        return ""

    # ---- 文本消息 ----
    if msg_type == "text":
        if content == SET_ADMIN_KEYWORD:
            db.set_admin(from_user)
            logger.info("设置管理员: %s", from_user)
            return _reply_text(from_user, to_user, "管理员设置成功！您将收到关注/取消关注通知。")

        background_tasks.add_task(
            send_notification,
            "公众号收到新留言",
            f"OpenID: {from_user}\n留言内容: {content}\n时间: {now}",
        )
        return _reply_text(from_user, to_user, DEFAULT_REPLY)

    return ""
