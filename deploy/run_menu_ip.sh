#!/bin/bash
# 跑 create_menu_ip.py 创建微信菜单（IP模式，绕过备案）
set -e
cd /opt/apps/zhongkenhui

echo "== 跑菜单创建（IP模式）=="
sudo -u ubuntu ./venv/bin/python scripts/create_menu_ip.py 2>&1

echo ""
echo "== 验证服务状态 =="
curl -s "http://127.0.0.1:8100/health"
echo ""
