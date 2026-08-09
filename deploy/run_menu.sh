#!/bin/bash
# 跑 create_menu.py 创建微信菜单，并把原始返回写到 /tmp/menu_result.txt
set -e
cd /opt/apps/zhongkenhui

# 临时把 PUBLIC_BASE 改成 wx.zonken.com（菜单链接用服务号域）
export PUBLIC_BASE="http://wx.zonken.com"

# 需要在 .env 里也同步，因为脚本读 settings
sed -i 's|^PUBLIC_BASE=.*|PUBLIC_BASE=http://wx.zonken.com|' .env

echo "== 当前 .env 中的 PUBLIC_BASE =="
grep PUBLIC_BASE .env

echo "== 跑菜单创建 =="
sudo -u ubuntu ./venv/bin/python scripts/create_menu.py 2>&1 | tee /tmp/menu_result.txt