-- 众肯会服务号 v2：独立数据库与账号（MySQL 8.0）
-- 用 root 执行：sudo mysql < init_db.sql
-- ⚠️ 执行前把下面的密码改成实际密码（与 .env 的 DB_PASSWORD 一致）

CREATE DATABASE IF NOT EXISTS zhongkenhui
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'zhongkenhui'@'localhost' IDENTIFIED BY 'CHANGE_ME_PASSWORD';
GRANT ALL PRIVILEGES ON zhongkenhui.* TO 'zhongkenhui'@'localhost';
FLUSH PRIVILEGES;

-- 数据表由应用启动时自动创建（app/db.py init_tables）
