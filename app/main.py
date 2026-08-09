"""众肯会服务号 v2 - FastAPI 主程序

功能对齐原 PHP 版（zhongkenhui_v1.0）：
- 微信回调：Token 验证 / 关注欢迎 / 取关通知 / 留言自动回复 / 设置管理员
- 微信 OAuth 2.0 网页授权：静默获取用户 OpenID
- H5 页面：首页 / 平台介绍 / 加入众肯 / 注册惊喜 / 达人推荐 / 项目信息 / 业务合作 / 技术合作
- 数据入库（独立库 zhongkenhui）+ 管理员邮件通知
"""
import logging
import logging.handlers
import os
import re
from pathlib import Path

from fastapi import BackgroundTasks, Cookie, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db, wechat
from .config import settings
from .mailer import send_notification

# ---------- 日志 ----------
logger = logging.getLogger("zhongkenhui")
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
logger.addHandler(_sh)
try:
    os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
    _fh = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    _fh.setFormatter(_fmt)
    logger.addHandler(_fh)
except OSError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="众肯会服务号", docs_url=None, redoc_url=None)

_static_dir = BASE_DIR / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")

# Cookie 名
OPENID_COOKIE = "zk_openid"
OAUTH_REDIRECT_PATH = "/wx/oauth"


@app.on_event("startup")
def _startup():
    try:
        db.init_tables()
    except Exception:
        logger.exception("启动建表失败（请检查数据库配置）")


# ---------- 工具函数 ----------
def _is_wechat(request: Request) -> bool:
    """检测请求是否来自微信内置浏览器"""
    ua = request.headers.get("user-agent", "")
    return "micromessenger" in ua.lower()


def _read_openid(request: Request) -> str:
    """从 Cookie 中读取 openid"""
    return request.cookies.get(OPENID_COOKIE, "") or ""


def _oauth_redirect(request: Request, scope: str = "snsapi_base") -> RedirectResponse:
    """构建 OAuth 授权重定向"""
    # 拼接当前完整路径作为 state，回调后再跳回来
    state = request.url.path
    oauth_url = wechat.build_oauth_url(
        redirect_uri=f"{settings.PUBLIC_BASE}{OAUTH_REDIRECT_PATH}",
        scope=scope,
        state=state,
    )
    return RedirectResponse(url=oauth_url, status_code=302)


def _need_oauth(request: Request) -> bool:
    """判断是否需要 OAuth 重定向（微信内且未授权且未跳过）"""
    # OAuth 未开启时直接返回 False（需在公众平台配置网页授权域名后开启）
    if not settings.OAUTH_ENABLED:
        return False
    if not _is_wechat(request):
        return False
    if _read_openid(request):
        return False
    # noauth=1 参数可跳过 OAuth（调试或域名未配置时使用）
    if request.query_params.get("noauth") == "1":
        return False
    return True


# ==================== 健康检查 ====================


@app.get("/health")
def health():
    try:
        with db.get_db() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"ok": True, "db": db_ok, "app": "zhongkenhui-v2"}


