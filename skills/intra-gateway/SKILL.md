---
name: intra-gateway
description: Use when accessing internal network resources through the intra-gateway MCP server — executing commands on Linux servers, reading/searching logs, querying Oracle databases, or managing Windows services. Trigger when the user asks to check inner network logs, query Oracle tables, restart inner network services, or debug inner network applications.
---

# Intra-Gateway

内网 MCP 网关 Skill。通过 `intra-gateway` MCP Server 操控内网资源。

**代码仓库：** `../intra-gateway/`（MCP Server 代码，部署到跳板机）
**本文件：** 教 AI 如何使用该 MCP Server（部署到本地 Claude Code）

## 触发条件

- 查看内网服务日志
- 查询内网 Oracle 数据库表
- 重启/操作内网 Linux/Windows 服务
- 根据外网代码排查内网服务 bug
- 调用内网 HTTP 接口（GET/POST/PUT/DELETE）
- 上传部署包到内网
- 升级跳板机 MCP Server

## 可用 MCP Tools

| Tool | 用途 | 关键参数 |
|------|------|----------|
| `exec_ssh` | 在 Linux 服务器执行命令 | `server_name`, `command` |
| `read_log` | 读取日志文件（tail/head） | `server_name`, `file_path`, `lines`, `head` |
| `grep_log` | 搜索日志（关键词+时间范围） | `server_name`, `keyword`, `time_from`, `time_to` |
| `query_oracle` | 只读 SQL 查询 | `db_name`, `sql`（仅 SELECT） |
| `list_logs` | 查找日志文件位置 | `server_name`, `service_name` |
| `send_http` | 内网 HTTP 请求 | `url`, `method`, `headers`, `body` |
| `self_upgrade` | 自助升级（替换代码+重启） | `package_path`, `deploy_dir`, `port` |

## 配置

MCP Server 连接信息在 `~/.claude/settings.json` 的 `mcpServers` 中：

```json
{
  "mcpServers": {
    "intra-gateway": {
      "url": "http://<跳板机IP>:8765/mcp",
      "headers": {
        "X-API-Key": "<your-api-key>"
      }
    }
  }
}
```

## 使用规范

1. **查 Oracle**：只允许 SELECT，不要尝试 INSERT/UPDATE/DELETE
2. **查日志**：先用 `list_logs` 确认路径，再用 `read_log` 或 `grep_log`
3. **执行命令**：危险操作（重启、删除）前先确认
4. **超时**：SQL 查询 60s，SSH 命令 30s，日志搜索 45s

## 排 Bug 流程

1. 本地读取代码上下文
2. 通过 `grep_log` 搜索内网日志错误关键词
3. 通过 `query_oracle` 查询相关数据状态
4. 综合分析代码 + 日志 + 数据，定位根因

## 目标服务器列表

在 `config.json` 的 `targets` 中定义，通过 `list_logs` 或 `exec_ssh` 的 `server_name` 参数引用。

## 升级 MCP Server 流程

1. 在外网将新版本代码打包为 `src.tar.gz`（包含 `src/` 和 `pyproject.toml`）
2. 通过 `exec_ssh` 或 `send_http` 上传到跳板机临时目录
3. 调用 `self_upgrade` 触发升级（替换代码 → 备份旧版 → 重启）
4. 等待 3 秒后验证：`send_http` 调 `http://跳板机:8765/mcp` 确认服务恢复
