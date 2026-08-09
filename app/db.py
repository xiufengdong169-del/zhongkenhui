"""众肯会服务号 v2 - 数据库访问层（PyMySQL，独立库 zhongkenhui）"""
import logging
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from .config import settings

logger = logging.getLogger("zhongkenhui")


def _connect():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=5,
    )


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


# ---------- 初始化建表 ----------
DDL = [
    """
    CREATE TABLE IF NOT EXISTS customer (
        id INT AUTO_INCREMENT PRIMARY KEY,
        openid VARCHAR(100) NOT NULL DEFAULT '',
        customername VARCHAR(100) NOT NULL DEFAULT '',
        phone VARCHAR(20) NOT NULL DEFAULT '',
        province VARCHAR(50) NOT NULL DEFAULT '',
        intro TEXT,
        submittime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_openid (openid),
        KEY idx_phone (phone)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS people_information (
        id INT AUTO_INCREMENT PRIMARY KEY,
        peoplename VARCHAR(100) NOT NULL DEFAULT '',
        peoplephone VARCHAR(20) NOT NULL DEFAULT '',
        peopledescribe TEXT,
        customername VARCHAR(100) NOT NULL DEFAULT '',
        customerid INT NOT NULL DEFAULT 0,
        customeropenid VARCHAR(100) NOT NULL DEFAULT '',
        submittime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_customerid (customerid),
        KEY idx_customeropenid (customeropenid)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS project_information (
        id INT AUTO_INCREMENT PRIMARY KEY,
        projectname VARCHAR(200) NOT NULL DEFAULT '',
        projectpeople VARCHAR(100) NOT NULL DEFAULT '',
        projectphone VARCHAR(20) NOT NULL DEFAULT '',
        projectdescribe TEXT,
        customername VARCHAR(100) NOT NULL DEFAULT '',
        customerid INT NOT NULL DEFAULT 0,
        customeropenid VARCHAR(100) NOT NULL DEFAULT '',
        submittime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_customerid (customerid),
        KEY idx_customeropenid (customeropenid)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS wx_admin (
        id INT AUTO_INCREMENT PRIMARY KEY,
        openid VARCHAR(100) NOT NULL UNIQUE,
        settime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS wx_message_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        openid VARCHAR(100) NOT NULL DEFAULT '',
        msgtype VARCHAR(30) NOT NULL DEFAULT '',
        event VARCHAR(30) NOT NULL DEFAULT '',
        content TEXT,
        createtime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_openid (openid),
        KEY idx_createtime (createtime)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_profile (
        openid VARCHAR(100) NOT NULL PRIMARY KEY,
        nickname VARCHAR(100) NOT NULL DEFAULT '',
        headimgurl VARCHAR(500) NOT NULL DEFAULT '',
        sex TINYINT NOT NULL DEFAULT 0,
        province VARCHAR(50) NOT NULL DEFAULT '',
        city VARCHAR(50) NOT NULL DEFAULT '',
        country VARCHAR(50) NOT NULL DEFAULT '',
        subscribe TINYINT NOT NULL DEFAULT 0,
        subscribe_time INT NOT NULL DEFAULT 0,
        updatetime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def init_tables():
    with get_db() as conn, conn.cursor() as cur:
        for ddl in DDL:
            cur.execute(ddl)
    logger.info("数据库表初始化完成")


# ---------- customer ----------
def get_customer_by_openid(openid: str):
    if not openid:
        return None
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, customername FROM customer WHERE openid=%s LIMIT 1", (openid,)
        )
        return cur.fetchone()


def upsert_customer(openid: str, name: str, phone: str, province: str, intro: str) -> int:
    with get_db() as conn, conn.cursor() as cur:
        row = None
        if openid:
            cur.execute("SELECT id FROM customer WHERE openid=%s LIMIT 1", (openid,))
            row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE customer SET customername=%s, phone=%s, province=%s, intro=%s, submittime=NOW() WHERE id=%s",
                (name, phone, province, intro, row["id"]),
            )
            return row["id"]
        cur.execute(
            "INSERT INTO customer (openid, customername, phone, province, intro, submittime) "
            "VALUES (%s,%s,%s,%s,%s,NOW())",
            (openid, name, phone, province, intro),
        )
        return cur.lastrowid


# ---------- people ----------
def insert_people(name: str, phone: str, describe: str, openid: str) -> int:
    cust = get_customer_by_openid(openid) or {}
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO people_information "
            "(peoplename, peoplephone, peopledescribe, customername, customerid, customeropenid, submittime) "
            "VALUES (%s,%s,%s,%s,%s,%s,NOW())",
            (name, phone, describe, cust.get("customername", ""), cust.get("id", 0), openid),
        )
        return cur.lastrowid


# ---------- project ----------
def insert_project(projectname: str, people: str, phone: str, describe: str, openid: str) -> int:
    cust = get_customer_by_openid(openid) or {}
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO project_information "
            "(projectname, projectpeople, projectphone, projectdescribe, customername, customerid, customeropenid, submittime) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())",
            (projectname, people, phone, describe, cust.get("customername", ""), cust.get("id", 0), openid),
        )
        return cur.lastrowid


# ---------- 微信管理员 ----------
def set_admin(openid: str):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO wx_admin (openid, settime) VALUES (%s, NOW()) "
            "ON DUPLICATE KEY UPDATE settime=NOW()",
            (openid,),
        )


# ---------- 消息日志 ----------
def log_message(openid: str, msgtype: str, event: str, content: str):
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO wx_message_log (openid, msgtype, event, content) VALUES (%s,%s,%s,%s)",
                (openid, msgtype, event, content[:60000] if content else ""),
            )
    except Exception:
        logger.exception("消息日志写入失败")


# ---------- 用户画像（OAuth / 关注事件自动保存） ----------
def save_user_profile(openid: str, nickname: str, headimgurl: str,
                      sex: int = 0, province: str = "", city: str = "",
                      country: str = "", subscribe: int = 0, subscribe_time: int = 0):
    """保存或更新用户画像"""
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_profile (openid, nickname, headimgurl, sex, province, city, country, subscribe, subscribe_time) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE "
                "nickname=IF(VALUES(nickname)!='',VALUES(nickname),nickname), "
                "headimgurl=IF(VALUES(headimgurl)!='',VALUES(headimgurl),headimgurl), "
                "sex=IF(VALUES(sex)!=0,VALUES(sex),sex), "
                "province=IF(VALUES(province)!='',VALUES(province),province), "
                "city=IF(VALUES(city)!='',VALUES(city),city), "
                "country=IF(VALUES(country)!='',VALUES(country),country), "
                "subscribe=VALUES(subscribe), "
                "subscribe_time=VALUES(subscribe_time)",
                (openid, nickname, headimgurl, sex, province, city, country, subscribe, subscribe_time),
            )
    except Exception:
        logger.exception("用户画像保存失败")


def get_user_profile(openid: str) -> dict:
    """查询用户画像（如昵称、头像等）"""
    if not openid:
        return {}
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT nickname, headimgurl, sex, province, city, country, subscribe, subscribe_time "
                "FROM user_profile WHERE openid=%s LIMIT 1",
                (openid,),
            )
            row = cur.fetchone()
            return row or {}
    except Exception:
        logger.exception("用户画像查询失败")
        return {}