@app.get("/wx/debug")
def wx_debug(openid: str = Query("")):
    """诊断端点：检查配置、access_token、菜单、用户信息"""
    import time as _time
    info = {
        "PUBLIC_BASE": settings.PUBLIC_BASE,
        "OAUTH_ENABLED": settings.OAUTH_ENABLED,
        "WX_APPID": settings.WX_APPID,
        "WX_APPSECRET_set": bool(settings.WX_APPSECRET),
        "WX_TOKEN": settings.WX_TOKEN,
        "MAIL_ENABLED": settings.MAIL_ENABLED,
        "time": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 测试 access_token
    token = wechat.get_access_token()
    info["access_token_ok"] = bool(token)
    info["access_token_prefix"] = token[:20] + "..." if token else "(empty)"

    # 测试菜单
    menu = wechat.get_menu_info()
    info["menu"] = menu

    # 如果传了 openid，测试获取用户信息
    if openid:
        user_info = wechat.get_user_info(openid)
        info["user_info_test"] = user_info

    # OAuth URL 示例
    oauth_url = wechat.build_oauth_url(
        redirect_uri=f"{settings.PUBLIC_BASE}/wx/oauth",
        scope="snsapi_base",
        state="/register",
    )
    info["oauth_url_example"] = oauth_url

    return JSONResponse(info)


# ==================== 微信回调 ====================


@app.get("/wx/callback")
def wx_verify(
    signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    echostr: str = Query(""),
):
    if wechat.check_signature(signature, timestamp, nonce):
        logger.info("微信 Token 验证成功")
        return PlainTextResponse(echostr)
    logger.warning("微信 Token 验证失败")
    return PlainTextResponse("error")


@app.post("/wx/callback")
async def wx_message(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    reply = wechat.handle_message(body, background_tasks)
    return PlainTextResponse(reply, media_type="application/xml")


# ==================== 微信 OAuth 2.0 回调 ====================


@app.get(OAUTH_REDIRECT_PATH)
def wx_oauth_callback(
    request: Request,
    code: str = Query(""),
    state: str = Query(""),
):
    """微信 OAuth 2.0 回调：用 code 换 openid，写 Cookie，跳回目标页面"""
    # state 是目标页面路径（如 /register），确保安全（只允许站内路径）
    redirect_url = state if (state and state.startswith("/")) else "/"

    if not code:
        logger.warning("OAuth 回调缺少 code 参数，直接跳转目标页面")
        return RedirectResponse(url=redirect_url, status_code=302)

    result = wechat.exchange_code(code)
    openid = result.get("openid", "")

    if not openid:
        logger.error("OAuth 回调获取 openid 失败: %s，直接跳转目标页面", result)
        # OAuth 失败时仍然跳转到目标页面（不设 cookie），确保页面可访问
        return RedirectResponse(url=redirect_url, status_code=302)

    logger.info("OAuth 授权成功，openid: %s...", openid[:8])

    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key=OPENID_COOKIE,
        value=openid,
        max_age=30 * 24 * 3600,   # 30 天
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


# ==================== H5 页面 ====================


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    openid = _read_openid(request)
    # 微信内未授权时跳 OAuth
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "index.html", {"request": request, "openid": openid}
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "about.html", {"request": request, "openid": openid}
    )


@app.get("/surprise", response_class=HTMLResponse)
def surprise(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "surprise.html", {"request": request, "openid": openid}
    )


@app.get("/business", response_class=HTMLResponse)
def business(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "business.html", {"request": request, "openid": openid}
    )


@app.get("/tech", response_class=HTMLResponse)
def tech(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "tech.html", {"request": request, "openid": openid}
    )


# ---- 加入众肯（注册） ----


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "openid": openid, "message": "", "success": False},
    )


@app.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(""),
    phone: str = Form(""),
    province: str = Form(""),
    describe: str = Form(""),
    openid: str = Cookie(default="", alias=OPENID_COOKIE),
):
    name, phone, province, describe = name.strip(), phone.strip(), province.strip(), describe.strip()
    ctx = {"request": request, "openid": openid, "success": False}

    if not name or not phone or not province:
        ctx["message"] = "请填写所有必填项"
    elif not PHONE_RE.match(phone):
        ctx["message"] = "请输入正确的手机号码"
    else:
        try:
            db.upsert_customer(openid, name, phone, province, describe)
        except Exception:
            logger.exception("注册入库失败")
            ctx["message"] = "系统繁忙，请稍后再试"
            return templates.TemplateResponse("register.html", ctx)
        background_tasks.add_task(
            send_notification,
            "新用户注册 - 众肯会",
            f"有新用户注册众肯会\n\n姓名: {name}\n手机: {phone}\n地区: {province}\n"
            f"简介: {describe}\nOpenID: {openid}",
        )
        ctx["success"] = True
        ctx["message"] = "注册成功！我们会尽快与您联系。"
    return templates.TemplateResponse("register.html", ctx)


# ---- 达人推荐 ----


@app.get("/people", response_class=HTMLResponse)
def people_page(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "people.html",
        {"request": request, "openid": openid, "message": "", "success": False},
    )


@app.post("/people", response_class=HTMLResponse)
def people_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(""),
    phone: str = Form(""),
    describe: str = Form(""),
    openid: str = Cookie(default="", alias=OPENID_COOKIE),
):
    name, phone, describe = name.strip(), phone.strip(), describe.strip()
    ctx = {"request": request, "openid": openid, "success": False}

    if not name or not phone or not describe:
        ctx["message"] = "请填写所有必填项"
    elif not PHONE_RE.match(phone):
        ctx["message"] = "请输入正确的手机号码"
    else:
        try:
            db.insert_people(name, phone, describe, openid)
        except Exception:
            logger.exception("达人推荐入库失败")
            ctx["message"] = "系统繁忙，请稍后再试"
            return templates.TemplateResponse("people.html", ctx)
        background_tasks.add_task(
            send_notification,
            "新达人推荐 - 众肯会",
            f"有新的达人推荐\n\n达人姓名: {name}\n联系方式: {phone}\n"
            f"达人简介: {describe}\n推荐人OpenID: {openid}",
        )
        ctx["success"] = True
        ctx["message"] = "推荐成功！感谢您的推荐，我们会尽快审核。"
    return templates.TemplateResponse("people.html", ctx)


# ---- 项目信息 ----


