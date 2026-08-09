# 众肯会服务号 v2

原 PHP 版（`zhongkenhui_v1.0`）的全新重写版本。技术栈与服务器上的数乘中台一致：
**Python FastAPI + Uvicorn + Supervisor + Nginx + 本地 MySQL 8.0（独立库 `zhongkenhui`）**。

- 服务号：众肯会（zhongkenhui），AppID `wxe8f700245a3d2af7`
- 服务器：腾讯云轻量 `193.112.79.220`（Ubuntu 24.04）
- 域名：`zonken.com`（需备案通过 + DNS A 记录指向服务器）
- 应用端口：本机 `127.0.0.1:8100`（Nginx 反代，与中台 8000 端口互不影响）

## 功能（对齐原版）

| 模块 | 说明 |
|---|---|
| 微信回调 `/wx/callback` | Token 验证；关注→欢迎语+邮件通知；取关→邮件通知；留言→自动回复+邮件通知；发"设置管理员"→绑定管理员 |
| H5 页面 | 首页 `/`、平台介绍 `/about`、加入众肯 `/register`、注册惊喜 `/surprise`、达人推荐 `/people`、项目信息 `/project`、业务合作 `/business`、技术合作 `/tech` |
| JSON API | `/api/customer`、`/api/people`、`/api/project`（兼容原 save_*.php 形态） |
| 数据库 | `customer` / `people_information` / `project_information` / `wx_admin` / `wx_message_log`，应用启动自动建表 |
| 邮件通知 | QQ 邮箱 SMTP SSL，后台任务发送不阻塞请求 |
| 菜单脚本 | `scripts/create_menu.py` 创建三组自定义菜单 |

相对原版的改进：SQL 全部参数化（原版有拼接注入风险）、密钥移出代码进 `.env`、
消息日志入库替代 txt 文件、管理员存库替代 txt 文件、邮件改为后台异步发送。

## 部署步骤（服务器上）

```bash
# 0) 上传代码
rsync -avz --exclude 'venv' --exclude '.env' --exclude '__pycache__' \
  ./zhongkenhui_v2/  ubuntu@193.112.79.220:/opt/apps/zhongkenhui/

# 1) 建库建账号（先编辑 init_db.sql 改密码）
sudo mysql < /opt/apps/zhongkenhui/deploy/init_db.sql

# 2) Python 环境
cd /opt/apps/zhongkenhui
python3 -m venv venv && source venv/bin/activate
pip install -U pip && pip install -r requirements.txt

# 3) 环境变量
cp env.example .env && nano .env    # 填 WX_APPSECRET / DB_PASSWORD / SMTP_PASS
chmod 600 .env

# 4) 日志目录 + Supervisor
sudo mkdir -p /var/log/zhongkenhui && sudo chown ubuntu:ubuntu /var/log/zhongkenhui
sudo cp deploy/supervisor-zhongkenhui.conf /etc/supervisor/conf.d/zhongkenhui.conf
sudo supervisorctl reread && sudo supervisorctl update && sudo supervisorctl status zhongkenhui

# 5) 自测
curl http://127.0.0.1:8100/health    # {"ok":true,"db":true,...}

# 6) Nginx
sudo cp deploy/nginx-zhongkenhui.conf /etc/nginx/sites-available/zhongkenhui.conf
sudo ln -sf /etc/nginx/sites-available/zhongkenhui.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 域名/备案就绪后

1. DNS：`zonken.com`、`www.zonken.com` A 记录 → `193.112.79.220`
2. HTTPS：`sudo certbot --nginx -d zonken.com -d www.zonken.com`
3. 微信公众平台 → 设置与开发 → 基本配置：
   - 服务器 URL：`http://zonken.com/wx/callback`（有证书后用 https）
   - Token：`zonken2025`，消息加解密：明文模式
   - ⚠️ 服务器 IP 需加入公众平台「IP 白名单」（调用菜单 API 用）
4. 创建菜单：`cd /opt/apps/zhongkenhui && source venv/bin/activate && python scripts/create_menu.py`
5. 管理员先关注公众号，发送「设置管理员」完成绑定

## 本地开发

```powershell
python -m venv venv; .\venv\Scripts\pip install -r requirements.txt
copy env.example .env   # 本地可设 MAIL_ENABLED=0
.\venv\Scripts\uvicorn app.main:app --reload --port 8100
```
