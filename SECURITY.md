# Security Policy

## Sensitive data

本项目会调用第三方数据源。API 密钥只能放在本地 `.env` 或 CI Secret 中，禁止写入源码、报告或测试夹具。

如果发现泄露的凭据或安全问题，请通过 GitHub Security Advisory 私下报告，不要创建公开 Issue。已经提交过的密钥应立即在服务商后台吊销并重新生成；仅删除 Git 历史中的文本并不能使密钥失效。

