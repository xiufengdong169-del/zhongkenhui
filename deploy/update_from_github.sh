#!/bin/bash
# 众肯会服务号 v2 - 从 GitHub 更新代码并重启
# 在服务器上执行: bash update_from_github.sh
set -e

APP_DIR=/opt/apps/zhongkenhui
REPO_URL=https://github.com/xiufengdong169-del/zhongkenhui.git

echo "== 1. 备份 .env =="
cp $APP_DIR/.env /tmp/zhongkenhui.env.bak
echo ".env 已备份到 /tmp/zhongkenhui.env.bak"

echo "== 2. 检查是否有 git 仓库 =="
if [ -d $APP_DIR/.git ]; then
    echo "已有 git 仓库，拉取最新代码..."
    cd $APP_DIR
    git fetch origin
    git reset --hard origin/main
else
    echo "没有 git 仓库，重新克隆..."
    cd /tmp
    git clone $REPO_URL zhongkenhui_new
    # 保留 .env 和 venv
    cp $APP_DIR/.env zhongkenhui_new/.env
    cp -r $APP_DIR/venv zhongkenhui_new/venv
    # 替换目录
    sudo mv $APP_DIR /opt/apps/zhongkenhui_old_$(date +%Y%m%d%H%M%S)
    sudo mv zhongkenhui_new $APP_DIR
    sudo chown -R ubuntu:ubuntu $APP_DIR
    cd $APP_DIR
fi

echo "== 3. 恢复 .env =="
cp /tmp/zhongkenhui.env.bak $APP_DIR/.env
chmod 600 $APP_DIR/.env
echo ".env 已恢复"

echo "== 4. 安装依赖 =="
cd $APP_DIR
if [ ! -d venv ]; then python3 -m venv venv; fi
./venv/bin/pip install -q -r requirements.txt
echo "依赖安装完成"

echo "== 5. 重启服务 =="
sudo supervisorctl restart zhongkenhui
sleep 3
sudo supervisorctl status zhongkenhui

echo "== 6. 健康检查 =="
curl -s http://127.0.0.1:8100/health
echo ""

echo "== 7. 重建微信菜单 =="
cd $APP_DIR
./venv/bin/python scripts/create_menu.py
echo ""

echo "== 更新完成 =="
echo "请验证: http://wx.zk550.cn/health"
