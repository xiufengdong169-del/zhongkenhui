#!/bin/bash
# 众肯会服务号 v2 - 服务器端一键部署脚本
set -e

APP_DIR=/opt/apps/zhongkenhui
DB_PASS='Zkh2026!DbLocal'

echo "== 1. 解压代码 =="
sudo mkdir -p $APP_DIR
sudo chown ubuntu:ubuntu $APP_DIR
tar -xzf /tmp/zhongkenhui_v2.tar.gz -C $APP_DIR
echo "代码就位: $(ls $APP_DIR | tr '\n' ' ')"

echo "== 2. 建独立数据库 =="
sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS zhongkenhui DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'zhongkenhui'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON zhongkenhui.* TO 'zhongkenhui'@'localhost';
FLUSH PRIVILEGES;
SQL
echo "数据库 zhongkenhui 就绪"

echo "== 3. Python 环境 =="
cd $APP_DIR
if [ ! -d venv ]; then python3 -m venv venv; fi
./venv/bin/pip install -q -U pip
./venv/bin/pip install -q -r requirements.txt
echo "依赖安装完成"

echo "== 4. 写 .env =="
cat > $APP_DIR/.env <<ENV
WX_TOKEN=zonken2025
WX_APPID=wxe8f700245a3d2af7
WX_APPSECRET=cac86329df391b7c6d5f55b1f5cb91bd

DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=zhongkenhui
DB_PASSWORD=$DB_PASS
DB_NAME=zhongkenhui

MAIL_ENABLED=1
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=32542256@qq.com
SMTP_PASS=iymhgmzhkkambica
ADMIN_EMAIL=32542256@qq.com

PUBLIC_BASE=http://wx.zk550.cn
LOG_FILE=/var/log/zhongkenhui/app.log
ENV
chmod 600 $APP_DIR/.env
echo ".env 已写入"

echo "== 5. 日志目录 + Supervisor =="
sudo mkdir -p /var/log/zhongkenhui
sudo chown ubuntu:ubuntu /var/log/zhongkenhui
sudo cp $APP_DIR/deploy/supervisor-zhongkenhui.conf /etc/supervisor/conf.d/zhongkenhui.conf
sudo supervisorctl reread
sudo supervisorctl update
sleep 3
sudo supervisorctl restart zhongkenhui || sudo supervisorctl start zhongkenhui
sleep 3
sudo supervisorctl status zhongkenhui

echo "== 6. Nginx 站点 =="
sudo cp $APP_DIR/deploy/nginx-zhongkenhui.conf /etc/nginx/sites-available/zhongkenhui.conf
sudo ln -sf /etc/nginx/sites-available/zhongkenhui.conf /etc/nginx/sites-enabled/zhongkenhui.conf
sudo nginx -t
sudo systemctl reload nginx

echo "== 7. 自检 =="
sleep 2
curl -s http://127.0.0.1:8100/health
echo ""
mysql -u zhongkenhui -p"$DB_PASS" zhongkenhui -e "SHOW TABLES;"
echo "== 部署完成 =="
