"""用 AppID 查微信服务号基本信息（确认账号类型/原始ID/认证状态）"""
import os, sys, json
sys.path.insert(0, '/opt/apps/zhongkenhui')
from app.config import settings
import httpx

# 取 access_token
token_url = (
    f"https://api.weixin.qq.com/cgi-bin/token"
    f"?grant_type=client_credential&appid={settings.WX_APPID}&secret={settings.WX_APPSECRET}"
)
tok = httpx.get(token_url, timeout=10).json()
access_token = tok.get("access_token")
if not access_token:
    print("取 access_token 失败:", tok); sys.exit(1)

# 拉取账号基本信息
info = httpx.get(
    f"https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo?access_token={access_token}",
    timeout=10
).json()
print("账号基本信息：")
print(json.dumps(info, ensure_ascii=False, indent=2))