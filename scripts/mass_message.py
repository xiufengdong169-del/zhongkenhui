"""发送微信公众号群发消息（覆盖旧消息）"""
import os, sys, json, httpx
sys.path.insert(0, '/opt/apps/zhongkenhui')
from app.config import settings

# 图文消息内容
ARTICLE = {
    "articles": [
        {
            "title": "欢迎加入众肯会",
            "thumb_media_id": "",  # 如果有封面图，先上传获取media_id
            "author": "众肯会",
            "digest": "众肯会是广州市众肯信息科技有限公司发起成立的面向公司客户、合作伙伴及员工的合作分享交流共赢平台！",
            "show_cover_pic": 0,
            "content": """
<p>欢迎加入众肯会！</p>
<p>众肯会是广州市众肯信息科技有限公司发起成立的面向公司客户、合作伙伴及员工的合作分享交流共赢平台！</p>
<p>我们致力于为广大IT朋友提供：</p>
<ul>
<li>信息系统工程咨询与监理服务</li>
<li>技术合作与业务对接</li>
<li>行业资源分享</li>
</ul>
<p>如有合作意向，欢迎通过公众号菜单提交信息，我们会尽快与您联系。</p>
<p>—— 众肯会团队</p>
""",
            "content_source_url": "http://193.112.79.220/about",
        }
    ]
}

def get_access_token():
    url = (
        f"https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={settings.WX_APPID}&secret={settings.WX_APPSECRET}"
    )
    resp = httpx.get(url, timeout=10).json()
    token = resp.get("access_token")
    if not token:
        print(f"获取 access_token 失败: {resp}")
        sys.exit(1)
    return token

def upload_news(token):
    """上传图文消息素材"""
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadnews?access_token={token}"
    resp = httpx.post(url, json=ARTICLE, timeout=10).json()
    if resp.get("errcode") and resp.get("errcode") != 0:
        print(f"上传图文失败: {resp}")
        sys.exit(1)
    media_id = resp.get("media_id")
    print(f"图文素材上传成功: {media_id}")
    return media_id

def send_mass(token, media_id):
    """群发图文消息给所有人"""
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token={token}"
    data = {
        "filter": {
            "is_to_all": True,
        },
        "mpnews": {
            "media_id": media_id
        },
        "msgtype": "mpnews",
        "send_ignore_reprint": 0
    }
    resp = httpx.post(url, json=data, timeout=10).json()
    print(f"群发结果: {resp}")
    if resp.get("errcode") == 0:
        print("✅ 群发消息发送成功！")
        print(f"消息ID: {resp.get('msg_id')}")
    else:
        print(f"❌ 群发失败: {resp.get('errmsg')}")

def main():
    token = get_access_token()
    print("access_token 获取成功")
    
    # 上传图文素材
    media_id = upload_news(token)
    
    # 群发
    send_mass(token, media_id)

if __name__ == "__main__":
    main()
