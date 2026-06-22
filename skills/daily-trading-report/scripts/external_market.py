"""Best-effort external market indicators used by the forecast section."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

CHINAMONEY_BASE = "https://www.chinamoney.com.cn"
USER_AGENT = "Mozilla/5.0"


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Referer": f"{CHINAMONEY_BASE}/chinese/bkcurvclosedy/",
    })
    return session


def _safe_get_json(url: str, timeout: int = 8) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.json()


def collect_chinamoney_repo_rates(timeout: int = 8) -> dict[str, Any]:
    """Fetch pledged repo rates from ChinaMoney static JSON."""
    source = f"{CHINAMONEY_BASE}/r/cms/www/chinamoney/data/currency/prr-md.json"
    try:
        payload = _safe_get_json(source, timeout=timeout)
        records = payload.get("records", [])
        selected = []
        for row in records:
            product = str(row.get("productCode", "")).strip()
            if product not in {"DR001", "DR007", "DR014", "R001", "R007", "R014"}:
                continue
            selected.append({
                "SECURITY_NAME": product,
                "LAST_PRICE": row.get("latestRate", ""),
                "LATEST_PRICE": row.get("latestRate", ""),
                "WEIGHTED_RATE": row.get("weightedRate", ""),
                "HIGH_PRICE": "",
                "LOW_PRICE": "",
                "VOLUME": "",
                "SOURCE": "中国货币网货币市场行情",
                "AS_OF": payload.get("data", {}).get("showDateCN", ""),
            })
        return {
            "available": bool(selected),
            "source": "中国货币网货币市场行情",
            "url": source,
            "as_of": payload.get("data", {}).get("showDateCN", ""),
            "repo_rates": selected,
            "error": "" if selected else "未解析到目标回购品种",
        }
    except Exception as exc:
        return {
            "available": False,
            "source": "中国货币网货币市场行情",
            "url": source,
            "as_of": "",
            "repo_rates": [],
            "error": str(exc),
        }


def _curve_points_from_xml(xml_text: str, terms: set[str]) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    xid_to_term = {
        value.attrib.get("xid", ""): (value.text or "").strip()
        for value in root.findall("./xaxis/value")
    }
    graph = root.find("./graphs/graph")
    if graph is None:
        return []

    points = []
    for value in graph.findall("./value"):
        term = xid_to_term.get(value.attrib.get("xid", ""))
        if term not in terms:
            continue
        yield_value = (value.text or "").strip()
        if yield_value:
            points.append({"term": term, "yield": yield_value})
    return points


def collect_chinamoney_treasury_curve(timeout: int = 12) -> dict[str, Any]:
    """Fetch selected treasury yield curve points from ChinaMoney."""
    source_page = f"{CHINAMONEY_BASE}/chinese/bkcurvclosedy/"
    base = f"{CHINAMONEY_BASE}/ags/ms/"
    terms = {"0.5", "1", "3", "5", "7", "10", "30"}
    try:
        session = _session()
        init = session.post(
            base + "cm-u-bk-currency/ClsYldCurvCurvData",
            timeout=timeout,
        ).json()
        options = session.post(
            base + "cm-u-bk-currency/ClsYldCurvCurvGO",
            timeout=timeout,
        ).json()
        interest_date = init.get("data", {}).get("interestRateDateCN", "")
        bond_type = options.get("data", {}).get("selectedBondType", "CYCC000")
        response = session.post(
            base + "cm-u-bk-currency/ClsYldCurvXml",
            params={
                "lang": "CN",
                "bondType": bond_type,
                "interestRateDate": interest_date,
                "maturityYield": "1",
                "currentYield": "",
                "futureYield": "",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        points = _curve_points_from_xml(payload.get("data", {}).get("dataXml", ""), terms)
        return {
            "available": bool(points),
            "source": "中国货币网债券收盘收益率曲线",
            "url": source_page,
            "as_of": interest_date,
            "curve_name": "国债",
            "points": points,
            "error": "" if points else "未解析到国债曲线关键期限",
        }
    except Exception as exc:
        return {
            "available": False,
            "source": "中国货币网债券收盘收益率曲线",
            "url": source_page,
            "as_of": "",
            "curve_name": "国债",
            "points": [],
            "error": str(exc),
        }


# ── 权益指数：新浪财经 + 腾讯财经双源 ──────────────────────────
_SINA_INDEXES: dict[str, str] = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
}
_SINA_BASE = "https://hq.sinajs.cn/list="
_TENCENT_BASE = "https://qt.gtimg.cn/q="
_SINA_REFERER = "https://finance.sina.com.cn"


def _parse_sina_line(line: str) -> dict | None:
    """Parse one Sina JS var line into {name, latest, pct_change}."""
    parts = line.split('"')
    if len(parts) < 2:
        return None
    fields = parts[1].split(",")
    if len(fields) < 10:
        return None
    try:
        name = fields[0].strip()
        prev_close = float(fields[2])
        latest = float(fields[3])
        pct_change = round((latest - prev_close) / prev_close * 100, 2) if prev_close else 0.0
        return {"name": name, "latest": str(latest), "pct_change": str(pct_change), "source": "新浪财经"}
    except (ValueError, IndexError):
        return None


def _parse_tencent_line(line: str) -> dict | None:
    """Parse one Tencent JS var line into {name, latest, pct_change}."""
    parts = line.split('"')
    if len(parts) < 2:
        return None
    fields = parts[1].split("~")
    if len(fields) < 40:
        return None
    try:
        name = fields[1].strip()
        latest = float(fields[3])
        pct_change = float(fields[32])
        return {"name": name, "latest": str(latest), "pct_change": str(pct_change), "source": "腾讯财经"}
    except (ValueError, IndexError):
        return None


def collect_equity_indices(timeout: int = 10) -> dict[str, Any]:
    """抓取 A 股四大指数行情：新浪主源，腾讯备源。"""
    # 主源：新浪财经
    try:
        codes = ",".join(_SINA_INDEXES.keys())
        r = requests.get(
            f"{_SINA_BASE}{codes}",
            headers={"Referer": _SINA_REFERER, "User-Agent": USER_AGENT},
            timeout=timeout,
        )
        r.encoding = "gbk"
        rows = []
        for line in r.text.strip().split("\n"):
            parsed = _parse_sina_line(line)
            if parsed:
                rows.append(parsed)
        if rows:
            return {
                "available": True,
                "source": "新浪财经",
                "url": f"{_SINA_BASE}{codes}",
                "indices": rows,
                "error": "",
            }
    except Exception:
        pass  # 降级到腾讯

    # 备源：腾讯财经
    try:
        tx_codes = ",".join(f"s_{c}" for c in _SINA_INDEXES.keys())
        r = requests.get(
            f"{_TENCENT_BASE}{tx_codes}",
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        r.encoding = "gbk"
        rows = []
        for line in r.text.strip().split("\n"):
            parsed = _parse_tencent_line(line)
            if parsed:
                rows.append(parsed)
        if rows:
            return {
                "available": True,
                "source": "腾讯财经",
                "url": f"{_TENCENT_BASE}{tx_codes}",
                "indices": rows,
                "error": "",
            }
    except Exception as exc:
        return {
            "available": False,
            "source": "新浪财经 / 腾讯财经",
            "url": "",
            "indices": [],
            "error": f"双源均失败: {exc}",
        }

    return {
        "available": False,
        "source": "新浪财经 / 腾讯财经",
        "url": "",
        "indices": [],
        "error": "双源均失败",
    }


def collect_external_market_indicators() -> dict[str, Any]:
    """Collect all currently supported external market indicators."""
    repo = collect_chinamoney_repo_rates()
    treasury_curve = collect_chinamoney_treasury_curve()
    equity_indices = collect_equity_indices()
    return {
        "repo_rates": repo,
        "treasury_curve": treasury_curve,
        "equity_indices": equity_indices,
        "sources": [item["source"] for item in (repo, treasury_curve, equity_indices) if item.get("available")],
    }
