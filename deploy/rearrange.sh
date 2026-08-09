#!/bin/bash
# 方案 A：把 zonken.com 让位给公司官网（/opt/apps/zonkenweb/）
# 服务号迁到 wx.zonken.com
set -e

echo "== 1. 建公司官网目录 + 占位首页 =="
sudo mkdir -p /opt/apps/zonkenweb
sudo chown ubuntu:ubuntu /opt/apps/zonkenweb
cat > /opt/apps/zonkenweb/index.html <<'HTML'
<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>广州市众肯信息科技有限公司</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>body{font-family:-apple-system,"PingFang SC",sans-serif;margin:0;padding:60px 20px;
background:linear-gradient(135deg,#6469ab 0%,#898dce 100%);color:#fff;text-align:center;min-height:100vh}
h1{font-size:32px;margin:0 0 12px;font-weight:300}.p{opacity:.85;font-size:15px;margin-top:40px}
.t{font-size:14px;padding:6px 14px;border:1px solid rgba(255,255,255,.4);border-radius:30px;display:inline-block;margin-bottom:20px}
</style></head><body>
<div class=t>网站搭建中</div>
<h1>广州市众肯信息科技有限公司</h1>
<p>Zhongken Information Technology Co., Ltd.</p>
<p class=p>zonken.com · zonkenweb</p>
</body></html>
HTML

echo "== 2. 写官网 Nginx 配置 =="
sudo tee /etc/nginx/sites-available/zonkenweb.conf >/dev/null <<'CONF'
server {
    listen 80;
    server_name zonken.com www.zonken.com;

    access_log /var/log/nginx/zonkenweb.access.log;
    error_log  /var/log/nginx/zonkenweb.error.log;

    root /opt/apps/zonkenweb;
    index index.html;

    # 静态资源
    location /static/ {
        alias /opt/apps/zonkenweb/static/;
        expires 7d;
    }

    # 官网首页/页面（占位阶段先全打到 index.html，后续接框架再说）
    location / {
        try_files $uri $uri/ /index.html;
    }
}
CONF

echo "== 3. 把服务号 Nginx 改成只认 wx.zonken.com =="
sudo sed -i 's|server_name zonken.com www.zonken.com;|server_name wx.zonken.com;|' \
  /etc/nginx/sites-available/zhongkenhui.conf

# 验证改对了
echo "  zhongkenhui.conf 现在的 server_name:"
grep server_name /etc/nginx/sites-available/zhongkenhui.conf

echo "== 4. 启用官网站点 + 验证 Nginx 配置 =="
sudo ln -sf /etc/nginx/sites-available/zonkenweb.conf /etc/nginx/sites-enabled/zonkenweb.conf
sudo nginx -t

echo "== 5. 重载 Nginx（不停服务号进程） =="
sudo systemctl reload nginx

echo "== 6. 本机验证三个 host =="
sleep 1
echo "--- 走 Host 头 wx.zonken.com 应命中 zhongkenhui ---"
curl -s -o /dev/null -w "wx.zonken.com -> %{http_code}\n" -H "Host: wx.zonken.com" http://127.0.0.1/
echo "--- 走 Host 头 zonken.com 应命中 zkh-website 占位页 ---"
curl -s -H "Host: zonken.com" http://127.0.0.1/ | grep -o "众肯信息科技有限公司"
echo "--- 走 Host 头 www.zonken.com 应命中 zkh-website 占位页 ---"
curl -s -H "Host: www.zonken.com" http://127.0.0.1/ | grep -o "众肯信息科技有限公司"

echo ""
echo "== 完成 =="
echo "下一步：在阿里云 DNS 加一条记录 wx.zonken.com -> 193.112.79.220（A 记录）"
echo "      然后把微信回调 URL 改成 http://wx.zonken.com/wx/callback"