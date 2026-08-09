"""创建微信菜单 - 使用IP地址绕过备案检查"""
import os, sys, json, httpx
sys.path.insert(0, '/opt/apps/zhongkenhui')
from app.config import settings

BASE = "http://193.112.79.220:8100"

MENU = {
    "button": [
        {
            "name": "关于众肯",
            "sub_button": [
                {"type": "view", "name": "平台介绍", "url": f"{BASE}/about"},
                {"type": "view", "name": "加入众肯", "url": f"{BASE}/surprise"},
                {"type": "view", "name": "注册惊喜", "url": f"{BASE}/register"},
            ]
        },
        {
            "name": "有偿信息",
            "sub_button": [
                {"type": "view", "name": "达人推荐", "url": f"{BASE}/people"},
                {"type": "view", "name": "项目信息", "url": f"{BASE}/project"},
            ]
        },
        {
            "name": "加盟合作",
            "sub_button": [
                {"type": "view", "name": "业务合作", "url": f"{BASE}/business"},
                {"type": "view", "name": "技术合作", "url": f"{BASE}/tech"},
            ]
        },
    ]
}

def main():
    token_url = (
        f"https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={settings.WX_APPID}&secret={settings.WX_APPSECRET}"
    )
    tok = httpx.get(token_url, timeout=10).json()
    access_token = tok.get("access_token")
    if not access_token:
        print("获取 access_token 失败:", tok)
        sys.exit(1)
    print("access_token 获取成功")

    del_resp = httpx.get(
        f"https://api.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}",
        timeout=10
    ).json()
    print(f"删除旧菜单: {del_resp}")

    resp = httpx.post(
        f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}",
        json=MENU,
        timeout=10
    ).json()
    print(f"API 返回: {resp}")
    if resp.get("errcode") == 0:
        print("✅ 菜单创建成功（IP模式）！")
    else:
        print("❌ 菜单创建失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
