"""配置加载模块 —— 支持 test/prod 环境切换。

环境选择优先级（高 → 低）：
    1. 命令行 --env（generate_report.py 解析后写入环境变量 DTR_ENV）
    2. 环境变量 DTR_ENV
    3. 默认 test

config.json 为基础配置（test 环境）；config.prod.json 仅放生产差异字段
（如 api_base_url、api_key），加载时浅 merge 覆盖。Oracle 等非环境字段
不重复，单点维护。
"""

import json
import os
from pathlib import Path

# scripts/ → skill 根目录
SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_CONFIG_PATH = SKILL_DIR / "config.json"
PROD_CONFIG_PATH = SKILL_DIR / "config.prod.json"


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    """加载并合并配置。

    以 config.json 为底；若当前环境为 prod 且 config.prod.json 存在，
    用其顶层字段覆盖（浅 merge）。prod 被显式要求但配置缺失时报错，
    避免静默回退到测试配置。
    """
    if not BASE_CONFIG_PATH.exists():
        raise FileNotFoundError(f"基础配置缺失: {BASE_CONFIG_PATH}")

    config = _read_json(BASE_CONFIG_PATH)

    env = os.getenv("DTR_ENV", "test").strip().lower()
    if env == "prod":
        if not PROD_CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"DTR_ENV=prod 但未找到 {PROD_CONFIG_PATH.name}。\n"
                f"请参考 config.prod.example.json 创建该文件。"
            )
        config.update(_read_json(PROD_CONFIG_PATH))  # 浅 merge：仅覆盖顶层字段

    return config