@app.get("/project", response_class=HTMLResponse)
def project_page(request: Request):
    openid = _read_openid(request)
    if _need_oauth(request):
        return _oauth_redirect(request)
    return templates.TemplateResponse(
        "project.html",
        {"request": request, "openid": openid, "message": "", "success": False},
    )


@app.post("/project", response_class=HTMLResponse)
def project_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    projectname: str = Form(""),
    projectpeople: str = Form(""),
    projectphone: str = Form(""),
    projectdescribe: str = Form(""),
    openid: str = Cookie(default="", alias=OPENID_COOKIE),
):
    projectname, projectpeople = projectname.strip(), projectpeople.strip()
    projectphone, projectdescribe = projectphone.strip(), projectdescribe.strip()
    ctx = {"request": request, "openid": openid, "success": False}

    if not projectname or not projectpeople or not projectphone or not projectdescribe:
        ctx["message"] = "请填写所有必填项"
    elif not PHONE_RE.match(projectphone):
        ctx["message"] = "请输入正确的手机号码"
    else:
        try:
            db.insert_project(projectname, projectpeople, projectphone, projectdescribe, openid)
        except Exception:
            logger.exception("项目信息入库失败")
            ctx["message"] = "系统繁忙，请稍后再试"
            return templates.TemplateResponse("project.html", ctx)
        background_tasks.add_task(
            send_notification,
            "新项目信息 - 众肯会",
            f"有新的项目信息提交\n\n项目名称: {projectname}\n项目负责人: {projectpeople}\n"
            f"联系电话: {projectphone}\n项目描述: {projectdescribe}\n提交人OpenID: {openid}",
        )
        ctx["success"] = True
        ctx["message"] = "提交成功！我们会尽快与您联系。"
    return templates.TemplateResponse("project.html", ctx)


# ==================== JSON API（兼容原 save_*.php 接口形态） ====================


@app.post("/api/customer")
def api_customer(
    background_tasks: BackgroundTasks,
    openid: str = Form(""),
    customername: str = Form(""),
    phone: str = Form(""),
    province: str = Form(""),
    describe: str = Form(""),
):
    if not customername.strip() or not phone.strip():
        return JSONResponse({"success": False, "message": "姓名和手机号码为必填项"})
    try:
        new_id = db.upsert_customer(openid, customername.strip(), phone.strip(), province.strip(), describe.strip())
    except Exception:
        logger.exception("api_customer 失败")
        return JSONResponse({"success": False, "message": "系统繁忙"})
    background_tasks.add_task(
        send_notification, "新用户注册 - 众肯会",
        f"姓名: {customername}\n手机: {phone}\n地区: {province}\n简介: {describe}\nOpenID: {openid}",
    )
    return {"success": True, "message": "注册成功", "id": new_id}


@app.post("/api/people")
def api_people(
    background_tasks: BackgroundTasks,
    openid: str = Form(""),
    peoplename: str = Form(""),
    peoplephone: str = Form(""),
    peopledescribe: str = Form(""),
):
    if not peoplename.strip() or not peoplephone.strip():
        return JSONResponse({"success": False, "message": "达人姓名和联系方式为必填项"})
    try:
        new_id = db.insert_people(peoplename.strip(), peoplephone.strip(), peopledescribe.strip(), openid)
    except Exception:
        logger.exception("api_people 失败")
        return JSONResponse({"success": False, "message": "系统繁忙"})
    background_tasks.add_task(
        send_notification, "新达人推荐 - 众肯会",
        f"达人姓名: {peoplename}\n联系方式: {peoplephone}\n简介: {peopledescribe}\nOpenID: {openid}",
    )
    return {"success": True, "message": "达人推荐提交成功", "id": new_id}


@app.post("/api/project")
def api_project(
    background_tasks: BackgroundTasks,
    openid: str = Form(""),
    projectname: str = Form(""),
    projectpeople: str = Form(""),
    projectphone: str = Form(""),
    projectdescribe: str = Form(""),
):
    if not projectname.strip() or not projectpeople.strip() or not projectphone.strip():
        return JSONResponse({"success": False, "message": "项目名称、负责人和联系电话为必填项"})
    try:
        new_id = db.insert_project(
            projectname.strip(), projectpeople.strip(), projectphone.strip(), projectdescribe.strip(), openid
        )
    except Exception:
        logger.exception("api_project 失败")
        return JSONResponse({"success": False, "message": "系统繁忙"})
    background_tasks.add_task(
        send_notification, "新项目信息 - 众肯会",
        f"项目名称: {projectname}\n负责人: {projectpeople}\n电话: {projectphone}\n"
        f"描述: {projectdescribe}\nOpenID: {openid}",
    )
    return {"success": True, "message": "项目信息提交成功", "id": new_id}
