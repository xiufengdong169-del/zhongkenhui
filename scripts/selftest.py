"""本地自测：页面渲染 / 微信签名验证 / 回调消息处理（不依赖数据库与邮件）"""
import hashlib
import os
import sys
import time
from pathlib import Path

os.environ["MAIL_ENABLED"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name} {extra}")


print("== 页面渲染 ==")
for path, keyword in [
    ("/", "众肯会"),
    ("/about", "平台介绍"),
    ("/register", "提交注册"),
    ("/surprise", "会员权益"),
    ("/people", "提交推荐"),
    ("/project", "提交项目"),
    ("/business", "万人操弓"),
    ("/tech", "技术合作"),
]:
    r = client.get(path, params={"openid": "test_openid_123"})
    check(f"GET {path}", r.status_code == 200 and keyword in r.text, f"status={r.status_code}")

print("== 表单校验（不写库路径）==")
r = client.post("/register", data={"name": "张三", "phone": "123", "province": "广东"})
check("注册-手机号格式校验", "请输入正确的手机号码" in r.text)
r = client.post("/people", data={"name": "", "phone": "", "describe": ""})
check("达人-必填校验", "请填写所有必填项" in r.text)
r = client.post("/project", data={"projectname": "", "projectpeople": "", "projectphone": "", "projectdescribe": ""})
check("项目-必填校验", "请填写所有必填项" in r.text)

print("== 微信 Token 验证 ==")
token = "zonken2025"
ts, nonce = str(int(time.time())), "abc123"
sig = hashlib.sha1("".join(sorted([token, ts, nonce])).encode()).hexdigest()
r = client.get("/wx/callback", params={"signature": sig, "timestamp": ts, "nonce": nonce, "echostr": "hello_wx"})
check("正确签名返回 echostr", r.text == "hello_wx")
r = client.get("/wx/callback", params={"signature": "bad", "timestamp": ts, "nonce": nonce, "echostr": "hello_wx"})
check("错误签名返回 error", r.text == "error")

print("== 微信消息回调 ==")
sub_xml = (
    "<xml><ToUserName><![CDATA[gh_test]]></ToUserName>"
    "<FromUserName><![CDATA[oUserTest]]></FromUserName>"
    "<CreateTime>123</CreateTime><MsgType><![CDATA[event]]></MsgType>"
    "<Event><![CDATA[subscribe]]></Event></xml>"
)
r = client.post("/wx/callback", content=sub_xml)
check("关注事件回复欢迎语", "欢迎加入众肯会" in r.text and "oUserTest" in r.text)

txt_xml = (
    "<xml><ToUserName><![CDATA[gh_test]]></ToUserName>"
    "<FromUserName><![CDATA[oUserTest]]></FromUserName>"
    "<CreateTime>123</CreateTime><MsgType><![CDATA[text]]></MsgType>"
    "<Content><![CDATA[你好]]></Content><MsgId>1</MsgId></xml>"
)
r = client.post("/wx/callback", content=txt_xml)
check("文本消息自动回复", "收到您的留言" in r.text)

r = client.get("/health")
check("health 返回 ok", r.status_code == 200 and r.json().get("ok") is True)

print(f"\n结果: {ok} 通过, {fail} 失败")
sys.exit(1 if fail else 0)
