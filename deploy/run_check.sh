#!/bin/bash
# 在服务器上跑：python scripts/inspect_account.py（检查公众号类型）
cp /tmp/check_wx.py /opt/apps/zhongkenhui/deploy/check_wx.py
cd /opt/apps/zhongkenhui
sudo -u ubuntu ./venv/bin/python deploy/check_wx.py 2>&1
rm -f /tmp/check_wx.py