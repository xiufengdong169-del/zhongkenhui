#!/bin/bash
# 部署后端到端验证
set -e
DB_PASS='Zkh2026!DbLocal'

echo "== API 提交测试 =="
curl -s -X POST http://127.0.0.1:8100/api/customer \
  -d 'openid=deploy_test' -d 'customername=部署测试' -d 'phone=13800138000' \
  -d 'province=广东' -d 'describe=自动化部署验证'
echo ""
curl -s -X POST http://127.0.0.1:8100/api/people \
  -d 'openid=deploy_test' -d 'peoplename=测试达人' -d 'peoplephone=13900139000' -d 'peopledescribe=测试'
echo ""
curl -s -X POST http://127.0.0.1:8100/api/project \
  -d 'openid=deploy_test' -d 'projectname=测试项目' -d 'projectpeople=测试人' -d 'projectphone=13700137000' -d 'projectdescribe=测试'
echo ""

echo "== 微信回调签名验证 =="
TS=$(date +%s); NONCE=abc123
SIG=$(python3 -c "import hashlib;print(hashlib.sha1(''.join(sorted(['zonken2025','$TS','$NONCE'])).encode()).hexdigest())")
RESP=$(curl -s "http://127.0.0.1:8100/wx/callback?signature=$SIG&timestamp=$TS&nonce=$NONCE&echostr=verify_ok_9527")
echo "回调验证返回: $RESP"

echo "== 页面渲染 =="
for p in / /about /register /people /project /business /tech /surprise; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8100$p)
  echo "GET $p -> $CODE"
done

sleep 4
echo "== 数据库检查 =="
mysql -u zhongkenhui -p"$DB_PASS" zhongkenhui 2>/dev/null <<'SQL'
SELECT id, customername, phone, province FROM customer WHERE openid='deploy_test';
SELECT id, peoplename, customername FROM people_information WHERE customeropenid='deploy_test';
SELECT id, projectname, customername FROM project_information WHERE customeropenid='deploy_test';
SQL

echo "== 清理测试数据 =="
mysql -u zhongkenhui -p"$DB_PASS" zhongkenhui 2>/dev/null <<'SQL'
DELETE FROM customer WHERE openid='deploy_test';
DELETE FROM people_information WHERE customeropenid='deploy_test';
DELETE FROM project_information WHERE customeropenid='deploy_test';
SQL
echo "已清理"

echo "== 应用日志（最近10行）=="
tail -10 /var/log/zhongkenhui/app.log
rm -f /tmp/zhongkenhui_v2.tar.gz /tmp/remote_deploy.sh /tmp/remote_verify.sh
echo "== 验证完成 =="
