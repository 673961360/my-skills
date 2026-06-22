"""API 客户端模块 — 封装 AI Gateway 的 HTTP 请求。

所有请求通过 Authorization: Bearer {api_key} 认证，
网关自动注入 userId 和 sysToken，调用方无需手动传递。
"""

import time
from typing import Any

import requests

from config_loader import load_config

# 模块级配置缓存
_config: dict | None = None


def get_config() -> dict:
    """获取配置（带缓存，按 DTR_ENV 合并环境差异）。"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def _build_headers(content_type: str = "application/json") -> dict[str, str]:
    """构建请求头。"""
    cfg = get_config()
    return {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": content_type,
    }


def call_sql_api(api_id: str, params: dict[str, Any] | None = None) -> dict:
    """调用 SQL 查询接口。

    URL 模式: POST {base_url}/admin/dataquery/execute/{api_id}
    Body: JSON

    Args:
        api_id: 接口 ID，如 "cat_sql_trade_0019"
        params: 请求参数 dict，无参数传 {} 或 None

    Returns:
        API 响应的 JSON dict
    """
    cfg = get_config()
    url = f"{cfg['api_base_url']}/admin/dataquery/execute/{api_id}"
    body = params or {}
    max_retries = cfg.get("api_max_retries", 3)
    timeout = cfg.get("api_timeout", 60)

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                url,
                json=body,
                headers=_build_headers(),
                timeout=timeout,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                raise RuntimeError(
                    f"API {api_id} 返回错误: code={result.get('code')}, "
                    f"message={result.get('message')}"
                )
            return result
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(1 * attempt)  # 递增退避
                continue
            raise RuntimeError(f"API {api_id} 请求失败（重试 {max_retries} 次后）: {e}") from e

    # 理论上不会到这里
    raise RuntimeError(f"API {api_id} 未知错误")


def call_api(
    api_id: str,
    params: dict[str, Any] | None = None,
    content_type: str = "application/json",
) -> dict:
    """调用 API 接口（非 SQL）。

    URL 模式: POST {base_url}/admin/apiquery/proxy/{api_id}
    Body: JSON 或 form-urlencoded（由 content_type 决定）

    Args:
        api_id: 接口 ID，如 "cat_api_trade_0002"
        params: 请求参数 dict
        content_type: "application/json" 或 "application/x-www-form-urlencoded"

    Returns:
        API 响应的 JSON dict
    """
    cfg = get_config()
    url = f"{cfg['api_base_url']}/admin/apiquery/proxy/{api_id}"
    max_retries = cfg.get("api_max_retries", 3)
    timeout = cfg.get("api_timeout", 60)

    for attempt in range(1, max_retries + 1):
        try:
            if content_type == "application/x-www-form-urlencoded":
                resp = requests.post(
                    url,
                    data=params or {},
                    headers=_build_headers(content_type),
                    timeout=timeout,
                )
            else:
                resp = requests.post(
                    url,
                    json=params or {},
                    headers=_build_headers(content_type),
                    timeout=timeout,
                )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(1 * attempt)
                continue
            raise RuntimeError(f"API {api_id} 请求失败（重试 {max_retries} 次后）: {e}") from e

    raise RuntimeError(f"API {api_id} 未知错误")


def call_form_api(api_id: str, params: dict[str, Any] | None = None) -> dict:
    """调用 Form Body 类型的 API 接口（便捷方法）。"""
    return call_api(api_id, params, content_type="application/x-www-form-urlencoded")
