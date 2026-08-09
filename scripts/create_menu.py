"""创建/更新微信服务号自定义菜单（对齐原 update_menu.php 的三组菜单）

用法（在服务器上）：
    cd /opt/apps/zhongkenhui && source venv/bin/activate
    python scripts/create_menu.py
"""
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

BASE = settings.PUBLIC_BASE.rstrip("/")

MENU = {
    "button": [
        {
            "name": "关于众肯",
            "sub_button": [
                {"type": "view", "name": "我们是谁", "url": f"{BASE}/about"},
                {"type": "view", "name": "加入我们", "url": f"{BASE}/register"},
                {"type": "view", "name": "会员权益", "url": f"{BASE}/surprise"},
                {"type": "click", "name": "联系客服", "key": "CONTACT_CS"},
            ],
        },
        {
            "name": "有偿信息",
            "sub_button": [
                {"type": "view", "name": "人才推荐", "url": f"{BASE}/people"},
                {"type": "view", "name": "项目机会", "url": f"{BASE}/project"},
            ],
        },
        {
            "name": "加盟合作",
            "sub_button": [
                {"type": "view", "name": "业务合作", "url": f"{BASE}/business"},
                {"type": "view", "name": "技术合作", "url": f"{BASE}/tech"},
            ],
        },
    ]
}


def main():
    if not settings.WX_APPSECRET:
        print("错误：.env 中未配置 WX_APPSECRET")
        sys.exit(1)

    token_url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={settings.WX_APPID}&secret={settings.WX_APPSECRET}"
    )
    resp = httpx.get(token_url, timeout=10).json()
    token = resp.get("access_token")
    if not token:
        print("获取 access_token 失败:", resp)
        sys.exit(1)
    print("access_token 获取成功")

    create_url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={token}"
    body = json.dumps(MENU, ensure_ascii=False).encode("utf-8")
    result = httpx.post(
        create_url, content=body, headers={"Content-Type": "application/json"}, timeout=10
    ).json()
    print("API 返回:", result)
    if result.get("errcode") == 0:
        print("✅ 菜单创建成功！取消关注后重新关注，或等待 24 小时菜单自动更新。")
    else:
        print("❌ 菜单创建失败:", result.get("errmsg"))
        sys.exit(1)


if __name__ == "__main__":
    main()
