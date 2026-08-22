# SMTP 配置指南

## 什么是 SMTP 授权码？

授权码是邮箱提供的、用于第三方客户端登录 SMTP 服务的专用密码，**不是邮箱登录密码**。它权限受限（只能收发邮件）、可随时重置，泄露风险可控。

## 各邮箱配置速查表

| 邮箱 | SMTP 服务器 | 端口 | 加密 | 授权码获取路径 |
|------|------------|------|------|---------------|
| QQ 邮箱 | smtp.qq.com | 465 | SSL | 网页版设置 → 账号 → POP3/IMAP/SMTP → 开启服务 → 生成授权码 |
| 163 邮箱 | smtp.163.com | 465 | SSL | 网页版设置 → POP3/SMTP/IMAP → 开启 SMTP → 新增授权密码 |
| 126 邮箱 | smtp.126.com | 465 | SSL | 同 163 |
| Foxmail | smtp.qq.com | 465 | SSL | 同 QQ 邮箱（同一体系） |
| Gmail | smtp.gmail.com | 587 | STARTTLS | Google 账号 → 安全性 → 两步验证 → 应用专用密码 |
| Outlook/Hotmail | smtp-mail.outlook.com | 587 | STARTTLS | 账号安全 → 应用密码（需开启两步验证） |
| 新浪邮箱 | smtp.sina.com | 465 | SSL | 设置 → 客户端 POP/IMAP/SMTP → 开启 |
| 搜狐邮箱 | smtp.sohu.com | 465 | SSL | 设置 → 邮箱设置 → 客户端设置 |
| 阿里企业邮箱 | smtp.qiye.aliyun.com | 465 | SSL | 管理后台开启 SMTP 后使用登录密码 |
| 腾讯企业邮箱 | smtp.exmail.qq.com | 465 | SSL | 设置 → 客户端专用密码 |

> 配置了 `SMTP_USER` 后，`SMTP_HOST` / `SMTP_PORT` / `SMTP_SSL` 会按上表自动推断，无需手填。

## .env 最小配置示例（QQ 邮箱）

```ini
SMTP_USER=123456789@qq.com
SMTP_PASS=abcdefghigklmnop   # 16 位授权码
TO_EMAIL=123456789@qq.com
```

## 常见故障排查

| 现象 | 原因与解法 |
|------|-----------|
| `(535, b'Error: authentication failed')` | 授权码错误——重新生成；注意 QQ 邮箱用授权码不是 QQ 密码 |
| 连接超时 / `Connection unexpectedly closed` | ① 465 端口被网络拦截（公司内网常见）→ 改用 587；② 服务器地址写错 |
| `SMTPAuthenticationError` 但确认授权码正确 | 部分邮箱要求先在网页端开启 SMTP 服务；Gmail 需关闭"安全性较低的应用"拦截或用应用专用密码 |
| 登录成功但收不到邮件 | 检查垃圾箱；QQ 邮箱可能拦截 HTML 重邮件，加白名单 |
| Gmail 应用专用密码入口找不到 | 需先开启两步验证才会出现该入口 |
| 发送频率限制 | QQ 邮箱每日发信上限约 50-100 封（个人版），日报场景完全够用 |

## 安全建议

1. **`.env` 永远不入库**（仓库已配 `.gitignore`，请勿强制添加）
2. 怀疑泄露 → 立即到邮箱设置重置授权码（旧码立即作废）
3. 多人共用部署 → 为日报单独注册一个发件邮箱
4. 授权码不要出现在截图、日志、对话记录中
