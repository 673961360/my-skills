"""敏感字段脱敏 —— 产品代码 / 产品名称。

在大模型分析前对产品信息脱敏，避免真实产品代码与名称外泄。

规则：
- 产品代码：前两位替换为 **（CJ5381 → **5381）
- 产品名称：
  1) "创金"、"合信" 各替换为 *
  2) 中英文括号 () （） 内容脱敏：闭合括号保留两端 (内容)→(*)；
     未闭合括号（无右括号）整体替换为 *
"""

import re

# 左括号(中/英) + 内容(非右括号字符) + 可选右括号(中/英)；未闭合时吃到行尾
_PAREN_PATTERN = re.compile(r"[\(（][^)）]*[)）]?")
# 品牌关键词
_BRAND_PATTERN = re.compile(r"创金|合信")


def _mask_paren(match: "re.Match") -> str:
    """括号块脱敏：闭合保留两端括号 (内容)→(*)；未闭合整体吞成 *。"""
    block = match.group(0)
    if block[-1] in ")）":  # 闭合：保留括号，仅内容换 *
        return f"{block[0]}*{block[-1]}"
    return "*"  # 未闭合：整体替换为 *


def mask_product_code(code):
    """产品代码脱敏：前两位换成 **。非字符串原样返回。"""
    if not isinstance(code, str):
        return code
    return "**" + code[2:]


def mask_product_name(name):
    """产品名称脱敏：创金/合信 换 *；括号内容——闭合 (x)→(*)，未闭合→*。非字符串原样返回。"""
    if not isinstance(name, str):
        return name
    name = _PAREN_PATTERN.sub(_mask_paren, name)
    name = _BRAND_PATTERN.sub("*", name)
    return name


def mask_product_fields(record: dict) -> dict:
    """对单条记录的产品代码/产品名称就地脱敏，返回同一 dict。"""
    if "产品代码" in record:
        record["产品代码"] = mask_product_code(record["产品代码"])
    if "产品名称" in record:
        record["产品名称"] = mask_product_name(record["产品名称"])
    return record
