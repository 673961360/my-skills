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


def collect_eastmoney_equity_indices(timeout: int = 8) -> dict[str, Any]:
    """Fetch Shanghai Composite and ChiNext index quotes from Eastmoney."""
    source = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    try:
        response = requests.get(
            source,
            params={
                "fltt": "2",
                "invt": "2",
                "fields": "f12,f14,f2,f3",
                "secids": "1.000001,0.399006",
            },
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": "https://quote.eastmoney.com/",
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = []
        for row in payload.get("data", {}).get("diff", []):
            name = str(row.get("f14", "")).strip()
            latest = row.get("f2")
            pct_change = row.get("f3")
            if name and latest not in (None, "-"):
                rows.append({
                    "name": name,
                    "latest": str(latest),
                    "pct_change": str(pct_change),
                    "source": "东方财富行情中心",
                })
        return {
            "available": bool(rows),
            "source": "东方财富行情中心",
            "url": source,
            "indices": rows,
            "error": "" if rows else "未解析到目标权益指数",
        }
    except Exception as exc:
        return {
            "available": False,
            "source": "东方财富行情中心",
            "url": source,
            "indices": [],
            "error": str(exc),
        }


def collect_external_market_indicators() -> dict[str, Any]:
    """Collect all currently supported external market indicators."""
    repo = collect_chinamoney_repo_rates()
    treasury_curve = collect_chinamoney_treasury_curve()
    equity_indices = collect_eastmoney_equity_indices()
    return {
        "repo_rates": repo,
        "treasury_curve": treasury_curve,
        "equity_indices": equity_indices,
        "sources": [item["source"] for item in (repo, treasury_curve, equity_indices) if item.get("available")],
    }
