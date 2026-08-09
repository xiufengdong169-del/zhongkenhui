#!/bin/bash
echo "===== 应用目录 /opt/apps/zhongkenhui ====="
cd /opt/apps/zhongkenhui 2>/dev/null || { echo "目录不存在!"; exit 1; }
find . -not -path '*/__pycache__/*' -not -name '*.pyc' | sort | sed 's|[^/]*/|  |g'
echo ""
echo "===== 关键文件确认 ====="
ls -la .env 2>/dev/null && echo ".env 权限: $(stat -c '%a' .env)"
echo "venv: $([ -d venv ] && echo 存在 || echo 缺失)"
echo ""
echo "===== 进程 / 日志 / 配置位置 ====="
echo "Supervisor 配置: /etc/supervisor/conf.d/zhongkenhui.conf"
echo "Nginx 站点: /etc/nginx/sites-enabled/zhongkenhui.conf"
echo "应用日志: /var/log/zhongkenhui/app.log"
echo "Uvicorn 日志: /var/log/zhongkenhui/uvicorn.out.log / uvicorn.err.log"
echo ""
echo "===== 运行状态 ====="
sudo supervisorctl status zhongkenhui 2>/dev/null
ps aux | grep -c '[u]vicorn app.main'
